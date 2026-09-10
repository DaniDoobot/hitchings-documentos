import hashlib
import hmac
import secrets
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

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


def verify_csrf_token(incoming_raw_token: str | None, stored_csrf_hash: str) -> bool:
    """
    Compara de forma segura en tiempo constante el hash del token CSRF recibido
    con el hash almacenado en la sesión de la base de datos.
    """
    if not incoming_raw_token or not stored_csrf_hash:
        return False
    incoming_hash = hash_token(incoming_raw_token)
    return hmac.compare_digest(incoming_hash, stored_csrf_hash)
