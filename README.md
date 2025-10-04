
# ETL-SERVICE

Backend del sistema **ETL-SERVICE** para procesamiento de artículos científicos de NASA, desarrollado con **FastAPI** y **MongoDB**.

## 🚀 Tecnologías utilizadas

- Python 3.13+
- FastAPI
- MongoDB (Motor - async driver)
- Pydantic / Pydantic Settings
- Sentence Transformers (embeddings)
- NumPy (vector similarity)
- Uvicorn
- dotenv

## 🎯 Características principales

- ✅ **Procesamiento de artículos científicos**: Chunking inteligente con overlap configurable
- ✅ **Detección de duplicados**: Sistema de similitud vectorial (cosine similarity)
- ✅ **Generación de embeddings**: Modelo all-MiniLM-L6-v2 (384 dimensiones)
- ✅ **Generación automática de tags**: Clasificación de artículos por categorías
- ✅ **Carga automática al inicio**: Procesamiento de artículos desde JSON al arrancar
- ✅ **Modo dry-run**: Previsualización de chunks sin inserción en BD

## 📦 Instalación de dependencias

```bash
pip install -r requirements.txt
```

## ⚙️ Variables de entorno para desarrollo local

```bash
# MongoDB Configuration
MONGO_USER=admin
MONGO_PASSWORD=admin
MONGO_HOST=localhost
MONGO_PORT=27017
MONGO_DB=mydb

# Environment
ENVIRONMENT=development

# Startup Configuration
AUTO_LOAD_ARTICLES=true  # Set to false to skip automatic article loading on startup

# CORS Configuration
CORS_ORIGINS=http://localhost,http://localhost:4200
```

## ⚙️ Variables de entorno para producción

```bash
# MongoDB Configuration
MONGO_URI="mongodb+srv://user:password@cluster.mongodb.net/dbname?retryWrites=true&w=majority"
MONGO_DB=production_db

# Environment
ENVIRONMENT=production

# Startup Configuration
AUTO_LOAD_ARTICLES=false  # Disable auto-loading in production, load manually

# CORS Configuration
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
```

## 🚀 Inicio automático de datos

Al iniciar la aplicación, el sistema automáticamente:

1. **Conecta a MongoDB** y crea la colección `chunks` con índices optimizados
2. **Carga artículos** desde `articles/complete_scrapping.json` (si `AUTO_LOAD_ARTICLES=true`)
3. **Procesa cada artículo**:
   - Divide el texto en chunks con overlap (default: 1500 chars, 400 overlap)
   - Genera embeddings vectoriales para detección de duplicados
   - Genera tags y categorías automáticamente
   - Detecta y omite chunks duplicados (threshold: 95% similitud)
   - Almacena en MongoDB con metadata completa

### Carga manual de artículos

Si deseas cargar artículos sin reiniciar el servidor:

```bash
python scripts/load_articles.py
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