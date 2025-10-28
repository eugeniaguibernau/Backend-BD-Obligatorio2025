# Imagen base (Python oficial)
FROM python:3.12-slim

# Carpeta de trabajo dentro del contenedor
WORKDIR /app

# Copiamos dependencias
COPY requirements.txt .

# Instalamos dependencias del proyecto
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos el resto del código fuente
COPY . .

# Exponemos el puerto que usa Flask
EXPOSE 5000

# Comando para ejecutar la app
CMD ["python", "app.py"]
