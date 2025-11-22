import pytesseract
from PIL import Image
from pdf2image import convert_from_path
import os
from dotenv import load_dotenv
import re

load_dotenv()

class OCRProcessor:
    def __init__(self):
        tesseract_path = os.getenv("TESSERACT_PATH")
        if tesseract_path and os.path.exists(tesseract_path):
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
    
    def check_tesseract(self):
        try:
            version = pytesseract.get_tesseract_version()
            return True
        except Exception as e:
            raise Exception(f"Tesseract not found: {str(e)}")
    
    def process_document(self, file_path: str) -> str:
        file_ext = file_path.lower().split('.')[-1]

        if file_ext == "txt":
            return self._process_txt(file_path)
        elif file_ext == "pdf":
            return self._process_pdf(file_path)
        elif file_ext in ["png", "jpg"]:
            return self._process_image(file_path)
        else:
            raise ValueError(f"Unsupported file type: {file_ext}")
    
    def _process_txt(self, txt_path: str) -> str:
        try:
            with open(txt_path, "r", encoding="utf-8") as f:
                text = f.read()
            return self._normalize_text(text)
        except Exception as e:
            raise Exception(f"TXT processing error: {str(e)}")
    
    def _process_pdf(self, pdf_path: str) -> str:
        try:
            images = convert_from_path(pdf_path, dpi=300)
            full_text = []
            for i, image in enumerate(images):
                text = pytesseract.image_to_string(image, lang="eng")
                full_text.append(f"--- Page {i+1} ---\n{text}")
            combined_text = "\n\n".join(full_text)
            return self._normalize_text(combined_text)
        except Exception as e:
            raise Exception(f"PDF processing error: {str(e)}")
    
    def _process_image(self, img_path: str) -> str:
        try:
            image = Image.open(img_path)
            text = pytesseract.image_to_string(image, lang="eng")
            return self._normalize_text(text)
        except Exception as e:
            raise Exception(f"Image processing error: {str(e)}")
    
    def _normalize_text(self, text: str) -> str:
        text = re.sub(r'\s+', ' ', text)
        text = text.replace("ﬁ", "fi").replace("ﬂ", "fl")
        text = text.strip()
        return text
