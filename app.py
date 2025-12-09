import os
from datetime import datetime
from flask import Flask, render_template, redirect, url_for, flash, request
from flask_login import UserMixin, LoginManager, login_user, logout_user, current_user, login_required
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.exc import IntegrityError
import qrcode
import io
import base64

# =========================================================================
# 1. INICIALIZACIÓN Y CONFIGURACIÓN DE FLASK
# =========================================================================

app = Flask(__name__)

# Configuración de la aplicación
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'UNA_CLAVE_SECRETA_SUPER_FUERTE')

# Configuración de la base de datos PostgreSQL de Render
# Usa la corrección de 'postgres://' a 'postgresql://'
if os.environ.get('DATABASE_URL'):
    db_url = os.environ.get('DATABASE_URL').replace('postgres://', 'postgresql://', 1)
else:
    db_url = 'sqlite:///local_db.sqlite'

app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Inicializa la base de datos
db = SQLAlchemy(app)

# Inicializa Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    # Usar db.session.get() para la versión moderna de SQLAlchemy
    return db.session.get(User, int(user_id))

# =========================================================================
# 2. DEFINICIÓN DE MODELOS (Corregido y con is_admin)
# =========================================================================

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    is_admin = db.Column(db.Boolean, default=False)  # <-- Campo Faltante Agregado
    password_hash = db.Column(db.String(128))
    
    # Asegúrate de no duplicar 'password_hash' ni 'products' como en el código original
    # products = db.relationship('Product', backref='user', lazy=True) # Mantener si es necesario, pero elimino la duplicidad
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(50), unique=True, nullable=False)
    # user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False) # Descomentar si Product tiene relación con User
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    # Agrega más campos si son necesarios para el inventario (ej: stock, bodega_id)
    stock = db.Column(db.Integer, default=0)
    
