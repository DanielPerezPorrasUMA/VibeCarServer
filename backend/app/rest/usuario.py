import os
from flask import jsonify, make_response, request
from flask_pymongo import PyMongo, ObjectId
from google.oauth2 import id_token
from google.auth.transport import requests
from ..app import app
from .trayecto import actualizar_conductor
from .utils import escape_regex
import cloudinary
import cloudinary.uploader
import cloudinary.api

try:
    # Fichero de configuración encontrado - lo usamos
    from .config import *
    cloudinary.config( 
        cloud_name = cloud_name, 
        api_key = cloud_api_key, 
        api_secret = cloud_api_secret 
    )
except ModuleNotFoundError:
    # Fichero de configuración no encontrado - consultamos variables de entorno
    cloudinary.config( 
        cloud_name = os.environ["CLOUD_NAME"], 
        api_key = os.environ["CLOUD_API_KEY"], 
        api_secret = os.environ["CLOUD_API_SECRET"] 
    )
    google_oauth_client_id = os.environ["GOOGLE_OAUTH_CLIENT_ID"]

mongo = PyMongo(app)
usuario = mongo.db.usuario
trayecto = mongo.db.trayecto
reserva = mongo.db.reserva
valoraciones = mongo.db.valoraciones



# ---- ENDPOINTS -------------------------------------------------------------------------


@app.route("/api/v1/usuarios", methods=["POST"])
def create_usuario():
    if request.is_json:
        datos = request.get_json()
        try:
            res = usuario.insert_one({
                "nombre": str(datos["nombre"]),
                "apellidos": str(datos["apellidos"]),
                "email": str(datos["email"]),
                "telefono": str(datos["telefono"]),
                "link_paypal": str(datos["link_paypal"]),
                "url_foto_perfil": str(datos["url_foto_perfil"]),
                "rol": int(datos["rol"])
            })
            return jsonify(msg="Usuario creado", new_id=str(res.inserted_id))

        except:
            respuesta = jsonify(msg="Petición no válida, faltan campos o no son del tipo correcto")
            return make_response(respuesta, 400)

    else:
        respuesta = jsonify(msg="Petición no válida, se requiere JSON")
        return make_response(respuesta, 400)

@app.route("/api/v1/usuarios", methods=["GET"])
def get_usuarios():

    cursor = None
    search = request.args.get("search")
    if search is not None:
        regex = {
            "$regex": escape_regex(search),
            "$options": "i"
            }
        cursor = usuario.find({"$or":
        [
            {"nombre": regex},
            {"apellidos": regex}
        ]})
    else:
        cursor = usuario.find()


    resultado = []
    for u in cursor:
        u["_id"] = str(u["_id"])
        resultado.append(u)
    return jsonify(resultado)

@app.route("/api/v1/usuarios/<id>", methods=["GET"])
def get_usuario(id):
    resultado = usuario.find_one({"_id" : ObjectId(id)})
    if resultado is not None:
        resultado["_id"] = str(resultado["_id"])
        return jsonify(resultado)
    else:
        respuesta = jsonify(msg="No existe ningún usuario con id = %s" % id)
        return make_response(respuesta, 404)

@app.route("/api/v1/usuarios/email/<email>", methods=["GET"])
def get_usuario_by_email(email):
    resultado = usuario.find_one({"email" : email})
    if resultado is not None:
        resultado["_id"] = str(resultado["_id"])
        return jsonify(resultado)
    else:
        respuesta = jsonify(msg="No existe ningún usuario con email = %s" % email)
        return make_response(respuesta, 404)

@app.route("/api/v1/login", methods=["POST"])
def login():
    if request.is_json:
        datos = request.get_json()
        if "token" in datos:
            try:
                token = id_token.verify_oauth2_token(datos["token"],
                    requests.Request(), google_oauth_client_id, 10)

                mi_usuario = usuario.find_one({ "email": token["email"] })
                if mi_usuario is not None:
                    mi_usuario["_id"] = str(mi_usuario["_id"])
                    return jsonify(mi_usuario)
                else:
                    return jsonify(msg="Usuario no encontrado"), 404

            except Exception as ex:
                respuesta = jsonify(msg="Token no válido")
                print(ex.args)
                return make_response(respuesta, 406)
        else:
            respuesta = jsonify(msg="Petición no válida, faltan campos o no son del tipo correcto")
            return make_response(respuesta, 400)

    else:
        respuesta = jsonify(msg="Petición no válida, se requiere JSON")
        return make_response(respuesta, 400)

