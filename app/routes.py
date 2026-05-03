"""API routes for RUME AI."""
import hashlib
import re
from datetime import datetime

from flask import Blueprint, current_app, jsonify, request
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from app.analyzer import ResumeAnalyzer
from app.config import Config
from app.main import db, limiter
from app.models import AnalysisResult, AuditLog, Job, Resume, User
from app.resume_parser import ResumeParser
from app.security import SecurityManager, clear_auth_cookie, log_action, require_auth, set_auth_cookie

api = Blueprint("api", __name__, url_prefix="/api")


def json_body():
    return request.get_json(silent=True) or {}


def error(message, status=400):
    return jsonify({"error": message}), status


def owned_job(job_id):
    return Job.query.filter_by(id=job_id, user_id=request.user_id).first()


def positive_int(value, default=0, maximum=50):
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default
    return max(0, min(number, maximum))


def serialize_candidates(resumes, security):
    return [resume.to_dict(security) for resume in resumes]


@api.route("/auth/register", methods=["POST"])
@limiter.limit("5 per minute")
def register():
    data = json_body()
    username = SecurityManager.sanitize(data.get("username"), 80).lower()
    email = SecurityManager.sanitize(data.get("email"), 200).lower()
    display_name = SecurityManager.sanitize(data.get("display_name"), 100)
    password = data.get("password") or ""

    if len(username) < 3 or not re.fullmatch(r"[a-z0-9_.-]{3,80}", username):
        return error("Username must be 3-80 characters and use letters, numbers, dots, dashes, or underscores")
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        return error("A valid email is required")
    if len(password) < 8:
        return error("Password must be at least 8 characters")

    if User.query.filter((User.username == username) | (User.email == email)).first():
        return error("Username or email already exists", 409)

    user = User(
        username=username,
        email=email,
        display_name=display_name or username,
        password_hash=SecurityManager.hash_password(password),
    )
    db.session.add(user)
    db.session.flush()
    request.user_id = user.id
    log_action("register", "user", user.id, "Account created")
    db.session.commit()

    token = SecurityManager.generate_token(user.id)
    response = jsonify({"user": user.to_dict()})
    return set_auth_cookie(response, token), 201


@api.route("/auth/login", methods=["POST"])
@limiter.limit("10 per minute")
def login():
    data = json_body()
    username = SecurityManager.sanitize(data.get("username"), 80).lower()
    password = data.get("password") or ""
    user = User.query.filter_by(username=username).first()

    if not user or not user.is_active or not SecurityManager.check_password(password, user.password_hash):
        return error("Invalid credentials", 401)

    request.user_id = user.id
    log_action("login", "user", user.id, "User signed in")
    db.session.commit()

    token = SecurityManager.generate_token(user.id)
    response = jsonify({"user": user.to_dict()})
    return set_auth_cookie(response, token)


@api.route("/auth/logout", methods=["POST"])
def logout():
    response = jsonify({"message": "Logged out"})
    return clear_auth_cookie(response)


@api.route("/auth/me", methods=["GET"])
@require_auth
def me():
    user = User.query.get(request.user_id)
    if not user or not user.is_active:
        return error("User not found", 404)
    return jsonify({"user": user.to_dict()})


