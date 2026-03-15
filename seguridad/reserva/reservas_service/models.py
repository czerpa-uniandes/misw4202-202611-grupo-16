from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class Cliente(Base):
    __tablename__ = "clientes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(180), nullable=False, unique=True)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class Habitacion(Base):
    __tablename__ = "habitaciones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    precio_base: Mapped[float] = mapped_column(Float, nullable=False)
    disponible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class Reserva(Base):
    __tablename__ = "reservas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cliente_id: Mapped[int] = mapped_column(ForeignKey("clientes.id"), nullable=False)
    habitacion_id: Mapped[int] = mapped_column(ForeignKey("habitaciones.id"), nullable=False)
    fecha_inicio: Mapped[date] = mapped_column(Date, nullable=False)
    fecha_fin: Mapped[date] = mapped_column(Date, nullable=False)
    subtotal_calculado: Mapped[float] = mapped_column(Float, nullable=False)
    impuesto_calculado: Mapped[float] = mapped_column(Float, nullable=False)
    total_calculado: Mapped[float] = mapped_column(Float, nullable=False)
    estado: Mapped[str] = mapped_column(String(40), nullable=False, default="confirmada")


class SeguridadLog(Base):
    __tablename__ = "seguridad_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tipo_evento: Mapped[str] = mapped_column(String(80), nullable=False)
    cliente_id: Mapped[int] = mapped_column(Integer, nullable=True)
    payload_recibido: Mapped[str] = mapped_column(Text, nullable=False)
    motivo: Mapped[str] = mapped_column(Text, nullable=False)
    fecha: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
