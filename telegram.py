import json
import urllib.parse
from logger import logger
import utils

class TelegramBot:
    def __init__(self, token: str):
        self.token = token
        self.api = f"https://api.telegram.org/bot{token}"
    
    def send_message(
        self, 
        chat_id: int, 
        text: str, 
        reply_markup: dict = None,
        parse_mode: str = "Markdown"
    ) -> dict:
        payload = {
            "chat_id": chat_id, 
            "text": text, 
            "parse_mode": parse_mode
        }
        if reply_markup:
            payload["reply_markup"] = json.dumps(reply_markup)
        
        result, _ = utils.http_request("POST", f"{self.api}/sendMessage", body=payload)
        if result.get("ok"):
            logger.debug(f"Sent message to {chat_id}")
        else:
            logger.error(f"Failed to send message: {result.get('description')}")
        return result
    
    def edit_message(
        self,
        chat_id: int,
        message_id: int,
        text: str,
        reply_markup: dict = None
    ) -> dict:
        payload = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text,
            "parse_mode": "Markdown"
        }
        if reply_markup:
            payload["reply_markup"] = json.dumps(reply_markup)
        
        result, _ = utils.http_request("POST", f"{self.api}/editMessageText", body=payload)
        return result
    
    def delete_message(self, chat_id: int, message_id: int) -> dict:
        payload = {"chat_id": chat_id, "message_id": message_id}
        return utils.http_request("POST", f"{self.api}/deleteMessage", body=payload)
    
    def answer_callback(self, callback_id: str, text: str = "", show_alert: bool = False) -> dict:
        payload = {
            "callback_query_id": callback_id,
            "text": text,
            "show_alert": show_alert
        }
        return utils.http_request("POST", f"{self.api}/answerCallbackQuery", body=payload)
    
    def get_updates(self, offset: int = None, timeout: int = 30) -> list:
        q = {"timeout": timeout, "allowed_updates": json.dumps(["message", "callback_query"])}
        if offset:
            q["offset"] = offset
        
        url = f"{self.api}/getUpdates?{urllib.parse.urlencode(q)}"
        payload, _ = utils.http_request("GET", url, timeout=timeout + 10)
        return payload.get("result", [])
    
    def get_file(self, file_id: str) -> dict:
        payload, _ = utils.http_request("GET", f"{self.api}/getFile?file_id={file_id}")
        if payload.get("ok"):
            return payload.get("result", {})
        logger.error(f"Failed to get file: {payload}")
        return {}
    
    def download_file(self, file_path: str, dest_path: str) -> bool:
        try:
            url = f"https://api.telegram.org/file/bot{self.token}/{file_path}"
            import os
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            urllib.request.urlretrieve(url, dest_path)
            logger.info(f"Downloaded file to {dest_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to download file: {e}")
            return False
    
    def send_document(self, chat_id: int, file_path: str, caption: str = None) -> dict:
        try:
            with open(file_path, 'rb') as f:
                import multipart
                # For simplicity, we'll use a different approach
                # This is a placeholder - in production, use proper multipart
                pass
        except Exception as e:
            logger.error(f"Error sending document: {e}")
        return {"ok": False}
    
    def send_photo(self, chat_id: int, photo_path: str, caption: str = None) -> dict:
        try:
            import os
            if not os.path.exists(photo_path):
                return {"ok": False, "error": "File not found"}
            
            with open(photo_path, 'rb') as f:
                photo_data = f.read()
            
            # Simple approach - send as document with photo type
            # In production, use proper multipart form-data
            return {"ok": False, "error": "Use document instead"}
        except Exception as e:
            logger.error(f"Error sending photo: {e}")
            return {"ok": False}

import urllib.request
