"""API routes for RUME AI."""
import csv
import hashlib
import io
import json
import re
from datetime import datetime

from flask import Blueprint, current_app, g, jsonify, request, Response
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from app.analyzer import ResumeAnalyzer
from app.config import Config
from app.main import db, limiter
from app.models import AnalysisResult, AuditLog, CalibrationVersion, CandidateComment, CandidateDecision, CandidateTag, Job, RequestLog, Resume, User
from app.resume_parser import ResumeParser
from app.security import SecurityManager, clear_auth_cookie, log_action, require_auth, set_auth_cookie

api = Blueprint("api", __name__, url_prefix="/api")


@api.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint for monitoring and load balancers."""
    return jsonify({
        "status": "healthy",
        "service": "rume-ai",
        "timestamp": datetime.utcnow().isoformat(),
    }), 200


def json_body():
    return request.get_json(silent=True) or {}


def error(message, status=400):
    payload = {"error": message}
    request_id = getattr(g, "request_id", None)
    if request_id:
        payload["request_id"] = request_id
    return jsonify(payload), status


def owned_job(job_id):
    return Job.query.filter_by(id=job_id, user_id=request.user_id).first()


def positive_int(value, default=0, maximum=50):
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default
    return max(0, min(number, maximum))


def serialize_candidates(resumes, security, blind=False):
    return [resume.to_dict(security, blind=blind) for resume in resumes]


def bool_arg(name, default=False):
    value = request.args.get(name)
    if value is None:
        return default
    return str(value).lower() in {"1", "true", "yes", "on"}


def calibration_criteria(job):
    return {
        "title": job.title,
        "required_skills_raw": job.required_skills or "",
        "required_skills_normalized": ResumeAnalyzer._required_skills(job.required_skills),
        "min_experience": job.min_experience,
        "min_education": job.min_education,
        "weights": ResumeAnalyzer.WEIGHTS,
        "status_thresholds": {
            "highly_qualified": 75,
            "qualified": 55,
            "partially_qualified": 35,
        },
    }


def create_calibration_version(job):
    criteria = calibration_criteria(job)
    criteria_json = json.dumps(criteria, sort_keys=True, separators=(",", ":"))
    criteria_hash = hashlib.sha256(criteria_json.encode("utf-8")).hexdigest()
    latest_version = (
        db.session.query(func.max(CalibrationVersion.version))
        .filter_by(job_id=job.id)
        .scalar()
        or 0
    )
    calibration = CalibrationVersion(
        job_id=job.id,
        user_id=request.user_id,
        version=latest_version + 1,
        criteria_hash=criteria_hash,
        criteria_json=criteria_json,
    )
    db.session.add(calibration)
    db.session.flush()
    return calibration


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

    # Advanced analytics
    status_breakdown = {}
    if job_ids:
        status_results = (
            db.session.query(AnalysisResult.status, func.count(AnalysisResult.id))
            .join(Resume)
            .filter(Resume.job_id.in_(job_ids))
            .group_by(AnalysisResult.status)
            .all()
        )
        status_breakdown = {status: count for status, count in status_results}

    skill_frequency = {}
    if job_ids:
        all_skills = db.session.query(Resume.extracted_skills).filter(Resume.job_id.in_(job_ids)).all()
        skill_counter = {}
        for (skills_str,) in all_skills:
            for skill in (skills_str or "").split(","):
                if skill.strip():
                    skill_counter[skill.strip()] = skill_counter.get(skill.strip(), 0) + 1
        skill_frequency = dict(sorted(skill_counter.items(), key=lambda x: x[1], reverse=True)[:20])

    score_distribution = {"0-25": 0, "26-50": 0, "51-75": 0, "76-100": 0}
    if job_ids:
        scores = (
            db.session.query(AnalysisResult.overall_score)
            .join(Resume)
            .filter(Resume.job_id.in_(job_ids))
            .all()
        )
        for (score,) in scores:
            if score <= 25:
                score_distribution["0-25"] += 1
            elif score <= 50:
                score_distribution["26-50"] += 1
            elif score <= 75:
                score_distribution["51-75"] += 1
            else:
                score_distribution["76-100"] += 1

    time_series_data = []
    if job_ids:
        last_30_days = (
            db.session.query(
                func.date(AnalysisResult.analyzed_at).label('date'),
                func.count(AnalysisResult.id).label('count')
            )
            .join(Resume)
            .filter(Resume.job_id.in_(job_ids))
            .filter(AnalysisResult.analyzed_at >= func.datetime('now', '-30 days'))
            .group_by(func.date(AnalysisResult.analyzed_at))
            .order_by(func.date(AnalysisResult.analyzed_at))
            .all()
        )
        time_series_data = [{"date": str(date), "count": count} for date, count in last_30_days]

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
            "analytics": {
                "status_breakdown": status_breakdown,
                "skill_frequency": skill_frequency,
                "score_distribution": score_distribution,
                "time_series_data": time_series_data,
            },
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
        data["calibration_versions"] = [item.to_dict() for item in job.calibration_versions[:10]]
        resumes = Resume.query.filter_by(job_id=job.id).order_by(Resume.uploaded_at.desc()).all()
        data["candidates"] = serialize_candidates(resumes, security, blind=bool_arg("blind"))
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
    calibration = create_calibration_version(job)
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
        result.evidence_encrypted = security.encrypt(json.dumps(analysis["evidence"], separators=(",", ":")))
        result.calibration_version_id = calibration.id
        resume.years_experience = analysis["experience"]
        resume.education_level = analysis["education"]
        resume.extracted_skills = ",".join(analysis["all_skills"])

        result_summary.append(
            {
                "resume_id": resume.id,
                "candidate_name": security.decrypt(resume.candidate_name_encrypted),
                "overall_score": result.overall_score,
                "status": result.status,
                "calibration_version": calibration.version,
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
            "calibration_version": calibration.to_dict(),
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
    page = positive_int(request.args.get("page"), default=1, maximum=100)
    per_page = positive_int(request.args.get("per_page"), default=20, maximum=100)
    search_query = request.args.get("search", "").strip().lower()
    min_score = positive_int(request.args.get("min_score"), default=0, maximum=100)
    max_score = positive_int(request.args.get("max_score"), default=100, maximum=100)
    skills_filter = request.args.get("skills", "").strip().lower()

    query = Resume.query.filter_by(job_id=job.id)

    # Apply search filter
    if search_query:
        query = query.join(AnalysisResult).filter(
            db.or_(
                Resume.candidate_name_encrypted.like(f"%{search_query}%"),
                Resume.extracted_skills.like(f"%{search_query}%"),
                AnalysisResult.strengths.like(f"%{search_query}%"),
                AnalysisResult.weaknesses.like(f"%{search_query}%"),
            )
        )

    # Apply skills filter
    if skills_filter:
        required_skills = [s.strip() for s in skills_filter.split(",")]
        for skill in required_skills:
            if skill:
                query = query.filter(Resume.extracted_skills.like(f"%{skill}%"))

    resumes = query.all()
    candidates = [resume.to_dict(security, blind=bool_arg("blind")) for resume in resumes]

    # Apply status filter
    if status != "all":
        candidates = [c for c in candidates if c.get("analysis") and c["analysis"]["status"] == status]

    # Apply score range filter
    if min_score > 0 or max_score < 100:
        candidates = [
            c for c in candidates
            if c.get("analysis") and min_score <= c["analysis"]["overall_score"] <= max_score
        ]

    def score_key(candidate):
        return candidate.get("analysis", {}).get("overall_score", 0) if candidate.get("analysis") else 0

    sorters = {
        "score": lambda c: (-score_key(c), c["candidate_name"].lower()),
        "experience": lambda c: (-(c.get("years_experience") or 0), -score_key(c)),
        "uploaded": lambda c: (c.get("uploaded_at") or ""),
        "name": lambda c: c["candidate_name"].lower(),
        "education": lambda c: (c.get("education_level") or "", -score_key(c)),
    }
    candidates.sort(key=sorters.get(sort, sorters["score"]), reverse=(sort == "uploaded"))

    # Pagination
    total_candidates = len(candidates)
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    paginated_candidates = candidates[start_idx:end_idx]

    job_data = job.to_dict(security)
    job_data["latest_calibration"] = job.calibration_versions[0].to_dict() if job.calibration_versions else None
    return jsonify({
        "job": job_data,
        "candidates": paginated_candidates,
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total_candidates,
            "total_pages": (total_candidates + per_page - 1) // per_page,
            "has_next": end_idx < total_candidates,
            "has_prev": page > 1,
        },
        "filters_applied": {
            "status": status,
            "sort": sort,
            "search": search_query,
            "min_score": min_score,
            "max_score": max_score,
            "skills": skills_filter,
        },
    })


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


@api.route("/jobs/<int:job_id>/candidates/<int:resume_id>/decision", methods=["GET", "POST"])
@require_auth
def candidate_decision(job_id, resume_id):
    security = SecurityManager
    job = owned_job(job_id)
    if not job:
        return error("Job not found", 404)

    resume = Resume.query.filter_by(id=resume_id, job_id=job.id).first()
    if not resume:
        return error("Candidate not found", 404)

    if request.method == "GET":
        decisions = CandidateDecision.query.filter_by(resume_id=resume.id).order_by(CandidateDecision.created_at.desc()).all()
        return jsonify({"decisions": [decision.to_dict(security) for decision in decisions]})

    data = json_body()
    decision = SecurityManager.sanitize(data.get("decision") or "manual_review", 40)
    allowed = {"manual_review", "advance", "hold", "reject", "needs_info"}
    if decision not in allowed:
        return error("Decision is invalid")

    note = SecurityManager.sanitize(data.get("note"), 2000)
    entry = CandidateDecision(
        job_id=job.id,
        resume_id=resume.id,
        user_id=request.user_id,
        decision=decision,
        note_encrypted=security.encrypt(note),
    )
    db.session.add(entry)
    log_action("candidate_decision", "resume", resume.id, f"Decision: {decision}")
    db.session.commit()
    return jsonify(entry.to_dict(security)), 201


@api.route("/jobs/<int:job_id>/candidates/bulk", methods=["POST", "DELETE"])
@require_auth
@limiter.limit("50 per hour")
def bulk_candidate_operations(job_id):
    security = SecurityManager
    job = owned_job(job_id)
    if not job:
        return error("Job not found", 404)

    data = json_body()
    resume_ids = data.get("resume_ids", [])
    if not resume_ids or not isinstance(resume_ids, list):
        return error("resume_ids array is required")
    if len(resume_ids) > 100:
        return error("Cannot process more than 100 candidates at once")

    resumes = Resume.query.filter(Resume.id.in_(resume_ids), Resume.job_id == job.id).all()
    found_ids = {resume.id for resume in resumes}
    missing_ids = set(resume_ids) - found_ids

    if request.method == "DELETE":
        deleted_count = 0
        for resume in resumes:
            log_action("delete_candidate", "resume", resume.id, f"Bulk removed candidate from job {job.id}")
            db.session.delete(resume)
            deleted_count += 1
        db.session.commit()
        return jsonify({
            "deleted": deleted_count,
            "missing": len(missing_ids),
            "message": f"Deleted {deleted_count} candidates"
        })

    # POST for bulk decisions
    decision = SecurityManager.sanitize(data.get("decision") or "manual_review", 40)
    allowed = {"manual_review", "advance", "hold", "reject", "needs_info"}
    if decision not in allowed:
        return error("Decision is invalid")

    note = SecurityManager.sanitize(data.get("note"), 2000)
    decisions_created = 0
    for resume in resumes:
        entry = CandidateDecision(
            job_id=job.id,
            resume_id=resume.id,
            user_id=request.user_id,
            decision=decision,
            note_encrypted=security.encrypt(note),
        )
        db.session.add(entry)
        decisions_created += 1

    log_action("bulk_candidate_decision", "job", job.id, f"Bulk decision: {decision} for {decisions_created} candidates")
    db.session.commit()
    return jsonify({
        "decisions_created": decisions_created,
        "missing": len(missing_ids),
        "decision": decision,
        "message": f"Applied {decision} to {decisions_created} candidates"
    })


@api.route("/jobs/<int:job_id>/skill-gap-analysis", methods=["GET"])
@require_auth
def skill_gap_analysis(job_id):
    security = SecurityManager
    job = owned_job(job_id)
    if not job:
        return error("Job not found", 404)

    required_skills = ResumeAnalyzer._required_skills(job.required_skills)
    resumes = Resume.query.filter_by(job_id=job.id).all()

    skill_coverage = {skill: {"covered": 0, "total": len(resumes)} for skill in required_skills}
    missing_skills_summary = {}

    for resume in resumes:
        resume_skills = set((resume.extracted_skills or "").split(","))
        for skill in required_skills:
            if skill in resume_skills:
                skill_coverage[skill]["covered"] += 1

        if resume.analysis:
            missing = (resume.analysis.missing_skills or "").split(",")
            for skill in missing:
                if skill.strip():
                    missing_skills_summary[skill.strip()] = missing_skills_summary.get(skill.strip(), 0) + 1

    # Learning recommendations based on missing skills
    learning_recommendations = {
        "python": {
            "courses": ["Python for Data Science", "Complete Python Bootcamp"],
            "resources": ["Python.org Documentation", "Real Python"],
            "estimated_time": "4-8 weeks",
        },
        "javascript": {
            "courses": ["JavaScript: Understanding the Weird Parts", "Modern JavaScript"],
            "resources": ["MDN Web Docs", "JavaScript.info"],
            "estimated_time": "6-10 weeks",
        },
        "machine learning": {
            "courses": ["Machine Learning Specialization", "Deep Learning Specialization"],
            "resources": ["Coursera", "fast.ai"],
            "estimated_time": "12-20 weeks",
        },
        "react": {
            "courses": ["React - The Complete Guide", "Modern React with Redux"],
            "resources": ["React Documentation", "React Patterns"],
            "estimated_time": "4-8 weeks",
        },
        "aws": {
            "courses": ["AWS Certified Solutions Architect", "AWS Cloud Practitioner"],
            "resources": ["AWS Documentation", "AWS Training"],
            "estimated_time": "8-12 weeks",
        },
    }

    # Add generic recommendations for skills not in the predefined list
    for skill in required_skills:
        if skill not in learning_recommendations:
            learning_recommendations[skill] = {
                "courses": [f"Advanced {skill.title()} Course"],
                "resources": [f"{skill.title()} Documentation", "Community Forums"],
                "estimated_time": "4-12 weeks",
            }

    coverage_percentage = {
        skill: round((data["covered"] / data["total"] * 100) if data["total"] > 0 else 0, 1)
        for skill, data in skill_coverage.items()
    }

    return jsonify({
        "job_id": job.id,
        "required_skills": required_skills,
        "skill_coverage": skill_coverage,
        "coverage_percentage": coverage_percentage,
        "missing_skills_summary": dict(sorted(missing_skills_summary.items(), key=lambda x: x[1], reverse=True)),
        "learning_recommendations": learning_recommendations,
        "total_candidates": len(resumes),
    })


@api.route("/jobs/<int:job_id>/calibrations", methods=["GET"])
@require_auth
def calibrations(job_id):
    job = owned_job(job_id)
    if not job:
        return error("Job not found", 404)
    return jsonify({"calibrations": [calibration.to_dict() for calibration in job.calibration_versions]})


@api.route("/jobs/<int:job_id>/audit-pack", methods=["GET"])
@require_auth
def audit_pack(job_id):
    security = SecurityManager
    job = owned_job(job_id)
    if not job:
        return error("Job not found", 404)

    resumes = Resume.query.filter_by(job_id=job.id).all()
    candidate_data = [resume.to_dict(security, blind=bool_arg("blind")) for resume in resumes]
    resume_ids = [resume.id for resume in resumes]
    audit_logs = (
        AuditLog.query.filter_by(user_id=request.user_id)
        .filter(
            ((AuditLog.resource_type == "job") & (AuditLog.resource_id == job.id))
            | ((AuditLog.resource_type == "resume") & (AuditLog.resource_id.in_(resume_ids or [0])))
        )
        .order_by(AuditLog.timestamp.asc())
        .all()
    )
    decisions = (
        CandidateDecision.query.filter_by(job_id=job.id)
        .order_by(CandidateDecision.created_at.asc())
        .all()
    )
    pack = {
        "generated_at": datetime.utcnow().isoformat(),
        "generated_by_user_id": request.user_id,
        "job": job.to_dict(security),
        "calibration_versions": [calibration.to_dict() for calibration in job.calibration_versions],
        "candidates": candidate_data,
        "decision_journal": [decision.to_dict(security) for decision in decisions],
        "audit_logs": [entry.to_dict() for entry in audit_logs],
        "privacy_note": "Raw resume text and unmasked emails are excluded from this audit pack.",
    }
    log_action("export_audit_pack", "job", job.id, f"Exported audit pack for {job.title}")
    db.session.commit()
    return jsonify(pack)


@api.route("/logs", methods=["GET"])
@require_auth
def request_logs():
    query = RequestLog.query.filter_by(user_id=request.user_id)
    level = request.args.get("level")
    event = request.args.get("event")
    request_id = request.args.get("request_id")
    path = request.args.get("path")
    status = request.args.get("status")
    if level in {"debug", "info", "error"}:
        query = query.filter_by(level=level)
    if event:
        query = query.filter(RequestLog.event.contains(SecurityManager.sanitize(event, 100)))
    if request_id:
        query = query.filter_by(request_id=SecurityManager.sanitize(request_id, 120))
    if path:
        query = query.filter(RequestLog.path.contains(SecurityManager.sanitize(path, 200)))
    if status:
        try:
            query = query.filter_by(status_code=int(status))
        except ValueError:
            return error("Status must be numeric")

    limit = positive_int(request.args.get("limit"), default=50, maximum=200)
    logs = query.order_by(RequestLog.created_at.desc()).limit(limit or 50).all()
    return jsonify({"logs": [entry.to_dict() for entry in logs]})


@api.route("/admin/rate-limit-stats", methods=["GET"])
@require_auth
def rate_limit_stats():
    """Get rate limiting statistics for monitoring."""
    from app.main import rate_limit_stats
    
    # Only allow admins or the user to see their own stats
    # For now, return aggregated stats
    return jsonify({
        "rate_limit_stats": dict(rate_limit_stats),
        "total_endpoints": len(rate_limit_stats),
        "total_hits": sum(stats["hits"] for stats in rate_limit_stats.values()),
        "total_blocked": sum(stats["blocked"] for stats in rate_limit_stats.values()),
    })


@api.route("/jobs/<int:job_id>/export", methods=["GET"])
@require_auth
def export_candidates(job_id):
    security = SecurityManager
    job = owned_job(job_id)
    if not job:
        return error("Job not found", 404)

    export_format = request.args.get("format", "csv").lower()
    if export_format not in {"csv", "json"}:
        return error("Format must be csv or json")

    resumes = Resume.query.filter_by(job_id=job.id).all()
    candidates = [resume.to_dict(security, blind=bool_arg("blind")) for resume in resumes]

    if export_format == "json":
        export_data = {
            "job": job.to_dict(security),
            "exported_at": datetime.utcnow().isoformat(),
            "total_candidates": len(candidates),
            "candidates": candidates,
        }
        response = jsonify(export_data)
        response.headers["Content-Disposition"] = f'attachment; filename="job_{job_id}_candidates.json"'
        return response

    # CSV export
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header row
    writer.writerow([
        "Candidate Name", "Email", "Filename", "Overall Score", "Status",
        "Skill Score", "Experience Score", "Education Score", "Similarity Score",
        "Matched Skills", "Missing Skills", "Years Experience", "Education Level",
        "Strengths", "Weaknesses", "Uploaded At"
    ])
    
    # Data rows
    for candidate in candidates:
        analysis = candidate.get("analysis", {})
        writer.writerow([
            candidate.get("candidate_name", ""),
            candidate.get("candidate_email_masked", ""),
            candidate.get("filename", ""),
            analysis.get("overall_score", ""),
            analysis.get("status", ""),
            analysis.get("skill_score", ""),
            analysis.get("experience_score", ""),
            analysis.get("education_score", ""),
            analysis.get("similarity_score", ""),
            analysis.get("matched_skills", ""),
            analysis.get("missing_skills", ""),
            candidate.get("years_experience", ""),
            candidate.get("education_level", ""),
            analysis.get("strengths", ""),
            analysis.get("weaknesses", ""),
            candidate.get("uploaded_at", ""),
        ])
    
    output.seek(0)
    response = Response(output.getvalue(), mimetype="text/csv")
    response.headers["Content-Disposition"] = f'attachment; filename="job_{job_id}_candidates.csv"'
    log_action("export_candidates", "job", job.id, f"Exported {len(candidates)} candidates as CSV")
    db.session.commit()
    return response


@api.route("/jobs/<int:job_id>/candidates/<int:resume_id>/comments", methods=["GET", "POST"])
@require_auth
def candidate_comments(job_id, resume_id):
    security = SecurityManager
    job = owned_job(job_id)
    if not job:
        return error("Job not found", 404)

    resume = Resume.query.filter_by(id=resume_id, job_id=job.id).first()
    if not resume:
        return error("Candidate not found", 404)

    if request.method == "GET":
        comments = CandidateComment.query.filter_by(resume_id=resume.id).order_by(CandidateComment.created_at.desc()).all()
        return jsonify({"comments": [comment.to_dict(security) for comment in comments]})

    data = json_body()
    comment = SecurityManager.sanitize(data.get("comment"), 5000)
    if not comment or len(comment) < 1:
        return error("Comment cannot be empty")

    new_comment = CandidateComment(
        job_id=job.id,
        resume_id=resume.id,
        user_id=request.user_id,
        comment_encrypted=security.encrypt(comment),
    )
    db.session.add(new_comment)
    log_action("add_comment", "resume", resume.id, "Added comment to candidate")
    db.session.commit()
    return jsonify(new_comment.to_dict(security)), 201


@api.route("/jobs/<int:job_id>/candidates/<int:resume_id>/comments/<int:comment_id>", methods=["PUT", "DELETE"])
@require_auth
def candidate_comment_detail(job_id, resume_id, comment_id):
    security = SecurityManager
    job = owned_job(job_id)
    if not job:
        return error("Job not found", 404)

    resume = Resume.query.filter_by(id=resume_id, job_id=job.id).first()
    if not resume:
        return error("Candidate not found", 404)

    comment = CandidateComment.query.filter_by(id=comment_id, resume_id=resume.id).first()
    if not comment:
        return error("Comment not found", 404)

    if request.method == "DELETE":
        log_action("delete_comment", "resume", resume.id, "Deleted comment from candidate")
        db.session.delete(comment)
        db.session.commit()
        return jsonify({"message": "Comment deleted"})

    data = json_body()
    updated_comment = SecurityManager.sanitize(data.get("comment"), 5000)
    if not updated_comment or len(updated_comment) < 1:
        return error("Comment cannot be empty")

    comment.comment_encrypted = security.encrypt(updated_comment)
    log_action("update_comment", "resume", resume.id, "Updated comment on candidate")
    db.session.commit()
    return jsonify(comment.to_dict(security))


@api.route("/jobs/<int:job_id>/candidates/<int:resume_id>/tags", methods=["GET", "POST"])
@require_auth
def candidate_tags(job_id, resume_id):
    job = owned_job(job_id)
    if not job:
        return error("Job not found", 404)

    resume = Resume.query.filter_by(id=resume_id, job_id=job.id).first()
    if not resume:
        return error("Candidate not found", 404)

    if request.method == "GET":
        tags = CandidateTag.query.filter_by(resume_id=resume.id).order_by(CandidateTag.created_at.desc()).all()
        return jsonify({"tags": [tag.to_dict() for tag in tags]})

    data = json_body()
    tag = SecurityManager.sanitize(data.get("tag"), 50)
    color = SecurityManager.sanitize(data.get("color", "#3b82f6"), 7)
    
    if not tag or len(tag) < 1:
        return error("Tag cannot be empty")
    if not re.match(r"^#[0-9a-fA-F]{6}$", color):
        return error("Color must be a valid hex color (e.g., #3b82f6)")

    # Check if tag already exists
    existing = CandidateTag.query.filter_by(resume_id=resume.id, tag=tag).first()
    if existing:
        return error("Tag already exists for this candidate", 409)

    new_tag = CandidateTag(
        job_id=job.id,
        resume_id=resume.id,
        user_id=request.user_id,
        tag=tag,
        color=color,
    )
    db.session.add(new_tag)
    log_action("add_tag", "resume", resume.id, f"Added tag: {tag}")
    db.session.commit()
    return jsonify(new_tag.to_dict()), 201


@api.route("/jobs/<int:job_id>/candidates/<int:resume_id>/tags/<int:tag_id>", methods=["DELETE"])
@require_auth
def candidate_tag_detail(job_id, resume_id, tag_id):
    job = owned_job(job_id)
    if not job:
        return error("Job not found", 404)

    resume = Resume.query.filter_by(id=resume_id, job_id=job.id).first()
    if not resume:
        return error("Candidate not found", 404)

    tag = CandidateTag.query.filter_by(id=tag_id, resume_id=resume.id).first()
    if not tag:
        return error("Tag not found", 404)

    log_action("delete_tag", "resume", resume.id, f"Deleted tag: {tag.tag}")
    db.session.delete(tag)
    db.session.commit()
    return jsonify({"message": "Tag deleted"})


@api.route("/jobs/<int:job_id>/tags", methods=["GET"])
@require_auth
def job_tags(job_id):
    job = owned_job(job_id)
    if not job:
        return error("Job not found", 404)

    tags = db.session.query(
        CandidateTag.tag,
        CandidateTag.color,
        func.count(CandidateTag.id).label('count')
    ).filter_by(job_id=job.id).group_by(CandidateTag.tag, CandidateTag.color).all()
    
    tag_summary = [{"tag": tag, "color": color, "count": count} for tag, color, count in tags]
    return jsonify({"tags": sorted(tag_summary, key=lambda x: x["count"], reverse=True)})


@api.route("/search", methods=["GET"])
@require_auth
def global_search():
    security = SecurityManager
    query = request.args.get("q", "").strip().lower()
    if not query or len(query) < 2:
        return error("Search query must be at least 2 characters")

    search_type = request.args.get("type", "all")
    limit = positive_int(request.args.get("limit"), default=20, maximum=50)

    results = {"jobs": [], "candidates": []}

    if search_type in {"all", "jobs"}:
        jobs = Job.query.filter_by(user_id=request.user_id).filter(
            db.or_(
                Job.title.like(f"%{query}%"),
                Job.required_skills.like(f"%{query}%"),
            )
        ).limit(limit).all()
        results["jobs"] = [job.to_dict(security, include_description=False) for job in jobs]

    if search_type in {"all", "candidates"}:
        user_job_ids = [job.id for job in Job.query.filter_by(user_id=request.user_id).all()]
        if user_job_ids:
            resumes = Resume.query.filter(Resume.job_id.in_(user_job_ids)).filter(
                db.or_(
                    Resume.candidate_name_encrypted.like(f"%{query}%"),
                    Resume.extracted_skills.like(f"%{query}%"),
                )
            ).join(AnalysisResult).filter(
                db.or_(
                    AnalysisResult.strengths.like(f"%{query}%"),
                    AnalysisResult.weaknesses.like(f"%{query}%"),
                    AnalysisResult.matched_skills.like(f"%{query}%"),
                )
            ).limit(limit).all()
            results["candidates"] = [resume.to_dict(security) for resume in resumes]

    return jsonify({
        "query": query,
        "results": results,
        "total": len(results["jobs"]) + len(results["candidates"]),
    })
