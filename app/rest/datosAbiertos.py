from flask import request, jsonify, make_response
from flask_pymongo import PyMongo, ObjectId
from ..app import app
from .utils import usuario_existe, escape_regex
from urllib.request import urlopen
import json, geojson

mongo = PyMongo(app)
db = mongo.db


aparcamientos_url = "https://datosabiertos.malaga.eu/recursos/aparcamientos/ocupappublicosmun/ocupappublicosmunfiware.json"
incidencias_url = "https://opendata.arcgis.com/datasets/a64659151f0a42c69a38563e9d006c6b_0.geojson"

datos_aparcamientos = []
datos_incidencias = []

@app.route("/api/v1/aparcamientos", methods=['GET'])
def getAparcamientos():

    return "HELLO WORLD"

@app.route("/api/v1/incidencias/<localidad>", methods=['GET'])
def getIncidencias(localidad):
    global datos_incidencias

    if len(datos_incidencias)==0:
        response = urlopen(incidencias_url)
        data = response.read()
        json_data = geojson.loads(data)
        datos_incidencias=json_data

    datos = []

    for feature in json_data["features"]:
        if localidad.lower() == feature["properties"]["poblacion"].lower():     
            datos.append(feature)

    return jsonify(datos)