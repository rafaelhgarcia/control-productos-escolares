import os
# Importamos la aplicación Flask, el objeto db y el modelo User
# Asegúrate de que estos están disponibles para ser importados desde app.py
from app import app, db, User 
from werkzeug.security import generate_password_hash
from dotenv import load_dotenv # Si usas variables de entorno localmente, aunque en Render usa su propio sistema

# Configuración de Contraseña de Administrador
# ----------------------------------------------------
# IMPORTANTE: Reemplaza 'tu_password_segura_aqui' con la contraseña que deseas usar
# para el usuario 'admin'. Este script solo se ejecutará una vez.
# Es altamente recomendado usar una Variable de Entorno en Render para esta contraseña,
# pero para la primera vez, puedes dejarla hardcodeada temporalmente para probar.
ADMIN_PASSWORD = os.environ.get('ADMIN_INIT_PASSWORD', 'admin123')
ADMIN_USERNAME = 'admin'
# ----------------------------------------------------

def initialize_database():
    """
    Función para crear todas las tablas e insertar el usuario administrador.
    """
    with app.app_context():
        print("--- Iniciando Configuración de Base de Datos ---")

    try:
        db.create_all()
        print("Tablas creadas/verificadas exitosamente (db.create_all()).")
    except Exception as e:
        print(f"ERROR CRÍTICO: Fallo al crear tablas. Verifica la conexión a DB. Error: {e}")
        return

    admin_user = User.query.filter_by(username=ADMIN_USERNAME).first()

    if not admin_user:
        password_hash = generate_password_hash(ADMIN_PASSWORD)
        
        new_admin = User(
            username=ADMIN_USERNAME,
            email='admin@control-escolar.com', 
            password_hash=password_hash,
            is_admin=True 
        )
        
        db.session.add(new_admin)
        db.session.commit()
        print(f"Usuario '{ADMIN_USERNAME}' creado.")
        print(f"¡IMPORTANTE! Contraseña de inicio de sesión: {ADMIN_PASSWORD}")
    else:
        print(f"Usuario '{ADMIN_USERNAME}' ya existe. No se creó uno nuevo.")
        
    print("--- Configuración de Base de Datos Terminada ---")
        
        # 1. Crear todas las tablas
        # Esto le dice a SQLAlchemy que cree las tablas definidas en todos los modelos (User, Producto, etc.)
        #try:
         #   db.create_all()
        #    print("Tablas creadas exitosamente (db.create_all()).")
       # except Exception as e:
         #   print(f"Error al crear tablas: {e}")
            # Si esto falla, verifica la variable de entorno DATABASE_URL en Render.

        # 2. Verificar y crear el usuario administrador si no existe
       # admin_user = User.query.filter_by(username=ADMIN_USERNAME).first()

       # if not admin_user:
            # Genera el hash de la contraseña. 
            # ASEGÚRATE de que el 'method' (default: 'pbkdf2:sha256') coincida con el que usa tu app.py si es diferente.
          #  password_hash = generate_password_hash(ADMIN_PASSWORD)
            
           # new_admin = User(
            #    username=ADMIN_USERNAME,
                # Email o cualquier otro campo requerido por tu modelo User
             #   email='admin@control-escolar.com', 
              #  password_hash=password_hash,
               # is_admin=True # Asegúrate de que tu modelo User tiene este campo
          #  )
            
          #  db.session.add(new_admin)
          #  db.session.commit()
          #  print(f"Usuario '{ADMIN_USERNAME}' creado.")
          #  print(f"¡IMPORTANTE! Usa la contraseña: {ADMIN_PASSWORD}")
       # else:
         #   print(f"Usuario '{ADMIN_USERNAME}' ya existe. No se creó uno nuevo.")
            
       # print("--- Configuración de Base de Datos Terminada ---")#

if __name__ == '__main__':
    initialize_database()