@api.route("/dashboard", methods=["GET"])
@require_auth
def dashboard():
    jobs = Job.query.filter_by(user_id=request.user_id).order_by(Job.updated_at.desc()).all()
    job_ids = [job.id for job in jobs]

    total_resumes = Resume.query.filter(Resume.job_id.in_(job_ids)).count() if job_ids else 0
    analyzed = (
        AnalysisResult.query.join(Resume).filter(Resume.job_id.in_(job_ids)).count()
        if job_ids
        else 0
    )
    qualified = (
        AnalysisResult.query.join(Resume)
        .filter(Resume.job_id.in_(job_ids), AnalysisResult.status.in_(("highly_qualified", "qualified")))
        .count()
        if job_ids
        else 0
    )
    average_score = (
        db.session.query(func.avg(AnalysisResult.overall_score))
        .join(Resume)
        .filter(Resume.job_id.in_(job_ids))
        .scalar()
        if job_ids
        else 0
    ) or 0

    activity = (
        AuditLog.query.filter_by(user_id=request.user_id)
        .order_by(AuditLog.timestamp.desc())
        .limit(10)
        .all()
    )

    security = SecurityManager
    return jsonify(
        {
            "stats": {
                "total_jobs": len(jobs),
                "active_jobs": len([job for job in jobs if job.status == "active"]),
                "total_resumes": total_resumes,
                "analyzed": analyzed,
                "qualified": qualified,
                "average_score": round(float(average_score), 1),
            },
            "recent_jobs": [job.to_dict(security, include_description=False) for job in jobs[:5]],
            "recent_activity": [entry.to_dict() for entry in activity],
        }
    )


@api.route("/jobs", methods=["GET", "POST"])
@require_auth
def jobs():
    security = SecurityManager
    if request.method == "GET":
        status = request.args.get("status")
        query = Job.query.filter_by(user_id=request.user_id)
        if status in {"active", "archived", "closed"}:
            query = query.filter_by(status=status)
        result = query.order_by(Job.updated_at.desc()).all()
        return jsonify([job.to_dict(security, include_description=False) for job in result])

    data = json_body()
    title = SecurityManager.sanitize(data.get("title"), 200)
    description = SecurityManager.sanitize(data.get("description"), 50000)
    required_skills = SecurityManager.sanitize(data.get("required_skills"), 2000)
    min_education = SecurityManager.sanitize(data.get("min_education") or "bachelor", 50).lower()

    if not title or not description:
        return error("Title and description are required")
    if min_education not in ResumeAnalyzer.EDUCATION_HIERARCHY:
        return error("Minimum education is invalid")

    job = Job(
        user_id=request.user_id,
        title=title,
        description_encrypted=security.encrypt(description),
        required_skills=required_skills,
        min_experience=positive_int(data.get("min_experience"), default=0),
        min_education=min_education,
    )
    db.session.add(job)
    db.session.flush()
    log_action("create_job", "job", job.id, f"Created job: {title}")
    db.session.commit()
    return jsonify(job.to_dict(security)), 201


@api.route("/jobs/<int:job_id>", methods=["GET", "PUT", "DELETE"])
@require_auth
def job_detail(job_id):
    security = SecurityManager
    job = owned_job(job_id)
    if not job:
        return error("Job not found", 404)

    if request.method == "GET":
        data = job.to_dict(security)
        resumes = Resume.query.filter_by(job_id=job.id).order_by(Resume.uploaded_at.desc()).all()
        data["candidates"] = serialize_candidates(resumes, security)
        return jsonify(data)

    if request.method == "PUT":
        data = json_body()
        if "title" in data:
            job.title = SecurityManager.sanitize(data.get("title"), 200)
        if "description" in data:
            description = SecurityManager.sanitize(data.get("description"), 50000)
            if not description:
                return error("Description cannot be empty")
            job.description_encrypted = security.encrypt(description)
        if "required_skills" in data:
            job.required_skills = SecurityManager.sanitize(data.get("required_skills"), 2000)
        if "min_experience" in data:
            job.min_experience = positive_int(data.get("min_experience"), default=job.min_experience)
        if "min_education" in data:
            min_education = SecurityManager.sanitize(data.get("min_education"), 50).lower()
            if min_education not in ResumeAnalyzer.EDUCATION_HIERARCHY:
                return error("Minimum education is invalid")
            job.min_education = min_education
        if "status" in data:
            status = data.get("status")
            if status not in {"active", "archived", "closed"}:
                return error("Status is invalid")
            job.status = status
        job.updated_at = datetime.utcnow()
        log_action("update_job", "job", job.id, f"Updated job: {job.title}")
        db.session.commit()
        return jsonify(job.to_dict(security))

    log_action("delete_job", "job", job.id, f"Deleted job: {job.title}")
    db.session.delete(job)
    db.session.commit()
    return jsonify({"message": "Job deleted"})


