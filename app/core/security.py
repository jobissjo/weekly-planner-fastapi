import asyncio
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext

from app.core.settings import setting
from app.models import User
from app.repositories import UserRepository
from app.utils.common import CustomException

pwd_content = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")


async def hash_password(password: str) -> str:
    def hashing(password: str) -> str:
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    return await asyncio.to_thread(hashing, password)


async def verify_password(password: str, hashed_password: str) -> bool:
    def verify(password: str, hashed_password: str) -> bool:
        return bcrypt.checkpw(password.encode("utf-8"), hashed_password.encode("utf-8"))

    return await asyncio.to_thread(verify, password, hashed_password)


async def create_access_token(
    data: dict, expires_delta: Optional[timedelta] = None
) -> str:
    to_encode = data.copy()

    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=1080))
    to_encode.update({"exp": expire, "token_type": "access"})
    return await asyncio.to_thread(
        jwt.encode, to_encode, setting.SECRET_KEY, algorithm=setting.ALGORITHM
    )


async def create_refresh_token(
    data: dict, expires_delta: Optional[timedelta] = None
) -> str:
    to_encode = data.copy()

    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(days=7))
    to_encode.update(
        {
            "exp": expire,
            "token_type": "refresh",  # you can differentiate token types if needed
        }
    )

    return await asyncio.to_thread(
        jwt.encode, to_encode, setting.SECRET_KEY, algorithm=setting.ALGORITHM
    )


async def verify_refresh_token(token: str) -> dict:
    try:
        payload = await asyncio.to_thread(
            jwt.decode, token, setting.SECRET_KEY, algorithms=[setting.ALGORITHM]
        )
        if payload.get("token_type") != "refresh":
            raise CustomException("Invalid token type", status_code=401)
        user_id: int = payload.get("user_id")
        if user_id is None:
            raise CustomException("Token is missing user id", status_code=401)
        return payload
    except jwt.ExpiredSignatureError:
        raise CustomException("Token has expired", status_code=401)
    except jwt.PyJWTError as e:
        raise CustomException(f"Token is invalid: {e}", status_code=401)


async def verify_token_get_user(
    token: str = Depends(oauth2_scheme),
) -> User:
    try:
        payload = await asyncio.to_thread(
            jwt.decode, token, setting.SECRET_KEY, algorithms=[setting.ALGORITHM]
        )
        if payload.get("token_type") != "access":
            raise CustomException("Invalid token type", status_code=401)
        user_id: str = payload.get("user_id")
        if user_id is None:
            raise CustomException("Token is missing user id", status_code=401)

        return await UserRepository.get_user_by_id(user_id)

    except jwt.ExpiredSignatureError:
        raise CustomException("Token has expired", status_code=401)
    except jwt.PyJWTError as e:
        raise CustomException(f"Token is invalid: {e}", status_code=401)
