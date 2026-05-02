# 🧠 RUME AI
**AI-Powered Resume Screening Platform**

RUME AI is a secure, full-stack application that uses NLP and ML to analyze, rank, and screen resumes against job requirements.

## ✨ Features
- **AI Scoring**: Weighted analysis of skills, experience, and job relevance.
- **NLP Engine**: Automatic extraction of technical/soft skills and education.
- **Secure PII**: All candidate data (names, emails, text) is AES-encrypted at rest.
- **Full Stack**: JWT authentication, rate limiting, and audit logging.
- **Premium UI**: Modern dark glassmorphic dashboard with real-time stats.

## 🚀 Quick Start
1. **Install**: `pip install -r requirements.txt`
2. **Setup**: Copy `.env.example` to `.env` and generate an `ENCRYPTION_KEY`.
3. **Run**: `python run.py`

## 🛠️ Tech
- **Backend**: Flask, SQLAlchemy, SQLite
- **AI/NLP**: scikit-learn, NLTK
- **Security**: Cryptography (Fernet), JWT, bcrypt
- **Frontend**: Vanilla JS, CSS Glassmorphism

---
© 2026 RUME AI