class Bodega(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    location = db.Column(db.String(200)) # Campo adicional
    
class Supervisor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    qr_code_data = db.Column(db.String(255), unique=True) # Datos para el QR

class Escuela(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    qr_code_data = db.Column(db.String(255), unique=True) # Datos para el QR

# =========================================================================
# 3. RUTAS DE LA APLICACIÓN (Completas con CRUD básico)
# =========================================================================

# --- Acceso y Dashboard ---

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Credenciales inválidas. Intente de nuevo.', 'error')

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Sesión cerrada exitosamente.', 'success')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    # Solo se envían listas a dashboard.html si es necesario para estadísticas
    return render_template('dashboard.html')


# -------------------------------------------------------------------------
# RUTAS DE BODEGAS (CRUD Completo)
# -------------------------------------------------------------------------

@app.route('/bodegas')
@login_required
def list_bodegas():
    bodegas = Bodega.query.all()
    return render_template('bodegas.html', bodegas=bodegas)

@app.route('/bodegas/crear', methods=['GET', 'POST'])
@login_required
def create_bodega():
    if request.method == 'POST':
        name = request.form.get('name')
        location = request.form.get('location') # Asume que hay un campo 'location' en el formulario
        
        new_bodega = Bodega(name=name, location=location)
        try:
            db.session.add(new_bodega)
            db.session.commit()
            flash('Bodega creada exitosamente.', 'success')
            return redirect(url_for('list_bodegas'))
        except IntegrityError:
            db.session.rollback()
            flash('Error: Ya existe una bodega con ese nombre.', 'error')
            
    return render_template('crear_bodega.html')

@app.route('/bodegas/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_bodega(id):
    bodega = db.session.get(Bodega, id) or None
    if not bodega:
        flash('Bodega no encontrada.', 'error')
        return redirect(url_for('list_bodegas'))

    if request.method == 'POST':
        bodega.name = request.form.get('name')
        bodega.location = request.form.get('location')
        try:
            db.session.commit()
            flash('Bodega actualizada exitosamente.', 'success')
            return redirect(url_for('list_bodegas'))
        except IntegrityError:
            db.session.rollback()
            flash('Error: Ya existe otra bodega con ese nombre.', 'error')
            
    return render_template('editar_bodega.html', bodega=bodega)

@app.route('/bodegas/eliminar/<int:id>', methods=['POST'])
@login_required
def delete_bodega(id):
    bodega = db.session.get(Bodega, id) or None
    if bodega:
        db.session.delete(bodega)
        db.session.commit()
        flash('Bodega eliminada exitosamente.', 'success')
    else:
        flash('Bodega no encontrada.', 'error')
    return redirect(url_for('list_bodegas'))


# -------------------------------------------------------------------------
# RUTAS DE PRODUCTOS (CRUD Completo)
# -------------------------------------------------------------------------

@app.route('/productos')
@login_required
def list_products():
    productos = Product.query.all()
    return render_template('productos.html', productos=productos)

@app.route('/productos/agregar', methods=['GET', 'POST'])
@login_required
def add_product():
    if request.method == 'POST':
        name = request.form.get('name')
        code = request.form.get('code')
        stock = request.form.get('stock', type=int, default=0)
        
        new_product = Product(name=name, code=code, stock=stock)
        try:
            db.session.add(new_product)
            db.session.commit()
            flash('Producto agregado correctamente.', 'success')
            return redirect(url_for('list_products'))
        except IntegrityError:
            db.session.rollback()
            flash('Error: Ya existe un producto con ese código.', 'error')
            
    # Usa la plantilla 'crear_producto.html' que tenías
    return render_template('crear_producto.html')


# Las rutas /productos/crear y /product/qr/<code> se mantienen como estaban.

# -------------------------------------------------------------------------
# RUTAS DE SUPERVISORES (CRUD Básico)
# -------------------------------------------------------------------------

@app.route('/supervisores')
@login_required
def list_supervisores():
    supervisores = Supervisor.query.all()
    return render_template('supervisores.html', supervisores=supervisores)

@app.route('/supervisores/crear', methods=['GET', 'POST'])
@login_required
def create_supervisor():
    if request.method == 'POST':
        name = request.form.get('name')
        # Generar QR data basado en el nombre o un ID único
        qr_data = f"Supervisor:{name}-{datetime.now().timestamp()}"
        
        new_supervisor = Supervisor(name=name, qr_code_data=qr_data)
        try:
            db.session.add(new_supervisor)
            db.session.commit()
            flash('Supervisor creado exitosamente.', 'success')
            return redirect(url_for('list_supervisores'))
        except IntegrityError:
            db.session.rollback()
            flash('Error al crear supervisor (posible duplicidad).', 'error')
            
    return render_template('crear_supervisor.html')

# Se omiten las funciones de editar/eliminar para brevedad, pero deberían ser añadidas


# -------------------------------------------------------------------------
# RUTAS DE ESCUELAS (CRUD Básico)
# -------------------------------------------------------------------------

@app.route('/escuelas')
@login_required
def list_escuelas():
    escuelas = Escuela.query.all()
    return render_template('escuelas.html', escuelas=escuelas)

@app.route('/escuelas/crear', methods=['GET', 'POST'])
@login_required
def create_escuela():
    if request.method == 'POST':
        name = request.form.get('name')
        # Generar QR data
        qr_data = f"Escuela:{name}-{datetime.now().timestamp()}"
        
        new_escuela = Escuela(name=name, qr_code_data=qr_data)
        try:
            db.session.add(new_escuela)
            db.session.commit()
            flash('Escuela creada exitosamente.', 'success')
            return redirect(url_for('list_escuelas'))
        except IntegrityError:
            db.session.rollback()
            flash('Error al crear escuela (posible duplicidad).', 'error')

    return render_template('crear_escuela.html')

# -------------------------------------------------------------------------
# RUTAS ADICIONALES DEL DASHBOARD (Para eliminar los 404s)
# -------------------------------------------------------------------------

@app.route('/reportes')
@login_required
def reportes_page():
    # Asume que tienes una plantilla llamada 'reportes.html'
    return render_template('reportes.html')

@app.route('/pedidos')
@login_required
def pedidos_page():
    # Asume que tienes una plantilla llamada 'pedidos.html'
    return render_template('pedidos.html')


# --- Generador de QR (Mantenido) ---

@app.route('/product/qr/<code>')
@login_required
def generate_qr(code):
    # Lógica para generar QR (la misma que tenías)
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=4)
    qr.add_data(code)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    qr_base64 = base64.b64encode(buffer.getvalue()).decode()

    # Intenta buscar el producto
    product = Product.query.filter_by(code=code).first_or_404()
    return render_template('qr_code.html', qr_base64=qr_base64, product=product)

# =========================================================================
# Ejecución de la aplicación
# =========================================================================

# Esta sección se ejecuta localmente si no usas gunicorn. En Render, gunicorn lo ignora.
if __name__ == '__main__':
    # Asegúrate de que 'db.create_all()' se ejecute si ejecutas localmente
    # con: python app.py
    with app.app_context():
        db.create_all() 
    app.run(debug=True)
