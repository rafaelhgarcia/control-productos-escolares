# 🚀 GUÍA COMPLETA: Desplegar en la Nube (PERMANENTE)

## 📋 Opciones Disponibles

### ✅ **Render.com** (RECOMENDADO - Más fácil)
- ✅ Gratis para empezar
- ✅ PostgreSQL incluido gratis
- ✅ Despliegue automático desde GitHub
- ✅ URL permanente: `tu-app.onrender.com`

### ✅ **Railway.app** (Alternativa)
- ✅ Gratis con límites generosos
- ✅ PostgreSQL incluido
- ✅ Muy fácil de usar
- ✅ URL permanente: `tu-app.railway.app`

---

## 🎯 OPCIÓN 1: RENDER.COM (Paso a Paso)

### Paso 1: Preparar GitHub

1. **Instala Git** (si no lo tienes):
   - Descarga: https://git-scm.com/download/win
   - Instala con opciones por defecto

2. **Crea cuenta en GitHub:**
   - Ve a: https://github.com
   - Crea cuenta gratuita

3. **Sube tu proyecto a GitHub:**
   ```powershell
   cd "C:\Users\Horacio Garcia\control_productos_escolares"
   git init
   git add .
   git commit -m "Primera versión - Control Productos Escolares"
   git branch -M main
   git remote add origin https://github.com/TU_USUARIO/control-productos-escolares.git
   git push -u origin main
   ```
   ⚠️ **Reemplaza `TU_USUARIO` con tu nombre de usuario de GitHub**

### Paso 2: Crear cuenta en Render

1. Ve a: https://render.com
2. Clic en **"Get Started for Free"**
3. Conecta con tu cuenta de GitHub

### Paso 3: Crear Base de Datos PostgreSQL

1. En el dashboard de Render, clic en **"New +"**
2. Selecciona **"PostgreSQL"**
3. Configura:
   - **Name:** `control-productos-db`
   - **Database:** `control_productos`
   - **User:** (se genera automáticamente)
   - **Region:** Elige el más cercano (US East, etc.)
   - **Plan:** Free
4. Clic en **"Create Database"**
5. **IMPORTANTE:** Copia la **"Internal Database URL"** (la necesitarás después)

### Paso 4: Desplegar la Aplicación

1. En el dashboard, clic en **"New +"**
2. Selecciona **"Web Service"**
3. Conecta tu repositorio de GitHub
4. Selecciona el repositorio `control-productos-escolares`
5. Configura:
   - **Name:** `control-productos-escolares`
   - **Region:** El mismo que la base de datos
   - **Branch:** `main`
   - **Root Directory:** (dejar vacío)
   - **Environment:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app`
6. En **"Environment Variables"**, agrega:
   - **Key:** `DATABASE_URL`
   - **Value:** Pega la "Internal Database URL" que copiaste antes
   - **Key:** `SECRET_KEY`
   - **Value:** Genera una clave secreta (usa: https://randomkeygen.com/)
   - **Key:** `FLASK_ENV`
   - **Value:** `production`
7. Clic en **"Create Web Service"**

### Paso 5: Esperar el Despliegue

- Render comenzará a construir tu aplicación (5-10 minutos)
- Verás logs en tiempo real
- Cuando termine, verás: **"Your service is live"**
- Tu URL será: `https://control-productos-escolares.onrender.com`

### Paso 6: Inicializar la Base de Datos

1. Visita tu URL: `https://tu-app.onrender.com`
2. La primera vez, la base de datos se creará automáticamente
3. El usuario admin se creará automáticamente:
   - Usuario: `admin`
   - Contraseña: `admin123`

---

## 🎯 OPCIÓN 2: RAILWAY.APP (Alternativa)

### Paso 1: Crear cuenta en Railway

1. Ve a: https://railway.app
2. Clic en **"Start a New Project"**
3. Conecta con GitHub

### Paso 2: Crear Proyecto

