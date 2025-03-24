import time
from datetime import datetime
import pandas as pd
import os
import sys
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from urllib.parse import urljoin
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# Configuración de encoding para Windows
sys.stdout.reconfigure(encoding='utf-8')

def safe_print(text):
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode('ascii', errors='replace').decode('ascii'))

# Archivos de checkpoint y errores
CHECKPOINT_PAGE_FILE = "checkpoint_page.txt"
CSV_FILE = "articles_data.csv"
ERROR_FILE = "error_links.txt"

# Función para guardar el batch en CSV (fusionando con datos previos)
def save_batch(data_batch, csv_file):
    df_new = pd.DataFrame(data_batch)
    if os.path.exists(csv_file):
        df_existing = pd.read_csv(csv_file, encoding="utf-8-sig")
        df_combined = pd.concat([df_existing, df_new], ignore_index=True)
    else:
        df_combined = df_new
    df_combined.to_csv(csv_file, index=False, encoding="utf-8-sig")
    safe_print(f"📁 Guardado intermedio: {len(df_combined)} registros en '{csv_file}'")
    return df_combined

# Funciones de checkpoint para página
def load_checkpoint_page():
    if os.path.exists(CHECKPOINT_PAGE_FILE):
        with open(CHECKPOINT_PAGE_FILE, "r", encoding="utf-8") as f:
            try:
                page = int(f.read().strip())
                safe_print(f"✅ Checkpoint página cargado: {page}")
                return page
            except:
                safe_print("⚠️ Error leyendo checkpoint de página. Iniciando desde la página 1.")
                return 1
    return 1

def update_checkpoint_page(page):
    with open(CHECKPOINT_PAGE_FILE, "w", encoding="utf-8") as f:
        f.write(str(page))
    safe_print(f"✅ Checkpoint página actualizado a: {page}")

def load_error_links():
    """Carga todos los enlaces registrados en error_links.txt sin borrarlos."""
    if os.path.exists(ERROR_FILE):
        with open(ERROR_FILE, "r", encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip()]
    return []

def get_incomplete_error_links(csv_file, error_links):
    """Verifica en el CSV si los enlaces de error existen y están incompletos (por ejemplo, falta dc.date o dc.title).
       Devuelve la lista de enlaces a reprocesar."""
    to_reprocess = []
    if os.path.exists(csv_file):
        df = pd.read_csv(csv_file, encoding="utf-8-sig")
        for link in error_links:
            # Si no existe el link en el CSV, se reprocesa
            if link not in df["URL"].tolist():
                to_reprocess.append(link)
            else:
                # Si existe pero el campo 'dc.date' o 'dc.title' está vacío, se reprocesa
                record = df[df["URL"] == link].iloc[0]
                if not record.get("dc.title") or not record.get("dc.date"):
                    to_reprocess.append(link)
    else:
        # Si no existe CSV, reprocesar todos los enlaces de error
        to_reprocess = error_links
    return list(set(to_reprocess))  # Eliminar duplicados

