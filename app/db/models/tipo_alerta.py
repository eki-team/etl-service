from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.orm import relationship
from app.db.base import Base

class TipoAlerta(Base):
    """
    Modelo para los tipos de alertas.
    
    Define las categorías y severidades de las alertas
    que pueden generarse en el sistema.
    """
    __tablename__ = "tipos_alertas"

    id_tipo_alerta = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(50), nullable=False)
    severidad = Column(String(20), nullable=False)  # "baja", "media", "alta", "critica"
    descripcion = Column(String)
    esta_activo = Column(Boolean, default=True)

    # Relaciones
    alertas = relationship("AlertaProceso", back_populates="tipo_alerta")