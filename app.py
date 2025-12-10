import os
from datetime import datetime
from flask import Flask, render_template, redirect, url_for, flash, request
from flask_login import UserMixin, LoginManager, login_user, logout_user, current_user, login_required
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.exc import IntegrityError, SQLAlchemyError 
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
    return db.session.get(User, int(user_id))

# =========================================================================
# 2. DEFINICIÓN DE MODELOS
# =========================================================================

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    password_hash = db.Column(db.String(128))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(50), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    stock = db.Column(db.Integer, default=0)
    
class Bodega(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    location = db.Column(db.String(200), nullable=True)

# CLASE SUPERVISOR (CORREGIDA)
class Supervisor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    apellido = db.Column(db.String(100), nullable=False) 
    email = db.Column(db.String(120), unique=True, nullable=False) 
    qr_code_data = db.Column(db.String(255), unique=True, nullable=True)
    # Se omite 'created_at' para coincidir con la plantilla supervisores.html (Solución 2)

class Escuela(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    qr_code_data = db.Column(db.String(255), unique=True, nullable=True)

# =========================================================================
# 3. RUTAS DE ACCESO Y DASHBOARD
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
    flash('Sesión cerrada exitosamente.', 'success')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')


# -------------------------------------------------------------------------
# RUTAS DE BODEGAS
# -------------------------------------------------------------------------

# (Tus rutas de Bodegas existentes...)

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
        location = request.form.get('location')

        if not name:
            flash('El nombre de la bodega es obligatorio.', 'error')
            return render_template('crear_bodega.html')
        
        new_bodega = Bodega(name=name, location=location)
        try:
            db.session.add(new_bodega)
            db.session.commit()
            flash('Bodega creada exitosamente.', 'success')
            return redirect(url_for('list_bodegas'))
        except IntegrityError:
            db.session.rollback()
            flash('Error: Ya existe una bodega con ese nombre.', 'error')
        except SQLAlchemyError as e:
            db.session.rollback()
            flash(f'Ocurrió un error inesperado al guardar la bodega: {e}', 'error')
            
    return render_template('crear_bodega.html')

@app.route('/bodegas/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_bodega(id):
    bodega = db.session.get(Bodega, id) or None
    if not bodega:
        flash('Bodega no encontrada.', 'error')
        return redirect(url_for('list_bodegas'))

    if request.method == 'POST':
        name = request.form.get('name')
        if not name:
            flash('El nombre de la bodega es obligatorio.', 'error')
            return render_template('editar_bodega.html', bodega=bodega)

        bodega.name = name
        bodega.location = request.form.get('location')
        try:
            db.session.commit()
            flash('Bodega actualizada exitosamente.', 'success')
            return redirect(url_for('list_bodegas'))
        except IntegrityError:
            db.session.rollback()
            flash('Error: Ya existe otra bodega con ese nombre.', 'error')
        except SQLAlchemyError as e:
            db.session.rollback()
            flash(f'Ocurrió un error inesperado al actualizar la bodega: {e}', 'error')
            
    return render_template('editar_bodega.html', bodega=bodega)

@app.route('/bodegas/eliminar/<int:id>', methods=['POST'])
@login_required
def delete_bodega(id):
    bodega = db.session.get(Bodega, id) or None
    if bodega:
        try:
            db.session.delete(bodega)
            db.session.commit()
            flash('Bodega eliminada exitosamente.', 'success')
        except SQLAlchemyError as e:
            db.session.rollback()
            flash(f'Error al eliminar la bodega. Posiblemente está vinculada a productos: {e}', 'error')
    else:
        flash('Bodega no encontrada.', 'error')
    return redirect(url_for('list_bodegas'))


# -------------------------------------------------------------------------
# RUTAS DE PRODUCTOS
# -------------------------------------------------------------------------

# (Tus rutas de Productos existentes...)

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
        
        if not name or not code:
            flash('Nombre y Código del producto son obligatorios.', 'error')
            return render_template('crear_producto.html')

        new_product = Product(name=name, code=code, stock=stock)
        try:
            db.session.add(new_product)
            db.session.commit()
            flash('Producto agregado correctamente.', 'success')
            return redirect(url_for('list_products'))
        except IntegrityError:
            db.session.rollback()
            flash('Error: Ya existe un producto con ese código.', 'error')
        except SQLAlchemyError as e:
            db.session.rollback()
            flash(f'Ocurrió un error inesperado al guardar el producto: {e}', 'error')
            
    return render_template('crear_producto.html')

@app.route('/productos/crear')
@login_required
def redirect_to_add_product():
    return redirect(url_for('add_product'))

@app.route('/product/qr/<code>')
@login_required
def generate_qr(code):
    # Lógica para generar QR (Mantenida por si necesitas la ruta específica de producto)
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=4)
    qr.add_data(code)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    qr_base64 = base64.b64encode(buffer.getvalue()).decode()
    product = Product.query.filter_by(code=code).first_or_404()
    return render_template('qr_code.html', qr_base64=qr_base64, item=product, item_type='Producto')


# -------------------------------------------------------------------------
# RUTAS DE SUPERVISORES (COMPLETO: CRUD + QR)
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
        apellido = request.form.get('apellido')
        email = request.form.get('email')
        
        if not name or not apellido or not email:
            flash('Todos los campos (Nombre, Apellido, Email) son obligatorios.', 'error')
            return render_template('crear_supervisor.html', name=name, apellido=apellido, email=email)

        # Generar el QR Data 
        qr_data = f"Supervisor:{name}-{apellido}:{email}-{datetime.now().timestamp()}"
        
        new_supervisor = Supervisor(
            name=name, 
            apellido=apellido,  
            email=email,        
            qr_code_data=qr_data
        )
        
        try:
            db.session.add(new_supervisor)
            db.session.commit()
            flash('Supervisor creado exitosamente.', 'success')
            return redirect(url_for('list_supervisores'))
            
        except IntegrityError:
            db.session.rollback()
            flash('Error: Ya existe un supervisor con ese Email o datos duplicados.', 'error')
            
        except SQLAlchemyError as e:
            db.session.rollback()
            flash(f'Ocurrió un error inesperado al guardar el supervisor: {e}', 'error')
            
    return render_template('crear_supervisor.html')


# NUEVA RUTA: EDITAR SUPERVISOR (GET y POST)
@app.route('/supervisores/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_supervisor(id):
    supervisor = db.session.get(Supervisor, id)
    if not supervisor:
        flash('Supervisor no encontrado.', 'error')
        return redirect(url_for('list_supervisores'))

    if request.method == 'POST':
        name = request.form.get('name')
        apellido = request.form.get('apellido')
        email = request.form.get('email')
        
        if not name or not apellido or not email:
            flash('Todos los campos son obligatorios.', 'error')
            return render_template('editar_supervisor.html', supervisor=supervisor)

        supervisor.name = name
        supervisor.apellido = apellido
        supervisor.email = email
        
        try:
            db.session.commit()
            flash('Supervisor actualizado exitosamente.', 'success')
            return redirect(url_for('list_supervisores'))
        except IntegrityError:
            db.session.rollback()
            flash('Error: El Email ya está registrado para otro supervisor.', 'error')
        except SQLAlchemyError as e:
            db.session.rollback()
            flash(f'Ocurrió un error inesperado al actualizar: {e}', 'error')

    return render_template('editar_supervisor.html', supervisor=supervisor)


# NUEVA RUTA: ELIMINAR SUPERVISOR (POST)
@app.route('/supervisores/eliminar/<int:id>', methods=['POST'])
@login_required
def delete_supervisor(id):
    supervisor = db.session.get(Supervisor, id)
    if not supervisor:
        flash('Supervisor no encontrado.', 'error')
        return redirect(url_for('list_supervisores'))

    try:
        db.session.delete(supervisor)
        db.session.commit()
        flash(f'Supervisor "{supervisor.name} {supervisor.apellido}" eliminado exitosamente.', 'success')
    except SQLAlchemyError as e:
        db.session.rollback()
        flash(f'Error al eliminar el supervisor: {e}', 'error')
        
    return redirect(url_for('list_supervisores'))


# NUEVA RUTA: VER QR DEL SUPERVISOR
@app.route('/supervisores/qr/<int:id>')
@login_required
def view_supervisor_qr(id):
    supervisor = db.session.get(Supervisor, id)
    if not supervisor:
        flash('Supervisor no encontrado.', 'error')
        return redirect(url_for('list_supervisores'))

    # Lógica para generar QR (usando el campo qr_code_data ya guardado)
    qr_data = supervisor.qr_code_data
    
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=4)
    qr.add_data(qr_data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Convertir la imagen a Base64 para incrustarla en HTML
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    qr_base64 = base64.b64encode(buffer.getvalue()).decode()
    
    # Renderizamos la plantilla genérica QR
    return render_template('qr_code.html', qr_base64=qr_base64, item=supervisor, item_type='Supervisor')


# -------------------------------------------------------------------------
# RUTAS DE ESCUELAS
# -------------------------------------------------------------------------

# (Tus rutas de Escuelas existentes...)

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
        
        if not name:
            flash('El nombre de la escuela es obligatorio.', 'error')
            return render_template('crear_escuela.html')

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
        except SQLAlchemyError as e:
            db.session.rollback()
            flash(f'Ocurrió un error inesperado al guardar la escuela: {e}', 'error')

    return render_template('crear_escuela.html')


# -------------------------------------------------------------------------
# RUTAS ADICIONALES DEL DASHBOARD
# -------------------------------------------------------------------------

@app.route('/reportes')
@login_required
def reportes_page():
    return render_template('reportes.html')

@app.route('/pedidos')
@login_required
def pedidos_page():
    return render_template('pedidos.html')


# =========================================================================
# Ejecución de la aplicación
# =========================================================================

if __name__ == '__main__':
    with app.app_context():
        # db.create_all() debe ejecutarse solo cuando la DB no existe o fue eliminada
        db.create_all() 
    app.run(debug=True)
