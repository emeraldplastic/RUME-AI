"""Database models for RUME AI."""
import json
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
    calibration_versions = db.relationship(
        "CalibrationVersion",
        back_populates="job",
        cascade="all, delete-orphan",
        order_by="CalibrationVersion.version.desc()",
    )

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


class CalibrationVersion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey("job.id"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    version = db.Column(db.Integer, nullable=False)
    criteria_hash = db.Column(db.String(64), nullable=False, index=True)
    criteria_json = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    job = db.relationship("Job", back_populates="calibration_versions")

    __table_args__ = (
        db.UniqueConstraint("job_id", "version", name="uq_calibration_job_version"),
        db.Index("rume_idx_calibration_job_time", "job_id", "created_at"),
    )

    def criteria(self):
        try:
            return json.loads(self.criteria_json or "{}")
        except json.JSONDecodeError:
            return {}

    def to_dict(self):
        return {
            "id": self.id,
            "job_id": self.job_id,
            "version": self.version,
            "criteria_hash": self.criteria_hash,
            "criteria": self.criteria(),
            "created_at": self.created_at.isoformat(),
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
    decisions = db.relationship(
        "CandidateDecision",
        back_populates="resume",
        cascade="all, delete-orphan",
        order_by="CandidateDecision.created_at.desc()",
    )

    __table_args__ = (
        db.UniqueConstraint("job_id", "file_sha256", name="uq_resume_job_file"),
        db.Index("rume_idx_resume_job_uploaded", "job_id", "uploaded_at"),
    )

    def to_dict(self, security=None, blind=False):
        filename = ""
        name = ""
        email = ""
        if security:
            filename = security.decrypt(self.original_filename_encrypted) or ""
            name = security.decrypt(self.candidate_name_encrypted) or ""
            email = security.decrypt(self.candidate_email_encrypted) or ""
        skills = [s for s in (self.extracted_skills or "").split(",") if s]
        latest_decision = self.decisions[0].to_dict(security) if self.decisions else None
        return {
            "id": self.id,
            "job_id": self.job_id,
            "filename": "Hidden in blind review" if blind else filename,
            "candidate_name": f"Candidate {self.id}" if blind else name or "Unknown candidate",
            "candidate_email_masked": "" if blind else security.mask_email(email) if security else "",
            "blind_review": blind,
            "extracted_skills": skills,
            "years_experience": self.years_experience,
            "education_level": self.education_level,
            "uploaded_at": self.uploaded_at.isoformat(),
            "analysis": self.analysis.to_dict(security) if self.analysis else None,
            "latest_decision": latest_decision,
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
    evidence_encrypted = db.Column(db.Text, default="")
    calibration_version_id = db.Column(db.Integer, db.ForeignKey("calibration_version.id"), nullable=True, index=True)
    analyzed_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    resume = db.relationship("Resume", back_populates="analysis")
    calibration_version = db.relationship("CalibrationVersion")

    def evidence(self, security=None):
        if not security or not self.evidence_encrypted:
            return {}
        try:
            return json.loads(security.decrypt(self.evidence_encrypted) or "{}")
        except json.JSONDecodeError:
            return {}

    def to_dict(self, security=None):
        return {
            "id": self.id,
            "resume_id": self.resume_id,
            "calibration_version_id": self.calibration_version_id,
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
            "evidence": self.evidence(security),
            "analyzed_at": self.analyzed_at.isoformat(),
        }


class CandidateDecision(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey("job.id"), nullable=False, index=True)
    resume_id = db.Column(db.Integer, db.ForeignKey("resume.id"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    decision = db.Column(db.String(40), default="manual_review", nullable=False, index=True)
    note_encrypted = db.Column(db.Text, default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    resume = db.relationship("Resume", back_populates="decisions")

    __table_args__ = (db.Index("rume_idx_decision_resume_time", "resume_id", "created_at"),)

    def to_dict(self, security=None):
        note = security.decrypt(self.note_encrypted) if security and self.note_encrypted else ""
        return {
            "id": self.id,
            "job_id": self.job_id,
            "resume_id": self.resume_id,
            "user_id": self.user_id,
            "decision": self.decision,
            "note": note,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
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


class RequestLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.String(120), nullable=False, index=True)
    user_id = db.Column(db.Integer, nullable=True, index=True)
    level = db.Column(db.String(20), nullable=False, index=True)
    event = db.Column(db.String(100), nullable=False, index=True)
    method = db.Column(db.String(12), default="")
    path = db.Column(db.String(300), default="", index=True)
    status_code = db.Column(db.Integer, nullable=True, index=True)
    duration_ms = db.Column(db.Float, nullable=True)
    payload_json = db.Column(db.Text, default="{}")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    __table_args__ = (
        db.Index("rume_idx_request_log_user_time", "user_id", "created_at"),
        db.Index("rume_idx_request_log_request_event", "request_id", "event"),
    )

    def payload(self):
        try:
            return json.loads(self.payload_json or "{}")
        except json.JSONDecodeError:
            return {}

    def to_dict(self):
        return {
            "id": self.id,
            "request_id": self.request_id,
            "user_id": self.user_id,
            "level": self.level,
            "event": self.event,
            "method": self.method,
            "path": self.path,
            "status_code": self.status_code,
            "duration_ms": self.duration_ms,
            "payload": self.payload(),
            "created_at": self.created_at.isoformat(),
        }
