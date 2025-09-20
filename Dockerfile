# Etapa de build
FROM python:3.11-slim AS build
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Etapa runtime mínima
FROM python:3.11-slim
WORKDIR /app

# Crea usuario sin privilegios
RUN useradd -ms /bin/bash appuser
USER appuser

# Copiar solo lo necesario
COPY --from=build /usr/local/lib/python3.11 /usr/local/lib/python3.11
COPY --from=build /usr/local/bin /usr/local/bin
COPY scraping_combustibles.py listas.py librerias.py descarga_base_combustible.py base_sql.py ./
# ¡No copiamos .env!

# Entrypoint explícito
CMD ["python", "scraping_combustibles.py"]