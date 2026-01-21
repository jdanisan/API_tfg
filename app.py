from flask import Flask, jsonify
import requests
from bs4 import BeautifulSoup
import unicodedata
from urllib.parse import urljoin
app = Flask(__name__)

BASE_DOMAIN = "https://observatorioprecios.es"
URL_BASE = "https://observatorioprecios.es/alimentos-frescos/patata"

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
        "patata", "acelga", "calabacin", "cebolla", "judia-verde-plana",
        "lechuga-romana", "pimiento-verde", "tomate-redondo-liso",
        "zanahoria", "limon", "manzana-golden", "clementina",
        "naranja-tipo-navel", "pera-de-agua-o-blanquilla", "platano",
    ]
    
    seleccion_normalizada = [normalizar(p) for p in seleccion]

    resultado = []

    # Construir URLs directamente
    for producto in seleccion_normalizada:
        url_producto = urljoin(URL_BASE, producto + "/")

        try:
            r = requests.get(url_producto, timeout=10)
            if r.status_code != 200:
                continue
        except requests.RequestException:
            continue

        soup_producto = BeautifulSoup(r.text, "html.parser")

        tabla = soup_producto.find("table", class_="anio-precios")
        if not tabla:
            continue

        celdas = tabla.find_all("td")
        if not celdas:
            continue

        thead = tabla.find("thead")
        if thead:
            num_cols = len(thead.find_all("th"))
        else:
            num_cols = 3  # fallback

        semanas = []
        precios = []

        for i in range(0, len(celdas), num_cols):
            fila = celdas[i:i + num_cols]
            if len(fila) < 2:
                continue

            fecha = fila[0].get_text(strip=True)

            try:
                precio_p = float(
                    fila[1].get_text(strip=True)
                    .replace("€", "")
                    .replace(",", ".")
                )
            except ValueError:
                precio_p = 0.0

            try:
                precio_m = float(
                    fila[2].get_text(strip=True)
                    .replace("€", "")
                    .replace(",", ".")
                )
            except (ValueError, IndexError):
                precio_m = 0.0

            semanas.append(fecha)
            precios.extend([precio_p, precio_m])

        resultado.append({
            "Producto": producto,
            "URL": url_producto,
            "Semanas": semanas,
            "Precios": precios
        })

    return jsonify(resultado)

if __name__ == "__main__":
    app.run(debug=True)