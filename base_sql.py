'''
Creación de la base de datos de combustibles 
Base creada en mysql, en el servidor que tenemos a disposicion desde la OGD
Cada nuevo set de queries se van a ir subiendo a la tabla de combustibles generada 
'''

#%% librerias
with open("librerias.py") as f:
    exec(f.read())

#%% carga de base combustibles a subir (bases parciales de 500 consultas)
archivos = glob.glob('inputs/data/combustibles_misiones_parcial.csv')
if not archivos:
    raise FileNotFoundError("No se encontraron archivos de combustibles en el directorio.")

archivo_csv = max(archivos, key=os.path.getmtime)
print(f"Archivo encontrado: {archivo_csv}")
df = pd.read_csv(archivo_csv)

#%%  creacion de datos de combustibles
# 0. Conexión al servidor MySQL 
load_dotenv() # carga de archivo con credenciales

config = {
    'user': os.getenv('MYSQL_USER'),
    'password': os.getenv('MYSQL_PASSWORD'),
    'host': os.getenv('MYSQL_HOST'),
    'port': int(os.getenv('MYSQL_PORT')),
}

cnx = pymysql.connect(
    host=config['host'],
    user=config['user'],
    password=config['password'],
    port=config['port']
)

# Crear un cursor
cursor = cnx.cursor()

# 1. Crear una nueva base de datos
new_db_name = 'datos_combustibles'
cursor.execute(f"CREATE DATABASE IF NOT EXISTS {new_db_name}")
print(f"Base de datos '{new_db_name}' creada exitosamente, si no existe previamente.")

# 2. Crear la tabla
# especificar base de datos
cursor.execute(f"USE `{new_db_name}`;")
# nombre
table_name = 'base_misiones'

# Limpiar nombres de columnas
print('Limpiando nombres de columnas')
columns = [col if isinstance(col, str) and col.strip() else f'col_{i}' for i, col in enumerate(df.columns)]
df.columns = columns

# Reemplazar NaN con vacío
print('Reemplazando NaN valores')
df = df.fillna('')

# Crear tabla si no existe
try:
    create_table_query = f'CREATE TABLE `{table_name}` ('
    for column in columns:
        create_table_query += f'`{column}` TEXT,'
    create_table_query = create_table_query.rstrip(',') + ') ENGINE=InnoDB'
    cursor.execute(create_table_query)
    print('Tabla creada exitosamente')
except pymysql.err.OperationalError as e:
    if e.args[0] == 1050:  # Table already exists
        print(f"La tabla `{table_name}` ya existe. Continuando con la carga de datos...")
    else:
        raise

# 3. Subir los datos
'''
Revisa si localidad, canal de comercializacion y mes no están en la base mysql
Como se extraen tablas enteras por la combinacion de dichas categorias, con solo
haber una fila que contenga valores con la combinacion de estas tres columnas
es suficiente para no subir todas las filas que tengan estas mismas categorias.
'''
print('Consultando combinaciones clave existentes...')
# validacion de columnas clave antes de filtrar
required_cols = ['Localidad', 'Canal de comercialización', 'Mes']
missing_cols = [col for col in required_cols if col not in df.columns]
if missing_cols:
    raise ValueError(f"Faltan columnas necesarias: {missing_cols}")

# consultar valores de variables clave en el mysql
cursor.execute(f"SELECT Localidad, `Canal de comercialización`, Mes FROM {table_name}")
existing_rows = set(cursor.fetchall())
# Convertir tuplas del SQL a string también
existing_rows_str = set(
    (str(localidad).strip(), str(canal).strip(), str(mes).strip())
    for localidad, canal, mes in existing_rows
)

# Filtrar filas nuevas
df['key_tuple'] = list(zip(
    df['Localidad'].astype(str),
    df['Canal de comercialización'].astype(str),
    df['Mes'].astype(str)
))
# Filtrar por categorias consultadas no subidas en mysql aún
df_filtered = df[~df['key_tuple'].isin(existing_rows_str)].drop(columns='key_tuple')
print(f"Filas nuevas para insertar: {len(df_filtered)}")

# Insertar solo si hay filas nuevas
if not df_filtered.empty:
    columns_filtered = df_filtered.columns.tolist()
    columns_escaped = ', '.join([f'`{col}`' for col in columns_filtered])
    placeholders = ', '.join(['%s'] * len(columns_filtered))
    insert_query = f'INSERT INTO `{table_name}` ({columns_escaped}) VALUES ({placeholders})'

    # Insertar en bloques
    chunk_size = 10000
    total_rows = len(df_filtered)

    for start in range(0, total_rows, chunk_size):
        end = min(start + chunk_size, total_rows)
        data_chunk = [tuple(row) for row in df_filtered.iloc[start:end].to_numpy()]

        try:
            cursor.executemany(insert_query, data_chunk)
            cnx.commit()
            print(f"Insertando filas {start + 1} a {end} de {total_rows}...")
        except pymysql.MySQLError as err:
            print(f"Error al insertar datos: {err}")
else:
    print("No hay filas nuevas para insertar.")


# consultar nuevamente los valores de variables clave en el mysql
cursor.execute(f"SELECT Localidad, `Canal de comercialización`, Mes FROM {table_name}")
existing_rows = set(cursor.fetchall())
# Convertir tuplas del SQL a string también
existing_rows_str = set(
    (str(localidad).strip(), str(canal).strip(), str(mes).strip())
    for localidad, canal, mes in existing_rows
)

# guardo categorias existentes en la base
'''
Asi en la próxima query ya filtramos previamente las categorias ya cargadas a la tabla del mysql
'''
pd.Series(list(existing_rows_str)).to_json('inputs/data/categorias_existentes.json', orient='records', force_ascii=False)

# Cerrar el cursor y la conexión
cursor.close()
cnx.close()
# %%