# Reprocesamiento de enlaces con error
error_links = load_error_links()
links_to_reprocess = get_incomplete_error_links(CSV_FILE, error_links)
if links_to_reprocess:
    safe_print(f"🔄 Se encontraron {len(links_to_reprocess)} enlaces de error para reprocesar.")
    for link in links_to_reprocess:
        try:
            driver.get(link)
            safe_print(f"🔍 Reprocesando artículo: {link}")
            time.sleep(3)
            try:
                full_page_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//a[contains(text(),'Página completa del artículo')]"))
                )
                driver.execute_script("arguments[0].scrollIntoView(true);", full_page_button)
                driver.execute_script("arguments[0].click();", full_page_button)
                wait.until(EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'metadata-table')]")))
                safe_print("✔ Botón 'Página completa' clickeado en reprocesamiento.")
            except TimeoutException:
                safe_print("⚠ No se encontró el botón 'Página completa' en reprocesamiento. Extrayendo metadata directamente.")
                time.sleep(2)
            
            # Extraer metadata similar a la función principal
            article_data = {
                "article_id": None,  # Se asignará luego
                "URL": link,
                "dc.contributor": [],
                "dc.creator": "",
                "dc.date": "",
                "dc.description.abstract": ""
            }
            try:
                article_data["dc.title"] = driver.find_element(By.CSS_SELECTOR, "h2.heading").text.strip()
            except Exception:
                article_data["dc.title"] = ""
            try:
                autores = driver.find_elements(By.CSS_SELECTOR, "div.authority span")
                if autores:
                    article_data["dc.creator"] = autores[0].text.strip()
                    for autor in autores:
                        article_data["dc.contributor"].append(autor.text.strip())
            except Exception:
                article_data["dc.creator"] = ""
            try:
                article_data["dc.date"] = driver.find_element(By.CSS_SELECTOR, "div.date").text.strip()
            except Exception:
                article_data["dc.date"] = ""
            try:
                article_data["dc.description.abstract"] = driver.find_element(By.CSS_SELECTOR, "div.abstract-text").text.strip()[:500]
            except Exception:
                article_data["dc.description.abstract"] = ""
            try:
                metadata_table = driver.find_element(By.XPATH, "//ds-themed-full-item-page//table")
                rows = metadata_table.find_elements(By.XPATH, ".//tbody/tr")
                for row in rows:
                    cells = row.find_elements(By.TAG_NAME, "td")
                    if len(cells) >= 2:
                        key = cells[0].text.strip().replace(":", "").replace(" ", ".")
                        value = cells[1].text.strip()
                        if key and value:
                            if key in article_data:
                                if isinstance(article_data[key], list):
                                    article_data[key].append(value)
                                else:
                                    article_data[key] = value
                            else:
                                article_data[key] = value
            except Exception as e:
                safe_print(f"⚠️ Error al extraer metadata en reprocesamiento: {str(e)}")
            
            for key, value in article_data.items():
                if isinstance(value, list):
                    article_data[key] = ", ".join(value)
            
            # Asignar ID autoincrementable: sumar al total actual
            global_article_id += 1
            article_data["article_id"] = global_article_id
            # Guardar este registro reprocesado en el CSV (añadiéndolo, luego se eliminarán duplicados si fuera necesario)
            save_batch([article_data], CSV_FILE)
            safe_print("✅ Reprocesamiento exitoso.")
        except Exception as e:
            safe_print(f"❌ Error reprocesando {link}: {str(e)}")
            continue

# Nota: Se mantienen los registros en error_links.txt para análisis posterior si es necesario.

# Configuración de Chrome
chrome_options = Options()
chrome_options.add_argument("--headless=new")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--window-size=1366,768")
chrome_options.add_argument("--start-maximized")
chrome_options.add_argument("--disable-blink-features=AutomationControlled")
chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
chrome_options.add_argument("--lang=es-ES.UTF-8")

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=chrome_options)
wait = WebDriverWait(driver, 40)

# URL base y parámetros de búsqueda
base_url = "https://repositorio.anid.cl"
search_url = base_url + '/search?query="universidad%20de%20la%20frontera"%20OR%20"university%20of%20the%20frontier"%20OR%20"university%20of%20la%20frontera"%20OR%20"university%20of%20frontier"%20OR%20"frontier%20university"%20OR%20"univ%20la%20frontera"'

batch_size = 50  # Guardar cada 50 artículos
data_list = []   # Batch actual
total_articles = 0
global_article_id = 0

# Cargar CSV existente para evitar duplicados y determinar global_article_id
processed_urls = set()
if os.path.exists(CSV_FILE):
    df_existing = pd.read_csv(CSV_FILE, encoding="utf-8-sig")
    global_article_id = len(df_existing)
    processed_urls = set(df_existing["URL"].tolist())
    safe_print(f"📁 CSV existente: {global_article_id} artículos previamente guardados.")
else:
    safe_print("📁 No se encontró CSV existente. Iniciando desde cero.")

