from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable
from app.models.user import User
from app.models.session import Session
from app.db.base import Base


def test_postgresql_ddl_users_compilation():
    """
    Verifica que el modelo User genera DDL 100% válido y compatible con PostgreSQL 16:
    - UUID nativo como Primary Key
    - VARCHAR(255) para email y password_hash
    - TIMESTAMP WITH TIME ZONE para created_at, updated_at y last_login_at
    - BOOLEAN para is_active
    """
    ddl = str(CreateTable(User.__table__).compile(dialect=postgresql.dialect()))
    assert "CREATE TABLE users" in ddl
    assert "id UUID NOT NULL" in ddl
    assert "email VARCHAR(255) NOT NULL" in ddl
    assert "password_hash VARCHAR(255) NOT NULL" in ddl
    assert "created_at TIMESTAMP WITH TIME ZONE NOT NULL" in ddl
    assert "updated_at TIMESTAMP WITH TIME ZONE NOT NULL" in ddl
    assert "last_login_at TIMESTAMP WITH TIME ZONE" in ddl
    assert "is_active BOOLEAN NOT NULL" in ddl
    assert "PRIMARY KEY (id)" in ddl


def test_postgresql_ddl_sessions_compilation():
    """
    Verifica que el modelo Session genera DDL 100% válido y compatible con PostgreSQL 16:
    - UUID nativo para id y user_id
    - VARCHAR(64) para hashes SHA-256
    - Clave foránea con ON DELETE CASCADE hacia users.id
    - TIMESTAMP WITH TIME ZONE para expires_at, created_at y last_seen_at
    """
    ddl = str(CreateTable(Session.__table__).compile(dialect=postgresql.dialect()))
    assert "CREATE TABLE sessions" in ddl
    assert "id UUID NOT NULL" in ddl
    assert "user_id UUID NOT NULL" in ddl
    assert "token_hash VARCHAR(64) NOT NULL" in ddl
    assert "csrf_token_hash VARCHAR(64) NOT NULL" in ddl
    assert "expires_at TIMESTAMP WITH TIME ZONE NOT NULL" in ddl
    assert "created_at TIMESTAMP WITH TIME ZONE NOT NULL" in ddl
    assert "last_seen_at TIMESTAMP WITH TIME ZONE NOT NULL" in ddl
    assert "FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE" in ddl
    assert "PRIMARY KEY (id)" in ddl


def test_metadata_tables_coverage():
    """Verifica que todos los modelos del sistema están registrados en Base.metadata."""
    table_names = set(Base.metadata.tables.keys())
    assert "users" in table_names
    assert "sessions" in table_names
