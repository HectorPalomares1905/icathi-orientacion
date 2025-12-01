import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime
CREDENTIALS_FILE = 'drive-python-446800-fe3f38b5a4b3.json'
SPREADSHEET_NAME = 'Resultados de Orientación vocacional'
SCOPE = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
# Variable global para cachear los datos
_cached_df = None
_last_update = None

def conectar_google_sheets():
    global _cached_df, _last_update
    try:
        print("📊 Conectando con Google Sheets...")
        # 1. Autenticación
        creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, SCOPE)
        client = gspread.authorize(creds)
        # 2. Obtener datos (Hoja 1)
        sheet = client.open(SPREADSHEET_NAME).get_worksheet(0)
        data = sheet.get_all_records() 
        # 3. Convertir a DataFrame
        df = pd.DataFrame(data)
        # 4. Normalizar emails para búsquedas
        if 'Dirección de correo electrónico' in df.columns:
            df['email_normalized'] = df['Dirección de correo electrónico'].str.lower().str.strip()
        # 5. Cachear datos
        _cached_df = df
        _last_update = datetime.now()
        print(f"✅ Conectado exitosamente: {len(df)} registros encontrados")
        return df
    except Exception as e:
        print(f"❌ Error al conectar con Google Sheets: {e}")
        return None


def obtener_dataframe():
    """
    Obtiene el DataFrame, usando cache si está disponible
    
    Returns:
        pd.DataFrame: DataFrame con los datos
    """
    global _cached_df
    
    if _cached_df is None:
        _cached_df = conectar_google_sheets()
    
    return _cached_df


def refrescar_datos():
    """
    Fuerza una actualización de los datos desde Google Sheets
    
    Returns:
        bool: True si la actualización fue exitosa
    """
    global _cached_df
    _cached_df = None
    df = conectar_google_sheets()
    return df is not None


# ============================================
# FUNCIONES DE BÚSQUEDA DE USUARIOS
# ============================================

def buscar_usuario_por_email(email):
    """
    Busca un usuario por su email en el DataFrame
    
    Args:
        email (str): Correo electrónico del usuario
        
    Returns:
        pd.Series: Fila del usuario o None si no se encuentra
    """
    df = obtener_dataframe()
    
    if df is None or df.empty:
        return None
    
    # Normalizar el email de búsqueda
    email_normalized = email.lower().strip()
    
    # Buscar por email normalizado
    resultado = df[df['email_normalized'] == email_normalized]
    
    if len(resultado) == 0:
        print(f"⚠️  No se encontraron resultados para: {email}")
        return None
    
    # Retornar la primera coincidencia
    return resultado.iloc[0]


def obtener_datos_basicos(usuario):
    """
    Extrae los datos básicos de un usuario
    
    Args:
        usuario (pd.Series): Fila del usuario
        
    Returns:
        dict: Diccionario con los datos básicos
    """
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
# FUNCIONES DE PROCESAMIENTO DE CARRERAS
# ============================================

def formatear_carreras(a1, a2, a3, a4):
    """
    Formatea las carreras de las columnas A1, A2, A3, A4
    
    Args:
        a1, a2, a3, a4: Contenido de las columnas de carreras
        
    Returns:
        list: Lista de carreras formateadas
    """
    carreras = []
    
    # Función auxiliar para procesar cada columna
    def procesar_columna(columna):
        if pd.notna(columna) and str(columna).strip():
            # Dividir por saltos de línea
            items = str(columna).split('\n')
            for item in items:
                item = item.strip()
                if item:
                    carreras.append(item)
    
    # Procesar todas las columnas
    procesar_columna(a1)
    procesar_columna(a2)
    procesar_columna(a3)
    procesar_columna(a4)
    
    return carreras if carreras else ['No se especificaron carreras']


def obtener_carreras_usuario(usuario):
    """
    Obtiene las carreras recomendadas para un usuario
    
    Args:
        usuario (pd.Series): Fila del usuario
        
    Returns:
        list: Lista de carreras
    """
    if usuario is None:
        return ['No se especificaron carreras']
    
    a1 = usuario.get('A1', '')
    a2 = usuario.get('A2', '')
    a3 = usuario.get('A3', '')
    a4 = usuario.get('A4', '')
    
    return formatear_carreras(a1, a2, a3, a4)


# ============================================
# FUNCIONES DE PROCESAMIENTO DE DESCRIPCIONES
# ============================================

