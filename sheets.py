import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime
import os
import json

# ============================================
# CONFIGURACIÓN
# ============================================

SPREADSHEET_NAME = 'Resultados de Orientación vocacional'
SCOPE = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']

_cached_df = None
_last_update = None

# ============================================
# CREDENCIALES
# ============================================

def get_credentials():
    """Obtiene credenciales desde variable de entorno (Render) o archivo local"""
    creds_json = os.getenv('GOOGLE_CREDENTIALS_JSON')
    
    if creds_json:
        # Producción (Render)
        print("🔐 Usando credenciales desde variable de entorno")
        credentials_dict = json.loads(creds_json)
        return ServiceAccountCredentials.from_json_keyfile_dict(credentials_dict, SCOPE)
    else:
        # Desarrollo local
        print("🔐 Usando credenciales desde archivo local")
        return ServiceAccountCredentials.from_json_keyfile_name(
            'drive-python-446800-fe3f38b5a4b3.json', 
            SCOPE
        )

# ============================================
# CONEXIÓN
# ============================================

def conectar_google_sheets():
    global _cached_df, _last_update
    try:
        print("📊 Conectando con Google Sheets...")
        creds = get_credentials()
        client = gspread.authorize(creds)
        sheet = client.open(SPREADSHEET_NAME).get_worksheet(0)
        data = sheet.get_all_records() 
        df = pd.DataFrame(data)
        
        if 'Dirección de correo electrónico' in df.columns:
            df['email_normalized'] = df['Dirección de correo electrónico'].str.lower().str.strip()
        
        _cached_df = df
        _last_update = datetime.now()
        print(f"✅ Conectado exitosamente: {len(df)} registros encontrados")
        return df
    except Exception as e:
        print(f"❌ Error al conectar con Google Sheets: {e}")
        import traceback
        traceback.print_exc()
        return None

def obtener_dataframe():
    global _cached_df
    if _cached_df is None:
        _cached_df = conectar_google_sheets()
    return _cached_df

def refrescar_datos():
    global _cached_df
    _cached_df = None
    df = conectar_google_sheets()
    return df is not None

# ============================================
# BÚSQUEDA
# ============================================

def buscar_usuario_por_email(email):
    df = obtener_dataframe()
    if df is None or df.empty:
        return None
    email_normalized = email.lower().strip()
    resultado = df[df['email_normalized'] == email_normalized]
    if len(resultado) == 0:
        print(f"⚠️ No se encontraron resultados para: {email}")
        return None
    return resultado.iloc[0]

def obtener_datos_basicos(usuario):
    if usuario is None:
        return None
    return {
        'fecha': str(usuario.get('Fecha', '')),
        'nombre': str(usuario.get('Nombre', '')),
        'email': str(usuario.get('Dirección de correo electrónico', '')),
        'edad': str(usuario.get('Edad', '')),
        'genero': str(usuario.get('Genero', '')),
        'escolaridad': str(usuario.get('Escolaridad', '')),
        'areas': str(usuario.get('Areas', ''))
    }

# ============================================
# CARRERAS
# ============================================

def formatear_carreras(a1, a2, a3, a4):
    carreras = []
    def procesar_columna(columna):
        if pd.notna(columna) and str(columna).strip():
            items = str(columna).split('\n')
            for item in items:
                item = item.strip()
                if item:
                    carreras.append(item)
    procesar_columna(a1)
    procesar_columna(a2)
    procesar_columna(a3)
    procesar_columna(a4)
    return carreras if carreras else ['No se especificaron carreras']

def obtener_carreras_usuario(usuario):
    if usuario is None:
        return ['No se especificaron carreras']
    return formatear_carreras(
        usuario.get('A1', ''),
        usuario.get('A2', ''),
        usuario.get('A3', ''),
        usuario.get('A4', '')
    )

# ============================================
# DESCRIPCIONES
# ============================================

def procesar_descripcion(texto):
    if pd.isna(texto) or not str(texto).strip():
        return ['Sin información disponible']
    texto_str = str(texto).strip()
    if '\n' in texto_str:
        items = texto_str.split('\n')
    elif '.' in texto_str:
        items = texto_str.split('.')
    else:
        return [texto_str] if texto_str else ['Sin información disponible']
    items_limpios = []
    for item in items:
        item_limpio = item.strip()
        if item_limpio:
            if not item_limpio.startswith('•'):
                item_limpio = f" {item_limpio}"
            items_limpios.append(item_limpio)
    return items_limpios if items_limpios else ['Sin información disponible']

def obtener_descripciones_usuario(usuario):
    if usuario is None:
        return {
            'aptitudes': ['Sin información disponible'],
            'inteligencias': ['Sin información disponible'],
            'kuder': ['Sin información disponible']
        }
    return {
        'aptitudes': procesar_descripcion(usuario.get('Descripción_Aptitudes_intereses', '')),
        'inteligencias': procesar_descripcion(usuario.get('Descripción_Inteligencias_Multiples', '')),
        'kuder': procesar_descripcion(usuario.get('Descripción_Test_de_Kuder', ''))
    }

# ============================================
# FUNCIÓN PRINCIPAL
# ============================================

def obtener_resultados_completos(email):
    usuario = buscar_usuario_por_email(email)
    if usuario is None:
        return None
    datos_basicos = obtener_datos_basicos(usuario)
    descripciones = obtener_descripciones_usuario(usuario)
    carreras = obtener_carreras_usuario(usuario)
    return {
        'fecha': datos_basicos['fecha'],
        'nombre': datos_basicos['nombre'],
        'email': datos_basicos['email'],
        'edad': datos_basicos['edad'],
        'genero': datos_basicos['genero'],
        'escolaridad': datos_basicos['escolaridad'],
        'areas': datos_basicos['areas'],
        'aptitudes': descripciones['aptitudes'],
        'inteligencias': descripciones['inteligencias'],
        'kuder': descripciones['kuder'],
        'carreras': carreras
    }

# ============================================
# UTILIDADES
# ============================================

def obtener_total_registros():
    df = obtener_dataframe()
    return len(df) if df is not None else 0

def obtener_ultima_actualizacion():
    return _last_update

def listar_columnas():
    df = obtener_dataframe()
    return list(df.columns) if df is not None else []

def diagnostico():
    print("\n" + "="*60)
    print("🔍 DIAGNÓSTICO DE GOOGLE SHEETS")
    print("="*60)
    df = obtener_dataframe()
    if df is None:
        print("❌ No se pudo conectar con Google Sheets")
        return
    print(f"\n✅ Conexión exitosa")
    print(f"📊 Total de registros: {len(df)}")
    print(f"📋 Total de columnas: {len(df.columns)}")
    print(f"🕐 Última actualización: {_last_update}")
    print("\n" + "="*60 + "\n")

# Inicialización
print("🚀 Inicializando módulo de Google Sheets...")
conectar_google_sheets()

