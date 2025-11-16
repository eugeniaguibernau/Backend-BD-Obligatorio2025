# Imagen base (Python oficial)
FROM python:3.12-slim

# Carpeta de trabajo dentro del contenedor
WORKDIR /app

# Copiamos dependencias
COPY requirements.txt .

# Instalar herramientas necesarias para compilar extensiones nativas (bcrypt y similares) + cron
RUN apt-get update \
	&& apt-get install -y --no-install-recommends \
	   build-essential \
	   libssl-dev \
	   libffi-dev \
	   cron \
	&& rm -rf /var/lib/apt/lists/*

# Instalamos dependencias del proyecto
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos el resto del código fuente
COPY . .

# Configurar cronjob para procesar sanciones diariamente a las 8:00 AM
RUN echo "0 8 * * * root cd /app && /usr/local/bin/python3 /app/scripts/procesar_sanciones_diarias.py >> /var/log/sanciones.log 2>&1" > /etc/cron.d/sanciones-cron \
	&& chmod 0644 /etc/cron.d/sanciones-cron \
	&& touch /var/log/sanciones.log

# Exponemos el puerto que usa Flask
EXPOSE 5000

# Crear script para iniciar ambos servicios
RUN echo '#!/bin/bash\ncron && python app.py' > /start.sh && chmod +x /start.sh

# Comando para ejecutar la app y cron en paralelo
CMD ["/start.sh"]
