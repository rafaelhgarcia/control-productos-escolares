import os
from datetime import datetime
from flask import Flask, render_template, redirect, url_for, flash, request
from flask_login import UserMixin, LoginManager, login_user, logout_user, current_user, login_required
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import qrcode
import io
import base64

# =========================================================================
# 1. INICIALIZACIÓN Y CONFIGURACIÓN DE FLASK (Soluciona el NameError)
# =========================================================================

# Inicializa la aplicación Flask - DEBE SER LA PRIMERA LÍNEA EJECUTABLE DE 'app'
app = Flask(__name__) 

# Configuración de la aplicación
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'UNA_CLAVE_SECRETA_POR_DEFECTO')

# Configuración de la base de datos PostgreSQL de Render
# CORRECCIÓN DE LA URI DE LA BASE DE DATOS (Soluciona NoSuchModuleError)
# Cambia 'postgres://' (Render) por 'postgresql://' (SQLAlchemy)
if os.environ.get('DATABASE_URL'):
    db_url = os.environ.get('DATABASE_URL').replace('postgres://', 'postgresql://', 1)
else:
    # URL local para desarrollo si no se encuentra la variable de entorno
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
    return db.session.get(User, int(user_id))

# =========================================================================
# 2. DEFINICIÓN DE MODELOS
# =========================================================================

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    products = db.relationship('Product', backref='user', lazy=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    products = db.relationship('Product', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(50), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Bodega(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)

class Supervisor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)

class Escuela(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)

# =========================================================================
# 3. RUTAS DE LA APLICACIÓN (Usando nombres de plantilla en español)
# =========================================================================

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
    return redirect(url_for('login'))

# --- Dashboard ---
@app.route('/dashboard')
@login_required
def dashboard():
    products = Product.query.all() 
    bodegas = Bodega.query.all()
    supervisores = Supervisor.query.all()
    escuelas = Escuela.query.all()
    return render_template('dashboard.html', products=products, bodegas=bodegas, supervisores=supervisores, escuelas=escuelas)

# --- Rutas de Gestión de Productos ---

@app.route('/productos')
@login_required
def list_products():
    productos = Product.query.all()
    return render_template('productos.html', productos=productos) 

@app.route('/product/add', methods=['GET', 'POST'])
@login_required
def add_product():
    if request.method == 'POST':
        flash('Producto agregado correctamente (Lógica de DB omitida aquí).', 'success')
        return redirect(url_for('list_products'))
    return render_template('crear_producto.html')

@app.route('/productos/crear')
@login_required
def redirect_to_add_product():
    return redirect(url_for('add_product'))

@app.route('/product/qr/<code>')
@login_required
def generate_qr(code):
    # Lógica para generar QR
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(code)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    qr_base64 = base64.b64encode(buffer.getvalue()).decode()

    # Busca el producto por código (usando first_or_404)
    product = Product.query.filter_by(code=code).first_or_404()
    return render_template('qr_code.html', qr_base64=qr_base64, product=product)

# --- Rutas de Gestión de Bodegas ---
@app.route('/bodegas')
@login_required
def list_bodegas():
    bodegas = Bodega.query.all()  
    return render_template('bodegas.html', bodegas=bodegas) 

@app.route('/bodegas/crear')
@login_required
def create_bodega_page():
    return render_template('crear_bodega.html') 

# --- Rutas de Gestión de Supervisores ---
@app.route('/supervisores')
@login_required
def list_supervisores():
    supervisores = Supervisor.query.all()
    return render_template('supervisores.html', supervisores=supervisores)

@app.route('/supervisores/crear')
@login_required
def create_supervisor_page():
    return render_template('crear_supervisor.html') 

# --- Rutas de Gestión de Escuelas ---
@app.route('/escuelas')
@login_required
def list_escuelas():
    escuelas = Escuela.query.all()
    return render_template('escuelas.html', escuelas=escuelas)

@app.route('/escuelas/crear')
@login_required
def create_escuela_page():
    return render_template('crear_escuela.html')

# =========================================================================
# Ejecución de la aplicación
# =========================================================================

if __name__ == '__main__':
    app.run(debug=True)
