import json
import random
import hashlib
import mysql.connector
import base64
import shutil
from datetime import datetime
from pathlib import Path
from bottle import route, run, template, post, request, static_file
import bcrypt
import secrets
from werkzeug.utils import secure_filename

def loadDatabaseSettings(pathjs):
	pathjs = Path(pathjs)
	sjson = False
	if pathjs.exists():
		with pathjs.open() as data:
			sjson = json.load(data)
	return sjson
	
"""
function loadDatabaseSettings(pathjs):
	string = file_get_contents(pathjs);
	json_a = json_decode(string, true);
	return json_a;

"""
def getToken():
    return secrets.token_urlsafe(32)  # 32 bytes = 43 caracteres URL-safe

"""
*/ 
# Registro
/*
 * Este Registro recibe un JSON con el siguiente formato
 * 
 * : 
 *		"uname": "XXX",
 *		"email": "XXX",
 * 		"password": "XXX"
 * 
 * */
"""
@post('/Registro')
def Registro():
	dbcnf = loadDatabaseSettings('db.json');
	db = mysql.connector.connect(
		host='localhost', port = dbcnf['port'],
		database = dbcnf['dbname'],
		user = dbcnf['user'],
		password = dbcnf['password']
	)
	####/ obtener el cuerpo de la peticion
	if not request.json:
		return {"R":-1}
	R = 'uname' in request.json and 'email' in request.json and 'password' in request.json
	# TODO checar si estan vacio los elementos del json
	if not R:
		return {"R":-1}
	# TODO validar correo en json
	# TODO Control de error de la DB
	R = False
	try:
		with db.cursor() as cursor:
			hashed_password = bcrypt.hashpw(request.json["password"].encode('utf-8'), bcrypt.gensalt())
			cursor.execute('INSERT INTO Usuario VALUES (null, %s, %s, %s)',(request.json["uname"], request.json["email"], hashed_password));
			R = cursor.lastrowid
			db.commit()
		db.close()
	except Exception as e:
		print(e) 
		return {"R":-2}
	return {"R":0,"D":R}




"""
/*
 * Este Registro recibe un JSON con el siguiente formato
 * 
 * : 
 *		"uname": "XXX",
 * 		"password": "XXX"
 * 
 * 
 * Debe retornar un Token 
 * */
"""

@post('/Login')
def Login():
	dbcnf = loadDatabaseSettings('db.json');
	db = mysql.connector.connect(
		host='localhost', port = dbcnf['port'],
		database = dbcnf['dbname'],
		user = dbcnf['user'],
		password = dbcnf['password']
	)
	###/ obtener el cuerpo de la peticion
	if not request.json:
		return {"R":-1}
	######/
	R = 'uname' in request.json  and 'password' in request.json
	# TODO checar si estan vacio los elementos del json
	if not R:
		return {"R":-1}
	
	# TODO validar correo en json
	# TODO Control de error de la DB
	R = False
	try:
		with db.cursor() as cursor:
			print('SELECT id, password FROM Usuario WHERE uname = %s')
			cursor.execute('SELECT id, password FROM Usuario WHERE uname = %s', (request.json["uname"],));
			R = cursor.fetchall()
	except Exception as e: 
		print(e)
		db.close()
		return {"R":-2}
	
	# Verificar password con bcrypt
	if not R or not bcrypt.checkpw(request.json["password"].encode('utf-8'), R[0][1].encode('utf-8')):
		db.close()
		return {"R":-3}
	
	T = getToken();
	#file_put_contents('/tmp/log','insert into AccesoToken values('.R[0].',"'.T.'",now())');
	with open("/tmp/log","a") as log:
		log.write(f'Delete from AccesoToken where id_Usuario = "{R[0][0]}"\n')
		log.write(f'insert into AccesoToken values({R[0][0]},"{T}",now())\n')
	
	try:
		with db.cursor() as cursor:
			cursor.execute('DELETE FROM AccesoToken WHERE id_Usuario = %s', (R[0][0],));
			cursor.execute('INSERT INTO AccesoToken VALUES (%s, %s, NOW(), DATE_ADD(NOW(), INTERVAL 1 HOUR))', (R[0][0], T));
			db.commit()
			db.close()
			return {"R":0,"D":T}
	except Exception as e:
		print(e)
		db.close()
		return {"R":-4}

