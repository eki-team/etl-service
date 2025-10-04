
from fastapi import FastAPI
from app.db.session import SessionLocal
from sqlalchemy import inspect, text
from fastapi.middleware.cors import CORSMiddleware
import os

app = FastAPI(
    title="SaveWater API",
    version="1.0.0"
)

raw = os.getenv(
    "CORS_ORIGINS",
    "http://localhost,http://localhost:4200,https://savewater-frontend.onrender.com"
)

origins = [o.strip().rstrip("/") for o in raw.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "savewater-backend"}

@app.get("/db/tables")
def get_tables():
    db = SessionLocal()
    try:
        inspector = inspect(db.bind)
        tables = inspector.get_table_names()
        
        tables_info = {}
        for table in tables:
            columns = inspector.get_columns(table)
            tables_info[table] = {
                "columns": len(columns),
                "column_names": [col['name'] for col in columns]
            }
        
        return {
            "total_tables": len(tables),
            "tables": sorted(tables),
            "tables_info": tables_info
        }
    except Exception as e:
        return {"error": str(e)}
    finally:
        db.close()

@app.get("/db/status")
def database_status():
    db = SessionLocal()
    try:
        result = db.execute(text("SELECT 1"))
        return {
            "status": "connected",
            "database": "savewater",
            "test_query": "successful"
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }
    finally:
        db.close()