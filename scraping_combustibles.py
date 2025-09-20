#%% librerias
with open("librerias.py") as f:
    exec(f.read())

#%% set de carpetas
inputs_cd = 'inputs'
img_cd = inputs_cd + '/img'
data_cd = inputs_cd + '/data'
outputs_cd = 'outputs' 

#%% chequeo inicial para que categorias_existentes.json tenga su versión más actualizada
# Cargar credenciales desde .env
load_dotenv()

config = {
    'user': os.getenv('MYSQL_USER'),
    'password': os.getenv('MYSQL_PASSWORD'),
    'host': os.getenv('MYSQL_HOST'),
    'port': int(os.getenv('MYSQL_PORT')),
}

# Conexión
cnx = pymysql.connect(
    host=config['host'],
    user=config['user'],
    password=config['password'],
    port=config['port']
)
cursor = cnx.cursor()

# Seleccionar base y tabla
new_db_name = 'datos_combustibles'
table_name = 'base_misiones'

cursor.execute(f"USE `{new_db_name}`;")

# Consultar combinaciones clave
cursor.execute(f"SELECT Localidad, `Canal de comercialización`, Mes FROM {table_name}")
existing_rows = set(cursor.fetchall())

# Convertir a tuplas de strings
existing_rows_str = set(
    (str(localidad).strip(), str(canal).strip(), str(mes).strip())
    for localidad, canal, mes in existing_rows
)

# Guardar como JSON para filtrar en el scraping
os.makedirs('inputs/data', exist_ok=True)
pd.Series(list(existing_rows_str)).to_json(
    'inputs/data/categorias_existentes.json',
    orient='records',
    force_ascii=False
)

cursor.close()
cnx.close()
#%% set de categorias
'''
Vamos a cargar las categorias existentes, combinarlas para tener 
todas las combinaciones posibles. Luego, cargamos la lista de combinaciones
existentes en la tabla del mysql para quedarnos con las combinaciones 
que quedan por consultar
'''
historic_list_meses = True

with open("listas.py") as f:
    exec(f.read())
if not historic_list_meses: # si es falso no correr el historico de meses
    meses = ['Junio de 2025','Mayo de 2025']


# Leer el JSON como lista de listas
try:
    with open('inputs/data/categorias_existentes.json', 'r', encoding='utf-8') as f:
        lista_de_listas = json.load(f)
except FileNotFoundError:
    lista_de_listas = []

# filtro de categorias ya existentes en la tabla del mysql
# Convertir a set de tuplas
tuplas_cargadas = set(tuple(x) for x in lista_de_listas)

# Generar todas las combinaciones posibles
todas_las_combinaciones = set(product(localidades, destinos, meses))

# Filtrar combinaciones que aún no fueron consultadas
combinaciones_a_consultar = todas_las_combinaciones - tuplas_cargadas

#%% ordenar elementos de las tuplas
# Función para convertir el string de mes en datetime
def parse_fecha_espanol(fecha_str):
    mes_str, _, anio_str = fecha_str.partition(" de ")
    mes_num = meses_es[mes_str]
    anio = int(anio_str)
    return datetime(anio, mes_num, 1)  # Día fijo (1)

# Ordenar combinaciones por meses y por localidad
combinaciones_ordenadas = sorted(
    combinaciones_a_consultar,
    key=lambda x: (-parse_fecha_espanol(x[2]).timestamp(), x[0])
)

