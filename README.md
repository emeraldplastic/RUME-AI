# RUME AI

**Secure, AI-powered resume screening for modern hiring teams.**

RUME AI helps you make better hiring decisions faster. Upload resumes, define job requirements, and let our intelligent system rank candidates based on skills, experience, and fit. Built with privacy-first architecture and enterprise-grade security.

---

## 🎯 What Makes RUME AI Different?

### For Hiring Managers & Recruiters
- **Save Time**: Screen hundreds of resumes in minutes instead of hours
- **Reduce Bias**: Blind review mode and objective scoring help you focus on qualifications
- **Make Data-Driven Decisions**: Advanced analytics show you exactly why candidates rank where they do
- **Collaborate Seamlessly**: Share notes, tags, and insights with your team
- **Stay Compliant**: GDPR-ready with data export and account deletion features

### For Candidates
- **Fair Evaluation**: Your resume is scored against actual job requirements, not arbitrary criteria
- **Privacy Protected**: Your personal data is encrypted and never shared
- **Transparent Process**: See exactly what skills match and what's missing

---

## ✨ Key Features

### 🤖 Intelligent Resume Analysis
- **Skill Extraction**: Automatically identifies and normalizes skills from resumes
- **Experience Scoring**: Evaluates years and relevance of work experience
- **Education Assessment**: Considers degree level and field relevance
- **Similarity Matching**: Compares resumes against job descriptions for fit

### 📊 Advanced Analytics Dashboard
- **Status Breakdown**: See candidate qualification distribution at a glance
- **Skill Frequency**: Track the most common skills across all applicants
- **Score Distribution**: Visualize candidate scores in meaningful ranges
- **Time Series Data**: Monitor your hiring activity over time

### 🔍 Powerful Search & Filtering
- **Full-Text Search**: Search across candidates, jobs, and analysis results
- **Score Range Filtering**: Find candidates within specific score ranges
- **Skills Filtering**: Filter by specific required skills
- **Smart Pagination**: Handle large datasets efficiently (up to 100 per page)
- **Multiple Sort Options**: Sort by score, experience, date, name, or education

### 🎓 Skill Gap Analysis
- **Coverage Tracking**: See which required skills your candidate pool covers
- **Coverage Percentage**: Quantitative measure of skill coverage
- **Missing Skills Summary**: Identify skill gaps in your pipeline
- **Learning Recommendations**: Get curated course suggestions for skill gaps

### ⚡ Bulk Operations
- **Bulk Decisions**: Apply hiring decisions to multiple candidates at once
- **Bulk Deletion**: Remove candidates from a job in one operation
- **Batch Processing**: Handle up to 100 candidates efficiently

### 📤 Export & Reporting
- **CSV Export**: Download candidate data with all analysis metrics
- **JSON Export**: Export complete data for integration with other tools
- **Masked Data**: Exports maintain privacy with masked emails
- **Audit Packs**: Complete audit trail for compliance

### 👥 Team Collaboration
- **Encrypted Comments**: Add private notes to candidates for team discussion
- **Color-Coded Tags**: Organize candidates with custom labels
- **Tag Statistics**: View tag usage across all candidates
- **Decision Journaling**: Track all hiring decisions with reasons

### 🔒 Enterprise Security
- **End-to-End Encryption**: All sensitive data is encrypted at rest
- **Secure Authentication**: JWT tokens with HttpOnly cookies
- **Rate Limiting**: Protect against abuse with configurable limits
- **Security Headers**: Comprehensive protection against common attacks
- **Audit Logging**: Complete traceability of all actions

### 🌍 GDPR Compliance
- **Data Export**: Download all your data on demand
- **Account Deletion**: Permanently delete your account and all data
- **Data Retention**: Configurable automatic data cleanup
- **Privacy by Design**: Built with privacy as a core principle

## 🚀 Getting Started

### Quick Start (Local Development)

1. **Clone the repository**
```bash
git clone https://github.com/emeraldplastic/RUME-AI.git
cd RUME-AI
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Set up environment variables**
```bash
cp .env.example .env
# Edit .env and add your secrets
```

4. **Generate encryption keys**
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# Add this to ENCRYPTION_KEY in your .env file
```

5. **Run the application**
```bash
python run.py
```

6. **Open your browser**
Navigate to `http://localhost:5000` and create your account.

---

## 🏗️ Architecture

