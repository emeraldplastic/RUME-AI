from datetime import datetime
from app.main import db
import json

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    display_name = db.Column(db.String(80))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    jobs = db.relationship('Job', backref='owner', lazy=True, cascade="all, delete-orphan")
    audit_logs = db.relationship('AuditLog', backref='user', lazy=True)

class Job(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    description_encrypted = db.Column(db.Text, nullable=False)
    required_skills = db.Column(db.Text)  # Comma separated
    min_experience = db.Column(db.Integer, default=0)
    min_education = db.Column(db.String(100))
    status = db.Column(db.String(20), default='active', index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    resumes = db.relationship('Resume', backref='job', lazy=True, cascade="all, delete-orphan")

class Resume(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey('job.id'), nullable=False, index=True)
    filename_hash = db.Column(db.String(64), nullable=False)
    original_filename_encrypted = db.Column(db.Text, nullable=False)
    candidate_name_encrypted = db.Column(db.Text)
    candidate_email_encrypted = db.Column(db.Text)
    raw_text_encrypted = db.Column(db.Text)
    extracted_skills = db.Column(db.Text)
    years_experience = db.Column(db.Float, default=0)
    education_level = db.Column(db.String(100))
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    analysis = db.relationship('AnalysisResult', backref='resume', uselist=False, cascade="all, delete-orphan")

class AnalysisResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    resume_id = db.Column(db.Integer, db.ForeignKey('resume.id'), nullable=False, unique=True)
    overall_score = db.Column(db.Float)
    skill_score = db.Column(db.Float)
    experience_score = db.Column(db.Float)
    education_score = db.Column(db.Float)
    similarity_score = db.Column(db.Float)
    status = db.Column(db.String(50)) # e.g., highly_qualified, qualified, not_qualified
    matched_skills = db.Column(db.Text)
    missing_skills = db.Column(db.Text)
    strengths = db.Column(db.Text)
    weaknesses = db.Column(db.Text)
    explanation = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True, index=True)
    action = db.Column(db.String(100), nullable=False)
    resource_type = db.Column(db.String(50))
    resource_id = db.Column(db.Integer)
    detail = db.Column(db.Text)
    ip_address = db.Column(db.String(45))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