# %% prueba individual ########################
run_individual = False
if run_individual:
    #  Configuración de opciones
    options = webdriver.ChromeOptions()
    options.add_experimental_option("detach", True)  # Mantener Chrome abierto

    # Inicializar el driver automáticamente con webdriver-manager
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    # Abrir la página
    driver.get("http://res1104.se.gob.ar/consultaprecios.eess.php")
    time.sleep(2)

    # 2. Seleccionar Período
    periodo_select = Select(driver.find_element(By.ID, "cmbperiodo"))
    periodo_select.select_by_visible_text(fecha)

    # Cambiar al iframe para provincia, localidad
    WebDriverWait(driver, 10).until(
        EC.frame_to_be_available_and_switch_to_it((By.ID, "iframe_consultaprecios"))
    )

    # 3. Seleccionar Provincia
    # Esperar hasta que el select esté presente
    provincia_select = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "codigodeprovincia"))
    )

    # Usar Select para elegir "MISIONES"
    Select(provincia_select).select_by_visible_text("MISIONES")

    # 4. Seleccionar Localidad
    localidad_select = Select(driver.find_element(By.ID, "idlocalidad"))
    localidad_select.select_by_visible_text("POSADAS")

    # ⚠️ Si vas a interactuar con contenido fuera del iframe después:
    driver.switch_to.default_content()

    # Esperar carga de localidades
    time.sleep(5)

    # 5. Canal de comercializacion (destino)
    localidad_select = Select(driver.find_element(By.ID, "iddestino"))
    localidad_select.select_by_visible_text(destino)

    # 5. Leer el CAPTCHA
    # Localizás el elemento del captcha (la imagen)
    captcha_element = driver.find_element(By.CSS_SELECTOR, "img[alt='']")  # O con otro selector válido

    # Sacás la captura completa de la pantalla con Selenium
    driver.save_screenshot("inputs/img/full_screenshot.png")

    # Tomás la posición y tamaño del captcha en la página
    location = captcha_element.location
    size = captcha_element.size

    # Abrís la imagen completa y recortás solo el captcha
    image = Image.open("full_screenshot.png")

    left = location['x']
    top = location['y']
    right = left + size['width']
    bottom = top + size['height']

    captcha_image = image.crop((left, top, right, bottom))
    captcha_image.save("captcha_cropped.png")

    # Aplicás OCR para leer el captcha
    texto_captcha = pytesseract.image_to_string(captcha_image, config='--psm 8').strip()
    print("Captcha detectado:", texto_captcha)

    # Ruta al binario de Tesseract (modificá si es necesario)
    pytesseract.pytesseract.tesseract_cmd = "/opt/homebrew/bin/tesseract"

    # Leer imagen completa
    image = cv2.imread('full_screenshot.png')

    # Convertir a escala de grises
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Aplicar umbral para resaltar áreas claras
    _, thresh = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY_INV)

    # Buscar contornos
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Buscar la región que parece un captcha por tamaño y proporciones
    captcha_roi = None
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        if 80 < w < 200 and 30 < h < 70 and y > 400:  # Ajustar según coordenadas típicas del captcha
            captcha_roi = image[y:y+h, x:x+w]
            break

    # Verificamos si se encontró el captcha
    if captcha_roi is not None:
        # Guardar la región del captcha (opcional)
        captcha_path = "captcha_detected.png"
        cv2.imwrite(captcha_path, captcha_roi)

        # Convertir a escala de grises para OCR
        pil_image = Image.fromarray(cv2.cvtColor(captcha_roi, cv2.COLOR_BGR2RGB)).convert("L")

        # OCR (modo solo números)
        text = pytesseract.image_to_string(pil_image, config='--psm 8 -c tessedit_char_whitelist=0123456789').strip()
        print("Texto detectado en el captcha:", text)
    else:
        print("No se detectó el captcha automáticamente.")

    # 6. Ingresar el CAPTCHA
    captcha_input = driver.find_element(By.ID, "tmptxt")
    captcha_input.clear()
    captcha_input.send_keys(text)

    # 7. Hacer clic en "Consultar" (usando input[value='Consultar'])
    consultar_btn = driver.find_element(By.CSS_SELECTOR, "input[type='submit'][value='Consultar']")
    consultar_btn.click()

    # 8. Esperar que cargue la tabla
    time.sleep(2)

    # Encontrar todas las filas que contienen datos
    rows = driver.find_elements(By.XPATH, "//table[@class='negro']//tr[position()>2]")

    # Extraer los datos
    data = []
    for row in rows:
        cols = row.find_elements(By.TAG_NAME, "td")
        if len(cols) == 9:  # asegurarse de que tenga todas las columnas esperadas
            data.append([col.text.strip() for col in cols])

    # Crear el DataFrame
    columnas = [
        "Localidad", "Derivado", "Boca de expendio", "Dirección",
        "Bandera", "Precio sin impuesto", "Precio final",
        "Volumen informado (m3)", "Exento"
    ]
    df = pd.DataFrame(data, columns=columnas)

    # Mostrar parte del resultado
    print(df.head())

    df['Canal de comercialización'] = destino
    df['Mes'] = fecha