def procesar_descripcion(texto):
    """
    Procesa una descripción dividiéndola en una lista de items
    
    Args:
        texto (str): Texto de la descripción
        
    Returns:
        list: Lista de descripciones individuales
    """
    if pd.isna(texto) or not str(texto).strip():
        return ['Sin información disponible']
    
    texto_str = str(texto).strip()
    
    # Dividir por saltos de línea o por puntos
    if '\n' in texto_str:
        items = texto_str.split('\n')
    elif '.' in texto_str:
        items = texto_str.split('.')
    else:
        # Si no hay separadores, devolver como un solo item
        return [texto_str] if texto_str else ['Sin información disponible']
    
    # Limpiar y filtrar items vacíos
    items_limpios = []
    for item in items:
        item_limpio = item.strip()
        if item_limpio:
            # Agregar viñeta si no la tiene
            if not item_limpio.startswith('•'):
                item_limpio = f" {item_limpio}"
            items_limpios.append(item_limpio)
    
    return items_limpios if items_limpios else ['Sin información disponible']


def obtener_descripciones_usuario(usuario):
    """
    Obtiene todas las descripciones de los tests de un usuario
    
    Args:
        usuario (pd.Series): Fila del usuario
        
    Returns:
        dict: Diccionario con las descripciones de cada test
    """
    if usuario is None:
        return {
            'aptitudes': ['Sin información disponible'],
            'inteligencias': ['Sin información disponible'],
            'kuder': ['Sin información disponible']
        }
    
    # Obtener descripciones directamente de las columnas
    desc_aptitudes = usuario.get('Descripción_Aptitudes_intereses', '')
    desc_inteligencias = usuario.get('Descripción_Inteligencias_Multiples', '')
    desc_kuder = usuario.get('Descripción_Test_de_Kuder', '')
    
    return {
        'aptitudes': procesar_descripcion(desc_aptitudes),
        'inteligencias': procesar_descripcion(desc_inteligencias),
        'kuder': procesar_descripcion(desc_kuder)
    }


# ============================================
# FUNCIÓN PRINCIPAL
# ============================================

def obtener_resultados_completos(email):
    """
    Obtiene todos los resultados procesados de un usuario
    
    Args:
        email (str): Correo electrónico del usuario
        
    Returns:
        dict: Diccionario completo con todos los datos del usuario o None
    """
    # 1. Buscar usuario
    usuario = buscar_usuario_por_email(email)
    
    if usuario is None:
        return None
    
    # 2. Obtener datos básicos
    datos_basicos = obtener_datos_basicos(usuario)
    
    # 3. Obtener descripciones de tests
    descripciones = obtener_descripciones_usuario(usuario)
    
    # 4. Obtener carreras
    carreras = obtener_carreras_usuario(usuario)
    
    # 5. Combinar todo
    resultado = {
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
    
    return resultado


# ============================================
# FUNCIONES DE UTILIDAD
# ============================================

def obtener_total_registros():
    """
    Obtiene el total de registros en la hoja
    
    Returns:
        int: Número total de registros
    """
    df = obtener_dataframe()
    return len(df) if df is not None else 0


def obtener_ultima_actualizacion():
    """
    Obtiene la fecha/hora de la última actualización
    
    Returns:
        datetime: Fecha y hora de última actualización o None
    """
    return _last_update


def listar_columnas():
    """
    Lista todas las columnas disponibles en el DataFrame
    
    Returns:
        list: Lista de nombres de columnas
    """
    df = obtener_dataframe()
    return list(df.columns) if df is not None else []


# ============================================
# FUNCIÓN DE DIAGNÓSTICO
# ============================================

def diagnostico():
    """
    Imprime información de diagnóstico sobre la conexión y datos
    """
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
    
    print("\n📝 Columnas principales:")
    columnas_importantes = [
        'Nombre', 
        'Dirección de correo electrónico',
        'Edad',
        'Escolaridad',
        'Areas',
        'Descripción_Aptitudes_intereses',
        'Descripción_Inteligencias_Multiples',
        'Descripción_Test_de_Kuder',
        'A1', 'A2', 'A3', 'A4'
    ]
    
    for col in columnas_importantes:
        existe = "✅" if col in df.columns else "❌"
        print(f"   {existe} {col}")
    
    print("\n" + "="*60 + "\n")


# Conectar automáticamente al importar el módulo
print("🚀 Inicializando conexión con Google Sheets...")
conectar_google_sheets()