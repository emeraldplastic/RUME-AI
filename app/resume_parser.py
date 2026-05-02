"""Resume parsing helpers for PDF, DOCX, and TXT files."""
import io
import re
from datetime import datetime

import docx
import PyPDF2


class ResumeParser:
    @staticmethod
    def validate_file(filename: str, file_content: bytes) -> tuple[bool, str]:
        if not filename or "." not in filename:
            return False, "Missing file extension"
        ext = filename.rsplit(".", 1)[1].lower()
        if ext not in {"pdf", "docx", "txt"}:
            return False, "Only PDF, DOCX, and TXT resumes are supported"
        if not file_content:
            return False, "File is empty"
        if ext == "pdf" and not file_content.startswith(b"%PDF"):
            return False, "PDF signature is invalid"
        if ext == "docx" and not file_content.startswith(b"PK"):
            return False, "DOCX signature is invalid"
        return True, ""

    @staticmethod
    def parse(filename: str, file_content: bytes) -> str:
        valid, error = ResumeParser.validate_file(filename, file_content)
        if not valid:
            raise ValueError(error)

        ext = filename.rsplit(".", 1)[1].lower()
        if ext == "pdf":
            return ResumeParser._pdf_text(file_content)
        if ext == "docx":
            return ResumeParser._docx_text(file_content)
        return ResumeParser._txt_text(file_content)

    @staticmethod
    def _pdf_text(file_content: bytes) -> str:
        reader = PyPDF2.PdfReader(io.BytesIO(file_content))
        text = []
        for page in reader.pages:
            text.append(page.extract_text() or "")
        return "\n".join(text).strip()

    @staticmethod
    def _docx_text(file_content: bytes) -> str:
        document = docx.Document(io.BytesIO(file_content))
        return "\n".join(p.text for p in document.paragraphs if p.text.strip()).strip()

    @staticmethod
    def _txt_text(file_content: bytes) -> str:
        return file_content.decode("utf-8", errors="ignore").strip()

    @staticmethod
    def extract_contact_info(text: str) -> dict:
        email_match = re.search(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", text)
        phone_match = re.search(r"\+?\d[\d\-\s().]{8,}\d", text)

        name = "Unknown candidate"
        for line in [line.strip() for line in text.splitlines()[:12] if line.strip()]:
            if "@" in line or re.search(r"\d", line):
                continue
            words = line.split()
            if 1 < len(words) <= 5 and len(line) <= 80:
                name = line
                break

        return {
            "name": name,
            "email": email_match.group(0).lower() if email_match else "",
            "phone": phone_match.group(0).strip() if phone_match else "",
        }

    @staticmethod
    def extract_experience_years(text: str) -> float:
        text_lower = text.lower()
        years = []
        patterns = [
            r"(\d+(?:\.\d+)?)\+?\s*(?:years?|yrs?)\s+(?:of\s+)?(?:experience|exp)",
            r"(?:experience|exp)\s*[:\-]?\s*(\d+(?:\.\d+)?)\+?\s*(?:years?|yrs?)",
            r"(?:over|more than|about|approximately)\s+(\d+(?:\.\d+)?)\s*(?:years?|yrs?)",
        ]
        for pattern in patterns:
            years.extend(float(match) for match in re.findall(pattern, text_lower))

        current_year = datetime.utcnow().year
        date_ranges = re.findall(
            r"(19\d{2}|20\d{2})\s*(?:-|to|until|through)\s*(19\d{2}|20\d{2}|present|current|now)",
            text_lower,
        )
        for start, end in date_ranges:
            start_year = int(start)
            end_year = current_year if end in {"present", "current", "now"} else int(end)
            duration = end_year - start_year
            if 0 < duration < 50:
                years.append(float(duration))

        return round(max(years), 1) if years else 0.0

    @staticmethod
    def detect_education(text: str) -> str:
        levels = (
            ("phd", ("phd", "ph.d", "doctorate", "doctoral")),
            ("master", ("master", "masters", "msc", "m.s", "mba", "mtech", "m.tech")),
            ("bachelor", ("bachelor", "bachelors", "bsc", "b.s", "ba", "b.a", "btech", "b.tech", "graduate")),
            ("associate", ("associate", "diploma", "certification")),
            ("high school", ("high school", "secondary", "ged")),
        )
        text_lower = text.lower()
        for level, keywords in levels:
            if any(re.search(r"\b" + re.escape(keyword) + r"\b", text_lower) for keyword in keywords):
                return level
        return "not specified"
