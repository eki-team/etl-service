from sqlalchemy import Column, Integer, Date, Boolean, String, JSON, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.db.base import Base


class Reporte(Base):
    """
    Reporte generado (manual o por programación).
    """
    __tablename__ = "reportes"

    id_reporte = Column(Integer, primary_key=True, index=True)
    id_remitente = Column(Integer, ForeignKey("usuarios.id_usuario", ondelete="RESTRICT"), nullable=False)

    inicio_periodo = Column(Date, nullable=False)
    fin_periodo = Column(Date, nullable=False)

    # Ej: "Balance Hídrico Diario"
    tipo_reporte = Column(String, nullable=False)

    # Ej: "Semanal" | "Quincenal" | "Mensual" | "Personalizado"
    periodo = Column(String, nullable=True)

    # 0=pending, 1-99=in progress, 100=done
    progreso = Column(Integer, default=0)

    esta_habilitado = Column(Boolean, default=True)

    # "Pendiente" | "En curso" | "Completado" | "Vencido"
    estado = Column(String, nullable=False)

    # Lista de correos (JSON)
    destinatarios = Column(JSON, nullable=True)

    # Relaciones
    remitente = relationship("Usuario", back_populates="reportes_enviados")
    # 1:1 con programación (si existe)
    programacion = relationship(
        "ReporteProgramado",
        back_populates="reporte",
        uselist=False,
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        Index("ix_reportes_remitente", "id_remitente"),
        Index("ix_reportes_estado", "estado"),
        Index("ix_reportes_periodo", "periodo"),
        Index("ix_reportes_tipo", "tipo_reporte"),
    )
