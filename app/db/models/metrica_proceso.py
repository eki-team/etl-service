from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base

class MetricaProceso(Base):
    """
    Modelo para las métricas de procesos.
    
    Almacena las métricas y mediciones de rendimiento
    de los diferentes procesos del sistema.
    """
    __tablename__ = "metricas_procesos"

    id_metrica_proceso = Column(Integer, primary_key=True, index=True)
    id_proceso = Column(Integer, ForeignKey("procesos.id_proceso"), nullable=False)
    nombre_metrica = Column(String(50), nullable=False)
    valor_metrica = Column(Float, nullable=False)
    marca_tiempo = Column(DateTime, nullable=False)

    # Relaciones
    proceso = relationship("Proceso", back_populates="metricas")