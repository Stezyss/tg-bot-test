# attachment_service.py
import os
import tempfile
import base64
import json
import requests
from telegram import Message
from docx import Document
import PyPDF2
from config import Config


class AttachmentService:
    def __init__(self, config: Config):
        self.folder_id = config.YANDEX_FOLDER_ID
        self.iam_token = config.YANDEX_IAM_TOKEN  # ← НОВОЕ: IAM-токен напрямую
        self.OCR_URL = "https://ocr.api.cloud.yandex.net/ocr/v1/recognizeText"

    async def download_file(self, message: Message, file_obj) -> str:
        file = await file_obj.get_file()
        suffix = os.path.splitext(file.file_path)[1] or ".jpg"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            await file.download_to_drive(tmp.name)
            print(f"[DOWNLOAD] Файл: {tmp.name} ({os.path.getsize(tmp.name)} байт)")
            return tmp.name

    def recognize_text_from_image(self, image_path: str) -> str:
        """Твой проверенный метод OCR из vision.py"""
        try:
            # --- Кодируем в Base64 ---
            with open(image_path, "rb") as f:
                content = base64.b64encode(f.read()).decode("utf-8")

            # --- MIME-тип ---
            ext = os.path.splitext(image_path)[1].lower()
            mime_map = {'.jpg': 'JPEG', '.jpeg': 'JPEG', '.png': 'PNG', '.webp': 'WEBP'}
            mime_type = mime_map.get(ext, 'JPEG')

            # --- Запрос ---
            data = {
                "mimeType": mime_type,
                "languageCodes": ["*"],
                "model": "page",
                "content": content
            }

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.iam_token}",
                "x-folder-id": self.folder_id,
                "x-data-logging-enabled": "true"
            }

            print(f"[OCR] Отправка: {len(content)} байт, {mime_type}")
            response = requests.post(self.OCR_URL, headers=headers, data=json.dumps(data), timeout=30)

            print(f"[OCR] Ответ: {response.status_code}")

            if response.status_code != 200:
                try:
                    error = response.json().get("error", {})
                    code = error.get("code", "unknown")
                    message = error.get("message", response.text)
                except:
                    code = "unknown"
                    message = response.text[:200]
                return f"OCR ошибка {code}: {message}"

            result = response.json()
            full_text = result.get("result", {}).get("textAnnotation", {}).get("fullText", "").strip()
            return full_text if full_text else "Текст не найден на фото."

        except Exception as e:
            print(f"[OCR] Ошибка: {e}")
            return f"Исключение: {str(e)}"

    async def process_photo(self, message: Message) -> str:
        photo = message.photo[-1]
        path = await self.download_file(message, photo)
        try:
            return self.recognize_text_from_image(path)
        finally:
            if os.path.exists(path):
                os.unlink(path)

    async def process_document(self, message: Message) -> str:
        doc = message.document
        path = await self.download_file(message, doc)

        try:
            mime = doc.mime_type or ""
            name = (doc.file_name or "").lower()

            if "pdf" in mime or name.endswith(".pdf"):
                with open(path, "rb") as f:
                    reader = PyPDF2.PdfReader(f)
                    text = " ".join(page.extract_text() or "" for page in reader.pages)
                return text[:4000] or "PDF пустой."

            elif "msword" in mime or "officedocument" in mime or name.endswith((".doc", ".docx")):
                docx = Document(path)
                text = " ".join(p.text for p in docx.paragraphs if p.text.strip())
                return text[:4000] or "DOCX пустой."

            elif "text" in mime or name.endswith(".txt"):
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    return f.read()[:4000]

            else:
                return "Формат не поддерживается. Отправь PDF, DOCX, TXT или фото."

        except Exception as e:
            return f"Ошибка чтения: {str(e)}"
        finally:
            if os.path.exists(path):
                os.unlink(path)

    async def process_attachment(self, message: Message) -> str:
        if message.photo:
            return await self.process_photo(message)
        elif message.document:
            return await self.process_document(message)
        return None