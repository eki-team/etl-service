from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base

class AlertaProceso(Base):
    """
    Modelo para las alertas de procesos.
    
    Registra las alertas generadas por los procesos
    cuando se detectan anomalías o problemas.
    """
    __tablename__ = "alertas_procesos"

    id_alerta_proceso = Column(Integer, primary_key=True, index=True)
    id_proceso = Column(Integer, ForeignKey("procesos.id_proceso"), nullable=False)
    id_tipo_alerta = Column(Integer, ForeignKey("tipos_alertas.id_tipo_alerta"), nullable=False)
    mensaje_alerta = Column(String, nullable=False)
    valor_disparador = Column(Float)
    umbral = Column(Float)
    esta_resuelto = Column(Boolean, default=False)
    resuelto_por = Column(Integer, ForeignKey("usuarios.id_usuario"))
    creado_en = Column(DateTime, nullable=False)
    resuelto_en = Column(DateTime)

    # Relaciones
    proceso = relationship("Proceso", back_populates="alertas")
    tipo_alerta = relationship("TipoAlerta", back_populates="alertas")
    resuelto_por_usuario = relationship("Usuario", back_populates="alertas_resueltas")