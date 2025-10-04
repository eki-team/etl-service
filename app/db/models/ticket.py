from sqlalchemy import Boolean, Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base
from sqlalchemy.sql import func

class Ticket(Base):
    __tablename__ = "tickets"

    # -------------------- atributos --------------------
    id_ticket = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    descripcion = Column(String)
    impacto_esperado = Column(String)
    fecha_limite = Column(DateTime)
    fecha_resolucion = Column(DateTime)
    progreso = Column(Integer, nullable=False, default=0)  # 0–100 %

    # -------------------- fks --------------------
    id_proceso = Column(Integer, ForeignKey("procesos.id_proceso"), nullable=True)
    id_prioridad = Column(Integer, ForeignKey("prioridades.id_prioridad"), nullable=False)
    id_usuario = Column(Integer, ForeignKey("usuarios.id_usuario"), nullable=False)   # creador
    eliminado_por = Column(Integer, ForeignKey("usuarios.id_usuario"), nullable=True) # soft-delete

    # -------------------- auditoria --------------------
    fecha_creacion = Column(DateTime, default=func.now())
    fecha_actualizacion = Column(DateTime, default=func.now(), onupdate=func.now())
    esta_eliminado = Column(Boolean, nullable=False, default=False)
    eliminado_en = Column(DateTime, nullable=True)

    # -------------------- relaciones --------------------
    proceso = relationship("Proceso", back_populates="tickets")
    prioridad = relationship("Prioridad", back_populates="tickets")
    usuario = relationship("Usuario", back_populates="tickets", foreign_keys=[id_usuario])
    eliminado_por_usuario = relationship("Usuario", back_populates="tickets_eliminados", foreign_keys=[eliminado_por])
    comentarios = relationship("ComentarioTicket", back_populates="ticket")