from sqlalchemy import Column, Integer, String, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from app.db.base import Base

class Usuario(Base):
    __tablename__ = "usuarios"

    # -------------------- atributos --------------------
    id_usuario = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    contrasenia = Column(String(255), nullable=False)
    email = Column(String(100), unique=True, nullable=False, index=True)
    es_activo = Column(Boolean, default=True, nullable=False)
    # -------------------- fks --------------------
    id_rol = Column(Integer, ForeignKey("roles.id_rol"), nullable=False)

    # -------------------- auditoria --------------------

    # -------------------- relaciones --------------------
    rol = relationship("Rol", back_populates="usuarios")

    # Tickets creados por este usuario
    tickets = relationship(
        "Ticket",
        back_populates="usuario",
        foreign_keys="Ticket.id_usuario",
    )

    # Tickets que este usuario marcó como eliminados (soft-delete)
    tickets_eliminados = relationship(
        "Ticket",
        back_populates="eliminado_por_usuario",
        foreign_keys="Ticket.eliminado_por",
    )

    reportes_enviados = relationship("Reporte", foreign_keys="Reporte.id_remitente", back_populates="remitente")
    comentarios_tickets = relationship("ComentarioTicket", back_populates="usuario")
    tokens_recuperacion = relationship("TokenRecuperacionContrasenia", back_populates="usuario")
    alertas_resueltas = relationship("AlertaProceso", back_populates="resuelto_por_usuario")