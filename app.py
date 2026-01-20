from flask import Flask, jsonify
import requests
from bs4 import BeautifulSoup
import unicodedata
from urllib.parse import urljoin
app = Flask(__name__)

BASE_DOMAIN = "https://observatorioprecios.es"
URL_BASE = "https://web.archive.org/web/20250803151436/https://observatorioprecios.es/alimentos-frescos/"

def normalizar(texto):
    if texto is None:
        return None
    texto = texto.lower().strip()
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    return texto

@app.route("/obtener-datos")
def obtener_datos_agricolas():
    seleccion = [
        "patata", "acelga", "calabacin", "cebolla", "judia",
        "lechuga", "pimiento", "tomate",
        "zanahoria", "limon", "manzana", "clementina",
        "naranja", "pera", "platano",
    ]
    seleccion_normalizada = [normalizar(p) for p in seleccion]

    # Get main page
    response = requests.get(URL_BASE)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    # Find all product links matching selection
    enlaces_productos = set()
    for a in soup.find_all("a", href=True):
        texto = normalizar(a.get_text())
        if texto and any(prod in texto for prod in seleccion_normalizada):
            enlaces_productos.add(urljoin(BASE_DOMAIN, a["href"]))

    resultado = []

    # Scrape each product page
    for url_producto in enlaces_productos:
        producto_nombre = next((prod for prod in seleccion_normalizada if prod in url_producto), None)
        

        r = requests.get(url_producto)
        soup_producto = BeautifulSoup(r.text, "html.parser")

        t = soup_producto.find("table", class_="anio-precios")
        if not t:
            continue

        # Handle non-standard table (flat <td> structure)
        celdas = t.find_all("td")
        if not celdas:
            continue

        # Detect number of columns dynamically from <thead>
        thead = t.find("thead")
        if thead:
            num_cols = len(thead.find_all("th"))
        else:
            num_cols = 3  # fallback

        semanas = []
        precios = []

        for i in range(0, len(celdas), num_cols):
            fila = celdas[i:i+num_cols]
            if len(fila) < 2:
                continue

            fecha = fila[0].get_text(strip=True)
            try:
                precio_p = float(fila[1].get_text(strip=True).replace("€","").replace(",","."))
            except:
                precio_p = 0.0

            try:
                precio_m = float(fila[2].get_text(strip=True).replace("€","").replace(",","."))
            except:
                precio_m = 0.0

            semanas.append(fecha)
            precios.extend([precio_p, precio_m])

        resultado.append({
            "Producto": producto_nombre,
            "Precios": precios,
            "Semanas": semanas
        })

    return jsonify(resultado)

if __name__ == "__main__":
    app.run()
