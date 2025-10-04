from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from app.db.base import Base

class OrigenAgua(Base):
    """
    Modelo para los orígenes del agua.
    
    Define las diferentes fuentes de origen
    del agua en el sistema.
    """
    __tablename__ = "origenes_agua"

    id_origen_agua = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(50), nullable=False)

    # Relaciones
    procesos = relationship("Proceso", back_populates="origen_agua")