@api.route("/jobs/<int:job_id>/upload", methods=["POST"])
@require_auth
@limiter.limit("30 per hour")
def upload_resumes(job_id):
    security = SecurityManager
    job = owned_job(job_id)
    if not job:
        return error("Job not found", 404)
    if "resumes" not in request.files:
        return error("No resume files uploaded")

    uploaded = []
    errors = []
    files = [file for file in request.files.getlist("resumes") if file and file.filename]
    if not files:
        return error("No resume files uploaded")
    if len(files) > current_app.config["MAX_FILES_PER_UPLOAD"]:
        return error(f"Upload up to {current_app.config['MAX_FILES_PER_UPLOAD']} resumes at a time", 413)

    for file in files:
        original_name = file.filename or "resume"
        safe_name = security.safe_filename(original_name)
        if not Config.allowed_file(safe_name):
            errors.append(f"{safe_name}: unsupported file type")
            continue
        if not Config.allowed_mime(safe_name, file.mimetype or ""):
            errors.append(f"{safe_name}: file type does not match its extension")
            continue

        try:
            content = file.read()
            if len(content) > current_app.config["MAX_CONTENT_LENGTH"]:
                errors.append(f"{safe_name}: file exceeds upload limit")
                continue

            text = ResumeParser.parse(safe_name, content)
            if len(text.strip()) < 20:
                errors.append(f"{safe_name}: not enough readable resume text")
                continue

            file_sha = hashlib.sha256(content).hexdigest()
            if Resume.query.filter_by(job_id=job.id, file_sha256=file_sha).first():
                errors.append(f"{safe_name}: duplicate resume already exists for this job")
                continue

            contact = ResumeParser.extract_contact_info(text)
            skills = ResumeAnalyzer.extract_skills(text)
            resume = Resume(
                job_id=job.id,
                filename_hash=hashlib.sha256(f"{job.id}:{file_sha}:{safe_name}".encode("utf-8")).hexdigest(),
                file_sha256=file_sha,
                original_filename_encrypted=security.encrypt(safe_name),
                candidate_name_encrypted=security.encrypt(contact["name"]),
                candidate_email_encrypted=security.encrypt(contact["email"]),
                candidate_phone_encrypted=security.encrypt(contact["phone"]),
                raw_text_encrypted=security.encrypt(text),
                extracted_skills=",".join(skills),
                years_experience=ResumeParser.extract_experience_years(text),
                education_level=ResumeParser.detect_education(text),
            )
            db.session.add(resume)
            db.session.flush()
            uploaded.append(
                {
                    "id": resume.id,
                    "filename": safe_name,
                    "candidate_name": contact["name"],
                    "candidate_email_masked": security.mask_email(contact["email"]),
                    "skills_found": len(skills),
                    "years_experience": resume.years_experience,
                    "education_level": resume.education_level,
                }
            )
        except ValueError as exc:
            errors.append(f"{safe_name}: {str(exc)}")
        except Exception:
            errors.append(f"{safe_name}: could not parse securely")

    try:
        log_action("upload_resumes", "job", job.id, f"Uploaded {len(uploaded)} resumes")
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return error("One or more resumes were duplicates", 409)

    status_code = 201 if uploaded else 400
    return jsonify({"uploaded": len(uploaded), "results": uploaded, "errors": errors}), status_code


