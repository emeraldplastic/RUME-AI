import bcrypt
import jwt
import os
import bleach
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify, current_app
from cryptography.fernet import Fernet
from app.models import AuditLog
from app.main import db

class SecurityManager:
    @staticmethod
    def get_fernet():
        key = current_app.config['ENCRYPTION_KEY']
        if not key:
            # Fallback for development if not in env
            print("[Security] WARNING: No ENCRYPTION_KEY found in .env. Using temporary key.")
            key = Fernet.generate_key()
        return Fernet(key)

    @classmethod
    def encrypt(cls, text):
        if not text: return None
        f = cls.get_fernet()
        return f.encrypt(text.encode()).decode()

    @classmethod
    def decrypt(cls, token):
        if not token: return None
        f = cls.get_fernet()
        try:
            return f.decrypt(token.encode()).decode()
        except:
            return "[Decryption Error]"

    @staticmethod
    def hash_password(password):
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    @staticmethod
    def check_password(password, hashed):
        return bcrypt.checkpw(password.encode(), hashed.encode())

    @staticmethod
    def generate_token(user_id):
        payload = {
            'exp': datetime.utcnow() + timedelta(seconds=current_app.config['JWT_ACCESS_TOKEN_EXPIRES']),
            'iat': datetime.utcnow(),
            'sub': user_id
        }
        return jwt.encode(payload, current_app.config['JWT_SECRET'], algorithm='HS256')

    @staticmethod
    def sanitize(text):
        if not text: return ""
        return bleach.clean(text, tags=[], attributes={}, strip=True)

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            token = request.headers['Authorization'].split(" ")[1]
        
        if not token:
            return jsonify({'error': 'Authentication token missing'}), 401
            
        try:
            data = jwt.decode(token, current_app.config['JWT_SECRET'], algorithms=['HS256'])
            request.user_id = data['sub']
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401
            
        return f(*args, **kwargs)
    return decorated

def log_action(action, resource_type=None, resource_id=None, detail=None):
    user_id = getattr(request, 'user_id', None)
    log = AuditLog(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        detail=detail,
        ip_address=request.remote_addr
    )
    db.session.add(log)
    db.session.commit()
