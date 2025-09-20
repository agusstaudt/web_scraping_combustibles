#%% librerias
import pymysql
import pandas as pd

#%% 1. Configuración de credenciales (inseguro para producción, OK para pruebas en Colab)
config = {
    'user': 'dev',
    'password': 'rtk099%!ZmY&101',
    'host': '45.228.176.80',
    'port': 43306,
    'database': 'datos_combustibles'
}

#%% 2. Conectarse a la base de datos MySQL
cnx = pymysql.connect(
    host=config['host'],
    user=config['user'],
    password=config['password'],
    port=config['port'],
    database=config['database']
)

#%% 3. Leer la tabla 'base_misiones'
query = "SELECT * FROM base_misiones"
df = pd.read_sql(query, cnx)

#%% 4. Cerrar la conexión
cnx.close()

#%% 5. Mostrar primeras filas
df.head()
# %%
