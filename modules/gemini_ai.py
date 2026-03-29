# ============================================
# MODULE GEMINI AI - MIỄN PHÍ
# Sử dụng Google Gemini API (miễn phí tier)
# ============================================

import logging
from typing import List, Dict, Optional
import google.generativeai as genai
from datetime import datetime
import config

logger = logging.getLogger(__name__)


class GeminiAI:
    """AI Assistant sử dụng Gemini - hoàn toàn miễn phí"""

    def __init__(self):
        self.api_key = config.GEMINI_API_KEY
        self.model_name = config.GEMINI_MODEL
        self.temperature = config.GEMINI_TEMPERATURE
        self.conversations: Dict[str, List[Dict]] = {}  # Lưu lịch sử hội thoại

        if self.api_key:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(self.model_name)
            logger.info(f"Khởi tạo Gemini AI: {self.model_name}")
        else:
            self.model = None
            logger.warning("GEMINI_API_KEY chưa được cấu hình!")

    def is_available(self) -> bool:
        """Kiểm tra AI có sẵn sàng không"""
        return self.model is not None

    def _build_system_prompt(self) -> str:
        """Xây dựng system prompt cho bot"""
        return f"""Bạn là {config.BOT_NAME} - một trợ lý AI thông minh, thân thiện và hữu ích.

## Khả năng của bạn:
1. Trả lời câu hỏi về mọi chủ đề
2. Hỗ trợ lập trình, viết code
3. Dịch thuật, tóm tắt văn bản
4. Phân tích dữ liệu, đưa ra gợi ý
5. Brainstorming ý tưởng
6. Hỗ trợ công việc và học tập

## Nguyên tắc:
- Trả lời ngắn gọn, dễ hiểu (trừ khi được yêu cầu chi tiết)
- Sử dụng emoji một cách phù hợp để tin nhắn sinh động hơn
- Nếu không biết, hãy thành thật nói ra
- Hỗ trợ tiếng Việt và tiếng Anh

## Lưu ý:
- Thời gian hiện tại: {datetime.now().strftime('%H:%M %d/%m/%Y')}
- Tên bot: {config.BOT_NAME}

Hãy trả lời một cách tự nhiên và hữu ích nhất!"""

    def chat(self, user_id: str, message: str, session_id: str = None) -> str:
        """Gửi tin nhắn và nhận phản hồi từ AI"""
        if not self.is_available():
            return "Xin lỗi, AI chưa được cấu hình. Vui lòng thêm GEMINI_API_KEY vào file .env"

        if session_id is None:
            session_id = user_id

        # Khởi tạo lịch sử nếu chưa có
        if session_id not in self.conversations:
            self.conversations[session_id] = []

        # Giới hạn số tin nhắn trong context
        while len(self.conversations[session_id]) > config.MAX_CONTEXT_MESSAGES:
            self.conversations[session_id].pop(0)

        try:
            # Xây dựng lịch sử hội thoại
            history = []
            for msg in self.conversations[session_id]:
                role = "user" if msg["role"] == "user" else "model"
                history.append({"role": role, "parts": [msg["content"]]})

            # Tạo chat với lịch sử
            chat = self.model.start_chat(history=history)
            system_prompt = self._build_system_prompt()

            # Gửi message với context
            full_message = f"{system_prompt}\n\nNgười dùng: {message}"
            response = chat.send_message(
                full_message,
                generation_config=genai.types.GenerationConfig(
                    temperature=self.temperature,
                    max_output_tokens=2048
                )
            )

            response_text = response.text

            # Lưu vào lịch sử
            self.conversations[session_id].append({"role": "user", "content": message})
            self.conversations[session_id].append({"role": "model", "content": response_text})

            logger.info(f"AI response for {session_id}: {response_text[:100]}...")
            return response_text

        except Exception as e:
            logger.error(f"Lỗi Gemini AI: {e}")
            return f"Xin lỗi, đã có lỗi xảy ra: {str(e)}"

    def summarize(self, text: str, max_length: int = 200) -> str:
        """Tóm tắt văn bản"""
        if not self.is_available():
            return "AI chưa được cấu hình"

        try:
            prompt = f"""Hãy tóm tắt văn bản sau một cách ngắn gọn (tối đa {max_length} ký tự):

{text}

Tóm tắt:"""
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            logger.error(f"Lỗi summarize: {e}")
            return f"Lỗi khi tóm tắt: {str(e)}"

    def translate(self, text: str, target_lang: str = "Vietnamese") -> str:
        """Dịch văn bản"""
        if not self.is_available():
            return "AI chưa được cấu hình"

        try:
            prompt = f"""Hãy dịch văn bản sau sang tiếng {target_lang}:

{text}

Bản dịch:"""
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            logger.error(f"Lỗi translate: {e}")
            return f"Lỗi khi dịch: {str(e)}"

    def analyze_sentiment(self, text: str) -> Dict:
        """Phân tích cảm xúc văn bản"""
        if not self.is_available():
            return {"sentiment": "unknown", "score": 0, "error": "AI chưa cấu hình"}

        try:
            prompt = f"""Phân tích cảm xúc của văn bản sau và trả lời theo format:
- sentiment: positive/negative/neutral
- score: -1 đến 1
- reason: lý do ngắn gọn

Văn bản: {text}"""
            response = self.model.generate_content(prompt)
            return {
                "sentiment": "positive",
                "score": 0.5,
                "analysis": response.text
            }
        except Exception as e:
            logger.error(f"Lỗi analyze_sentiment: {e}")
            return {"sentiment": "error", "score": 0, "error": str(e)}

    def generate_ideas(self, topic: str, count: int = 5) -> List[str]:
        """Tạo ý tưởng về một chủ đề"""
        if not self.is_available():
            return []

        try:
            prompt = f"""Hãy đề xuất {count} ý tưởng về: {topic}

Format mỗi ý tưởng trên 1 dòng, ngắn gọn, có emoji phù hợp."""
            response = self.model.generate_content(prompt)
            ideas = [line.strip() for line in response.text.split("\n") if line.strip()]
            return ideas[:count]
        except Exception as e:
            logger.error(f"Lỗi generate_ideas: {e}")
            return []

    def code_review(self, code: str, language: str = "python") -> str:
        """Review code"""
        if not self.is_available():
            return "AI chưa được cấu hình"

        try:
            prompt = f"""Hãy review đoạn code {language} sau và đưa ra nhận xét:

```{language}
{code}
```

Nhận xét (theo format):
1. Điểm mạnh: ...
2. Điểm cần cải thiện: ...
3. Đề xuất: ..."""
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            logger.error(f"Lỗi code_review: {e}")
            return f"Lỗi khi review code: {str(e)}"

    def clear_conversation(self, session_id: str):
        """Xóa lịch sử hội thoại"""
        if session_id in self.conversations:
            self.conversations[session_id] = []
            logger.info(f"Đã xóa lịch sử: {session_id}")

    def get_conversation_count(self) -> int:
        """Đếm số cuộc hội thoại đang active"""
        return len(self.conversations)


# Singleton instance
gemini_ai = GeminiAI()
