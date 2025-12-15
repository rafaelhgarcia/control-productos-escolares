import os
from datetime import datetime, timedelta
from flask import Flask, render_template, redirect, url_for, flash, request
from flask_login import UserMixin, LoginManager, login_user, logout_user, current_user, login_required
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy import func

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
    # Adaptación para Render PostgreSQL
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

class Supervisor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    apellido = db.Column(db.String(100), nullable=False) 
    email = db.Column(db.String(120), unique=True, nullable=False) 
    qr_code_data = db.Column(db.String(255), unique=True, nullable=True)

class Escuela(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    qr_code_data = db.Column(db.String(255), unique=True, nullable=True)

# Relación Supervisor-Escuela
class SupervisorEscuela(db.Model):
    __tablename__ = 'supervisor_escuela'
    id = db.Column(db.Integer, primary_key=True)
    supervisor_id = db.Column(db.Integer, db.ForeignKey('supervisor.id'), nullable=False)
    escuela_id = db.Column(db.Integer, db.ForeignKey('escuela.id'), nullable=False)
    
    __table_args__ = (db.UniqueConstraint('supervisor_id', 'escuela_id', name='_supervisor_escuela_uc'),)

    supervisor = db.relationship('Supervisor', backref='asignaciones')
    escuela = db.relationship('Escuela', backref='asignaciones')

# Solicitud de Pedido
class Solicitud(db.Model):
    __tablename__ = 'solicitud'
    id = db.Column(db.Integer, primary_key=True)
    supervisor_id = db.Column(db.Integer, db.ForeignKey('supervisor.id'), nullable=False)
    escuela_id = db.Column(db.Integer, db.ForeignKey('escuela.id'), nullable=False)
    fecha_solicitud = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_aprobacion = db.Column(db.DateTime, nullable=True)
    estado = db.Column(db.String(50), default='Pendiente', nullable=False) # Pendiente, Aprobada, Rechazada
    
    supervisor = db.relationship('Supervisor', backref='solicitudes')
    escuela = db.relationship('Escuela', backref='solicitudes')

# Detalle del Pedido
class DetalleSolicitud(db.Model):
    __tablename__ = 'detalle_solicitud'
    id = db.Column(db.Integer, primary_key=True)
    solicitud_id = db.Column(db.Integer, db.ForeignKey('solicitud.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    cantidad_solicitada = db.Column(db.Integer, nullable=False)
    
    solicitud = db.relationship('Solicitud', backref='detalles')
    producto = db.relationship('Product', backref='solicitud_detalles')

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
# RUTAS DE BODEGAS (CRUD)
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
# RUTAS DE PRODUCTOS (CRUD)
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
# RUTAS DE SUPERVISORES (CRUD + QR Corregido)
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

        # Generar el QR Data usando el email como clave única
        qr_data = f"SUPERVISOR_EMAIL:{email}"
        
        new_supervisor = Supervisor(
            name=name, 
            apellido=apellido, 
            email=email,     
            qr_code_data=qr_data
        )
        
        try:
            db.session.add(new_supervisor)
            db.session.commit()
            flash('Supervisor creado exitosamente. QR Data generado.', 'success')
            return redirect(url_for('list_supervisores'))
            
        except IntegrityError:
            db.session.rollback()
            flash('Error: Ya existe un supervisor con ese Email o datos duplicados.', 'error')
            
        except SQLAlchemyError as e:
            db.session.rollback()
            flash(f'Ocurrió un error inesperado al guardar el supervisor: {e}', 'error')
            
    return render_template('crear_supervisor.html')

@app.route('/supervisores/qr/<int:id>')
@login_required
def view_supervisor_qr(id):
    supervisor = db.session.get(Supervisor, id)
    if not supervisor:
        flash('Supervisor no encontrado.', 'error')
        return redirect(url_for('list_supervisores'))

    # 1. Obtener los IDs de las escuelas asignadas
    asignaciones = SupervisorEscuela.query.filter_by(supervisor_id=id).all()
    escuela_ids = [a.escuela_id for a in asignaciones]
    
    # 2. Obtener los pedidos de las escuelas ASIGNADAS
    if escuela_ids:
        solicitudes = Solicitud.query.filter(
            Solicitud.escuela_id.in_(escuela_ids)
        ).order_by(Solicitud.fecha_solicitud.desc()).all()
    else:
        solicitudes = []
        flash('Este supervisor no tiene escuelas asignadas. Por favor, asigne una escuela.', 'warning')
        
    # 3. Lógica para generar QR (usando el campo qr_code_data)
    qr_data = supervisor.qr_code_data
    
    # Manejar caso si el QR data es None (supervisores antiguos)
    if not qr_data:
        flash('El QR del supervisor estaba vacío. Intente editar y guardar para regenerarlo permanentemente.', 'warning')
        qr_data = f"SUPERVISOR_EMAIL:{supervisor.email}" 
    
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=4)
    qr.add_data(qr_data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    qr_base64 = base64.b64encode(buffer.getvalue()).decode()
    
    # 4. Renderizamos la plantilla con el QR y las Solicitudes filtradas
    return render_template('qr_supervisor_pedidos.html', 
                           qr_base64=qr_base64, 
                           supervisor=supervisor, 
                           solicitudes=solicitudes) 

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

        # Lógica de regeneración de QR si cambia el email o si el campo estaba vacío
        if supervisor.email != email or not supervisor.qr_code_data:
            supervisor.email = email
            supervisor.qr_code_data = f"SUPERVISOR_EMAIL:{email}"
        else:
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


# -------------------------------------------------------------------------
# RUTAS DE ESCUELAS (CRUD)
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
        
        if not name:
            flash('El nombre de la escuela es obligatorio.', 'error')
            return render_template('crear_escuela.html')

        # Usar el nombre y un timestamp para un QR Data único
        qr_data = f"ESCUELA_NAME:{name}-{datetime.now().timestamp()}"
        
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
# RUTAS DE PEDIDOS (Admin y Público)
# -------------------------------------------------------------------------

@app.route('/pedidos')
@login_required
def pedidos_page():
    # Obtener todas las solicitudes para que el administrador las revise
    solicitudes = Solicitud.query.order_by(Solicitud.fecha_solicitud.desc()).all()
    return render_template('pedidos.html', solicitudes=solicitudes)


@app.route('/pedidos/<int:solicitud_id>')
@login_required
def view_solicitud(solicitud_id):
    solicitud = db.session.get(Solicitud, solicitud_id)
    if not solicitud:
        flash('Solicitud no encontrada.', 'error')
        return redirect(url_for('pedidos_page'))

    detalles = DetalleSolicitud.query.filter_by(solicitud_id=solicitud_id).all()

    return render_template('detalle_solicitud.html', solicitud=solicitud, detalles=detalles)


@app.route('/pedidos/aprobar/<int:solicitud_id>', methods=['POST'])
@login_required
def aprobar_solicitud(solicitud_id):
    solicitud = db.session.get(Solicitud, solicitud_id)
    if not solicitud:
        flash('Solicitud no encontrada.', 'error')
        return redirect(url_for('pedidos_page'))

    if solicitud.estado != 'Pendiente':
        flash('Esta solicitud ya ha sido procesada.', 'warning')
        return redirect(url_for('view_solicitud', solicitud_id=solicitud_id))
        
    detalles = DetalleSolicitud.query.filter_by(solicitud_id=solicitud_id).all()
    try:
        # Verificar y actualizar stock
        for detalle in detalles:
            producto = db.session.get(Product, detalle.product_id)
            if producto and producto.stock >= detalle.cantidad_solicitada:
                producto.stock -= detalle.cantidad_solicitada
            else:
                flash(f'ERROR: Stock insuficiente para {producto.name}. Solicitud no aprobada.', 'error')
                return redirect(url_for('view_solicitud', solicitud_id=solicitud_id))

        solicitud.estado = 'Aprobada'
        solicitud.fecha_aprobacion = datetime.utcnow()
        db.session.commit()
        flash('Solicitud Aprobada y Stock Actualizado exitosamente.', 'success')
        
    except SQLAlchemyError as e:
        db.session.rollback()
        flash(f'Error al procesar la aprobación: {e}', 'error')

    return redirect(url_for('view_solicitud', solicitud_id=solicitud_id))


# RUTA PÚBLICA: Realizar un pedido desde el QR de la escuela
@app.route('/pedido/escuela/<int:escuela_id>', methods=['GET', 'POST'])
def hacer_pedido_escuela(escuela_id):
    escuela = db.session.get(Escuela, escuela_id)
    if not escuela:
        flash("Escuela no válida o no encontrada.", 'error')
        return render_template('error_page.html', message="Escuela no encontrada"), 404

    productos = Product.query.all()
    
    if request.method == 'POST':
        # --- 1. Lógica de Validación de 2 pedidos por semana ---
        hace_7_dias = datetime.utcnow() - timedelta(days=7)
        pedidos_recientes = Solicitud.query.filter(
            Solicitud.escuela_id == escuela_id,
            Solicitud.fecha_solicitud >= hace_7_dias
        ).count()
        
        if pedidos_recientes >= 2:
            flash('Límite excedido: Solo se permiten 2 solicitudes por escuela a la semana.', 'error')
            return render_template('hacer_pedido.html', escuela=escuela, productos=productos)
        
        # --- 2. Encontrar el Supervisor Asignado ---
        asignacion = SupervisorEscuela.query.filter_by(escuela_id=escuela_id).first()
        if not asignacion:
            flash('Error: Esta escuela no tiene un supervisor asignado para recibir pedidos.', 'error')
            return render_template('hacer_pedido.html', escuela=escuela, productos=productos)
        
        supervisor_id = asignacion.supervisor_id

        # --- 3. Crear Solicitud y Detalles ---
        try:
            nueva_solicitud = Solicitud(supervisor_id=supervisor_id, escuela_id=escuela_id)
            db.session.add(nueva_solicitud)
            db.session.flush() # Obtener ID antes de commit
            
            detalles_agregados = False
            for product in productos:
                cantidad = request.form.get(f'cantidad_{product.id}', type=int, default=0)
                
                if cantidad > 0:
                    # --- 4. Lógica de Validación de Máximo 3 por producto ---
                    if cantidad > 3:
                        db.session.rollback()
                        flash(f'Límite excedido para {product.name}: Solo se pueden pedir 3 unidades por producto.', 'error')
                        return render_template('hacer_pedido.html', escuela=escuela, productos=productos)
                        
                    detalle = DetalleSolicitud(
                        solicitud_id=nueva_solicitud.id,
                        product_id=product.id,
                        cantidad_solicitada=cantidad
                    )
                    db.session.add(detalle)
                    detalles_agregados = True
            
            if not detalles_agregados:
                db.session.rollback()
                flash('Debe seleccionar al menos un producto para el pedido.', 'error')
                return render_template('hacer_pedido.html', escuela=escuela, productos=productos)
                
            db.session.commit()
            return redirect(url_for('pedido_exitoso', solicitud_id=nueva_solicitud.id))
            
        except SQLAlchemyError as e:
            db.session.rollback()
            flash(f'Ocurrió un error al guardar el pedido: {e}', 'error')


    return render_template('hacer_pedido.html', escuela=escuela, productos=productos)

@app.route('/pedido/exitoso/<int:solicitud_id>')
def pedido_exitoso(solicitud_id):
    # RUTA PÚBLICA: Muestra un mensaje de confirmación
    return render_template('pedido_exitoso.html', solicitud_id=solicitud_id)


# -------------------------------------------------------------------------
# RUTAS DE ASIGNACIÓN (Supervisor-Escuela)
# -------------------------------------------------------------------------

@app.route('/asignaciones', methods=['GET', 'POST'])
@login_required
def administrar_asignaciones():
    supervisores = Supervisor.query.all()
    escuelas = Escuela.query.all()
    asignaciones_existentes = SupervisorEscuela.query.all()
    
    if request.method == 'POST':
        supervisor_id = request.form.get('supervisor_id', type=int)
        escuela_id = request.form.get('escuela_id', type=int)
        
        if not supervisor_id or not escuela_id:
            flash('Debe seleccionar un Supervisor y una Escuela.', 'error')
            return redirect(url_for('administrar_asignaciones'))
            
        new_asignacion = SupervisorEscuela(supervisor_id=supervisor_id, escuela_id=escuela_id)
        
        try:
            db.session.add(new_asignacion)
            db.session.commit()
            flash('Asignación realizada exitosamente.', 'success')
        except IntegrityError:
            db.session.rollback()
            flash('Error: Esta escuela ya está asignada a este supervisor.', 'error')
        except SQLAlchemyError as e:
            db.session.rollback()
            flash(f'Error al guardar la asignación: {e}', 'error')
            
        return redirect(url_for('administrar_asignaciones'))

    return render_template('asignaciones.html', 
                           supervisores=supervisores, 
                           escuelas=escuelas, 
                           asignaciones=asignaciones_existentes)

@app.route('/asignaciones/eliminar/<int:id>', methods=['POST'])
@login_required
def eliminar_asignacion(id):
    asignacion = db.session.get(SupervisorEscuela, id)
    if not asignacion:
        flash('Asignación no encontrada.', 'error')
        return redirect(url_for('administrar_asignaciones'))
    
    try:
        db.session.delete(asignacion)
        db.session.commit()
        flash('Asignación eliminada exitosamente.', 'success')
    except SQLAlchemyError as e:
        db.session.rollback()
        flash(f'Error al eliminar la asignación: {e}', 'error')
        
    return redirect(url_for('administrar_asignaciones'))


# -------------------------------------------------------------------------
# RUTAS ADICIONALES DEL DASHBOARD
# -------------------------------------------------------------------------

@app.route('/reportes')
@login_required
def reportes_page():
    return render_template('reportes.html')


# =========================================================================
# Ejecución de la aplicación
# =========================================================================

if __name__ == '__main__':
    with app.app_context():
        # Crear la base de datos y el usuario admin (si no existe, usa tu script)
        db.create_all()
    app.run(debug=True)
