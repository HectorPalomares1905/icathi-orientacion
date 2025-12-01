import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd

# 1. Configuración
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name('drive-python-446800-70fe8811bed3.json', scope)
client = gspread.authorize(creds)

# 2. Obtener datos (Hoja 1)
sheet = client.open('Resultados de Orientación vocacional').get_worksheet(0)
data = sheet.get_all_records()

# 3. DataFrame e impresión
df = pd.DataFrame(data)
print(df.columns)