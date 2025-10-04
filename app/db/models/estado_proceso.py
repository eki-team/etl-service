from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.orm import relationship
from app.db.base import Base

class EstadoProceso(Base):
    """
    Modelo para los estados de procesos.
    
    Define los diferentes estados en los que puede
    encontrarse un proceso del sistema.
    """
    __tablename__ = "estados_procesos"

    id_estado_proceso = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(50), nullable=False)
    codigo = Column(String(50), nullable=False, unique=True)
    descripcion = Column(String)
    es_final = Column(Boolean, default=False)
    esta_activo = Column(Boolean, default=True)
    orden = Column(Integer)

    # Relaciones
    procesos = relationship("Proceso", back_populates="estado_proceso")