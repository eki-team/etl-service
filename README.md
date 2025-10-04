
# ETL-SERVICE

Backend del sistema **ETL-SERVICE**, desarrollado con **FastAPI** y **PostgreSQL**.

## 🚀 Tecnologías utilizadas

- Python 3.11+
- FastAPI
- SQLAlchemy
- Alembic
- Pydantic / Pydantic Settings
- PostgreSQL
- Uvicorn
- dotenv

## 📦 Instalación de dependencias

```bash
pip install -r requirements.txt
```

## ⚙️ Variables de entorno para desarrollo local

```bash
DATABASE_URL=postgresql://usuario_db:password_db@db:5432/nombre_db

POSTGRES_USER=usuario_db
POSTGRES_PASSWORD=password_db
POSTGRES_DB=nombre_db

DB_HOST=db
DB_PORT=5432

SECRET_KEY=tu_clave_secreta
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

RUN_MIGRATIONS=true
AUTO_GENERATE_MIGRATION=false  
SEED_ON_START=false        
ALEMBIC_STAMP_TO_HEAD=false 
```

## ⚙️ Variables de entorno para producción

```bash
ACCESS_TOKEN_EXPIRE_MINUTES=30
ALEMBIC_STAMP_TO_HEAD=false
ALGORITHM=HS256
AUTO_GENERATE_MIGRATION=false
DATABASE_URL=internal_url_db_prod
DB_HOST=host_db_prod
DB_PORT=5432
POSTGRES_DB=nombre_db_prod
POSTGRES_PASSWORD=password_db_prod
POSTGRES_USER=usuario_db_prod
RESET_ALEMBIC=false
RESET_PUBLIC_SCHEMA=false
RUN_MIGRATIONS=true
SECRET_KEY=tu_clave_secreta
SEED_ON_START=false
```

## 📁 Estructura del proyecto

```bash
├── alembic/
│   ├── env.py
│   ├── script.py.mako
│   ├── versions/
│   │   ├── .gitkeep
├── alembic.ini
├── app/
│   ├── api/
│   │   ├── dependencies.py
│   │   ├── v1/
│   │   │   ├── routes/
│   ├── core/
│   │   ├── config.py
│   ├── db/
│   │   ├── base.py
│   │   ├── deps.py
│   │   ├── init_db.py
│   │   ├── models/
│   │   ├── session.py
│   ├── main.py
│   ├── schemas/
│   ├── services/
│   ├── utils/
├── middlewares/
├── requirements.txt
├── scripts/
├── seeds/
├── tests/
│   ├── integration/
│   ├── unit/
├── .env.example
├── .gitignore
├── README.md
```