from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base

class TokenRecuperacionContrasenia(Base):
    """
    Modelo para los tokens de recuperación de contraseña.
    
    Gestiona los tokens temporales utilizados para el
    proceso de recuperación de contraseñas de usuarios.
    """
    __tablename__ = "tokens_recuperacion_contrasenia"

    id_token = Column(Integer, primary_key=True, index=True)
    id_usuario = Column(Integer, ForeignKey("usuarios.id_usuario"), nullable=False)
    token = Column(String(255), nullable=False)
    creado_en = Column(DateTime, nullable=False)
    expira_en = Column(DateTime, nullable=False)
    esta_usado = Column(Boolean, default=False)

    # Relaciones
    usuario = relationship("Usuario", back_populates="tokens_recuperacion")