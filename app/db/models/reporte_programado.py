from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from app.db.base import Base


class ReporteProgramado(Base):
    """
    Programación 1:1 de un reporte.
    - Puede usar 'frecuencia' humana (ej: "Diaria", "Semanal", "Mensual")
      o una 'rrule' iCal, o 'n_dias' (guardado dentro de rrule o en frecuencia).
    - Se agenda en 'proxima_programacion' (aware) bajo un 'timezone'.
    """
    __tablename__ = "reportes_programados"

    id_reporte_programado = Column(Integer, primary_key=True, index=True)

    id_reporte = Column(
        Integer,
        ForeignKey("reportes.id_reporte", ondelete="CASCADE"),
        nullable=False,
        unique=True,   # 1:1
        index=True,
    )

    # Compatibilidad: etiqueta humana (ej: "Diaria" | "Semanal" | "Mensual" | "Personalizada")
    frecuencia = Column(String(120), nullable=True)

    # Regla iCal opcional (ej: "FREQ=DAILY;BYHOUR=8;BYMINUTE=0;BYSECOND=0")
    rrule = Column(String(512), nullable=True)

    # Zona horaria en que se interpreta la regla
    timezone = Column(String(64), nullable=False, default="UTC")

    # Próxima/última ejecución reales (aware)
    proxima_programacion = Column(DateTime(timezone=True), nullable=False)
    ultima_ejecucion = Column(DateTime(timezone=True), nullable=True)

    # Relaciones
    reporte = relationship("Reporte", back_populates="programacion")

    __table_args__ = (
        UniqueConstraint("id_reporte", name="uq_programado_id_reporte"),
        Index("ix_programado_proxima", "proxima_programacion"),
    )
