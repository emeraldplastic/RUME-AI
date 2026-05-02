"""Database models for RUME AI."""
from datetime import datetime

from app.main import db


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(200), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    display_name = db.Column(db.String(100), default="")
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    jobs = db.relationship("Job", back_populates="owner", cascade="all, delete-orphan")
    audit_logs = db.relationship("AuditLog", back_populates="user", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "display_name": self.display_name or self.username,
            "created_at": self.created_at.isoformat(),
        }


class Job(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    description_encrypted = db.Column(db.Text, nullable=False)
    required_skills = db.Column(db.Text, default="")
    min_experience = db.Column(db.Integer, default=0, nullable=False)
    min_education = db.Column(db.String(50), default="bachelor", nullable=False)
    status = db.Column(db.String(20), default="active", nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    owner = db.relationship("User", back_populates="jobs")
    resumes = db.relationship("Resume", back_populates="job", cascade="all, delete-orphan")

    __table_args__ = (
        db.Index("rume_idx_job_user_status", "user_id", "status"),
        db.Index("rume_idx_job_user_updated", "user_id", "updated_at"),
    )

    def to_dict(self, security=None, include_description=True):
        description = ""
        if include_description and security:
            description = security.decrypt(self.description_encrypted)
        return {
            "id": self.id,
            "title": self.title,
            "description": description,
            "required_skills": self.required_skills or "",
            "min_experience": self.min_experience,
            "min_education": self.min_education,
            "status": self.status,
            "resume_count": len(self.resumes),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class Resume(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey("job.id"), nullable=False, index=True)
    filename_hash = db.Column(db.String(64), nullable=False, index=True)
    file_sha256 = db.Column(db.String(64), nullable=False, index=True)
    original_filename_encrypted = db.Column(db.Text, nullable=False)
    candidate_name_encrypted = db.Column(db.Text, default="")
    candidate_email_encrypted = db.Column(db.Text, default="")
    candidate_phone_encrypted = db.Column(db.Text, default="")
    raw_text_encrypted = db.Column(db.Text, nullable=False)
    extracted_skills = db.Column(db.Text, default="")
    years_experience = db.Column(db.Float, default=0.0)
    education_level = db.Column(db.String(100), default="not specified")
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    job = db.relationship("Job", back_populates="resumes")
    analysis = db.relationship("AnalysisResult", back_populates="resume", uselist=False, cascade="all, delete-orphan")

    __table_args__ = (
        db.UniqueConstraint("job_id", "file_sha256", name="uq_resume_job_file"),
        db.Index("rume_idx_resume_job_uploaded", "job_id", "uploaded_at"),
    )

    def to_dict(self, security=None):
        filename = ""
        name = ""
        email = ""
        if security:
            filename = security.decrypt(self.original_filename_encrypted) or ""
            name = security.decrypt(self.candidate_name_encrypted) or ""
            email = security.decrypt(self.candidate_email_encrypted) or ""
        skills = [s for s in (self.extracted_skills or "").split(",") if s]
        return {
            "id": self.id,
            "job_id": self.job_id,
            "filename": filename,
            "candidate_name": name or "Unknown candidate",
            "candidate_email_masked": security.mask_email(email) if security else "",
            "extracted_skills": skills,
            "years_experience": self.years_experience,
            "education_level": self.education_level,
            "uploaded_at": self.uploaded_at.isoformat(),
            "analysis": self.analysis.to_dict() if self.analysis else None,
        }


class AnalysisResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    resume_id = db.Column(db.Integer, db.ForeignKey("resume.id"), nullable=False, unique=True, index=True)
    overall_score = db.Column(db.Float, default=0.0, nullable=False)
    skill_score = db.Column(db.Float, default=0.0, nullable=False)
    experience_score = db.Column(db.Float, default=0.0, nullable=False)
    education_score = db.Column(db.Float, default=0.0, nullable=False)
    similarity_score = db.Column(db.Float, default=0.0, nullable=False)
    status = db.Column(db.String(50), default="pending", nullable=False, index=True)
    matched_skills = db.Column(db.Text, default="")
    missing_skills = db.Column(db.Text, default="")
    strengths = db.Column(db.Text, default="")
    weaknesses = db.Column(db.Text, default="")
    explanation = db.Column(db.Text, default="")
    analyzed_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    resume = db.relationship("Resume", back_populates="analysis")

    def to_dict(self):
        return {
            "id": self.id,
            "resume_id": self.resume_id,
            "overall_score": round(self.overall_score, 1),
            "skill_score": round(self.skill_score, 1),
            "experience_score": round(self.experience_score, 1),
            "education_score": round(self.education_score, 1),
            "similarity_score": round(self.similarity_score, 1),
            "status": self.status,
            "matched_skills": self.matched_skills or "",
            "missing_skills": self.missing_skills or "",
            "strengths": self.strengths or "",
            "weaknesses": self.weaknesses or "",
            "explanation": self.explanation or "",
            "analyzed_at": self.analyzed_at.isoformat(),
        }


class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True, index=True)
    action = db.Column(db.String(100), nullable=False)
    resource_type = db.Column(db.String(50), default="")
    resource_id = db.Column(db.Integer)
    detail = db.Column(db.Text, default="")
    ip_address = db.Column(db.String(45), default="")
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    user = db.relationship("User", back_populates="audit_logs")

    __table_args__ = (db.Index("rume_idx_audit_user_time", "user_id", "timestamp"),)

    def to_dict(self):
        return {
            "id": self.id,
            "action": self.action,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "detail": self.detail,
            "timestamp": self.timestamp.isoformat(),
        }
