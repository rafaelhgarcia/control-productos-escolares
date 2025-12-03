from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import qrcode
import io
import base64
import os
import smtplib
from email.mime.text import MIMEText #from email.mime.text import MimeText
from email.MIMEMultipart import MIMEMultipart # from email.mime.multipart import MimeMultipart

app = Flask(__name__)
# Configuración para producción (nube) o desarrollo (local)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'tu-clave-secreta-aqui-cambiar-en-produccion')
# Usar PostgreSQL en producción (Render/Railway) o SQLite en desarrollo
database_url = os.environ.get('DATABASE_URL')
if database_url:
    # Render y Railway proporcionan DATABASE_URL con postgres://, necesitamos cambiarlo a postgresql://
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///control_productos.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# ConfiguraciÃ³n de email
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'tu-email@gmail.com'  # Cambiar por tu email
app.config['MAIL_PASSWORD'] = 'tu-password'  # Cambiar por tu contraseÃ±a

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Modelos de la base de datos
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Bodega(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    direccion = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Producto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text)
    cantidad = db.Column(db.Integer, default=0)
    bodega_id = db.Column(db.Integer, db.ForeignKey('bodega.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    bodega = db.relationship('Bodega', backref=db.backref('productos', lazy=True))

class Supervisor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    apellido = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    qr_code = db.Column(db.String(200), unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Escuela(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(200), nullable=False)
    direccion = db.Column(db.String(300), nullable=False)
    supervisor_id = db.Column(db.Integer, db.ForeignKey('supervisor.id'))
    qr_code = db.Column(db.String(200), unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    supervisor = db.relationship('Supervisor', backref=db.backref('escuelas', lazy=True))

class Pedido(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    escuela_id = db.Column(db.Integer, db.ForeignKey('escuela.id'), nullable=False)
    solicitante = db.Column(db.String(100), nullable=False)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)
    observaciones = db.Column(db.Text)
    estado = db.Column(db.String(20), default='pendiente')
    escuela = db.relationship('Escuela', backref=db.backref('pedidos', lazy=True))

class DetallePedido(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pedido_id = db.Column(db.Integer, db.ForeignKey('pedido.id'), nullable=False)
    producto_id = db.Column(db.Integer, db.ForeignKey('producto.id'), nullable=False)
    cantidad = db.Column(db.Integer, nullable=False)
    pedido = db.relationship('Pedido', backref=db.backref('detalles', lazy=True))
    producto = db.relationship('Producto', backref=db.backref('detalles_pedido', lazy=True))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# FunciÃ³n para generar cÃ³digo QR
def generate_qr_code(data, size=10, border=4):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=size,
        border=border,
    )
    qr.add_data(data)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Convertir imagen a base64
    img_buffer = io.BytesIO()
    img.save(img_buffer, format='PNG')
    img_buffer.seek(0)
    img_base64 = base64.b64encode(img_buffer.getvalue()).decode()
    
    return f"data:image/png;base64,{img_base64}"

# FunciÃ³n para enviar email
def send_email(to_email, subject, body):
    try:
        msg = MimeMultipart()
        msg['From'] = app.config['MAIL_USERNAME']
        msg['To'] = to_email
        msg['Subject'] = subject
        
        msg.attach(MimeText(body, 'html'))
        
        server = smtplib.SMTP(app.config['MAIL_SERVER'], app.config['MAIL_PORT'])
        server.starttls()
        server.login(app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
        text = msg.as_string()
        server.sendmail(app.config['MAIL_USERNAME'], to_email, text)
        server.quit()
        return True
    except Exception as e:
        print(f"Error enviando email: {e}")
        return False

# FunciÃ³n para verificar stock bajo
def check_low_stock():
    productos_bajo_stock = Producto.query.filter(Producto.cantidad < 11).all()
    if productos_bajo_stock:
        admin = User.query.filter_by(is_admin=True).first()
        if admin:
            subject = "Alerta: Stock Bajo en Productos"
            body = f"""
            <h2>Alerta de Stock Bajo</h2>
            <p>Los siguientes productos tienen menos de 11 unidades:</p>
            <ul>
            """
            for producto in productos_bajo_stock:
                body += f"<li><strong>{producto.nombre}</strong> - Stock actual: {producto.cantidad} unidades</li>"
            body += "</ul>"
            
            send_email(admin.email, subject, body)

# Rutas principales
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Usuario o contraseÃ±a incorrectos')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    if not current_user.is_admin:
        flash('No tienes permisos de administrador')
        return redirect(url_for('index'))
    
    # EstadÃ­sticas para el dashboard
    total_bodegas = Bodega.query.count()
    total_productos = Producto.query.count()
    total_supervisores = Supervisor.query.count()
    total_escuelas = Escuela.query.count()
    total_pedidos = Pedido.query.count()
    
    return render_template('dashboard.html', 
                         total_bodegas=total_bodegas,
                         total_productos=total_productos,
                         total_supervisores=total_supervisores,
                         total_escuelas=total_escuelas,
                         total_pedidos=total_pedidos)

# Rutas para Bodegas
@app.route('/bodegas')
@login_required
def bodegas():
    if not current_user.is_admin:
        flash('No tienes permisos de administrador')
        return redirect(url_for('index'))
    
    bodegas = Bodega.query.all()
    return render_template('bodegas.html', bodegas=bodegas)

@app.route('/bodegas/crear', methods=['GET', 'POST'])
@login_required
def crear_bodega():
    if not current_user.is_admin:
        flash('No tienes permisos de administrador')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        nombre = request.form['nombre']
        direccion = request.form['direccion']
        
        bodega = Bodega(nombre=nombre, direccion=direccion)
        db.session.add(bodega)
        db.session.commit()
        flash('Bodega creada exitosamente')
        return redirect(url_for('bodegas'))
    
    return render_template('crear_bodega.html')

@app.route('/bodegas/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def editar_bodega(id):
    if not current_user.is_admin:
        flash('No tienes permisos de administrador')
        return redirect(url_for('index'))
    
    bodega = Bodega.query.get_or_404(id)
    
    if request.method == 'POST':
        bodega.nombre = request.form['nombre']
        bodega.direccion = request.form['direccion']
        db.session.commit()
        flash('Bodega actualizada exitosamente')
        return redirect(url_for('bodegas'))
    
    return render_template('editar_bodega.html', bodega=bodega)

@app.route('/bodegas/<int:id>/eliminar', methods=['POST'])
@login_required
def eliminar_bodega(id):
    if not current_user.is_admin:
        flash('No tienes permisos de administrador')
        return redirect(url_for('index'))
    
    bodega = Bodega.query.get_or_404(id)
    db.session.delete(bodega)
    db.session.commit()
    flash('Bodega eliminada exitosamente')
    return redirect(url_for('bodegas'))

# Rutas para Productos
@app.route('/productos')
@login_required
def productos():
    if not current_user.is_admin:
        flash('No tienes permisos de administrador')
        return redirect(url_for('index'))
    
    productos = Producto.query.join(Bodega).all()
    return render_template('productos.html', productos=productos)

@app.route('/productos/crear', methods=['GET', 'POST'])
@login_required
def crear_producto():
    if not current_user.is_admin:
        flash('No tienes permisos de administrador')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        nombre = request.form['nombre']
        descripcion = request.form['descripcion']
        cantidad = int(request.form['cantidad'])
        bodega_id = int(request.form['bodega_id'])
        
        producto = Producto(nombre=nombre, descripcion=descripcion, 
                          cantidad=cantidad, bodega_id=bodega_id)
        db.session.add(producto)
        db.session.commit()
        
        # Verificar stock bajo despuÃ©s de crear producto
        check_low_stock()
        
        flash('Producto creado exitosamente')
        return redirect(url_for('productos'))
    
    bodegas = Bodega.query.all()
    return render_template('crear_producto.html', bodegas=bodegas)

@app.route('/productos/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def editar_producto(id):
    if not current_user.is_admin:
        flash('No tienes permisos de administrador')
        return redirect(url_for('index'))
    
    producto = Producto.query.get_or_404(id)
    
    if request.method == 'POST':
        producto.nombre = request.form['nombre']
        producto.descripcion = request.form['descripcion']
        producto.cantidad = int(request.form['cantidad'])
        producto.bodega_id = int(request.form['bodega_id'])
        db.session.commit()
        
        # Verificar stock bajo despuÃ©s de editar producto
        check_low_stock()
        
        flash('Producto actualizado exitosamente')
        return redirect(url_for('productos'))
    
    bodegas = Bodega.query.all()
    return render_template('editar_producto.html', producto=producto, bodegas=bodegas)

@app.route('/productos/<int:id>/eliminar', methods=['POST'])
@login_required
def eliminar_producto(id):
    if not current_user.is_admin:
        flash('No tienes permisos de administrador')
        return redirect(url_for('index'))
    
    producto = Producto.query.get_or_404(id)
    db.session.delete(producto)
    db.session.commit()
    flash('Producto eliminado exitosamente')
    return redirect(url_for('productos'))

# Rutas para Supervisores
@app.route('/supervisores')
@login_required
def supervisores():
    if not current_user.is_admin:
        flash('No tienes permisos de administrador')
        return redirect(url_for('index'))
    
    supervisores = Supervisor.query.all()
    return render_template('supervisores.html', supervisores=supervisores)

@app.route('/supervisores/crear', methods=['GET', 'POST'])
@login_required
def crear_supervisor():
    if not current_user.is_admin:
        flash('No tienes permisos de administrador')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        nombre = request.form['nombre']
        apellido = request.form['apellido']
        email = request.form['email']
        
        # Generar cÃ³digo QR Ãºnico
        qr_code = f"SUP_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        supervisor = Supervisor(nombre=nombre, apellido=apellido, 
                              email=email, qr_code=qr_code)
        db.session.add(supervisor)
        db.session.commit()
        flash('Supervisor creado exitosamente')
        return redirect(url_for('supervisores'))
    
    return render_template('crear_supervisor.html')

@app.route('/supervisores/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def editar_supervisor(id):
    if not current_user.is_admin:
        flash('No tienes permisos de administrador')
        return redirect(url_for('index'))
    
    supervisor = Supervisor.query.get_or_404(id)
    
    if request.method == 'POST':
        supervisor.nombre = request.form['nombre']
        supervisor.apellido = request.form['apellido']
        supervisor.email = request.form['email']
        db.session.commit()
        flash('Supervisor actualizado exitosamente')
        return redirect(url_for('supervisores'))
    
    return render_template('editar_supervisor.html', supervisor=supervisor)

@app.route('/supervisores/<int:id>/eliminar', methods=['POST'])
@login_required
def eliminar_supervisor(id):
    if not current_user.is_admin:
        flash('No tienes permisos de administrador')
        return redirect(url_for('index'))
    
    supervisor = Supervisor.query.get_or_404(id)
    db.session.delete(supervisor)
    db.session.commit()
    flash('Supervisor eliminado exitosamente')
    return redirect(url_for('supervisores'))

# Rutas para Escuelas
@app.route('/escuelas')
@login_required
def escuelas():
    if not current_user.is_admin:
        flash('No tienes permisos de administrador')
        return redirect(url_for('index'))
    
    escuelas = Escuela.query.join(Supervisor).all()
    return render_template('escuelas.html', escuelas=escuelas)

@app.route('/escuelas/crear', methods=['GET', 'POST'])
@login_required
def crear_escuela():
    if not current_user.is_admin:
        flash('No tienes permisos de administrador')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        nombre = request.form['nombre']
        direccion = request.form['direccion']
        supervisor_id = int(request.form['supervisor_id']) if request.form['supervisor_id'] else None
        
        # Generar cÃ³digo QR Ãºnico
        qr_code = f"ESC_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        escuela = Escuela(nombre=nombre, direccion=direccion, 
                         supervisor_id=supervisor_id, qr_code=qr_code)
        db.session.add(escuela)
        db.session.commit()
        flash('Escuela creada exitosamente')
        return redirect(url_for('escuelas'))
    
    supervisores = Supervisor.query.all()
    return render_template('crear_escuela.html', supervisores=supervisores)

@app.route('/escuelas/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def editar_escuela(id):
    if not current_user.is_admin:
        flash('No tienes permisos de administrador')
        return redirect(url_for('index'))
    
    escuela = Escuela.query.get_or_404(id)
    
    if request.method == 'POST':
        escuela.nombre = request.form['nombre']
        escuela.direccion = request.form['direccion']
        escuela.supervisor_id = int(request.form['supervisor_id']) if request.form['supervisor_id'] else None
        db.session.commit()
        flash('Escuela actualizada exitosamente')
        return redirect(url_for('escuelas'))
    
    supervisores = Supervisor.query.all()
    return render_template('editar_escuela.html', escuela=escuela, supervisores=supervisores)

@app.route('/escuelas/<int:id>/eliminar', methods=['POST'])
@login_required
def eliminar_escuela(id):
    if not current_user.is_admin:
        flash('No tienes permisos de administrador')
        return redirect(url_for('index'))
    
    escuela = Escuela.query.get_or_404(id)
    db.session.delete(escuela)
    db.session.commit()
    flash('Escuela eliminada exitosamente')
    return redirect(url_for('escuelas'))

# Rutas para cÃ³digos QR
@app.route('/qr/supervisor/<int:id>')
@login_required
def qr_supervisor(id):
    if not current_user.is_admin:
        flash('No tienes permisos de administrador')
        return redirect(url_for('index'))
    
    supervisor = Supervisor.query.get_or_404(id)
    
    # Crear URL para el supervisor
    qr_data = f"supervisor_login:{supervisor.qr_code}"
    qr_image = generate_qr_code(qr_data)
    
    return render_template('qr_supervisor.html', supervisor=supervisor, qr_image=qr_image)

@app.route('/qr/escuela/<int:id>')
@login_required
def qr_escuela(id):
    if not current_user.is_admin:
        flash('No tienes permisos de administrador')
        return redirect(url_for('index'))
    
    escuela = Escuela.query.get_or_404(id)
    
    # Crear URL para la escuela
    qr_data = f"escuela_pedidos:{escuela.qr_code}"
    qr_image = generate_qr_code(qr_data)
    
    return render_template('qr_escuela.html', escuela=escuela, qr_image=qr_image)

# Rutas para sistema de pedidos (SIN AUTENTICACIÃ“N)
@app.route('/pedidos/escuela/<string:qr_code>')
def pedidos_escuela(qr_code):
    # Buscar escuela por cÃ³digo QR
    escuela = Escuela.query.filter_by(qr_code=qr_code).first()
    if not escuela:
        flash('CÃ³digo QR invÃ¡lido')
        return redirect(url_for('index'))
    
    # Obtener productos disponibles
    productos = Producto.query.filter(Producto.cantidad > 0).all()
    
    # Verificar si la escuela puede hacer pedidos (mÃ¡ximo 2 por semana)
    inicio_semana = datetime.now() - timedelta(days=datetime.now().weekday())
    pedidos_semana = Pedido.query.filter(
        Pedido.escuela_id == escuela.id,
        Pedido.fecha >= inicio_semana
    ).count()
    
    puede_pedir = pedidos_semana < 2
    
    return render_template('pedidos_escuela.html', 
                         escuela=escuela, 
                         productos=productos, 
                         puede_pedir=puede_pedir,
                         pedidos_semana=pedidos_semana)

@app.route('/pedidos/crear', methods=['POST'])
def crear_pedido():
    qr_code = request.form['qr_code']
    solicitante = request.form['solicitante']
    observaciones = request.form.get('observaciones', '')
    
    # Buscar escuela
    escuela = Escuela.query.filter_by(qr_code=qr_code).first()
    if not escuela:
        flash('CÃ³digo QR invÃ¡lido')
        return redirect(url_for('index'))
    
    # Verificar lÃ­mite de pedidos por semana
    inicio_semana = datetime.now() - timedelta(days=datetime.now().weekday())
    pedidos_semana = Pedido.query.filter(
        Pedido.escuela_id == escuela.id,
        Pedido.fecha >= inicio_semana
    ).count()
    
    if pedidos_semana >= 2:
        flash('Esta escuela ya ha realizado el mÃ¡ximo de 2 pedidos esta semana')
        return redirect(url_for('pedidos_escuela', qr_code=qr_code))
    
    # Crear pedido
    pedido = Pedido(
        escuela_id=escuela.id,
        solicitante=solicitante,
        observaciones=observaciones
    )
    db.session.add(pedido)
    db.session.flush()  # Para obtener el ID del pedido
    
    # Procesar productos del pedido
    total_productos = 0
    for key, value in request.form.items():
        if key.startswith('producto_') and value:
            producto_id = int(key.split('_')[1])
            cantidad = int(value)
            
            # Verificar que no exceda 3 cajas por producto
            if cantidad > 3:
                flash(f'No se puede pedir mÃ¡s de 3 cajas del producto {producto_id}')
                db.session.rollback()
                return redirect(url_for('pedidos_escuela', qr_code=qr_code))
            
            # Verificar stock disponible
            producto = Producto.query.get(producto_id)
            if producto.cantidad < cantidad:
                flash(f'No hay suficiente stock del producto {producto.nombre}')
                db.session.rollback()
                return redirect(url_for('pedidos_escuela', qr_code=qr_code))
            
            # Crear detalle del pedido
            detalle = DetallePedido(
                pedido_id=pedido.id,
                producto_id=producto_id,
                cantidad=cantidad
            )
            db.session.add(detalle)
            total_productos += cantidad
    
    if total_productos == 0:
        flash('Debe seleccionar al menos un producto')
        db.session.rollback()
        return redirect(url_for('pedidos_escuela', qr_code=qr_code))
    
    # Actualizar stock de productos
    for detalle in pedido.detalles:
        producto = Producto.query.get(detalle.producto_id)
        producto.cantidad -= detalle.cantidad
        if producto.cantidad < 0:
            producto.cantidad = 0
    
    db.session.commit()
    
    # Verificar stock bajo despuÃ©s del pedido
    check_low_stock()
    
    flash('Pedido creado exitosamente')
    return redirect(url_for('pedidos_escuela', qr_code=qr_code))

# Rutas para reportes
@app.route('/reportes')
@login_required
def reportes():
    if not current_user.is_admin:
        flash('No tienes permisos de administrador')
        return redirect(url_for('index'))
    
    return render_template('reportes.html')

@app.route('/reportes/semanal')
@login_required
def reporte_semanal():
    if not current_user.is_admin:
        flash('No tienes permisos de administrador')
        return redirect(url_for('index'))
    
    # Obtener datos de la semana actual
    inicio_semana = datetime.now() - timedelta(days=datetime.now().weekday())
    fin_semana = inicio_semana + timedelta(days=6)
    
    pedidos = Pedido.query.filter(
        Pedido.fecha >= inicio_semana,
        Pedido.fecha <= fin_semana
    ).all()
    
    return render_template('reporte_semanal.html', 
                         pedidos=pedidos, 
                         inicio_semana=inicio_semana,
                         fin_semana=fin_semana)

@app.route('/reportes/mensual')
@login_required
def reporte_mensual():
    if not current_user.is_admin:
        flash('No tienes permisos de administrador')
        return redirect(url_for('index'))
    
    # Obtener datos del mes actual
    inicio_mes = datetime.now().replace(day=1)
    if inicio_mes.month == 12:
        fin_mes = inicio_mes.replace(year=inicio_mes.year + 1, month=1)
    else:
        fin_mes = inicio_mes.replace(month=inicio_mes.month + 1)
    
    pedidos = Pedido.query.filter(
        Pedido.fecha >= inicio_mes,
        Pedido.fecha < fin_mes
    ).all()
    
    return render_template('reporte_mensual.html', 
                         pedidos=pedidos, 
                         inicio_mes=inicio_mes,
                         fin_mes=fin_mes)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        
        # Crear usuario administrador por defecto
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(
                username='admin',
                email='admin@control.com',
                password_hash=generate_password_hash('admin123'),
                is_admin=True
            )
            db.session.add(admin)
            db.session.commit()
    
    # En producción, gunicorn maneja el servidor
    # En desarrollo local, usar el servidor de Flask
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') != 'production'
    app.run(host='0.0.0.0', port=port, debug=debug)