### Technology Stack
- **Backend**: Flask 3.1.1 with Python 3.11+
- **Database**: SQLite with SQLAlchemy ORM
- **Security**: bcrypt, PyJWT, cryptography (Fernet)
- **Document Processing**: PyPDF2, python-docx
- **Rate Limiting**: Flask-Limiter
- **Deployment**: Vercel

### Security Architecture
- **Encryption at Rest**: All sensitive data (names, emails, resume text) encrypted with Fernet
- **Secure Authentication**: JWT tokens stored in HttpOnly cookies
- **CSRF Protection**: Authenticated writes require CSRF header
- **Input Validation**: All user inputs sanitized and validated
- **Rate Limiting**: Per-user and per-IP limits to prevent abuse
- **Security Headers**: HSTS, X-Frame-Options, X-Content-Type-Options, etc.

---

## 📡 API Endpoints

### Authentication
- `POST /api/auth/register` - Create a new account
- `POST /api/auth/login` - Sign in to your account
- `POST /api/auth/logout` - Sign out
- `GET /api/auth/me` - Get your profile
- `GET /api/auth/me/data-export` - Download all your data (GDPR)
- `POST /api/auth/me/account-delete` - Delete your account (GDPR)

### Jobs & Candidates
- `GET /api/jobs` - List all your jobs
- `POST /api/jobs` - Create a new job posting
- `GET /api/jobs/<id>` - Get job details
- `PUT /api/jobs/<id>` - Update job requirements
- `DELETE /api/jobs/<id>` - Delete a job
- `POST /api/jobs/<id>/upload` - Upload resumes
- `POST /api/jobs/<id>/analyze` - Analyze uploaded resumes
- `GET /api/jobs/<id>/results` - Get ranked candidates with filtering
- `GET /api/jobs/<id>/skill-gap-analysis` - Analyze skill gaps
- `GET /api/jobs/<id>/export` - Export candidates (CSV/JSON)

### Collaboration
- `GET /api/jobs/<id>/candidates/<resume_id>/comments` - Get comments
- `POST /api/jobs/<id>/candidates/<resume_id>/comments` - Add comment
- `PUT /api/jobs/<id>/candidates/<resume_id>/comments/<id>` - Update comment
- `DELETE /api/jobs/<id>/candidates/<resume_id>/comments/<id>` - Delete comment
- `GET /api/jobs/<id>/candidates/<resume_id>/tags` - Get tags
- `POST /api/jobs/<id>/candidates/<resume_id>/tags` - Add tag
- `DELETE /api/jobs/<id>/candidates/<resume_id>/tags/<id>` - Delete tag

### Search & Analytics
- `GET /api/search` - Global search across jobs and candidates
- `GET /api/dashboard` - Analytics dashboard
- `GET /api/admin/rate-limit-stats` - Rate limiting statistics
- `GET /api/health` - Health check endpoint

### Audit & Logging
- `GET /api/logs` - Request logs with filtering
- `GET /api/jobs/<id>/audit-pack` - Export audit pack

---

## 🔐 Security Best Practices

### For Production Deployment

1. **Use Strong Secrets**
   - Never use placeholder or default values
   - Generate unique secrets for each deployment
   - Rotate secrets regularly

2. **Enable HTTPS**
   - Always use HTTPS in production
   - Set `FORCE_SECURE_COOKIES=1`
   - Configure proper SSL certificates

3. **Configure Rate Limiting**
   - Adjust limits based on your traffic
   - Monitor rate limit statistics
   - Set up alerts for abuse detection

4. **Regular Backups**
   - Backup your SQLite database regularly
   - Store backups securely
   - Test restore procedures

5. **Monitor Logs**
   - Review security logs regularly
   - Set up alerts for suspicious activity
   - Keep logs for compliance

---

## 🌐 Vercel Deployment

### One-Click Deployment

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https://github.com/emeraldplastic/RUME-AI)

### Manual Deployment

1. **Push your code to GitHub**
2. **Import project in Vercel**
3. **Configure environment variables** (see below)
4. **Deploy**

### Required Environment Variables

Set these in your Vercel project settings:

