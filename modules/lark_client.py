# ============================================
# MODULE KẾT NỐI LARK API
# Xử lý gửi/nhận tin nhắn với Lark
# ============================================

import logging
import json
import time
import hashlib
import hmac
import base64
import requests
from typing import Optional, Dict, Any, List
from datetime import datetime
import config

logger = logging.getLogger(__name__)


class LarkClient:
    """Client tương tác với Lark API"""

    def __init__(self):
        self.app_id = config.LARK_APP_ID
        self.app_secret = config.LARK_APP_SECRET
        self.base_url = "https://open.feishu.cn/open-apis"
        self.access_token = None
        self.token_expires_at = 0

    def _get_access_token(self) -> str:
        """Lấy access token từ Lark"""
        if self.access_token and time.time() < self.token_expires_at:
            return self.access_token

        url = f"{self.base_url}/auth/v3/tenant_access_token/internal"
        headers = {"Content-Type": "application/json"}
        payload = {
            "app_id": self.app_id,
            "app_secret": self.app_secret
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            data = response.json()

            if data.get("code") == 0:
                self.access_token = data.get("tenant_access_token")
                self.token_expires_at = time.time() + data.get("expire", 7200) - 300
                logger.info("Lấy access token thành công")
                return self.access_token
            else:
                logger.error(f"Lỗi lấy token: {data}")
                raise Exception(f"Không lấy được access token: {data}")

        except Exception as e:
            logger.error(f"Lỗi kết nối Lark: {e}")
            raise

    def send_message(self, receive_id: str, msg_type: str, content: Dict) -> bool:
        """Gửi tin nhắn đến người dùng hoặc nhóm"""
        url = f"{self.base_url}/im/v1/messages"
        token = self._get_access_token()

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        # Xác định receive_id_type dựa trên format
        if "@" in receive_id or receive_id.startswith("oc_"):
            receive_id_type = "open_id"
        elif receive_id.isdigit():
            receive_id_type = "user_id"
        else:
            receive_id_type = "chat_id"

        params = {
            "receive_id": receive_id,
            "receive_id_type": receive_id_type
        }

        payload = {
            "msg_type": msg_type,
            "content": json.dumps(content)
        }

        try:
            response = requests.post(url, headers=headers, params=params, json=payload, timeout=10)
            data = response.json()

            if data.get("code") == 0:
                logger.info(f"Gửi tin nhắn thành công đến {receive_id}")
                return True
            else:
                logger.error(f"Lỗi gửi tin nhắn: {data}")
                return False

        except Exception as e:
            logger.error(f"Lỗi gửi tin nhắn: {e}")
            return False

    def send_text(self, receive_id: str, text: str) -> bool:
        """Gửi tin nhắn text"""
        return self.send_message(receive_id, "text", {"text": text})

    def send_rich_text(self, receive_id: str, title: str, content: str) -> bool:
        """Gửi tin nhắn rich text (card)"""
        card_content = {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {"tag": "plain_text", "content": title},
                "template": "blue"
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": content
                    }
                },
                {"tag": "hr"},
                {
                    "tag": "note",
                    "elements": [
                        {"tag": "plain_text", "content": f"🤖 {config.BOT_NAME} • {datetime.now().strftime('%H:%M:%S')}"}
                    ]
                }
            ]
        }
        return self.send_message(receive_id, "interactive", card_content)

    def send_image(self, receive_id: str, image_key: str) -> bool:
        """Gửi hình ảnh"""
        return self.send_message(receive_id, "image", {"image_key": image_key})

    def reply_message(self, message_id: str, msg_type: str, content: Dict) -> bool:
        """Trả lời tin nhắn (reply)"""
        url = f"{self.base_url}/im/v1/messages/{message_id}/reply"
        token = self._get_access_token()

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        payload = {
            "msg_type": msg_type,
            "content": json.dumps(content)
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            data = response.json()
            return data.get("code") == 0
        except Exception as e:
            logger.error(f"Lỗi reply tin nhắn: {e}")
            return False

    def get_user_info(self, user_id: str) -> Optional[Dict]:
        """Lấy thông tin người dùng"""
        url = f"{self.base_url}/contact/v3/users/{user_id}"
        token = self._get_access_token()

        headers = {"Authorization": f"Bearer {token}"}
        params = {"user_id_type": "open_id"}

        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)
            data = response.json()
            if data.get("code") == 0:
                return data.get("data", {}).get("user", {})
        except Exception as e:
            logger.error(f"Lỗi lấy thông tin user: {e}")
        return None

    def create_task(self, title: str, description: str = "", due_date: str = None, assignee_id: str = None) -> Optional[str]:
        """Tạo task mới trong Lark Tasks"""
        url = f"{self.base_url}/task/v2/tasks"
        token = self._get_access_token()

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        payload = {
            "summary": title,
            "description": description,
        }

        if due_date:
            payload["due"] = {
                "timestamp": str(int(pd.to_datetime(due_date).timestamp() * 1000)),
                "is_all_day": True
            }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            data = response.json()
            if data.get("code") == 0:
                task = data.get("data", {}).get("task", {})
                logger.info(f"Tạo task thành công: {title}")
                return task.get("guid")
        except Exception as e:
            logger.error(f"Lỗi tạo task: {e}")
        return None

    def get_chat_members(self, chat_id: str) -> List[Dict]:
        """Lấy danh sách thành viên trong nhóm"""
        url = f"{self.base_url}/im/v1/chats/{chat_id}/members"
        token = self._get_access_token()

        headers = {"Authorization": f"Bearer {token}"}
        members = []

        try:
            response = requests.get(url, headers=headers, timeout=10)
            data = response.json()
            if data.get("code") == 0:
                members = data.get("data", {}).get("items", [])
        except Exception as e:
            logger.error(f"Lỗi lấy members: {e}")

        return members

    def upload_image(self, image_path: str) -> Optional[str]:
        """Upload hình ảnh và trả về image_key"""
        url = f"{self.base_url}/im/v1/images"
        token = self._get_access_token()

        headers = {"Authorization": f"Bearer {token}"}

        try:
            with open(image_path, "rb") as f:
                files = {"image": f}
                response = requests.post(url, headers=headers, files=files, timeout=30)
                data = response.json()
                if data.get("code") == 0:
                    return data.get("data", {}).get("image_key")
        except Exception as e:
            logger.error(f"Lỗi upload ảnh: {e}")
        return None

    @staticmethod
    def verify_signature(verify_token: str, timestamp: str, signature: str, encrypt_key: str = None) -> bool:
        """Xác thực signature từ Lark webhook"""
        if config.LARK_VERIFICATION_TOKEN and verify_token != config.LARK_VERIFICATION_TOKEN:
            return False

        if not encrypt_key:
            # Không có encryption
            return True

        # Có encryption
        string_to_sign = f"{timestamp}{encrypt_key}"
        sign = hashlib.sha256(string_to_sign.encode()).hexdigest()
        return sign == signature


# Singleton instance
lark_client = LarkClient()