#%% BUCLE de localidades, fechas y destinos
# funcion para leer el captcha
def leer_captcha(driver, img_cd, max_intentos=3):
    import os
    import cv2
    import time
    import numpy as np
    from PIL import Image
    import pytesseract
    from selenium.webdriver.common.by import By

    # muteamos la ruta si se ejecuta dentro de docker
    #pytesseract.pytesseract.tesseract_cmd = "/opt/homebrew/bin/tesseract"

    for intento in range(max_intentos):
        try:
            # Guardar imagen del captcha
            captcha_element = driver.find_element(By.CSS_SELECTOR, "img[alt='']")
            captcha_path = f"{img_cd}/captcha_directo.png"
            captcha_element.screenshot(captcha_path)

            # Leer imagen con OpenCV
            img = cv2.imread(captcha_path)

            # Convertir a escala de grises
            pil_image = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB)).convert("L")

            # (opcional: guardar para debugging)
            pil_image.save(f"{img_cd}/captcha_grises.png")

            # OCR
            config = '--psm 8 -c tessedit_char_whitelist=0123456789'
            texto = pytesseract.image_to_string(pil_image, config=config).strip()

            # Limpiar
            texto = ''.join(filter(str.isdigit, texto)).strip()

            print(f"[Intento {intento+1}] Texto detectado: {texto}")

            if len(texto) == 8:
                return texto

        except Exception as e:
            print(f"[ERROR] al leer captcha (intento {intento+1}): {e}")

        time.sleep(1)  # Pausa entre intentos por si hay recarga

    return None

