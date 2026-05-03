# RUME AI

Secure resume screening for hiring teams. RUME AI lets a user create job requirements, upload resumes, run deterministic ML/NLP scoring, and review a ranked candidate list.

## What It Does

- User accounts with bcrypt password hashing and JWT auth in an HttpOnly cookie.
- SQLite database with encrypted resume text, names, emails, phones, and filenames.
- Resume upload for PDF, DOCX, and TXT files with extension, MIME, size, and batch limits. Original files are parsed in memory and not stored.
- Candidate ranking by weighted skill match, experience, education, and job-description similarity.
- Dashboard, audit trail, job management, resume intake, searchable sorted results, candidate detail modal, candidate removal, and masked-email CSV export.

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