# Reprocesar enlaces con errores
error_links = load_error_links()
if error_links:
    safe_print(f"\n🔄 Reprocesando {len(error_links)} enlaces de error...")
    for link in error_links:
        if link in processed_urls:
            continue
        try:
            driver.get(link)
            safe_print(f"🔍 Reprocesando artículo: {link}")
            time.sleep(3)
            try:
                full_page_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//a[contains(text(),'Página completa del artículo')]"))
                )
                driver.execute_script("arguments[0].scrollIntoView(true);", full_page_button)
                driver.execute_script("arguments[0].click();", full_page_button)
                wait.until(EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'metadata-table')]")))
                safe_print("✔ Botón 'Página completa' clickeado.")
            except TimeoutException:
                safe_print("⚠ No se encontró el botón 'Página completa' al reprocesar. Extrayendo metadata directamente.")
                time.sleep(2)
            
            # Extraer metadata (similar a la extracción normal)
            article_data = {
                "article_id": None,  # Se asignará luego
                "URL": link,
                "dc.contributor": [],
                "dc.creator": "",
                "dc.date": "",
                "dc.description.abstract": ""
            }
            try:
                article_data["dc.title"] = driver.find_element(By.CSS_SELECTOR, "h2.heading").text.strip()
            except Exception:
                article_data["dc.title"] = ""
            try:
                autores = driver.find_elements(By.CSS_SELECTOR, "div.authority span")
                if autores:
                    article_data["dc.creator"] = autores[0].text.strip()
                    for autor in autores:
                        article_data["dc.contributor"].append(autor.text.strip())
            except Exception:
                article_data["dc.creator"] = ""
            try:
                article_data["dc.date"] = driver.find_element(By.CSS_SELECTOR, "div.date").text.strip()
            except Exception:
                article_data["dc.date"] = ""
            try:
                article_data["dc.description.abstract"] = driver.find_element(By.CSS_SELECTOR, "div.abstract-text").text.strip()[:500]
            except Exception:
                article_data["dc.description.abstract"] = ""
            try:
                metadata_table = driver.find_element(By.XPATH, "//ds-themed-full-item-page//table")
                rows = metadata_table.find_elements(By.XPATH, ".//tbody/tr")
                for row in rows:
                    cells = row.find_elements(By.TAG_NAME, "td")
                    if len(cells) >= 2:
                        key = cells[0].text.strip().replace(":", "").replace(" ", ".")
                        value = cells[1].text.strip()
                        if key and value:
                            if key in article_data:
                                if isinstance(article_data[key], list):
                                    article_data[key].append(value)
                                else:
                                    article_data[key] = value
                            else:
                                article_data[key] = value
            except Exception as e:
                safe_print(f"⚠️ Error al extraer metadata de la tabla en {link}: {str(e)}")
            
            # Convertir todas las listas a cadenas separadas por comas
            for key, value in article_data.items():
                if isinstance(value, list):
                    article_data[key] = ", ".join(value)
            
            # Asignar un ID autoincrementable
            global_article_id += 1
            article_data["article_id"] = global_article_id
            processed_urls.add(link)
            # Guardar este artículo (se añade al CSV de inmediato para evitar pérdida)
            df_existing = save_batch([article_data], CSV_FILE)
        except Exception as e:
            safe_print(f"❌ Error reprocesando el enlace {link}: {str(e)}")
            continue
    # Borrar el archivo de errores al finalizar el reprocesamiento
    clear_error_links()

# Actualizar global_article_id si se ha modificado el CSV
if os.path.exists(CSV_FILE):
    df_existing = pd.read_csv(CSV_FILE, encoding="utf-8-sig")
    global_article_id = len(df_existing)

# Cargar checkpoint de página
start_page = load_checkpoint_page()
# Reanudar desde la página siguiente al último batch completo
if global_article_id > 0:
    safe_print(f"⏩ Reanudando desde la página siguiente al último batch guardado: {start_page + 1}")
    page = start_page + 1
else:
    page = start_page

