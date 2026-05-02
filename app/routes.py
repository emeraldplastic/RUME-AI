from flask import Blueprint, request, jsonify, current_app
from app.main import db, limiter
from app.models import User, Job, Resume, AnalysisResult, AuditLog
from app.security import SecurityManager, require_auth, log_action
from app.resume_parser import ResumeParser
from app.analyzer import ResumeAnalyzer
import os
from werkzeug.utils import secure_filename
import hashlib

api = Blueprint('api', __name__)

# --- AUTH ---

@api.route('/api/auth/register', methods=['POST'])
@limiter.limit("5 per minute")
def register():
    data = request.json
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({'error': 'Missing credentials'}), 400
    
    if User.query.filter_by(username=data['username']).first():
        return jsonify({'error': 'Username already exists'}), 400
        
    user = User(
        username=SecurityManager.sanitize(data['username']),
        email=SecurityManager.sanitize(data.get('email')),
        password_hash=SecurityManager.hash_password(data['password']),
        display_name=SecurityManager.sanitize(data.get('display_name'))
    )
    db.session.add(user)
    db.session.commit()
    
    log_action('register', 'user', user.id, f"User {user.username} registered")
    token = SecurityManager.generate_token(user.id)
    return jsonify({'token': token, 'user': {'username': user.username, 'display_name': user.display_name}}), 201

@api.route('/api/auth/login', methods=['POST'])
@limiter.limit("10 per minute")
def login():
    data = request.json
    user = User.query.filter_by(username=data.get('username')).first()
    
    if user and SecurityManager.check_password(data.get('password'), user.password_hash):
        token = SecurityManager.generate_token(user.id)
        log_action('login', 'user', user.id)
        return jsonify({'token': token, 'user': {'username': user.username, 'display_name': user.display_name}}), 200
        
    return jsonify({'error': 'Invalid credentials'}), 401

@api.route('/api/auth/me', methods=['GET'])
@require_auth
def me():
    user = User.query.get(request.user_id)
    return jsonify({'user': {'username': user.username, 'display_name': user.display_name, 'email': user.email}}), 200

# --- DASHBOARD ---

@api.route('/api/dashboard', methods=['GET'])
@require_auth
def dashboard():
    jobs = Job.query.filter_by(user_id=request.user_id).all()
    job_ids = [j.id for j in jobs]
    resumes_count = Resume.query.filter(Resume.job_id.in_(job_ids)).count() if job_ids else 0
    
    qualified = 0
    if job_ids:
        qualified = AnalysisResult.query.join(Resume).filter(
            Resume.job_id.in_(job_ids), 
            AnalysisResult.status.in_(['highly_qualified', 'qualified'])
        ).count()
    
    recent_activity = AuditLog.query.filter_by(user_id=request.user_id).order_by(AuditLog.timestamp.desc()).limit(10).all()
    
    return jsonify({
        'stats': {
            'total_jobs': len(jobs),
            'total_resumes': resumes_count,
            'qualified': qualified,
            'average_score': 0 # Placeholder
        },
        'recent_jobs': [{'id': j.id, 'title': j.title, 'status': j.status, 'created_at': j.created_at.isoformat(), 'resume_count': len(j.resumes)} for j in jobs[-5:]],
        'recent_activity': [{'action': a.action, 'detail': a.detail, 'timestamp': a.timestamp.isoformat()} for a in recent_activity]
    }), 200

# --- JOBS ---

@api.route('/api/jobs', methods=['GET', 'POST'])
@require_auth
def handle_jobs():
    if request.method == 'GET':
        jobs = Job.query.filter_by(user_id=request.user_id).all()
        return jsonify([{
            'id': j.id, 'title': j.title, 'status': j.status, 
            'resume_count': len(j.resumes), 'created_at': j.created_at.isoformat(),
            'min_experience': j.min_experience, 'min_education': j.min_education
        } for j in jobs]), 200
    
    data = request.json
    job = Job(
        user_id=request.user_id,
        title=SecurityManager.sanitize(data.get('title')),
        description_encrypted=SecurityManager.encrypt(data.get('description')),
        required_skills=SecurityManager.sanitize(data.get('required_skills')),
        min_experience=data.get('min_experience', 0),
        min_education=data.get('min_education', 'bachelor')
    )
    db.session.add(job)
    db.session.commit()
    log_action('create_job', 'job', job.id, f"Created job: {job.title}")
    return jsonify({'id': job.id, 'message': 'Job created'}), 201

@api.route('/api/jobs/<int:id>', methods=['GET', 'PUT', 'DELETE'])
@require_auth
def handle_job(id):
    job = Job.query.filter_by(id=id, user_id=request.user_id).first_or_404()
    
    if request.method == 'GET':
        return jsonify({
            'id': job.id, 'title': job.title, 
            'description': SecurityManager.decrypt(job.description_encrypted),
            'required_skills': job.required_skills,
            'min_experience': job.min_experience,
            'min_education': job.min_education,
            'status': job.status,
            'candidates': [{
                'id': r.id, 'filename': SecurityManager.decrypt(r.original_filename_encrypted),
                'candidate_name': SecurityManager.decrypt(r.candidate_name_encrypted)
            } for r in job.resumes]
        }), 200
        
    if request.method == 'PUT':
        data = request.json
        job.title = SecurityManager.sanitize(data.get('title', job.title))
        if 'description' in data:
            job.description_encrypted = SecurityManager.encrypt(data['description'])
        job.required_skills = SecurityManager.sanitize(data.get('required_skills', job.required_skills))
        job.min_experience = data.get('min_experience', job.min_experience)
        job.min_education = data.get('min_education', job.min_education)
        job.status = data.get('status', job.status)
        db.session.commit()
        log_action('update_job', 'job', job.id)
        return jsonify({'message': 'Job updated'}), 200
        
    if request.method == 'DELETE':
        db.session.delete(job)
        db.session.commit()
        log_action('delete_job', 'job', id)
        return jsonify({'message': 'Job deleted'}), 200

