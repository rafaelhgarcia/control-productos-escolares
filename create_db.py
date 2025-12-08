import os
from app import app, db
from werkzeug.security import generate_password_hash

# Importamos TODOS los modelos definidos en app.py para que db.create_all() los vea
from app import User, Product, Bodega, Supervisor, Escuela 

with app.app_context():
    # 1. Crear todas las tablas: Users, Products, Bodegas, Supervisors, Escuelas
    db.create_all()
    print(">>> Base de datos y TODAS las tablas creadas/verificadas exitosamente.")

    # 2. Verificar y crear el usuario admin
    admin_user = User.query.filter_by(username='admin').first()
    
    if not admin_user:
        print(">>> Creando usuario administrador...")
        hashed_pw = generate_password_hash('admin123', method='pbkdf2:sha256')
        
        new_admin = User(
            username='admin',
            email='admin@escuela.com',
            password_hash=hashed_pw,
            is_admin=True
        )
        
        db.session.add(new_admin)
        db.session.commit()
        print(">>> Usuario admin creado exitosamente.")
    else:
        print(">>> El usuario admin ya existe.")
