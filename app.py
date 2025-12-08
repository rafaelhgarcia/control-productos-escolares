# Importaciones necesarias
import os
from datetime import datetime
from flask import Flask, render_template, redirect, url_for, flash, request
from flask_login import UserMixin, LoginManager, login_user, logout_user, current_user, login_required
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
# Importación de módulos de qrcode
import qrcode
import io
import base64

# Inicialización de la Aplicación y Configuración
app = Flask(__name__)

# Configuración secreta de la app
# Render necesita esta variable de entorno
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'default_secret_key_local')

# Configuración de Base de Datos PostgreSQL para Render
# Usamos SQLALCHEMY_DATABASE_URI para la conexión
# La variable de entorno 'DATABASE_URL' debe ser establecida en Render
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Base de datos
db = SQLAlchemy(app)

# ---------------------------------------------
# Configuración de Flask-Login
# ---------------------------------------------
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# ---------------------------------------------
# Definición de Modelos (User y Product ya estaban)
# ---------------------------------------------
class User(UserMixin, db.Model):
    __tablename__ = 'users' 
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    products = db.relationship('Product', backref='owner', lazy='dynamic')
    supervisors_created = db.relationship('Supervisor', backref='creator', lazy='dynamic')
    escuelas_managed = db.relationship('Escuela', backref='manager', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'


class Product(db.Model):
    __tablename__ = 'products' 
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(100), unique=True, nullable=False)
    quantity = db.Column(db.Integer, default=0)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False) 
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Product {self.name}>'

# ---------------------------------------------
# MODELOS NUEVOS AGREGADOS
# ---------------------------------------------

class Bodega(db.Model):
    __tablename__ = 'bodegas'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    location = db.Column(db.String(150), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Bodega {self.name}>'

class Supervisor(db.Model):
    __tablename__ = 'supervisors'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    employee_code = db.Column(db.String(50), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False) # Asumiendo que el admin crea supervisores
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Supervisor {self.name}>'

class Escuela(db.Model):
    __tablename__ = 'escuelas'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    address = db.Column(db.String(250), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False) # Asumiendo que el admin las gestiona
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Escuela {self.name}>'

# ---------------------------------------------
# Rutas
# ---------------------------------------------

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
        
        # Buscar el usuario
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user, remember=True)
            flash('Inicio de sesión exitoso.', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard'))
        else:
            flash('Nombre de usuario o contraseña inválidos.', 'danger')
            
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Has cerrado sesión.', 'info')
    return redirect(url_for('login'))

# --- Dashboard y Gestión de Productos (Rutas dummy para contexto) ---

@app.route('/dashboard')
@login_required
def dashboard():
    products = Product.query.filter_by(user_id=current_user.id).order_by(Product.created_at.desc()).all()
    # Modificado para pasar datos de ejemplo para las nuevas secciones
    bodegas = Bodega.query.all()
    supervisores = Supervisor.query.all()
    escuelas = Escuela.query.all()
    
    return render_template('dashboard.html', products=products, bodegas=bodegas, supervisores=supervisores, escuelas=escuelas)

@app.route('/product/add', methods=['GET', 'POST'])
@login_required
def add_product():
    if request.method == 'POST':
        name = request.form.get('name')
        code = request.form.get('code')
        quantity = int(request.form.get('quantity', 0))
        
        # Validación: Código de producto único
        existing_product = Product.query.filter_by(code=code).first()
        if existing_product:
            flash(f'El código de producto "{code}" ya existe.', 'danger')
            return redirect(url_for('add_product'))

        new_product = Product(
            name=name,
            code=code,
            quantity=quantity,
            user_id=current_user.id
        )
        db.session.add(new_product)
        db.session.commit()
        flash('Producto agregado exitosamente.', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('add_product.html')

@app.route('/product/qr/<code>')
@login_required
def generate_qr(code):
    product = Product.query.filter_by(code=code, user_id=current_user.id).first_or_404()
    
    # Contenido del código QR
    qr_data = f"Nombre: {product.name}, Código: {product.code}, Cantidad: {product.quantity}"
    
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(qr_data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    # Guardar en buffer de memoria
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    
    # Codificar a base64 para incrustar en HTML
    qr_base64 = base64.b64encode(buffer.getvalue()).decode()
    
    return render_template('qr_code.html', qr_base64=qr_base64, product=product)

# NOTA: Se ha eliminado el bloque if __name__ == '__main__':
# La aplicación 'app' es importada y servida por Gunicorn.
