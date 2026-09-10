import importlib.util
import logging
from pathlib import Path
from unittest.mock import patch
import pytest
from sqlalchemy.dialects.postgresql.psycopg import PGDialect_psycopg

from app.core.config import settings

# Cargar el módulo alembic/env.py de forma robusta sin colisionar con el paquete 'alembic' de pip
_env_path = Path(__file__).resolve().parent.parent / "alembic" / "env.py"
_spec = importlib.util.spec_from_file_location("alembic_env_module", str(_env_path))
_alembic_env = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_alembic_env)

get_database_url = _alembic_env.get_database_url
get_dialect_description = _alembic_env.get_dialect_description
create_migration_engine = _alembic_env.create_migration_engine


def test_database_url_from_settings_prevailed_over_alembic_ini():
    """
    Requisito 1: La variable DATABASE_URL de configuración/entorno prevalece
    absolutamente sobre el archivo alembic.ini (el cual contiene el placeholder driver://).
    """
    target_url = "postgresql+psycopg://test_user:test_pass@postgres:5432/test_db"
    with patch.object(settings, "DATABASE_URL", target_url):
        resolved_url = get_database_url()
        assert resolved_url == target_url
        assert "driver://" not in resolved_url


def test_database_url_builds_engine_with_postgresql_psycopg_dialect():
    """
    Requisito 2: Si DATABASE_URL es postgresql+psycopg://..., Alembic construye
    un engine de SQLAlchemy con el dialecto PostgreSQL y el driver psycopg.
    """
    sample_url = "postgresql+psycopg://hitchings_app:Secr3t%25Pass!@postgres:5432/hitchings_docs"
    with patch.object(settings, "DATABASE_URL", sample_url):
        url = get_database_url()
        engine = create_migration_engine(url)
        assert engine.dialect.name == "postgresql"
        assert engine.dialect.driver == "psycopg"
        assert isinstance(engine.dialect, PGDialect_psycopg)
        # El engine no debe inicializar un pool persistente para migraciones (NullPool)
        assert engine.pool.__class__.__name__ == "NullPool"


def test_alembic_never_loads_driver_placeholder():
    """
    Requisito 3: Alembic nunca intenta cargar el dialecto ficticio 'driver'.
    La descripción del dialecto para logging se identifica como PostgreSQL/psycopg.
    """
    sample_url = "postgresql+psycopg://hitchings_app:SecretPassword123@postgres:5432/hitchings_docs"
    with patch.object(settings, "DATABASE_URL", sample_url):
        url = get_database_url()
        assert not url.startswith("driver://")
        desc = get_dialect_description(url)
        assert desc == "PostgreSQL/psycopg"


def test_database_url_missing_or_placeholder_fails_fast():
    """
    Requisito 4: Si DATABASE_URL está vacía o contiene el placeholder 'driver://',
    Alembic falla de forma temprana con ValueError explicativo en lugar de caer en fallos crípticos.
    """
    # 1. URL vacía
    with patch.object(settings, "DATABASE_URL", ""):
        with pytest.raises(ValueError, match="DATABASE_URL no está configurada o contiene un placeholder inválido"):
            get_database_url()

    # 2. Solo espacios
    with patch.object(settings, "DATABASE_URL", "   "):
        with pytest.raises(ValueError, match="DATABASE_URL no está configurada o contiene un placeholder inválido"):
            get_database_url()

    # 3. Placeholder driver://
    with patch.object(settings, "DATABASE_URL", "driver://user:pass@localhost/dbname"):
        with pytest.raises(ValueError, match="contiene un placeholder inválido"):
            get_database_url()


def test_alembic_logging_does_not_leak_credentials(caplog):
    """
    Requisito 5: El diagnóstico de carga de base de datos nunca imprime contraseñas,
    usuarios ni la URL completa en los logs.
    """
    secret_pass = "P@ssw0rdConCaracteresEspeciales%21"
    secret_user = "usuario_sensible_prod"
    secret_host = "cluster-pg-privado.internal"
    sensitive_url = f"postgresql+psycopg://{secret_user}:{secret_pass}@{secret_host}:5432/hitchings_docs"

    logger = logging.getLogger("alembic.env")

    with patch.object(settings, "DATABASE_URL", sensitive_url):
        with caplog.at_level(logging.INFO, logger="alembic.env"):
            url = get_database_url()
            desc = get_dialect_description(url)
            logger.info("Database configuration loaded: %s", desc)

    captured_text = caplog.text
    # Debe contener la descripción segura del dialecto
    assert "Database configuration loaded: PostgreSQL/psycopg" in captured_text
    # NUNCA debe contener los datos sensibles
    assert secret_pass not in captured_text
    assert secret_user not in captured_text
    assert secret_host not in captured_text
    assert "5432" not in captured_text