"""
/*
 * Este subir imagen recibe un JSON con el siguiente formato
 * 
 * 
 * 		"token: "XXX"
 *		"name": "XXX",
 * 		"data": "XXX",
 * 		"ext": "PNG"
 * 
 * 
 * Debe retornar codigo de estado
 * */
"""
@post('/Imagen')
def Imagen():
	#Directorio
	tmp = Path('tmp')
	if not tmp.exists():
		tmp.mkdir()
	img = Path('img')
	if not img.exists():
		img.mkdir()
	
	###/ obtener el cuerpo de la peticion
	if not request.json:
		return {"R":-1}
	######/
	R = 'name' in request.json  and 'data' in request.json and 'ext' in request.json  and 'token' in request.json
	# TODO checar si estan vacio los elementos del json
	if not R:
		return {"R":-1}
	
	dbcnf = loadDatabaseSettings('db.json');
	db = mysql.connector.connect(
		host='localhost', port = dbcnf['port'],
		database = dbcnf['dbname'],
		user = dbcnf['user'],
		password = dbcnf['password']
	)

	# Validar si el usuario esta en la base de datos
	TKN = request.json['token'];
	
	R = False
	try:
		with db.cursor() as cursor:
			cursor.execute('SELECT id_Usuario FROM AccesoToken WHERE token = %s AND expira > NOW()', (TKN,));
			R = cursor.fetchall()
	except Exception as e: 
		print(e)
		db.close()
		return {"R":-2}
	
	
	id_Usuario = R[0][0];
	with open(f'tmp/{id_Usuario}',"wb") as imagen:
		imagen.write(base64.b64decode(request.json['data'].encode()))
	
	############################
	############################
	# Guardar info del archivo en la base de datos
	try:
		with db.cursor() as cursor:
			cursor.execute('INSERT INTO Imagen VALUES (null, %s, "img/", %s)',(request.json["name"], id_Usuario));
			cursor.execute('SELECT max(id) as idImagen FROM Imagen WHERE id_Usuario = %s', (id_Usuario,));
			R = cursor.fetchall()
			idImagen = R[0][0];
			cursor.execute('UPDATE Imagen SET ruta = %s WHERE id = %s',(f"img/{idImagen}.{request.json['ext']}", idImagen));
			db.commit()
			# Mover archivo a su nueva locacion
			ruta_destino = f'img/{idImagen}.{request.json["ext"]}'
			# Validar que no haya path traversal
			if '..' in ruta_destino or not ruta_destino.startswith('img/'):
				return {"R": -1, "error": "Ruta de destino inválida"}
			shutil.move(f'tmp/{id_Usuario}', ruta_destino)
			return {"R":0,"D":idImagen}
	except Exception as e: 
		print(e)
		db.close()
		return {"R":-3}
	
"""
/*
 * Este Registro recibe un JSON con el siguiente formato
 * 
 * : 
 * 		"token: "XXX",
 * 		"id": "XXX"
 * 
 * 
 * Debe retornar un Token 
 * */
"""

@post('/Descargar')
def Descargar():
    dbcnf = loadDatabaseSettings('db.json')
    db = mysql.connector.connect(
        host='localhost', port=dbcnf['port'],
        database=dbcnf['dbname'],
        user=dbcnf['user'],
        password=dbcnf['password']
    )
    
    if not request.json:
        return {"R": -1}
    
    R = 'token' in request.json and 'id' in request.json  
    if not R:
        return {"R": -1}
    
    TKN = request.json['token']
    idImagen = request.json['id']
    
    # Validar token y obtener ID de usuario
    try:
        with db.cursor() as cursor:
            cursor.execute('SELECT id_Usuario FROM AccesoToken WHERE token = %s AND expira > NOW()', (TKN,));
            R = cursor.fetchall()
    except Exception as e: 
        print(e)
        db.close()
        return {"R": -2}
    
    if not R:
        db.close()
        return {"R": -2, "error": "Token inválido"}
    
    id_usuario = R[0][0]
    
    # VERIFICACIÓN CRÍTICA: ¿Pertenece esta imagen al usuario?
    try:
        with db.cursor() as cursor:
            cursor.execute('''
                SELECT name, ruta 
                FROM Imagen 
                WHERE id = %s AND id_Usuario = %s
            ''', (idImagen, id_usuario));
            R = cursor.fetchall()
    except Exception as e: 
        print(e)
        db.close()
        return {"R": -3}
    
    if not R:
        db.close()
        return {"R": -3, "error": "Imagen no encontrada o sin permisos"}
    
    # Path traversal protection
    ruta_archivo = R[0][1]
    if not ruta_archivo.startswith('img/') or '..' in ruta_archivo:
        return {"R": -1, "error": "Ruta de archivo inválida"}
    
    ruta_completa = Path(ruta_archivo)
    if not ruta_completa.exists():
        return {"R": -1, "error": "Archivo no encontrado"}
    
    db.close()
    return static_file(str(ruta_completa), root=Path(".").resolve())

if __name__ == '__main__':
    run(
        host='0.0.0.0', 
        port=8080, 
        debug=True,
        server='cheroot',
        certfile='/home/edgar/apitopicos/insecure-webapi/certs/142.93.76.148.pem',
        keyfile='/home/edgar/apitopicos/insecure-webapi/certs/142.93.76.148-key.pem'
    )

