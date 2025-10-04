from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from app.db.base import Base

class TipoProceso(Base):
    """
    Modelo para los tipos de procesos.
    
    Categoriza los diferentes tipos de procesos
    de tratamiento de agua disponibles.
    """
    __tablename__ = "tipos_procesos"

    id_tipo_proceso = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(50), nullable=False)

    # Relaciones
    procesos = relationship("Proceso", back_populates="tipo_proceso")