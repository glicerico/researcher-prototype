from datetime import datetime, timedelta, UTC
import jwt
from fastapi import HTTPException, status
from typing import Optional
import config


class AuthManager:
    """Manages admin authentication using JWT tokens."""
    
    def __init__(self):
        self.secret_key = config.ADMIN_JWT_SECRET
        self.algorithm = config.ADMIN_JWT_ALGORITHM
        self.expire_minutes = config.ADMIN_JWT_EXPIRE_MINUTES
        self.admin_password = config.ADMIN_PASSWORD

    def verify_password(self, password: str) -> bool:
        """Verify if the provided password matches the admin password."""
        return password == self.admin_password

    def create_access_token(self) -> str:
        """Create a new JWT access token for admin."""
        expire = datetime.now(UTC) + timedelta(minutes=self.expire_minutes)
        to_encode = {
            "sub": "admin",
            "exp": expire,
            "iat": datetime.now(UTC),
            "type": "access"
        }
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt

    def verify_token(self, token: str) -> bool:
        """Verify if the provided JWT token is valid."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            username: str = payload.get("sub")
            token_type: str = payload.get("type")
            
            if username != "admin" or token_type != "access":
                return False
            
            return True
        except jwt.PyJWTError:
            return False

    def get_token_payload(self, token: str) -> Optional[dict]:
        """Get the payload from a valid JWT token."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.PyJWTError:
            return None


# Global auth manager instance
auth_manager = AuthManager()


def verify_admin_token(token: str) -> bool:
    """Helper function to verify admin token."""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not token.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token format",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = token.replace("Bearer ", "")
    
    if not auth_manager.verify_token(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return True 