#%% Comienzo del proceso (version 1)
# Configuración del navegador
run_old = False
if run_old:
    service = Service()
    options = webdriver.ChromeOptions()
    driver = webdriver.Chrome(service=service, options=options)
    # 1. Ingresar a la página
    driver.get("http://res1104.se.gob.ar/consultaprecios.eess.php")
    time.sleep(2)

    # Lista para acumular los DataFrames
    dfs = []

    # contador
    c=1

    # Resultado: lista de combinaciones a scrapear
    for loc, d, mes in combinaciones_ordenadas:
        print(f"Iterando sobre : {loc}, {d}, {mes}. {c}/{len(combinaciones_a_consultar)}")
        # 2. Seleccionar Período
        periodo_select = Select(driver.find_element(By.ID, "cmbperiodo"))
        periodo_select.select_by_visible_text(mes)

        # Cambiar al iframe para provincia, localidad
        WebDriverWait(driver, 10).until(
            EC.frame_to_be_available_and_switch_to_it((By.ID, "iframe_consultaprecios"))
        )

        # 3. Seleccionar Provincia
        # Esperar hasta que el select esté presente
        provincia_select = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "codigodeprovincia"))
        )

        # Usar Select para elegir "MISIONES"
        Select(provincia_select).select_by_visible_text("MISIONES")

        # 4. Seleccionar Localidad
        localidad_select = Select(driver.find_element(By.ID, "idlocalidad"))
        localidad_select.select_by_visible_text(loc)

        # ⚠️ Si vas a interactuar con contenido fuera del iframe después:
        driver.switch_to.default_content()

        # Esperar carga de localidades
        time.sleep(5)

        # 5. Canal de comercializacion (destino)
        localidad_select = Select(driver.find_element(By.ID, "iddestino"))
        localidad_select.select_by_visible_text(d)

        # Esperar carga de localidades
        time.sleep(2)

        # 6. Leer el CAPTCHA
        # Intentar resolver el captcha hasta un máximo de intentos
        max_intentos = 5
        intento = 0
        captcha_ok = False

        while intento < max_intentos:
            # Leer captcha
            captcha_texto = leer_captcha(driver, img_cd)
            if captcha_texto is None:
                print("No se pudo resolver el captcha.")
                break

            # Ingresar el código
            captcha_input = driver.find_element(By.ID, "tmptxt")
            captcha_input.clear()
            captcha_input.send_keys(captcha_texto)

            # Hacer clic en Consultar
            consultar_btn = driver.find_element(By.CSS_SELECTOR, 
                                                "input[type='submit'][value='Consultar']")
            consultar_btn.click()
            time.sleep(2)

            # Verificar si aparece el cartel de error
            try:
                error_msg = driver.find_element(By.XPATH, "//div[contains(text(),'Error: El código de seguridad es incorrecto.')]")
                print(f"Captcha incorrecto (intento {intento+1}). Reintentando...")
                intento += 1
            except:
                # Si no se encontró el error, asumimos que el captcha fue correcto
                captcha_ok = True
                break

        if not captcha_ok:
            print("No se pudo ingresar correctamente el captcha después de varios intentos. Saltando esta iteración.")
            c+=1
            continue

        # 7. Encontrar todas las filas que contienen datos (luego del encabezado)
        rows = driver.find_elements(By.XPATH, "//table[@class='negro']//tr[position()>2]")

        data = []

        # Verificar si existe una fila con el mensaje "No hay datos..."
        if any("No hay datos" in row.text for row in rows):
            # Agregar fila vacía con NA (salvo localidad)
            columnas = [
                "Localidad", "Derivado", "Boca de expendio", "Dirección",
                "Bandera", "Precio sin impuesto", "Precio final",
                "Volumen informado (m3)", "Exento"
            ]
            data.append([
                loc,  # deberías tener esta variable definida previamente en tu loop
                *["NA"] * (len(columnas) - 1)
            ])
        else:
            # Extraer datos normalmente
            for row in rows:
                cols = row.find_elements(By.TAG_NAME, "td")
                if len(cols) == 9:
                    data.append([col.text.strip() for col in cols])

        # 8. Crear el DataFrame
        columnas = [
            "Localidad", "Derivado", "Boca de expendio", "Dirección",
            "Bandera", "Precio sin impuesto", "Precio final",
            "Volumen informado (m3)", "Exento"
        ]
        df = pd.DataFrame(data, columns=columnas)

        # Agregar columnas adicionales
        df['Canal de comercialización'] = d
        df['Mes'] = mes

        # Agregar el DataFrame a la lista de resultados
        dfs.append(df)

        # Al final de cada iteración, justo antes de continuar con la siguiente:
        try:
            os.remove(f"{img_cd}/captcha_directo.png")
        except FileNotFoundError:
            pass

        try:
            os.remove(f"{img_cd}/captcha_grises.png")
        except FileNotFoundError:
            pass

        # volver atrás 
        driver.find_element(By.PARTIAL_LINK_TEXT, "Volver a la página anterior").click()
        # descanso antes de retomar
        time.sleep(2)
        
        # 9. --- CADA 500 ITERACIONES: guardar y subir ---
        if c % 500 == 0 or c == len(combinaciones_ordenadas):
            print(f">>> Subiendo datos a SQL en iteración {c}")
            
            df_parcial = pd.concat(dfs, ignore_index=True)
            csv_path = f'inputs/data/combustibles_misiones_parcial.csv'  # nombre fijo

            df_parcial.to_csv(csv_path, index=False)

            # Ejecutar base_sql
            with open("base_sql.py") as f:
                exec(f.read())

            dfs.clear()  # vaciar para próximo lote

        # aumentar el contador
        c+=1

    driver.quit()

#%% ################## Comienzo del proceso (version 2, final) ########################## 
'''
Mejora del scraping anterior
Al no detectar correctamente el captcha en los intentos, la página se actualiza para que se cambie el captcha, 
pero se mantenga la misma consulta, debido a que con el código de arriba, al no poder identificar correctamente
el código del captcha, se continua a la siguiente iteracion, pero el captcha no va a cambiar, por lo que el error
va a continuar infinitamente.
'''
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import tempfile

# Configurar opciones para Chromium en Docker
options = Options()
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--headless=new")
options.add_argument(f"--user-data-dir={tempfile.mkdtemp()}")

# Importante: usar el ejecutable de Chromium
options.binary_location = "/usr/bin/chromium"

# Usar ChromeDriver ya instalado en la imagen
service = Service(executable_path="/usr/bin/chromedriver")

# Inicializar el navegador
driver = webdriver.Chrome(service=service, options=options)
# Lista para acumular los DataFrames
dfs = []

# contador
c=1

