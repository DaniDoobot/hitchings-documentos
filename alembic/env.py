import logging
import os
import sys
from logging.config import fileConfig

from sqlalchemy import create_engine, pool
from sqlalchemy.engine import make_url

from alembic import context

# Añadir raíz del proyecto al sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.models import Base

logger = logging.getLogger("alembic.env")

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = getattr(context, "config", None)

# Interpret the config file for Python logging if in Alembic context.
if config is not None and config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_database_url() -> str:
    """
    Obtiene la DATABASE_URL desde la configuración unificada de la aplicación (settings).
    Ignora cualquier valor o placeholder de alembic.ini y falla de forma temprana si no es válida.
    """
    url = getattr(settings, "DATABASE_URL", "")
    if not url or not str(url).strip() or str(url).strip().startswith("driver://"):
        raise ValueError(
            "DATABASE_URL no está configurada o contiene un placeholder inválido ('driver://'). "
            "Asegúrese de definir DATABASE_URL en las variables de entorno."
        )
    return str(url).strip()


def get_dialect_description(url: str) -> str:
    """Retorna una descripción segura del dialecto sin exponer usuario, contraseña ni host."""
    parsed = make_url(url)
    drivername = parsed.drivername
    if "psycopg" in drivername or "postgres" in drivername:
        return "PostgreSQL/psycopg"
    return drivername


def create_migration_engine(url: str):
    """Crea el engine de SQLAlchemy para migraciones usando pool.NullPool sin pasar por ConfigParser."""
    connect_args = {}
    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False

    return create_engine(
        url,
        poolclass=pool.NullPool,
        connect_args=connect_args,
    )


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = get_database_url()
    logger.info("Database configuration loaded: %s", get_dialect_description(url))

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    url = get_database_url()
    logger.info("Database configuration loaded: %s", get_dialect_description(url))

    connectable = create_migration_engine(url)

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


# Ejecutar migraciones solo cuando env.py se ejecuta dentro de Alembic runner
try:
    if context.is_offline_mode():
        run_migrations_offline()
    else:
        run_migrations_online()
except (NameError, AttributeError):
    # Ocurre cuando el módulo se importa fuera del runner de Alembic (ej. en tests unitarios)
    pass
