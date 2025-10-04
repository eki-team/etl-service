from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.orm import relationship
from app.db.base import Base

class Prioridad(Base):
    """
    Modelo para las prioridades de tickets.
    
    Define los diferentes niveles de prioridad que pueden
    asignarse a los tickets del sistema.
    """
    __tablename__ = "prioridades"

    id_prioridad = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(50), nullable=False)

    # Relaciones
    tickets = relationship("Ticket", back_populates="prioridad")