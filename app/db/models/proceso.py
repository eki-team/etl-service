from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base

class Proceso(Base):
    """
    Modelo para los procesos del sistema de agua.
    
    Representa los diferentes procesos de tratamiento
    y gestión del agua en el sistema.
    """
    __tablename__ = "procesos"

    id_proceso = Column(Integer, primary_key=True, index=True)
    id_tipo_proceso = Column(Integer, ForeignKey("tipos_procesos.id_tipo_proceso"), nullable=False)
    id_origen_agua = Column(Integer, ForeignKey("origenes_agua.id_origen_agua"), nullable=False)
    id_tipo_flujo = Column(Integer, ForeignKey("tipos_flujos.id_tipo_flujo"), nullable=False)
    tipo_balance = Column(String(50), nullable=False)
    eficiencia = Column(Float, nullable=False)
    creado_en = Column(DateTime, nullable=False)
    actualizado_en = Column(DateTime, nullable=False)
    id_estado_proceso = Column(Integer, ForeignKey("estados_procesos.id_estado_proceso"), nullable=False)

    # Relaciones
    tipo_proceso = relationship("TipoProceso", back_populates="procesos")
    origen_agua = relationship("OrigenAgua", back_populates="procesos")
    tipo_flujo = relationship("TipoFlujo", back_populates="procesos")
    estado_proceso = relationship("EstadoProceso", back_populates="procesos")
    tickets = relationship("Ticket", back_populates="proceso")
    metricas = relationship("MetricaProceso", back_populates="proceso")
    configuraciones = relationship("ConfiguracionProceso", back_populates="proceso")
    alertas = relationship("AlertaProceso", back_populates="proceso")