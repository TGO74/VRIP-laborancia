# Documentación de Extracción de Metadata de Artículos del Repositorio ANID

Este repositorio contiene el código desarrollado para extraer de manera automatizada la metadata de los artículos publicados en el repositorio ANID, utilizando Selenium en Python. La solución se ha optimizado con mecanismos de guardado por batches y checkpoints para evitar la pérdida de datos en caso de interrupciones, además de incluir un sistema de registro y reprocesamiento de errores.

---

## Índice

- [Introducción](#introducción)
- [Objetivos](#objetivos)
- [Requisitos](#requisitos)
- [Instalación](#instalación)
- [Ejecución](#ejecución)
- [Descripción del Proceso](#descripción-del-proceso)
  - [Extracción de Enlaces](#31-extracción-de-enlaces)
  - [Procesamiento de Artículos](#32-procesamiento-de-artículos)
  - [Extracción de Metadata](#33-extracción-de-metadata)
  - [Conversión de Listas](#34-conversión-de-listas)
  - [Guardado en Batches y Checkpoints](#35-guardado-en-batches-y-checkpoints)
  - [Registro de Errores y Reprocesamiento](#36-registro-de-errores)
- [Conclusión](#conclusión)
- [Notas Adicionales](#notas-adicionales)

---

## Introducción

Este proyecto documenta el proceso de scraping implementado para extraer metadatos de artículos publicados en el repositorio ANID. La solución se desarrolló en Python utilizando Selenium y se ha optimizado para garantizar la continuidad del proceso mediante el uso de batches y checkpoints. Además, se incluye un mecanismo de registro de errores para identificar y reprocesar aquellos artículos que presenten incidencias, asegurando la integridad y trazabilidad de la información extraída.

## Objetivos

- Automatizar la extracción de metadatos (título, autores, fecha, resumen, y demás información disponible en la tabla de metadata) de artículos del repositorio ANID.
- Garantizar la continuidad del proceso mediante el guardado periódico en batches y el uso de checkpoints, permitiendo reanudar el scraping desde el último batch guardado.
- Registrar y reprocesar los enlaces de artículos que generen errores, de modo que se pueda corregir la metadata incompleta sin reprocesar datos ya almacenados.
- Generar un identificador autoincrementable único para cada artículo extraído.

## Requisitos

- Python 3.7 o superior
- Selenium
- Pandas
- webdriver-manager

## Instalación

1. Clona el repositorio o descarga el código fuente.
2. Instala las dependencias necesarias ejecutando:

   ```bash
   pip install selenium pandas webdriver-manager
   ```

## Ejecución

Para ejecutar el script, utiliza el siguiente comando en la terminal:

```bash
python nombre_del_script.py
```

El script comenzará a extraer datos del repositorio ANID, guardando cada 50 artículos en el archivo `articles_data.csv` y actualizando los archivos de checkpoint (`checkpoint_page.txt` y, opcionalmente, `checkpoint_article.txt`). Los enlaces que generen errores se registrarán en `error_links.txt` para su posterior reprocesamiento.

## Descripción del Proceso

### 3.1 Extracción de Enlaces

El proceso de extracción de enlaces se inicia navegando a la URL de búsqueda del repositorio ANID con una consulta que incluye diversas expresiones relacionadas con la Universidad de la Frontera. Se realizan los siguientes pasos:

- **Carga de la Página de Búsqueda:**  
  El script accede a la URL de búsqueda y utiliza `WebDriverWait` para esperar a que el contenido de la página (el contenedor principal `<ds-app>`) se cargue completamente.

- **Desplazamiento (Scroll):**  
  Se ejecuta un script de desplazamiento en la página para forzar la carga completa de los artículos, ya que el contenido se carga de forma dinámica. Se verifica el cambio en la altura de la página para confirmar que todos los elementos están visibles.

- **Identificación de Enlaces:**  
  Se seleccionan los elementos `li[data-test='list-object']` y, dentro de cada uno, se extrae la URL contenida en la etiqueta `<a>` que apunta al artículo individual. Los enlaces se normalizan utilizando `urljoin` para obtener rutas absolutas.

### 3.2 Procesamiento de Artículos

Una vez extraídos los enlaces, el script procesa cada artículo de forma individual:

- **Acceso a la Página del Artículo:**  
  Se abre la URL del artículo y se espera la carga completa del contenido.

- **Interacción con el Botón "Página completa del artículo":**  
  Se utiliza `WebDriverWait` para detectar y hacer clic en el botón que permite acceder a la metadata completa. En caso de que no se encuentre, se extraen los datos visibles de la página.

- **Extracción de Datos Esenciales:**  
  Se recogen campos críticos como `dc.title` (título), `dc.creator` y `dc.contributor` (autores y colaboradores), `dc.date` (fecha) y `dc.description.abstract` (resumen).  
  Además, se recorre la tabla de metadata para capturar campos adicionales.

- **Manejo de Excepciones:**  
  Cada operación se encierra en bloques `try-except` para evitar que errores individuales interrumpan el proceso global. En caso de error, se registra la URL del artículo en `error_links.txt`.

### 3.3 Extracción de Metadata

En esta fase se extraen los campos esenciales y la información adicional contenida en la tabla de metadata del artículo. Los pasos incluyen:

- **Captura de Campos Esenciales:**  
  Se extrae el título, los autores, la fecha y el resumen del artículo utilizando selectores CSS específicos.

- **Recorrido de la Tabla de Metadata:**  
  Se localiza la tabla de metadata y se itera sobre cada fila para capturar claves y valores, normalizando las claves (eliminando dos puntos y espacios) para garantizar la homogeneidad.

- **Manejo de Datos Faltantes:**  
  Si algún campo no se encuentra, se asigna un valor vacío para evitar errores posteriores en el análisis.

### 3.4 Conversión de Listas

Dado que algunos campos (como autores o palabras clave) pueden contener múltiples valores, se convierten todas las listas en cadenas de texto, separadas por comas. Esto se realiza de forma general en el diccionario de metadata:

```python
for key, value in article_data.items():
    if isinstance(value, list):
        article_data[key] = ", ".join(value)
```

Este paso garantiza que todos los campos tengan un formato consistente al exportar la información al CSV.

### 3.5 Guardado en Batches y Checkpoints

Para evitar la pérdida de datos en caso de interrupciones, se implementa un sistema de guardado por batches y checkpoints:

- **Guardado por Batches:**  
  Cada 50 artículos procesados se guardan en el archivo CSV (`articles_data.csv`), fusionándolos con los registros existentes. Esto se realiza mediante la función `save_batch`, que concatena los datos nuevos con los ya guardados.

- **Checkpoints de Página:**  
  Se utiliza el archivo `checkpoint_page.txt` para registrar la última página de búsqueda procesada. Al reiniciar el script, se retoma desde la página siguiente al último batch guardado, asegurando que no se reprocesen artículos incompletos.

- **Reanudación del Proceso:**  
  Al iniciar, el script carga el CSV existente para determinar el número total de artículos ya procesados y ajustar el contador global `global_article_id`. De esta forma, el ID asignado a cada nuevo artículo es autoincrementable y continuo.

### 3.6 Registro de Errores

El sistema de registro de errores cumple las siguientes funciones:

- **Captura de Enlaces Problemáticos:**  
  Durante el procesamiento, si se produce una excepción (por ejemplo, fallos al hacer clic en el botón "Página completa del artículo" o problemas al extraer la metadata), se captura la URL del artículo que generó el error.

- **Registro en Archivo de Texto:**  
  La función `log_error_link(link)` guarda estos enlaces en el archivo `error_links.txt` en modo de adición, de manera que cada error se documenta en una línea separada.

- **Ventajas y Beneficios:**  
  - Permite realizar un análisis posterior para identificar patrones o incidencias recurrentes.  
  - Facilita la re-procesamiento manual o automatizado de los artículos fallidos, verificando si existen registros incompletos en el CSV.  
  - Proporciona trazabilidad y control de calidad en el proceso de extracción, asegurando la integridad de los datos.

Además, el script incorpora un módulo de reprocesamiento que, al inicio, verifica los enlaces registrados en `error_links.txt` y los compara con el CSV existente. Si se detectan registros incompletos (por ejemplo, ausencia de `dc.title` o `dc.date`), se reprocesa el artículo para intentar obtener la metadata completa y se actualiza el CSV.

---

## Conclusión

Este documento detalla un proceso robusto de scraping para el repositorio ANID, optimizado para extraer de manera automatizada y sistemática la metadata de los artículos. La solución implementa un guardado en batches cada 50 artículos y utiliza mecanismos de checkpoint para reanudar el proceso desde la última página completa procesada, evitando la reprocesación de datos ya guardados. Además, se incorpora un sistema de registro de errores que permite identificar, analizar y reprocesar los enlaces problemáticos, asegurando la integridad y continuidad del proceso de extracción.

Esta solución está diseñada para el equipo de datos de VRIP UFRO y ofrece una arquitectura modular que facilita futuras mejoras, tales como la ejecución en paralelo o la migración a tecnologías más eficientes.

---

## Notas Adicionales

- **Ejecución:**  
  Se recomienda ejecutar el script en un ambiente controlado y monitorearlo, ya que la estructura de la página del repositorio ANID puede cambiar con el tiempo.
  
- **Mantenimiento:**  
  La arquitectura modular del script permite ajustes en los selectores, tiempos de espera y estrategias de guardado, lo que facilita la adaptación a futuras actualizaciones del sitio web.

- **Reprocesamiento de Errores:**  
  Se debe revisar periódicamente el archivo `error_links.txt` para evaluar y reprocesar manualmente los enlaces que sigan generando problemas, mejorando así la calidad del dataset final.


