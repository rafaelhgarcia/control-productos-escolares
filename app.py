# ... (Importaciones y Configuraciones) ...

# ---------------------------------------------
# Rutas
# ---------------------------------------------

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    # Asegúrate de que tienes 'login.html'
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    # ... (Lógica de login) ...
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    # ... (Lógica de logout) ...
    return redirect(url_for('login'))

# --- Dashboard y Gestión de Productos (Rutas dummy para contexto) ---

@app.route('/dashboard')
@login_required
def dashboard():
    products = Product.query.filter_by(user_id=current_user.id).order_by(Product.created_at.desc()).all()
    bodegas = Bodega.query.all()
    supervisores = Supervisor.query.all()
    escuelas = Escuela.query.all()
    # Usa 'dashboard.html'
    return render_template('dashboard.html', products=products, bodegas=bodegas, supervisores=supervisores, escuelas=escuelas)

@app.route('/product/add', methods=['GET', 'POST'])
@login_required
def add_product():
    # ... (Lógica de agregar producto) ...
    # Usa 'crear_producto.html'
    return render_template('crear_producto.html') # ***Ajustado para usar crear_producto.html***

@app.route('/product/qr/<code>')
@login_required
def generate_qr(code):
    # ... (Lógica de QR) ...
    return render_template('qr_code.html', qr_base64=qr_base64, product=product)

# --- RUTAS DE GESTIÓN DE PRODUCTOS ---
@app.route('/productos')
@login_required
def list_products():
    productos = Product.query.filter_by(user_id=current_user.id).all()
    # Usa 'productos.html' (Asumo que renombraste list_products.html a productos.html o viceversa)
    return render_template('productos.html', productos=productos) # ***Ajustado para usar productos.html***

@app.route('/productos/crear')
@login_required
def redirect_to_add_product():
    # Redirige el enlace amigable a la función real de creación
    return redirect(url_for('add_product'))


# --- RUTAS DE GESTIÓN DE BODEGAS ---
@app.route('/bodegas')
@login_required
def list_bodegas():
    bodegas = Bodega.query.all()  
    # Usa 'bodegas.html'
    return render_template('bodegas.html', bodegas=bodegas) # ***Ajustado para usar bodegas.html***

@app.route('/bodegas/crear')
@login_required
def create_bodega_page():
    # Usa 'crear_bodega.html'
    return render_template('crear_bodega.html') # ***Ajustado para usar crear_bodega.html***


# --- RUTAS DE GESTIÓN DE SUPERVISORES ---
@app.route('/supervisores')
@login_required
def list_supervisores():
    supervisores = Supervisor.query.all()
    # Usa 'supervisores.html'
    return render_template('supervisores.html', supervisores=supervisores) # ***Ajustado para usar supervisores.html***

@app.route('/supervisores/crear')
@login_required
def create_supervisor_page():
    # Usa 'crear_supervisor.html'
    return render_template('crear_supervisor.html') # ***Ajustado para usar crear_supervisor.html***


# --- RUTAS DE GESTIÓN DE ESCUELAS ---
@app.route('/escuelas')
@login_required
def list_escuelas():
    escuelas = Escuela.query.all()
    # Usa 'escuelas.html'
    return render_template('escuelas.html', escuelas=escuelas) # ***Ajustado para usar escuelas.html***

@app.route('/escuelas/crear')
@login_required
def create_escuela_page():
    # Usa 'crear_escuela.html'
    return render_template('crear_escuela.html') # ***Ajustado para usar crear_escuela.html***
