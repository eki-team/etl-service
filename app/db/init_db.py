from app.db.base import Base
from app.db.session import engine

#from app.db.models import ()

def init_db():
    Base.metadata.create_all(bind=engine)

def create_tables():
    init_db()

if __name__ == "__main__":
    init_db()
    print("Tablas creadas:", list(Base.metadata.tables.keys()))