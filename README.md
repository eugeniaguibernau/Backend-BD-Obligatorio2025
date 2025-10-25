# Backend-BD-Obligatorio2025

Proyecto backend para el trabajo práctico. Usando Flask y MySQL.

Setup rápido (macOS / zsh):

1. Crear y activar un entorno virtual

```zsh
python3 -m venv .venv
source .venv/bin/activate
```

2. Instalar dependencias

```zsh
pip install -r requirements.txt
```

3. Configurar variables de entorno (ejemplo con MySQL local)

```zsh
export DB_USER=root
export DB_PASSWORD=secret
export DB_HOST=127.0.0.1
export DB_PORT=3306
export DB_NAME=obligatorio
# o export DATABASE_URL='mysql+pymysql://user:pass@host:port/dbname'
```

4. Ejecutar la app

```zsh
python app.py
```

La app expondrá /health para comprobar que está levantada.