- `SECRET_KEY` - Flask secret key (generate with: `python -c "import secrets; print(secrets.token_hex(32))"`)
- `JWT_SECRET` - JWT signing secret (generate with: `python -c "import secrets; print(secrets.token_hex(32))"`)
- `ENCRYPTION_KEY` - Fernet encryption key (generate with: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`)
- `FLASK_ENV` - Set to `production`
- `DATABASE_URL` - SQLite path (e.g., `sqlite:///instance/rume_ai.db`)

### Optional Environment Variables

- `JWT_EXPIRY_HOURS` - JWT token expiry in hours (default: 24)
- `MAX_UPLOAD_SIZE` - Max upload size in bytes (default: 16777216)
- `MAX_FILES_PER_UPLOAD` - Max files per upload (default: 20)
- `RATELIMIT_DEFAULT` - Default rate limit (default: "200 per hour")
- `RATELIMIT_AUTH` - Auth endpoint rate limit (default: "100 per hour")
- `RATELIMIT_UPLOAD` - Upload endpoint rate limit (default: "20 per hour")
- `RATELIMIT_ANALYZE` - Analyze endpoint rate limit (default: "50 per hour")
- `DATA_RETENTION_DAYS` - Data retention period in days (default: 365)
- `ALLOW_DATA_EXPORT` - Enable GDPR data export (default: 1)
- `LOG_LEVEL` - Logging level (default: INFO for production)

---

## 🧪 Testing

Run the test suite:

```bash
python -m pytest tests/ -v
```

The test suite includes:
- API security tests
- Configuration validation tests
- Observability tests
- Trust layer tests
- Resume analyzer tests

---

## 📝 License

This project is licensed under the MIT License.

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

---

## 📧 Support

For questions or issues, please open an issue on GitHub.

---

## 🙏 Acknowledgments

Built with modern Python web technologies and security best practices.

## Setup

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python run.py
```

Open `http://127.0.0.1:5000`.

## Tests

```bash
venv\Scripts\python.exe -m unittest discover -s tests
venv\Scripts\python.exe -m compileall app tests
node --check app\static\app.js
```

## Project Structure

```text
app/
  analyzer.py       ML scoring and skill matching
  config.py         environment and security configuration
  main.py           Flask app factory and security headers
  models.py         encrypted resume database models
  resume_parser.py  PDF, DOCX, TXT parsing
  routes.py         auth, jobs, uploads, analysis, results API
  security.py       encryption, JWT, sanitization, audit helpers
  static/           browser UI
  templates/        single-page app shell
tests/              API and privacy regression tests
```

## API Endpoints

### Authentication
- `POST /api/auth/register` - User registration
- `POST /api/auth/login` - User login
- `POST /api/auth/logout` - User logout
- `GET /api/auth/me` - Get current user

### Dashboard & Analytics
- `GET /api/dashboard` - Dashboard stats with advanced analytics
- `GET /api/admin/rate-limit-stats` - Rate limiting statistics

### Jobs
- `GET /api/jobs` - List jobs with filtering
- `POST /api/jobs` - Create new job
- `GET /api/jobs/<id>` - Get job details
- `PUT /api/jobs/<id>` - Update job
- `DELETE /api/jobs/<id>` - Delete job

### Candidate Management
- `POST /api/jobs/<id>/upload` - Upload resumes
- `POST /api/jobs/<id>/analyze` - Analyze resumes
- `GET /api/jobs/<id>/results` - Get results with pagination and filtering
- `DELETE /api/jobs/<id>/candidates/<resume_id>` - Delete candidate
- `POST /api/jobs/<id>/candidates/bulk` - Bulk operations
- `DELETE /api/jobs/<id>/candidates/bulk` - Bulk delete

### Analysis & Insights
- `GET /api/jobs/<id>/skill-gap-analysis` - Skill gap analysis with recommendations
- `GET /api/jobs/<id>/export` - Export candidates (CSV/JSON)

### Collaboration
- `GET /api/jobs/<id>/candidates/<resume_id>/comments` - Get comments
- `POST /api/jobs/<id>/candidates/<resume_id>/comments` - Add comment
- `PUT /api/jobs/<id>/candidates/<resume_id>/comments/<comment_id>` - Update comment
- `DELETE /api/jobs/<id>/candidates/<resume_id>/comments/<comment_id>` - Delete comment
- `GET /api/jobs/<id>/candidates/<resume_id>/tags` - Get tags
- `POST /api/jobs/<id>/candidates/<resume_id>/tags` - Add tag
- `DELETE /api/jobs/<id>/candidates/<resume_id>/tags/<tag_id>` - Delete tag
- `GET /api/jobs/<id>/tags` - Get job-level tag statistics

### Search
- `GET /api/search` - Global search across jobs and candidates

### Audit & Logging
- `GET /api/logs` - Request logs with filtering
- `GET /api/jobs/<id>/audit-pack` - Export audit pack
