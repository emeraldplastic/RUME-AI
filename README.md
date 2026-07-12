# RUME AI

Secure resume screening for hiring teams. RUME AI lets a user create job requirements, upload resumes, run deterministic ML/NLP scoring, and review a ranked candidate list.

## What It Does

- User accounts with bcrypt password hashing and JWT auth in an HttpOnly cookie.
- SQLite database with encrypted resume text, names, emails, phones, and filenames.
- Resume upload for PDF, DOCX, and TXT files with extension, MIME, size, and batch limits. Original files are parsed in memory and not stored.
- Candidate ranking by weighted skill match, experience, education, and job-description similarity, with common skill aliases normalized before scoring.
- Evidence-backed scoring with encrypted resume snippets, calibration version history, blind review mode, decision journaling, audit-pack export, and searchable structured request logs.
- Dashboard, audit trail, job management, resume intake, searchable sorted results, candidate detail modal, candidate removal, and masked-email CSV export.

## New Features

### Advanced Analytics Dashboard
- **Status Breakdown**: View candidate qualification distribution (highly_qualified, qualified, partially_qualified, not_qualified)
- **Skill Frequency**: Track most common skills across all candidates
- **Score Distribution**: Visualize candidate scores in ranges (0-25, 26-50, 51-75, 76-100)
- **Time Series Data**: Monitor analysis activity over the last 30 days

### Enhanced Candidate Filtering & Pagination
- **Advanced Search**: Full-text search across candidate names, skills, strengths, and weaknesses
- **Score Range Filtering**: Filter candidates by minimum and maximum scores
- **Skills Filtering**: Filter candidates by specific required skills
- **Pagination**: Handle large datasets with configurable page size (up to 100 per page)
- **Multiple Sort Options**: Sort by score, experience, upload date, name, or education level

### Skill Gap Analysis
- **Coverage Tracking**: See which required skills are covered by candidates
- **Coverage Percentage**: Quantitative measure of skill coverage across all candidates
- **Missing Skills Summary**: Identify most frequently missing skills
- **Learning Recommendations**: Get curated course and resource recommendations for skill gaps

### Bulk Operations
- **Bulk Decisions**: Apply hiring decisions (advance, hold, reject, etc.) to multiple candidates at once
- **Bulk Deletion**: Remove multiple candidates from a job in a single operation
- **Batch Processing**: Handle up to 100 candidates in bulk operations

### Export Functionality
- **CSV Export**: Download candidate data in CSV format with all analysis metrics
- **JSON Export**: Export complete candidate data including analysis results
- **Masked Data**: Exports maintain privacy with masked emails

### Team Collaboration Features
- **Candidate Comments**: Add encrypted comments to candidates for team discussion
- **Comment Management**: Edit and delete comments with full audit trail
- **Candidate Tags**: Tag candidates with custom labels and colors
- **Tag Management**: Add, remove, and view tags across candidates
- **Job-Level Tags**: View tag usage statistics across all candidates in a job

### Global Search
- **Cross-Resource Search**: Search across jobs and candidates simultaneously
- **Targeted Search**: Limit search to specific resource types
- **Comprehensive Results**: Search job titles, skills, candidate names, and analysis results

### Enhanced Rate Limiting & Monitoring
- **Rate Limit Statistics**: Track rate limit hits and blocks per endpoint
- **Configurable Strategies**: Support for different rate limiting strategies
- **Monitoring Endpoint**: API endpoint to view rate limiting metrics

## Security Notes

- Set `SECRET_KEY`, `JWT_SECRET`, and `ENCRYPTION_KEY` before production use.
- Generate `ENCRYPTION_KEY` with:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

- Production mode fails fast if required secrets are missing.
- Session tokens are not exposed to browser JavaScript; authenticated writes require a CSRF header.
- Candidate email is masked in API results and exports. Raw resume text is never returned by the API.
- Use `FORCE_SECURE_COOKIES=1` behind HTTPS in production.
- Structured JSON logs are emitted to stdout with `timestamp`, `level`, `event`, `request_id`, `user_id`, route data, status, and duration. On Vercel, search them in Runtime Logs or with `vercel logs https://rume-ai.vercel.app --json`.
- Use `LOG_LEVEL=DEBUG` during local development and `LOG_LEVEL=INFO` for normal operations. Runtime failures are logged at `error`.
- Rate limit responses include `X-RateLimit-*` headers, a `request_id`, and retry metadata when available.

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
