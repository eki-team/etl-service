from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base

class ConfiguracionProceso(Base):
    """
    Modelo para las configuraciones de procesos.
    
    Almacena los parámetros de configuración
    específicos para cada proceso.
    """
    __tablename__ = "configuraciones_procesos"

    id_configuracion_proceso = Column(Integer, primary_key=True, index=True)
    id_proceso = Column(Integer, ForeignKey("procesos.id_proceso"), nullable=False)
    clave_configuracion = Column(String(50), nullable=False)
    valor_configuracion = Column(String(50), nullable=False)

    # Relaciones
    proceso = relationship("Proceso", back_populates="configuraciones")