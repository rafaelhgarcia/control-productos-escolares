from app import app, db, User
from werkzeug.security import generate_password_hash

# Esto permite interactuar con la base de datos dentro del contexto de la app
with app.app_context():
    # 1. Crear las tablas de la base de datos
    db.create_all()
    print(">>> Base de datos y tablas creadas exitosamente.")

    # 2. Verificar si ya existe el usuario admin para no duplicarlo
    existing_admin = User.query.filter_by(username='admin').first()
    
    if not existing_admin:
        print(">>> Creando usuario administrador...")
        # Generar el hash de la contraseña
        hashed_password = generate_password_hash('admin123', method='pbkdf2:sha256')
        
        # Crear el usuario (Asegúrate de que estos campos coincidan con tu modelo en app.py)
        # Basado en tus logs, tu tabla tiene: username, email, password_hash, is_admin
        new_admin = User(
            username='admin', 
            email='admin@escuela.com',  # Pon un email cualquiera
            password_hash=hashed_password, 
            is_admin=True
        )
        
        db.session.add(new_admin)
        db.session.commit()
        print(">>> Usuario 'admin' creado con contraseña 'admin123'.")
    else:
        print(">>> El usuario admin ya existe. No se realizaron cambios.")