# Resultado: lista de combinaciones a scrapear
for loc, d, mes in combinaciones_ordenadas:
    print(f"Iterando sobre : {loc}, {d}, {mes}. {c}/{len(combinaciones_a_consultar)}")

    captcha_ok = False
    max_intentos = 5
    intento = 0

    while not captcha_ok and intento < max_intentos:
        try:
            # 1. Ingresar a la página
            # Refrescar página e iniciar todo de nuevo en cada intento
            driver.get("http://res1104.se.gob.ar/consultaprecios.eess.php")
            time.sleep(2)

            # 2. Seleccionar Período
            periodo_select = Select(driver.find_element(By.ID, "cmbperiodo"))
            periodo_select.select_by_visible_text(mes)

            # Cambiar al iframe para provincia, localidad
            WebDriverWait(driver, 10).until(
                EC.frame_to_be_available_and_switch_to_it((By.ID, "iframe_consultaprecios"))
            )

            # 3. Seleccionar Provincia
            provincia_select = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "codigodeprovincia"))
            )
            Select(provincia_select).select_by_visible_text("MISIONES")

            # 4. Seleccionar Localidad
            localidad_select = Select(driver.find_element(By.ID, "idlocalidad"))
            localidad_select.select_by_visible_text(loc)

            driver.switch_to.default_content()
            time.sleep(5)

            # 5. Canal de comercializacion (destino)
            localidad_select = Select(driver.find_element(By.ID, "iddestino"))
            localidad_select.select_by_visible_text(d)
            time.sleep(2)

            # 6. Leer el CAPTCHA
            captcha_texto = leer_captcha(driver, img_cd)
            if captcha_texto is None:
                print(f"No se pudo resolver el captcha (intento {intento+1}). Refrescando...")
                intento += 1
                continue

            captcha_input = driver.find_element(By.ID, "tmptxt")
            captcha_input.clear()
            captcha_input.send_keys(captcha_texto)

            consultar_btn = driver.find_element(By.CSS_SELECTOR, "input[type='submit'][value='Consultar']")
            consultar_btn.click()
            time.sleep(2)

            try:
                driver.find_element(By.XPATH, "//div[contains(text(),'Error: El código de seguridad es incorrecto.')]")
                print(f"Captcha incorrecto (intento {intento+1}). Reintentando...")
                intento += 1
            except:
                captcha_ok = True

        except Exception as e:
            print(f"Error durante el intento {intento+1}: {e}")
            intento += 1

    if not captcha_ok:
        print("No se pudo ingresar correctamente el captcha después de varios intentos. Saltando esta iteración.")
        continue

    # 7. Encontrar todas las filas que contienen datos (luego del encabezado)
    rows = driver.find_elements(By.XPATH, "//table[@class='negro']//tr[position()>2]")

    data = []
    if any("No hay datos" in row.text for row in rows):
        columnas = [
            "Localidad", "Derivado", "Boca de expendio", "Dirección",
            "Bandera", "Precio sin impuesto", "Precio final",
            "Volumen informado (m3)", "Exento"
        ]
        data.append([
            loc,
            *["NA"] * (len(columnas) - 1)
        ])
    else:
        for row in rows:
            cols = row.find_elements(By.TAG_NAME, "td")
            if len(cols) == 9:
                data.append([col.text.strip() for col in cols])

    columnas = [
        "Localidad", "Derivado", "Boca de expendio", "Dirección",
        "Bandera", "Precio sin impuesto", "Precio final",
        "Volumen informado (m3)", "Exento"
    ]
    df = pd.DataFrame(data, columns=columnas)
    df['Canal de comercialización'] = d
    df['Mes'] = mes
    dfs.append(df)

    try:
        os.remove(f"{img_cd}/captcha_directo.png")
    except FileNotFoundError:
        pass
    try:
        os.remove(f"{img_cd}/captcha_grises.png")
    except FileNotFoundError:
        pass

    try:
        driver.find_element(By.PARTIAL_LINK_TEXT, "Volver a la página anterior").click()
        time.sleep(2)
    except:
        pass

    if c % 40 == 0 or c == len(combinaciones_ordenadas):
        print(f">>> Subiendo datos a SQL en iteración {c}")
        df_parcial = pd.concat(dfs, ignore_index=True)
        csv_path = f'inputs/data/combustibles_misiones_parcial.csv'
        df_parcial.to_csv(csv_path, index=False)
        with open("base_sql.py") as f:
            exec(f.read())
        dfs.clear()

    c += 1

driver.quit()

