import firebase_admin
from firebase_admin import credentials, db
from flask import Flask, jsonify
import requests
from bs4 import BeautifulSoup
import unicodedata
from urllib.parse import urljoin

# Inicializar Firebase Admin
cred = credentials.Certificate('ruta/a/tu/archivo/firebase-adminsdk.json')
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://<tu-database>.firebaseio.com/'  # Cambia por tu URL de Firebase Realtime Database
})

app = Flask(__name__)

BASE_DOMAIN = "https://observatorioprecios.es"
URL_BASE = "https://observatorioprecios.es/alimentos-frescos"

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

    # Obtener la página principal
    response = requests.get(URL_BASE)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    # Encontrar enlaces a productos relevantes
    enlaces_productos = set()
    for a in soup.find_all("a", href=True):
        texto = normalizar(a.get_text())
        if texto and any(prod in texto for prod in seleccion_normalizada):
            enlaces_productos.add(urljoin(BASE_DOMAIN, a["href"]))

    resultado = []

    # Scrapear datos de cada producto
    for url_producto in enlaces_productos:
        producto_nombre = next((prod for prod in seleccion_normalizada if prod in url_producto), None)
        

        r = requests.get(url_producto)
        soup_producto = BeautifulSoup(r.text, "html.parser")

        t = soup_producto.find("table", class_="anio-precios")
        if not t:
            continue

        # Manejar tablas no estándar (estructura plana de <td>)
        celdas = t.find_all("td")
        if not celdas:
            continue

        # Detectar el numero de columnas dinámicamente desde <thead>
        thead = t.find("thead")
        if thead:
            num_cols = len(thead.find_all("th"))
        else:
            num_cols = 3  # por defecto si no hay thead

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

        # Subir los datos a Firebase Realtime Database
        for semana, precio_p, precio_m in zip(semanas, precios[::2], precios[1::2]):
            producto_ref = db.reference(f'productos/{producto_nombre}')  # La ruta en Firebase
            producto_ref.push({
                'semana': semana,
                'precio_p': precio_p,
                'precio_m': precio_m
            })

        resultado.append({
            "Producto": producto_nombre,
            "Precios": precios,
            "Semanas": semanas
        })

    return jsonify({"status": "Datos guardados exitosamente en Firebase Realtime Database"})

if __name__ == "__main__":
    app.run()