1. Clic en **"New Project"**
2. Selecciona **"Deploy from GitHub repo"**
3. Selecciona tu repositorio `control-productos-escolares`

### Paso 3: Agregar Base de Datos

1. En tu proyecto, clic en **"+ New"**
2. Selecciona **"Database"** → **"Add PostgreSQL"**
3. Railway creará automáticamente la base de datos

### Paso 4: Configurar Variables de Entorno

1. Ve a la pestaña **"Variables"**
2. Railway ya agregó `DATABASE_URL` automáticamente
3. Agrega manualmente:
   - **SECRET_KEY:** (genera una clave secreta)
   - **FLASK_ENV:** `production`

### Paso 5: Desplegar

1. Railway detectará automáticamente que es una app Python
2. Desplegará automáticamente
3. Tu URL será: `https://tu-app.railway.app`

---

## 🔐 SEGURIDAD IMPORTANTE

### Cambiar credenciales por defecto:

1. Una vez desplegado, inicia sesión como admin
2. Ve a configuración de usuarios
3. Cambia la contraseña del admin inmediatamente

### Configurar SECRET_KEY seguro:

- Usa: https://randomkeygen.com/
- Copia una clave de 64 caracteres
- Agrégala como variable de entorno `SECRET_KEY`

---

## 📱 USAR LA APLICACIÓN DESPLEGADA

### Para Administrador:
```
https://tu-app.onrender.com/login
Usuario: admin
Contraseña: admin123
```

### Para Escuelas (QR Codes):
- Los QR codes deben usar la nueva URL
- Ejemplo: `https://tu-app.onrender.com/pedidos/escuela/ESC_XXXXX`
- **Necesitarás regenerar los QR codes** con la nueva URL

### Para Supervisores (QR Codes):
- Similar a escuelas
- Ejemplo: `https://tu-app.onrender.com/supervisor/acceso/SUP_XXXXX`
- **Regenera los QR codes** con la nueva URL

---

## 🔄 ACTUALIZAR LA APLICACIÓN

Cada vez que hagas cambios:

```powershell
cd "C:\Users\Horacio Garcia\control_productos_escolares"
git add .
git commit -m "Descripción de los cambios"
git push
```

Render/Railway detectará los cambios y desplegará automáticamente.

---

## 💰 COSTOS

### Render.com:
- **Free Tier:** Gratis para siempre
- Límites: La app se "duerme" después de 15 min sin uso (se despierta en 30 seg)
- Para producción 24/7: $7/mes

### Railway.app:
- **Free Tier:** $5 créditos gratis/mes
- Después: Pay-as-you-go (muy económico)

---

## 🆘 SOLUCIÓN DE PROBLEMAS

### La app no inicia:
- Verifica los logs en Render/Railway
- Revisa que `requirements.txt` tenga todas las dependencias
- Verifica que `DATABASE_URL` esté configurada

### Error de base de datos:
- Verifica que PostgreSQL esté creado
- Verifica que `DATABASE_URL` sea correcta
- Asegúrate de que la URL use `postgresql://` no `postgres://`

### Los QR codes no funcionan:
- Los QR codes tienen URLs hardcodeadas
- Necesitas regenerarlos desde el panel admin con la nueva URL

---

## ✅ CHECKLIST FINAL

- [ ] Proyecto subido a GitHub
- [ ] Cuenta creada en Render/Railway
- [ ] Base de datos PostgreSQL creada
- [ ] Aplicación desplegada
- [ ] Variables de entorno configuradas
- [ ] URL funcionando
- [ ] Login de admin funciona
- [ ] QR codes regenerados con nueva URL
- [ ] Contraseña de admin cambiada

---

## 🎉 ¡LISTO!

Tu aplicación está en la nube y accesible desde cualquier lugar con internet.

**URL Permanente:** `https://tu-app.onrender.com` (o railway.app)

¡Comparte esta URL con tus supervisores y escuelas!

