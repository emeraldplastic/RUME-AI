# Changelog

All notable changes to RUME AI will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-01-01

### Added
- Resume upload and parsing (PDF, DOCX, TXT)
- Deterministic resume analysis engine with weighted scoring
- Skill extraction with alias normalization (50+ technical and soft skills)
- Experience year detection from resume text
- Education level detection
- TF-IDF cosine similarity matching against job descriptions
- Multi-job pipeline with per-job candidate management
- Candidate tagging, commenting, and decision tracking
- Skill gap analysis with learning recommendations
- CSV and JSON export for candidate results
- Calibration versioning for audit trail
- JWT authentication with bcrypt password hashing
- AES-256 encryption for PII data at rest
- Rate limiting on all sensitive endpoints
- Request logging and audit trail
- GDPR data export and account deletion endpoints
- Vercel deployment configuration
