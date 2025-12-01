from flask import Flask, render_template, request, redirect, url_for, session, flash
from auth import AuthManager
import sheets
import secrets

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)  # Clave secreta para sesiones

# Inicializa el gestor de autenticación
auth_manager = AuthManager()

@app.route('/')
def index():
    """Página principal - redirige al login o dashboard según estado de sesión"""
    if 'user_email' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Página de login"""
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        
        # Valida que los campos no estén vacíos
        if not email or not password:
            flash('Por favor ingresa tu email y contraseña', 'error')
            return render_template('login.html')
        
        # Autentica al usuario
        user = auth_manager.authenticate(email, password)
        
        if user:
            # Guarda la información en la sesión
            session['user_email'] = user['email']
            session['user_name'] = user['nombre']
            flash(f'¡Bienvenido/a {user["nombre"]}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Email o contraseña incorrectos', 'error')
            return render_template('login.html')
    
    # Si ya está logueado, redirige al dashboard
    if 'user_email' in session:
        return redirect(url_for('dashboard'))
    
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    """Dashboard del usuario - muestra sus resultados"""
    # Verifica que el usuario esté logueado
    if 'user_email' not in session:
        flash('Por favor inicia sesión para ver tus resultados', 'error')
        return redirect(url_for('login'))
    
    # Obtiene el email del usuario desde la sesión
    user_email = session['user_email']
    
    # Obtiene los resultados del usuario desde Google Sheets
    data = sheets.obtener_resultados_completos(user_email)
    
    if data is None:
        flash('No se encontraron resultados para tu cuenta. Contacta al administrador.', 'error')
        user_name = session.get('user_name', 'Usuario')
        return f"""
        <!DOCTYPE html>
        <html lang="es">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Sin resultados - ICATHI 4.0</title>
            <link rel="stylesheet" href="{url_for('static', filename='styles.css')}">
        </head>
        <body>
            <div class="container" style="text-align: center; padding: 50px;">
                <h1>⚠️ Sin resultados</h1>
                <p>Hola {user_name}, no se encontraron resultados para tu cuenta.</p>
                <p>Por favor contacta al administrador.</p>
                <br>
                <a href="{url_for('logout')}" style="background: #d05a7e; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Cerrar Sesión</a>
            </div>
        </body>
        </html>
        """
    
    return render_template('dashboard.html', data=data)

@app.route('/logout')
def logout():
    """Cierra la sesión del usuario"""
    user_name = session.get('user_name', 'Usuario')
    session.clear()
    flash(f'Hasta luego, {user_name}. Has cerrado sesión correctamente.', 'info')
    return redirect(url_for('login'))

@app.route('/refresh')
def refresh():
    """Refresca los datos desde Google Sheets"""
    if 'user_email' not in session:
        return redirect(url_for('login'))
    
    if sheets.refrescar_datos():
        flash('Datos actualizados correctamente', 'success')
    else:
        flash('Error al actualizar los datos', 'error')
    
    return redirect(url_for('dashboard'))

@app.errorhandler(404)
def page_not_found(e):
    """Maneja errores 404"""
    return f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>404 - Página no encontrada</title>
        <link rel="stylesheet" href="{url_for('static', filename='styles.css')}">
    </head>
    <body>
        <div class="container" style="text-align: center; padding: 50px;">
            <h1 style="font-size: 72px; color: #d05a7e;">404</h1>
            <h2 style="color: #3d5a96;">Página no encontrada</h2>
            <p>La página que buscas no existe.</p>
            <br>
            <a href="{url_for('index')}" style="background: #3d5a96; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Ir al inicio</a>
        </div>
    </body>
    </html>
    """, 404

@app.errorhandler(500)
def internal_error(e):
    """Maneja errores 500"""
    return f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>500 - Error interno</title>
        <link rel="stylesheet" href="{url_for('static', filename='styles.css')}">
    </head>
    <body>
        <div class="container" style="text-align: center; padding: 50px;">
            <h1 style="font-size: 72px; color: #d05a7e;">500</h1>
            <h2 style="color: #3d5a96;">Error interno del servidor</h2>
            <p>Lo sentimos, algo salió mal. Por favor intenta de nuevo más tarde.</p>
            <br>
            <a href="{url_for('index')}" style="background: #3d5a96; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Ir al inicio</a>
        </div>
    </body>
    </html>
    """, 500

if __name__ == '__main__':
    print("\n" + "="*70)
    print("🚀 INICIANDO SERVIDOR ICATHI 4.0 - SISTEMA DE ORIENTACIÓN VOCACIONAL")
    print("="*70)
    
    # Verifica la conexión con usuarios
    print("\n📋 Verificando archivo de usuarios...")
    total_users = auth_manager.get_total_users()
    if total_users > 0:
        print(f"✅ {total_users} usuarios registrados")
    else:
        print("⚠️  No se cargaron usuarios. Verifica el archivo 'Usuarios.xlsx'")
    
    # Verifica la conexión con Google Sheets
    print("\n📊 Verificando conexión con Google Sheets...")
    total_records = sheets.obtener_total_registros()
    if total_records > 0:
        print(f"✅ {total_records} registros de resultados encontrados")
        ultima_act = sheets.obtener_ultima_actualizacion()
        if ultima_act:
            print(f"🕐 Última actualización: {ultima_act.strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        print("⚠️  No se pudo conectar con Google Sheets")
    
    print("\n🌐 Servidor corriendo en: http://127.0.0.1:5000")
    print("📱 Para detener el servidor presiona: Ctrl+C")
    print("\n💡 Instrucciones:")
    print("   1. Abre http://127.0.0.1:5000 en tu navegador")
    print("   2. Inicia sesión con tu email y contraseña")
    print("   3. Visualiza tus resultados del test vocacional")
    print("\n" + "="*70 + "\n")
    
    app.run(debug=True, port=5000, host='0.0.0.0')