import hashlib
import hmac
import secrets
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

import uuid

from app.core.config import settings

# Instancia global de PasswordHasher configurada con Argon2id por defecto
_password_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    """Genera un hash seguro Argon2id con sal única criptográfica."""
    return _password_hasher.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifica una contraseña contra su hash Argon2id de manera resistente a ataques de temporización.
    Retorna False ante cualquier inconsistencia sin lanzar excepciones.
    """
    try:
        return _password_hasher.verify(hashed_password, plain_password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def generate_random_token(nbytes: int = 32) -> str:
    """Genera un token opaco criptográficamente aleatorio (URL-safe)."""
    return secrets.token_urlsafe(nbytes)


def hash_token(raw_token: str) -> str:
    """
    Calcula el hash SHA-256 de un token opaco.
    Solo este hash se almacena en la base de datos, nunca el token RAW.
    """
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def derive_csrf_token(session_id: uuid.UUID | str, token_hash: str) -> str:
    """
    Deriva de forma determinista y criptográficamente sólida el token CSRF
    a partir del session_id y token_hash mediante HMAC-SHA256 firmado con el secreto del servidor.

    Garantiza que múltiples pestañas o llamadas a /auth/me obtengan el mismo
    token CSRF consistente y válido durante toda la vida de la sesión,
    sin almacenar el token CSRF raw en la base de datos ni en el navegador.
    """
    secret = settings.effective_session_secret
    message = f"csrf:{str(session_id)}:{token_hash}".encode("utf-8")
    return hmac.new(secret, message, hashlib.sha256).hexdigest()


def verify_csrf_token(
    incoming_raw_token: str | None,
    stored_csrf_hash: str,
    session_id: uuid.UUID | str | None = None,
    token_hash: str | None = None,
) -> bool:
    """
    Compara de forma segura en tiempo constante:
    1) El hash del token CSRF recibido contra el hash persistido en la sesión de base de datos.
    2) Si se proporcionan session_id y token_hash, valida también contra el token HMAC derivado.
    """
    if not incoming_raw_token or not stored_csrf_hash:
        return False
    incoming_hash = hash_token(incoming_raw_token)
    if not hmac.compare_digest(incoming_hash, stored_csrf_hash):
        return False
    if session_id is not None and token_hash is not None:
        expected_token = derive_csrf_token(session_id, token_hash)
        if not hmac.compare_digest(incoming_raw_token, expected_token):
            return False
    return True
