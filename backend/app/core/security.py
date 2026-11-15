from datetime import timedelta
import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, InvalidHashError
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from app.core.config import settings
from app.core.db import get_db
from app.models import User, Audit, now

hasher = PasswordHasher()
oauth = OAuth2PasswordBearer(tokenUrl='/api/auth/token')
ROLES = ('ADMIN', 'DATA_OWNER', 'DATA_STEWARD', 'DATA_ENGINEER', 'AUDITOR')
WRITERS = ('ADMIN', 'DATA_STEWARD', 'DATA_ENGINEER')


def verify(password, hashed):
    try:
        return hasher.verify(hashed, password)
    except (VerificationError, InvalidHashError):
        return False


def token(user):
    return jwt.encode({'sub': str(user.id), 'ver': user.token_version,
                       'exp': now() + timedelta(minutes=settings().token_minutes)},
                      settings().jwt_secret, algorithm='HS256')


def current_user(bearer=Depends(oauth), db=Depends(get_db)):
    try:
        claims = jwt.decode(bearer, settings().jwt_secret, algorithms=['HS256'], options={'require': ['sub', 'exp', 'ver']})
        user = db.get(User, int(claims['sub']))
        if not user or not user.active or user.token_version != claims['ver']:
            raise ValueError()
        return user
    except (jwt.PyJWTError, ValueError, KeyError):
        raise HTTPException(401, 'Sessão inválida ou expirada', headers={'WWW-Authenticate': 'Bearer'})


def allow(*roles):
    def dependency(user=Depends(current_user)):
        if user.role not in roles:
            raise HTTPException(403, 'O perfil não permite esta operação')
        return user
    return dependency


def audit(db, user, action, entity, entity_id='', result='SUCCESS', **details):
    db.add(Audit(username=user.username if isinstance(user, User) else str(user), action=action,
                 entity=entity, entity_id=str(entity_id), result=result, details=details))
