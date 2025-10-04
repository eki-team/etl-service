from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base

class ComentarioTicket(Base):
    """
    Modelo para los comentarios de tickets.
    
    Permite agregar comentarios y seguimiento
    a los tickets del sistema.
    """
    __tablename__ = "comentarios_tickets"

    id_comentario_ticket = Column(Integer, primary_key=True, index=True)
    id_ticket = Column(Integer, ForeignKey("tickets.id_ticket"), nullable=False)
    id_usuario = Column(Integer, ForeignKey("usuarios.id_usuario"), nullable=False)
    comentario = Column(String, nullable=False)
    creado_en = Column(DateTime, nullable=False)

    # Relaciones
    ticket = relationship("Ticket", back_populates="comentarios")
    usuario = relationship("Usuario", back_populates="comentarios_tickets")