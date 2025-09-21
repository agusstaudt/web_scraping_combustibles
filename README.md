# Sistematización de datos de combustibles mediante web scraping con lectura de imágenes, MySQL y Docker 

Desde la Oficina de Gestión de Datos de la Municipalidad de Posadas (Misiones, Argentina) desarrollé un sistema que automatiza la recolección y almacenamiento de información sobre precios y cantidades de combustibles vendidos en las estaciones de servicio de la provincia.

El proyecto emplea técnicas de web scraping con Python para descargar los datos actualizados de cada punto de venta. Debido a que la misma página de donde se obtienen los datos contiene un captcha generado mediante imagen, se realiza un procesamiento de detección de imágenes para extraer el código de validación, y así poder ingresar a la base que sale del query. Estos datos son procesados y exportados automáticamente a una base de datos MySQL para su análisis posterior.

Para garantizar portabilidad y reproducibilidad, el sistema se implementa en un entorno Dockerizado, lo que facilita la ejecución del código en distintos servidores de manera estandarizada y segura.

Esta solución permitió a la municipalidad disponer de información confiable y actualizada sobre el mercado de combustibles, optimizando la toma de decisiones y el diseño de políticas públicas basadas en evidencia.
