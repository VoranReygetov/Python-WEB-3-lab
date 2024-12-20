# auth.py
import jwt
from datetime import datetime, timedelta
from fastapi import HTTPException, status, Request
from config import SECRET_KEY, ALGORITHM


def create_access_token(data: dict, expires_delta: timedelta = timedelta(minutes=1)):
    to_encode = data.copy()
    expire = datetime.now() + expires_delta
    print(datetime.now(), expire)  # Перевіряємо значення
    to_encode.update({"exp": int(expire.timestamp())})  # Конвертація в UNIX timestamp
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

def authenticate_user(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return verify_token(token)