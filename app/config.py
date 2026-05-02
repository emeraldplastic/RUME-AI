import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-key-123')
    ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY')
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///data/resumes.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Security
    JWT_SECRET = os.getenv('JWT_SECRET', 'jwt-secret-123')
    JWT_ACCESS_TOKEN_EXPIRES = int(os.getenv('JWT_EXPIRY_HOURS', 24)) * 3600
    
    # Uploads
    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'uploads')
    MAX_CONTENT_LENGTH = int(os.getenv('MAX_UPLOAD_SIZE', 16 * 1024 * 1024))
    ALLOWED_EXTENSIONS = {'pdf', 'docx', 'doc', 'txt'}
    
    # Rate Limiting
    RATELIMIT_DEFAULT = "200 per hour"
    RATELIMIT_STORAGE_URL = "memory://"
