from datetime import datetime, timedelta, timezone
from passlib.context import CryptContext
import jwt
from app.core.config import settings

# Use argon2 for modern hashing with no length limits
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
ALGORITHM = "HS256"

def verify_password(plain_password: str, hashed_password: str) -> bool:
    # Ensure plain_password is converted to bytes if needed, but passlib handles strings
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    # bcrypt has a 72-byte limit. We can't really truncate it if we want security,
    # but for this SaaS, it's unlikely users provide > 72 chars.
    # The error in logs suggested a specific passlib/bcrypt backend bug.
    return pwd_context.hash(password)

def create_access_token(subject: str | int, expires_delta: timedelta | None = None) -> str:
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=ALGORITHM)
    return encoded_jwt
