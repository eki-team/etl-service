from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from app.db.base import Base

class Rol(Base):
    """
    Modelo para los roles del sistema.
    
    Define los diferentes roles de usuario para control de acceso
    y permisos dentro de la aplicación.
    """
    __tablename__ = "roles"

    id_rol = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(50), nullable=False)
    descripcion = Column(String)

    # Relaciones
    usuarios = relationship("Usuario", back_populates="rol")