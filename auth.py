import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import os
import json

class AuthManager:
    """Gestor de autenticación de usuarios desde Google Sheets"""
    
    def __init__(self, spreadsheet_id='1dg8BX4N1t0Owxkv65fxmRLhTTU4h9Vj8GOzWIZ0k1NM', sheet_name='Usuarios'):
        self.spreadsheet_id = spreadsheet_id
        self.sheet_name = sheet_name
        self.users_df = None
        self.load_users()
    
    def get_credentials(self):
        """Obtiene credenciales desde variable de entorno (Render) o archivo local"""
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        
        # Intentar obtener desde variable de entorno
        creds_json = os.getenv('GOOGLE_CREDENTIALS_JSON')
        
        if creds_json:
            # Producción (Render)
            print("🔐 [Auth] Usando credenciales desde variable de entorno")
            credentials_dict = json.loads(creds_json)
            return ServiceAccountCredentials.from_json_keyfile_dict(credentials_dict, scope)
        else:
            # Desarrollo local
            print("🔐 [Auth] Usando credenciales desde archivo local")
            return ServiceAccountCredentials.from_json_keyfile_name(
                'drive-python-446800-fe3f38b5a4b3.json', 
                scope
            )
    
    def load_users(self):
        """Carga los usuarios desde Google Sheets"""
        try:
            print(f"📊 Cargando usuarios desde Google Sheets...")
            
            # 1. Autenticación
            creds = self.get_credentials()
            client = gspread.authorize(creds)
            
            # 2. Abrir hoja por ID
            spreadsheet = client.open_by_key(self.spreadsheet_id)
            
            # 3. Obtener worksheet por nombre
            worksheet = spreadsheet.worksheet(self.sheet_name)
            
            # 4. Obtener todos los datos
            data = worksheet.get_all_records()
            
            # 5. Convertir a DataFrame
            self.users_df = pd.DataFrame(data)
            
            print(f"✅ Usuarios cargados: {len(self.users_df)} registros")
            
            # 6. Verificar columnas necesarias
            required_columns = ['Dirección de correo electrónico', 'Contraseña', 'Nombre completo']
            missing_columns = [col for col in required_columns if col not in self.users_df.columns]
            
            if missing_columns:
                print(f"❌ Error: Faltan columnas: {missing_columns}")
                print(f"📋 Columnas disponibles: {list(self.users_df.columns)}")
                return False
            
            # 7. Normalizar emails (minúsculas y sin espacios)
            self.users_df['email_normalized'] = self.users_df['Dirección de correo electrónico'].str.lower().str.strip()
            
            return True
            
        except Exception as e:
            print(f"❌ Error al cargar usuarios desde Google Sheets: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def authenticate(self, email, password):
        """
        Autentica un usuario
        
        Args:
            email: Correo electrónico del usuario
            password: Contraseña del usuario
            
        Returns:
            dict: Información del usuario si la autenticación es exitosa, None si falla
        """
        if self.users_df is None or self.users_df.empty:
            print("⚠️ No hay usuarios cargados")
            return None
        
        # Normalizar el email de entrada
        email_normalized = email.lower().strip()
        
        # Buscar el usuario
        user = self.users_df[
            (self.users_df['email_normalized'] == email_normalized) & 
            (self.users_df['Contraseña'].astype(str) == str(password))
        ]
        
        if len(user) == 0:
            print(f"⚠️ Login fallido para: {email}")
            return None
        
        # Retornar la información del usuario
        user_data = user.iloc[0]
        print(f"✅ Login exitoso: {user_data['Nombre completo']}")
        return {
            'email': user_data['Dirección de correo electrónico'],
            'nombre': user_data['Nombre completo'],
            'password': user_data['Contraseña']
        }
    
    def get_user_by_email(self, email):
        """
        Obtiene información de un usuario por su email
        
        Args:
            email: Correo electrónico del usuario
            
        Returns:
            dict: Información del usuario o None si no existe
        """
        if self.users_df is None or self.users_df.empty:
            return None
        
        email_normalized = email.lower().strip()
        user = self.users_df[self.users_df['email_normalized'] == email_normalized]
        
        if len(user) == 0:
            return None
        
        user_data = user.iloc[0]
        return {
            'email': user_data['Dirección de correo electrónico'],
            'nombre': user_data['Nombre completo'],
            'password': user_data['Contraseña']
        }
    
    def user_exists(self, email):
        """
        Verifica si un usuario existe
        
        Args:
            email: Correo electrónico del usuario
            
        Returns:
            bool: True si el usuario existe, False si no
        """
        return self.get_user_by_email(email) is not None
    
    def get_total_users(self):
        """Retorna el total de usuarios registrados"""
        if self.users_df is None or self.users_df.empty:
            return 0
        return len(self.users_df)
    
    def refresh_users(self):
        """Recarga los usuarios desde Google Sheets"""
        print("🔄 Refrescando datos de usuarios...")
        return self.load_users()