@api.route("/jobs/<int:job_id>/analyze", methods=["POST"])
@require_auth
@limiter.limit("20 per hour")
def analyze_resumes(job_id):
    security = SecurityManager
    job = owned_job(job_id)
    if not job:
        return error("Job not found", 404)

    resumes = Resume.query.filter_by(job_id=job.id).all()
    if not resumes:
        return error("Upload at least one resume before analysis")

    job_description = security.decrypt(job.description_encrypted)
    result_summary = []
    for resume in resumes:
        resume_text = security.decrypt(resume.raw_text_encrypted)
        analysis = ResumeAnalyzer.analyze(
            resume_text,
            job_description,
            job.required_skills,
            job.min_experience,
            job.min_education,
        )

        if resume.analysis:
            result = resume.analysis
            result.analyzed_at = datetime.utcnow()
        else:
            result = AnalysisResult(resume_id=resume.id)
            db.session.add(result)

        result.overall_score = analysis["overall_score"]
        result.skill_score = analysis["skill_score"]
        result.experience_score = analysis["experience_score"]
        result.education_score = analysis["education_score"]
        result.similarity_score = analysis["similarity_score"]
        result.status = analysis["status"]
        result.matched_skills = analysis["matched_skills"]
        result.missing_skills = analysis["missing_skills"]
        result.strengths = analysis["strengths"]
        result.weaknesses = analysis["weaknesses"]
        result.explanation = analysis["explanation"]
        resume.years_experience = analysis["experience"]
        resume.education_level = analysis["education"]
        resume.extracted_skills = ",".join(analysis["all_skills"])

        result_summary.append(
            {
                "resume_id": resume.id,
                "candidate_name": security.decrypt(resume.candidate_name_encrypted),
                "overall_score": result.overall_score,
                "status": result.status,
            }
        )

    result_summary.sort(key=lambda item: item["overall_score"], reverse=True)
    qualified_count = len([r for r in result_summary if r["status"] in {"highly_qualified", "qualified"}])
    scores = [r["overall_score"] for r in result_summary]

    log_action("analyze_resumes", "job", job.id, f"Analyzed {len(resumes)} resumes")
    db.session.commit()

    return jsonify(
        {
            "total": len(result_summary),
            "qualified": qualified_count,
            "not_qualified": len(result_summary) - qualified_count,
            "average_score": round(sum(scores) / len(scores), 1) if scores else 0,
            "highest_score": round(max(scores), 1) if scores else 0,
            "candidates": result_summary,
        }
    )


@api.route("/jobs/<int:job_id>/results", methods=["GET"])
@require_auth
def results(job_id):
    security = SecurityManager
    job = owned_job(job_id)
    if not job:
        return error("Job not found", 404)

    status = request.args.get("status", "all")
    sort = request.args.get("sort", "score")

    resumes = Resume.query.filter_by(job_id=job.id).all()
    candidates = [resume.to_dict(security) for resume in resumes]
    if status != "all":
        candidates = [c for c in candidates if c.get("analysis") and c["analysis"]["status"] == status]

    def score_key(candidate):
        return candidate.get("analysis", {}).get("overall_score", 0) if candidate.get("analysis") else 0

    sorters = {
        "score": lambda c: (-score_key(c), c["candidate_name"].lower()),
        "experience": lambda c: (-(c.get("years_experience") or 0), -score_key(c)),
        "uploaded": lambda c: (c.get("uploaded_at") or ""),
        "name": lambda c: c["candidate_name"].lower(),
    }
    candidates.sort(key=sorters.get(sort, sorters["score"]), reverse=(sort == "uploaded"))

    return jsonify({"job": job.to_dict(security), "candidates": candidates})


@api.route("/jobs/<int:job_id>/candidates/<int:resume_id>", methods=["DELETE"])
@require_auth
def delete_candidate(job_id, resume_id):
    job = owned_job(job_id)
    if not job:
        return error("Job not found", 404)

    resume = Resume.query.filter_by(id=resume_id, job_id=job.id).first()
    if not resume:
        return error("Candidate not found", 404)

    log_action("delete_candidate", "resume", resume.id, f"Removed candidate from job {job.id}")
    db.session.delete(resume)
    db.session.commit()
    return jsonify({"message": "Candidate removed"})
