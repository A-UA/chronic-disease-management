from datetime import datetime, timedelta, timezone
from passlib.context import CryptContext
import jwt
from app.core.config import settings

# Use argon2 for modern hashing with no length limits
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
ALGORITHM = "HS256"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(
    subject: str | int,
    tenant_id: int | None = None,
    org_id: int | None = None,
    roles: list[str] | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode: dict = {"exp": expire, "sub": str(subject)}
    if tenant_id is not None:
        to_encode["tenant_id"] = str(tenant_id)
    if org_id is not None:
        to_encode["org_id"] = str(org_id)
    if roles:
        to_encode["roles"] = roles
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=ALGORITHM)
    return encoded_jwt


def create_selection_token(user_id: str | int) -> str:
    """创建短期临时 token，仅用于 select-org 端点"""
    expire = datetime.now(timezone.utc) + timedelta(minutes=5)
    to_encode = {"exp": expire, "sub": str(user_id), "purpose": "org_selection"}
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=ALGORITHM)