@app.route("/api/v1/usuarios/<id>", methods=["PUT"])
def update_usuario(id):
    oid = ObjectId(id)
    resultado = usuario.find_one({"_id" : oid})
    if resultado is not None:
        if request.is_json:
            datos = request.get_json()
            nuevos_valores = {}
            try:
                if "nombre" in datos:
                    nuevos_valores["nombre"] = str(datos["nombre"])
                if "apellidos" in datos:
                    nuevos_valores["apellidos"] = str(datos["apellidos"])
                if "email" in datos:
                    nuevos_valores["email"] = str(datos["email"])
                if "telefono" in datos:
                    nuevos_valores["telefono"] = str(datos["telefono"])
                if "link_paypal" in datos:
                    nuevos_valores["link_paypal"] = str(datos["link_paypal"])
                if "url_foto_perfil" in datos:
                    nuevos_valores["url_foto_perfil"] = str(datos["url_foto_perfil"])
                if "rol" in datos:
                    nuevos_valores["rol"] = int(datos["rol"])
            except Exception:
                respuesta = jsonify(msg="Petición no válida, hay campos que no son del tipo correcto")
                return make_response(respuesta, 400)

            usuario.update_one({"_id": oid}, {"$set": nuevos_valores})

            user = usuario.find_one({"_id" : oid})
            valoraciones.update_many({"usuarioQueValora" : oid}, {"$set" : {
                "nombre" : user["nombre"],
                "apellidos" : user["apellidos"],
                "url_foto_perfil" : user["url_foto_perfil"]
            }})
            cliente = { "_id" : user["_id"], "nombre" : user["nombre"], "url_foto_perfil" : user["url_foto_perfil"]}
            reserva.update_many({"cliente._id" : oid}, { "$set" : {
                "cliente" : cliente
            }})
            trayecto.update_many({"conductor._id" : oid}, { "$set" : {
                "conductor" : cliente
            }})

            # Actualizar datos redundantes
            actualizar_conductor(oid)

            return jsonify(msg='Usuario actualizado')

        else:
            respuesta = jsonify(msg="Petición no válida, se requiere JSON")
            return make_response(respuesta, 400)
    else:
        respuesta = jsonify(msg="No existe ningún usuario con id = %s" % id)
        return make_response(respuesta, 404)

@app.route("/api/v1/usuarios/<id>", methods=["DELETE"])
def delete_usuario(id):
    oid = ObjectId(id)
    resultado = usuario.find_one({"_id" : oid})
    if resultado is not None:
        usuario.delete_one({"_id": oid})

        # Cascada
        valoraciones.delete_many({"usuarioQueValora" : oid})
        valoraciones.delete_many({"usuarioValorado" : oid})
        reserva.delete_many({"cliente._id" : oid})
        trayecto.delete_many({"conductor._id" : oid})
        

        return jsonify(msg='Usuario borrado')
    else:
        respuesta = jsonify(msg="No existe ningún usuario con id = %s" % id)
        return make_response(respuesta, 404)

@app.route("/api/v1/imagen",methods=["POST"])
def uploadImg():
    img = request.files["img"]
    res = cloudinary.uploader.upload(img)
    print(res["url"])
    return jsonify({"msg":"Imagen Subida a la url " + str(res["url"])})

@app.route("/api/v1/usuarios/image/<id>", methods=["PUT"])
def uploadProfilePic(id):
    oid = ObjectId(id)
    img = request.files['file']
    # print(img.filename)
    if True: # (img.filename).endswith(".jpg", ".png"):
        res = cloudinary.uploader.upload(img)
        nuevos_valores = {}
        nuevos_valores["url_foto_perfil"] = str(res["url"])
        usuario.update_one({"_id": oid}, {"$set": nuevos_valores})

        valoraciones.update_many({"usuarioQueValora" : oid}, {"$set" : {
            "url_foto_perfil" : str(res["url"])
        }})
        reserva.update_many({"cliente._id" : oid}, { "$set" : {
            "cliente.url_foto_perfil" : str(res["url"])
        }})
        trayecto.update_many({"conductor._id" : oid}, { "$set" : {
            "conductor.url_foto_perfil" : str(res["url"])
        }})

        return jsonify({"msg":str(res["url"])})
    else:
        return({"msg":"El archivo no es una imagen"})