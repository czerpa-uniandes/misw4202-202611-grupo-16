from __future__ import annotations

from sqlalchemy import select

from database import Base, SessionLocal, engine
from models import Cliente, Habitacion


def init_schema_and_seed() -> None:
    Base.metadata.create_all(bind=engine)

    with SessionLocal() as session:
        has_clientes = session.execute(select(Cliente.id)).first() is not None
        if not has_clientes:
            session.add_all(
                [
                    Cliente(id=1, nombre="Ana Torres", email="ana@example.com", activo=True),
                    Cliente(id=2, nombre="Carlos Ruiz", email="carlos@example.com", activo=True),
                    Cliente(id=3, nombre="Cliente Inactivo", email="inactivo@example.com", activo=False),
                ]
            )

        has_habitaciones = session.execute(select(Habitacion.id)).first() is not None
        if not has_habitaciones:
            session.add_all(
                [
                    Habitacion(id=101, nombre="Suite 101", precio_base=120000, disponible=True),
                    Habitacion(id=102, nombre="Deluxe 102", precio_base=180000, disponible=True),
                ]
            )

        session.commit()
