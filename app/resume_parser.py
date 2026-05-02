import os
import re
import PyPDF2
import docx
from werkzeug.utils import secure_filename

class ResumeParser:
    @staticmethod
    def extract_text(file_path):
        ext = os.path.splitext(file_path)[1].lower()
        text = ""
        try:
            if ext == '.pdf':
                with open(file_path, 'rb') as f:
                    reader = PyPDF2.PdfReader(f)
                    for page in reader.pages:
                        text += page.extract_text() or ""
            elif ext == '.docx':
                doc = docx.Document(file_path)
                text = "\n".join([p.text for p in doc.paragraphs])
            elif ext == '.txt':
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    text = f.read()
        except Exception as e:
            print(f"[Parser] Error reading {file_path}: {e}")
        return text

    @staticmethod
    def extract_contact_info(text):
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        phone_pattern = r'\+?\d[\d\-\s\(\)]{8,}\d'
        
        email = re.search(email_pattern, text)
        phone = re.search(phone_pattern, text)
        
        # Simple name extraction (usually first line or near email)
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        name = lines[0] if lines else "Unknown"
        if len(name) > 50: name = name[:47] + "..."
            
        return {
            'name': name,
            'email': email.group(0) if email else None,
            'phone': phone.group(0) if phone else None
        }

    @staticmethod
    def extract_experience_years(text):
        # Look for "X years", "X+ years", or date ranges like "2018 - 2022"
        patterns = [
            r'(\d+)\s*(?:\+)?\s*years?',
            r'(\d+)\s*(?:\+)?\s*yrs'
        ]
        total = 0
        for p in patterns:
            matches = re.findall(p, text, re.IGNORECASE)
            if matches:
                total = max(total, max(int(m) for m in matches))
        
        # Heuristic: count year spans
        year_span_pattern = r'(20\d{2})\s*[-–—]\s*(20\d{2}|Present)'
        spans = re.findall(year_span_pattern, text)
        span_total = 0
        for start, end in spans:
            start_yr = int(start)
            end_yr = datetime.now().year if end.lower() == 'present' else int(end)
            if end_yr >= start_yr:
                span_total += (end_yr - start_yr)
        
        return max(total, span_total)

    @staticmethod
    def detect_education(text):
        levels = {
            'phd': ['phd', 'doctorate', 'ph.d'],
            'master': ['master', 'msc', 'm.s', 'mba'],
            'bachelor': ['bachelor', 'bsc', 'b.s', 'b.a', 'graduate'],
            'associate': ['associate', 'diploma'],
            'high school': ['high school', 'secondary']
        }
        text_lower = text.lower()
        for level, keywords in levels.items():
            if any(k in text_lower for k in keywords):
                return level
        return "none"
