"""
Script interactivo seguro para la creación del primer usuario administrador en la plataforma.
Uso recomendado:
    python -m scripts.create_admin

Garantías de seguridad:
- Solicita la contraseña mediante getpass sin eco en pantalla ni en shell history.
- Normaliza el correo electrónico a minúsculas.
- Valida longitud mínima (12 caracteres) y máxima (128 caracteres).
- Genera hash seguro con Argon2id.
- Asigna role='admin' e is_active=True.
- Nunca imprime la contraseña ni el hash.
"""

import argparse
import getpass
import sys
from pathlib import Path

# Asegurar raíz del proyecto en sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.user import User


def create_admin_user(email: str, password: str, db: DbSession | None = None) -> bool:
    """Crea un usuario administrador en la base de datos con contraseña Argon2id."""
    normalized_email = email.strip().lower()

    if not normalized_email or "@" not in normalized_email:
        print("[ERROR] El correo electrónico no tiene un formato válido.")
        return False

    if len(password) < 12:
        print("[ERROR] La contraseña debe tener al menos 12 caracteres.")
        return False

    if len(password) > 128:
        print("[ERROR] La contraseña no puede superar los 128 caracteres.")
        return False

    own_db = False
    if db is None:
        db = SessionLocal()
        own_db = True

    try:
        stmt = select(User).where(User.email == normalized_email)
        existing = db.execute(stmt).scalar_one_or_none()
        if existing:
            print(f"[ERROR] Ya existe un usuario registrado con el correo: {normalized_email}")
            return False

        pwd_hash = hash_password(password)
        admin_user = User(
            email=normalized_email,
            password_hash=pwd_hash,
            role="admin",
            is_active=True,
        )
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)

        print(f"[OK] Usuario administrador creado exitosamente con ID: {admin_user.id}")
        return True
    except Exception as exc:
        db.rollback()
        print(f"[ERROR] No se pudo crear el usuario administrador: {exc}")
        return False
    finally:
        if own_db:
            db.close()


def main():
    parser = argparse.ArgumentParser(description="Crear usuario administrador de HITCHINGS Documentos.")
    parser.add_argument("--email", type=str, default=None, help="Correo del administrador (opcional, si se omite se solicita)")
    parser.add_argument("--password", type=str, default=None, help="Contraseña (opcional para entornos automatizados)")
    args = parser.parse_args()

    email = args.email
    password = args.password

    print("=====================================================")
    print("=== HITCHINGS Documentos — Crear Administrador ===")
    print("=====================================================")

    if not email:
        try:
            email = input("Email: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nOperación cancelada.")
            sys.exit(1)

    if not password:
        try:
            password = getpass.getpass("Contraseña (mínimo 12 caracteres): ")
            confirm_password = getpass.getpass("Confirmar contraseña: ")
        except (KeyboardInterrupt, EOFError):
            print("\nOperación cancelada.")
            sys.exit(1)

        if password != confirm_password:
            print("[ERROR] Las contraseñas no coinciden.")
            sys.exit(1)

    success = create_admin_user(email, password)
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