# Proceso principal: recorrer páginas de búsqueda
while True:
    safe_print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Procesando página de búsqueda {page}...")
    try:
        driver.get(f"{search_url}&spc.page={page}")
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        time.sleep(3)
        app_container = wait.until(EC.presence_of_element_located((By.TAG_NAME, "ds-app")))
        safe_print("✅ Contenedor principal ds-app encontrado.")
        # Hacer scroll para cargar artículos
        last_height = driver.execute_script("return document.body.scrollHeight")
        for _ in range(5):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height
        time.sleep(2)
    except TimeoutException:
        safe_print(f"❌ No se pudo cargar la página {page}. Terminando proceso.")
        break

    # Extraer enlaces de artículos
    try:
        safe_print("🔎 Extrayendo enlaces de artículos (li[data-test='list-object'])...")
        li_elements = driver.find_elements(By.CSS_SELECTOR, "li[data-test='list-object']")
        page_links = []
        for li in li_elements:
            try:
                a_element = li.find_element(By.CSS_SELECTOR, "a[href*='/entities/']")
                href = a_element.get_attribute("href")
                if href:
                    full_link = urljoin(base_url, href)
                    page_links.append(full_link)
                    if len(page_links) >= 10:
                        break
            except NoSuchElementException:
                continue
        safe_print(f"✅ Se encontraron {len(page_links)} enlaces en la página {page}.")
        if not page_links:
            safe_print("❌ No se encontraron enlaces en esta página. Terminando paginación.")
            break
    except Exception as e:
        safe_print(f"⚠️ Error al extraer enlaces: {str(e)}")
        break

    # Filtrar enlaces ya procesados (evitar duplicados)
    page_links = [link for link in page_links if link not in processed_urls]
    total_articles += len(page_links)

    # Procesar cada artículo en la página
    for article_link in page_links:
        global_article_id += 1
        safe_print(f"\n📖 Procesando artículo global ID {global_article_id} - URL: {article_link}")
        try:
            driver.get(article_link)
            safe_print(f"🔍 Abriendo artículo: {article_link}")
            time.sleep(3)
            try:
                full_page_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//a[contains(text(),'Página completa del artículo')]"))
                )
                driver.execute_script("arguments[0].scrollIntoView(true);", full_page_button)
                driver.execute_script("arguments[0].click();", full_page_button)
                wait.until(EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'metadata-table')]")))
                safe_print("✔ Botón 'Página completa' clickeado.")
            except TimeoutException:
                safe_print("⚠ No se encontró el botón 'Página completa'. Extrayendo metadata directamente.")
                time.sleep(2)
            
            # Inicializar diccionario de datos del artículo
            article_data = {
                "article_id": global_article_id,
                "URL": article_link,
                "dc.contributor": [],
                "dc.creator": "",
                "dc.date": "",
                "dc.description.abstract": ""
            }
            
            try:
                article_data["dc.title"] = driver.find_element(By.CSS_SELECTOR, "h2.heading").text.strip()
            except Exception:
                pass
            
            try:
                autores = driver.find_elements(By.CSS_SELECTOR, "div.authority span")
                if autores:
                    article_data["dc.creator"] = autores[0].text.strip()
                    for autor in autores:
                        article_data["dc.contributor"].append(autor.text.strip())
            except Exception:
                pass
            
            try:
                article_data["dc.date"] = driver.find_element(By.CSS_SELECTOR, "div.date").text.strip()
            except Exception:
                pass
            
            try:
                article_data["dc.description.abstract"] = driver.find_element(By.CSS_SELECTOR, "div.abstract-text").text.strip()[:500]
            except Exception:
                pass
            
            # Extraer metadata de la tabla
            try:
                metadata_table = driver.find_element(By.XPATH, "//ds-themed-full-item-page//table")
                rows = metadata_table.find_elements(By.XPATH, ".//tbody/tr")
                for row in rows:
                    cells = row.find_elements(By.TAG_NAME, "td")
                    if len(cells) >= 2:
                        key = cells[0].text.strip().replace(":", "").replace(" ", ".")
                        value = cells[1].text.strip()
                        if key and value:
                            if key in article_data:
                                if isinstance(article_data[key], list):
                                    article_data[key].append(value)
                                else:
                                    article_data[key] = value
                            else:
                                article_data[key] = value
            except Exception as e:
                safe_print(f"⚠️ No se pudo extraer la metadata completa de la tabla: {str(e)}")
            
            # Convertir todas las listas a cadenas separadas por comas (para todas las claves)
            for key, value in article_data.items():
                if isinstance(value, list):
                    article_data[key] = ", ".join(value)
            
            data_list.append(article_data)
            safe_print("✅ Artículo procesado correctamente.")
            processed_urls.add(article_link)
            
            # Guardar en CSV cada batch_size artículos
            if len(data_list) >= batch_size:
                safe_print(f"💾 Guardando tanda de {len(data_list)} artículos...")
                save_batch(data_list, CSV_FILE)
                data_list.clear()

        except Exception as e:
            safe_print(f"❌ Error procesando el artículo: {str(e)}")
            log_error_link(article_link)
            continue

    update_checkpoint_page(page)
    page += 1

# Guardar cualquier dato restante
if data_list:
    safe_print(f"💾 Guardando los últimos {len(data_list)} artículos...")
    save_batch(data_list, CSV_FILE)

safe_print("\n📊 Resumen final:")
safe_print(f"📄 Páginas de búsqueda procesadas: {page - 1}")
safe_print(f"🔗 Artículos totales nuevos encontrados (según páginas): {total_articles}")
if os.path.exists(ERROR_FILE):
    with open(ERROR_FILE, 'r', encoding='utf-8') as f:
        error_lines = f.readlines()
    safe_print(f"❌ Errores: {len(error_lines)}")
else:
    safe_print("❌ Errores: 0")

driver.quit()
safe_print("🚀 Proceso finalizado.")
