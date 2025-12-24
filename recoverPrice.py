from flask import Flask, render_template, request, redirect, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
db = SQLAlchemy(app)

def obtener_datos_agricolas():
    url_base = "https://observatorioprecios.es/alimentos-frescos"
    seleccion = [
        "patata", "acelga", "calabacin", "cebolla", "judia-verde-plana",
        "lechuga-romana", "pimiento-verde", "tomate-redondo-liso",
        "zanahoria", "limon", "manzana-golden", "clementina",
        "naranja-tipo-navel", "pera-de-agua-o-blanquilla", "platano",
    ]

    response = requests.get(url_base)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    productos_scrapeados = {}
    enlaces_productos = []

    # ✔ Buscar enlaces correctamente
    for a in soup.select(".wrapper a"):
        href = a.get("href", "")
        nombre_producto = href.strip("/").split("/")[-1]
        if nombre_producto in seleccion:
            enlaces_productos.append(nombre_producto)

    # ✔ Scraping de cada producto
    for producto in enlaces_productos:
        url_producto = f"{url_base}/{producto}"
        html_producto = requests.get(url_producto).text
        soup_producto = BeautifulSoup(html_producto, "html.parser")

        # ✔ Encontrar la tabla correcta
        tabla = None
        for t in soup_producto.find_all("table"):
            if t.find("thead") and t.find("tbody"):
                tabla = t
                break

        if not tabla:
            continue

        productos_scrapeados[producto] = {}

        for fila in tabla.find_all("tr")[1:]:
            celdas = fila.find_all("td")
            if len(celdas) >= 2:
                semana = celdas[0].text.strip()
                precio = celdas[1].text.strip().replace(",", ".")
                try:
                    productos_scrapeados[producto][semana] = float(precio)
                except:
                    productos_scrapeados[producto][semana] = None

    return productos_scrapeados

# Crear la base de datos
with app.app_context():
    db.create_all()

# Ejecutar la app
if __name__ == "__main__":
    app.run(debug=True)