# --- UPLOAD & ANALYSIS ---

@api.route('/api/jobs/<int:id>/upload', methods=['POST'])
@require_auth
def upload_resumes(id):
    job = Job.query.filter_by(id=id, user_id=request.user_id).first_or_404()
    if 'resumes' not in request.files:
        return jsonify({'error': 'No files uploaded'}), 400
        
    files = request.files.getlist('resumes')
    uploaded = []
    errors = []
    
    for file in files:
        if file.filename == '': continue
        try:
            orig_name = file.filename
            filename = secure_filename(orig_name)
            file_hash = hashlib.sha256(f"{request.user_id}_{filename}_{datetime.utcnow()}".encode()).hexdigest()
            
            save_path = os.path.join(current_app.config['UPLOAD_FOLDER'], file_hash)
            file.save(save_path)
            
            text = ResumeParser.extract_text(save_path)
            contact = ResumeParser.extract_contact_info(text)
            exp = ResumeParser.extract_experience_years(text)
            edu = ResumeParser.detect_education(text)
            
            resume = Resume(
                job_id=job.id,
                filename_hash=file_hash,
                original_filename_encrypted=SecurityManager.encrypt(orig_name),
                candidate_name_encrypted=SecurityManager.encrypt(contact['name']),
                candidate_email_encrypted=SecurityManager.encrypt(contact['email']),
                raw_text_encrypted=SecurityManager.encrypt(text),
                extracted_skills=",".join(ResumeAnalyzer.extract_skills(text)),
                years_experience=exp,
                education_level=edu
            )
            db.session.add(resume)
            uploaded.append({'filename': orig_name, 'candidate_name': contact['name']})
        except Exception as e:
            errors.append(f"{file.filename}: {str(e)}")
            
    db.session.commit()
    log_action('upload_resumes', 'job', job.id, f"Uploaded {len(uploaded)} resumes")
    return jsonify({'uploaded': len(uploaded), 'results': uploaded, 'errors': errors}), 201

@api.route('/api/jobs/<int:id>/analyze', methods=['POST'])
@require_auth
def analyze_resumes(id):
    job = Job.query.filter_by(id=id, user_id=request.user_id).first_or_404()
    resumes = Resume.query.filter_by(job_id=job.id).all()
    
    job_desc = SecurityManager.decrypt(job.description_encrypted)
    
    results = []
    for r in resumes:
        # Check if already analyzed
        if r.analysis: db.session.delete(r.analysis)
        
        analysis = ResumeAnalyzer.analyze(
            SecurityManager.decrypt(r.raw_text_encrypted),
            job_desc,
            job.required_skills,
            job.min_experience,
            job.min_education
        )
        
        ar = AnalysisResult(
            resume_id=r.id,
            overall_score=analysis['overall_score'],
            skill_score=analysis['skill_score'],
            experience_score=analysis['experience_score'],
            education_score=analysis['education_score'],
            similarity_score=analysis['similarity_score'],
            status=analysis['status'],
            matched_skills=analysis['matched_skills'],
            missing_skills=analysis['missing_skills'],
            strengths=analysis['strengths'],
            weaknesses=analysis['weaknesses'],
            explanation=analysis['explanation']
        )
        db.session.add(ar)
        results.append(ar)
        
    db.session.commit()
    log_action('analyze_resumes', 'job', job.id, f"Analyzed {len(resumes)} resumes")
    
    return jsonify({
        'total': len(resumes),
        'qualified': len([res for res in results if res.status in ['highly_qualified', 'qualified']]),
        'not_qualified': len([res for res in results if res.status == 'not_qualified']),
        'average_score': round(sum(res.overall_score for res in results)/len(results), 1) if results else 0
    }), 200

@api.route('/api/jobs/<int:id>/results', methods=['GET'])
@require_auth
def get_results(id):
    job = Job.query.filter_by(id=id, user_id=request.user_id).first_or_404()
    resumes = Resume.query.filter_by(job_id=job.id).all()
    
    candidates = []
    for r in resumes:
        a = r.analysis
        candidates.append({
            'id': r.id,
            'filename': SecurityManager.decrypt(r.original_filename_encrypted),
            'candidate_name': SecurityManager.decrypt(r.candidate_name_encrypted),
            'candidate_email': SecurityManager.decrypt(r.candidate_email_encrypted),
            'years_experience': r.years_experience,
            'education_level': r.education_level,
            'analysis': {
                'overall_score': a.overall_score,
                'skill_score': a.skill_score,
                'experience_score': a.experience_score,
                'education_score': a.education_score,
                'similarity_score': a.similarity_score,
                'status': a.status,
                'matched_skills': a.matched_skills,
                'missing_skills': a.missing_skills,
                'strengths': a.strengths,
                'weaknesses': a.weaknesses,
                'explanation': a.explanation
            } if a else None
        })
    
    # Sort by overall score
    candidates.sort(key=lambda x: x['analysis']['overall_score'] if x['analysis'] else 0, reverse=True)
    return jsonify({'job_title': job.title, 'candidates': candidates}), 200
