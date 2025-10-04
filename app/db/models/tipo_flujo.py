from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from app.db.base import Base

class TipoFlujo(Base):
    """
    Modelo para los tipos de flujo.
    
    Define los diferentes tipos de flujo
    de agua en los procesos.
    """
    __tablename__ = "tipos_flujos"

    id_tipo_flujo = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(50), nullable=False)

    # Relaciones
    procesos = relationship("Proceso", back_populates="tipo_flujo")