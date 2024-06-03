from datetime import datetime
from typing import Any
from fastapi import HTTPException, status
import jwt
from pydantic import BaseModel, ValidationError

from server.settings import settings

from fastapi import HTTPException

class Token(BaseModel):
    """Token model."""
    token: str

class JWTPayload(BaseModel):
    """JWT payload model."""
    sub: str
    exp: int
    aud: str
    iss: str
    iat: int
    username: str
    email: str
    name: str



def verify_jwt(jwtoken: str) -> JWTPayload:
    """Verify the JWT token."""
    payload: JWTPayload = decode_jwt(jwtoken)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload

def decode_jwt(token: str) -> Any:
    """Decode the JWT token."""
    try:
        decoded_token = jwt.decode(jwt=token, key=settings.jwt_secret, algorithms=[settings.jwt_algorithm], audience=settings.jwt_audience, issuer=settings.jwt_issuer, options={"require": ["exp", "sub", "aud", "iss"]})
        exp = datetime.fromtimestamp(decoded_token["exp"]).timestamp()
        return decoded_token if exp >= datetime.now().timestamp() else None
    except(jwt.DecodeError, ValidationError) as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e
