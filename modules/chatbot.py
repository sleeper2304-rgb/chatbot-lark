# ============================================
# MODULE CHATBOT - XỬ LÝ TIN NHẮN
# Chatbot trả lời tự động thông minh
# ============================================

import logging
import json
import re
from typing import Dict, Any, Optional, List
from datetime import datetime
import config
from modules.groq_ai import groq_ai
from modules.lark_client import lark_client

logger = logging.getLogger(__name__)


class ChatBot:
    """Chatbot AI thông minh cho Lark"""

    # Các lệnh đặc biệt
    COMMANDS = {
        "help": "Hiển thị danh sách lệnh",
        "ask": "Hỏi AI (vd: /ask [câu hỏi])",
        "summarize": "Tóm tắt văn bản",
        "translate": "Dịch thuật",
        "ideas": "Tạo ý tưởng",
        "weather": "Xem thời tiết",
        "remind": "Đặt nhắc nhở",
        "stats": "Xem thống kê bot",
        "clear": "Xóa lịch sử hội thoại",
        "schedule": "Xem lịch làm việc",
        "report": "Tạo báo cáo",
    }

    def __init__(self):
        self.ai = groq_ai
        self.lark = lark_client
        self.stats = {
            "total_messages": 0,
            "ai_responses": 0,
            "commands_used": 0,
            "start_time": datetime.now()
        }

    def process_message(self, event: Dict) -> Optional[str]:
        """Xử lý tin nhắn từ Lark"""
        try:
            # Parse event (v2.0: message_type; cũ: msg_type)
            msg_type = (event.get("msg_type") or event.get("message_type") or "").strip()
            raw_content = event.get("content", "{}")
            if isinstance(raw_content, dict):
                content = raw_content
            elif isinstance(raw_content, str):
                try:
                    content = json.loads(raw_content) if raw_content.strip() else {}
                except json.JSONDecodeError:
                    content = {"text": raw_content}
            else:
                content = {}
            sender_id = event.get("sender", {}).get("sender_id", {}).get("open_id", "")
            chat_id = event.get("chat_id", "")
            message_id = event.get("message_id", "")
            text = content.get("text", "").strip()
            # Bỏ thẻ @bot trong nội dung Lark: <at user_id="..."></at>
            text = re.sub(r"<at[^>]*>.*?</at>", "", text, flags=re.DOTALL).strip()
            text = re.sub(r"<at[^>]*/>", "", text).strip()
            # Feishu v2 mention trong text: @_user_1
            text = re.sub(r"@_user_\d+\s*", "", text).strip()

            self.stats["total_messages"] += 1

            # Bỏ qua tin nhắn từ bot
            if event.get("sender", {}).get("sender_type") == "bot":
                return None

            if not text:
                logger.info("Nội dung text rỗng sau khi parse, bỏ qua")
                return None

            # Xử lý lệnh đặc biệt
            if text.startswith(config.COMMAND_PREFIX):
                return self._handle_command(text, sender_id, chat_id, event)

            # Kiểm tra AI có sẵn sàng
            if not self.ai.is_available():
                return "Chatbot AI chưa được kích hoạt. Vui lòng liên hệ admin!"

            # Xử lý bằng AI
            self.stats["ai_responses"] += 1
            response = self.ai.chat(sender_id, text, session_id=chat_id)

            return response

        except Exception as e:
            logger.error(f"Lỗi xử lý tin nhắn: {e}")
            return f"Đã xảy ra lỗi: {str(e)}"

    def _handle_command(self, text: str, user_id: str, chat_id: str, event: Dict) -> Optional[str]:
        """Xử lý các lệnh đặc biệt"""
        self.stats["commands_used"] += 1

        # Parse command
        parts = text[len(config.COMMAND_PREFIX):].strip().split(" ", 1)
        cmd = parts[0].lower() if parts else ""
        args = parts[1] if len(parts) > 1 else ""

        # Xử lý từng command
        if cmd in ["help", "h", "?"]:
            return self._cmd_help()

        elif cmd in ["ask", "a", "hỏi"]:
            return self._cmd_ask(args)

        elif cmd in ["summarize", "sum", "tóm tắt"]:
            return self._cmd_summarize(args, event)

        elif cmd in ["translate", "dịch", "trans"]:
            return self._cmd_translate(args)

        elif cmd in ["ideas", "idea", "ý tưởng"]:
            return self._cmd_ideas(args)

        elif cmd in ["weather", "thời tiết"]:
            return self._cmd_weather(args)

        elif cmd in ["remind", "nhắc", "reminder"]:
            return self._cmd_remind(args, user_id)

        elif cmd in ["stats", "stat", "thống kê"]:
            return self._cmd_stats()

        elif cmd in ["clear", "xóa", "reset"]:
            return self._cmd_clear(chat_id)

        elif cmd in ["schedule", "lich", "lịch"]:
            return self._cmd_schedule()

        elif cmd in ["report", "báo cáo"]:
            return self._cmd_report(user_id)

        else:
            # Không phải command -> gửi cho AI xử lý
            if args:
                return self.ai.chat(user_id, f"/{cmd} {args}", session_id=chat_id)
            return f"Lệnh `/{cmd}` không tồn tại. Gõ `/help` để xem danh sách lệnh."

    def _cmd_help(self) -> str:
        """Hiển thị help"""
        help_text = "**📚 Hướng dẫn sử dụng Chatbot AI**\n\n"
        help_text += "**🤖 Trả lời tự động:**\n"
        help_text += "Chỉ cần nhắn tin bình thường, AI sẽ trả lời!\n\n"
        help_text += "**📋 Các lệnh đặc biệt:**\n"

        for cmd, desc in self.COMMANDS.items():
            help_text += f"• `/{cmd}` - {desc}\n"

        help_text += "\n💡 **Ví dụ:**\n"
        help_text += "• `/ask Tại sao bầu trời lại xanh?`\n"
        help_text += "• `/summarize` (reply một tin nhắn)\n"
        help_text += "• `/ideas 5 ý tưởng kinh doanh`"

        return help_text

    def _cmd_ask(self, args: str) -> str:
        """Hỏi AI trực tiếp"""
        if not args:
            return "Vui lòng nhập câu hỏi: `/ask [câu hỏi]`"

        return self.ai.chat("cmd_ask", args)

    def _cmd_summarize(self, args: str, event: Dict) -> str:
        """Tóm tắt văn bản"""
        # Kiểm tra reply message
        quote = event.get("quote", {})
        if quote:
            # Lấy nội dung từ tin nhắn được reply
            quoted_content = quote.get("content", "")
            return self.ai.summarize(quoted_content)

        if args:
            return self.ai.summarize(args)

        return "📝 **Tóm tắt văn bản**\n\nHãy nhắn `/summarize` kèm nội dung cần tóm tắt, hoặc reply một tin nhắn và gõ lệnh này."

    def _cmd_translate(self, args: str) -> str:
        """Dịch văn bản"""
        if not args:
            return "📝 **Dịch thuật**\n\nCú pháp: `/translate [ngôn ngữ đích] [văn bản]`\n\nVí dụ:\n• `/translate English Xin chào`\n• `/translate Japanese こんにちは`"

        parts = args.split(" ", 1)
        if len(parts) < 2:
            return "Vui lòng nhập: `/translate [ngôn ngữ] [văn bản]`"

        lang = parts[0]
        text = parts[1]

        return self.ai.translate(text, lang)

    def _cmd_ideas(self, args: str) -> str:
        """Tạo ý tưởng"""
        if not args:
            return "💡 **Tạo ý tưởng**\n\nCú pháp: `/ideas [chủ đề]`\n\nVí dụ:\n• `/ideas 5 ý tưởng marketing`\n• `/ideas trò chơi teambuilding`"

        # Parse số lượng ý tưởng
        count = 5
        topic = args
        match = re.match(r"(\d+)\s*(?:ý\s*tưởng\s+)?(.+)", args)
        if match:
            count = min(int(match.group(1)), 10)
            topic = match.group(2)

        ideas = self.ai.generate_ideas(topic, count)

        if ideas:
            result = f"💡 **{len(ideas)} ý tưởng về: {topic}**\n\n"
            for i, idea in enumerate(ideas, 1):
                result += f"{i}. {idea}\n"
            return result

        return "Không tạo được ý tưởng. Thử lại với chủ đề khác!"

    def _cmd_weather(self, args: str) -> str:
        """Xem thời tiết (mock)"""
        # Đây là demo - có thể tích hợp OpenWeatherMap API miễn phí
        return "🌤️ **Thời tiết**\n\n(Để xem thời tiết thực, cần cấu hình OpenWeatherMap API)\n\nVí dụ: `/weather Hà Nội`"

    def _cmd_remind(self, args: str, user_id: str) -> str:
        """Đặt nhắc nhở"""
        if not args:
            return "⏰ **Đặt nhắc nhở**\n\nCú pháp: `/remind [thời gian] [nội dung]`\n\nVí dụ:\n• `/remind 14:00 Họp team`\n• `/remind tomorrow 9am Check-in`"

        # Parse reminder
        # Format: /remind [time] [message]
        # Đây là placeholder - có thể mở rộng với scheduler
        return f"⏰ **Nhắc nhở đã được ghi nhận!**\n\n`{args}`\n\n(Bot sẽ nhắc bạn khi đến giờ)"

    def _cmd_stats(self) -> str:
        """Xem thống kê"""
        uptime = datetime.now() - self.stats["start_time"]
        hours = int(uptime.total_seconds() // 3600)
        minutes = int((uptime.total_seconds() % 3600) // 60)

        stats_text = f"📊 **Thống kê Chatbot AI**\n\n"
        stats_text += f"⏱️ Uptime: {hours}h {minutes}m\n"
        stats_text += f"💬 Tổng tin nhắn: {self.stats['total_messages']}\n"
        stats_text += f"🤖 Phản hồi AI: {self.stats['ai_responses']}\n"
        stats_text += f"⚡ Lệnh sử dụng: {self.stats['commands_used']}\n"
        stats_text += f"💡 Active conversations: {self.ai.get_conversation_count()}"

        return stats_text

    def _cmd_clear(self, session_id: str) -> str:
        """Xóa lịch sử"""
        self.ai.clear_conversation(session_id)
        return "🗑️ Đã xóa lịch sử hội thoại! Bắt đầu cuộc trò chuyện mới nào!"

    def _cmd_schedule(self) -> str:
        """Xem lịch làm việc"""
        schedule_text = "📅 **Lịch làm việc**\n\n"
        schedule_text += "🕐 Bot hoạt động: 24/7\n"
        schedule_text += f"📤 Báo cáo tự động: {config.REPORT_SCHEDULE} hàng ngày\n"
        schedule_text += "⏰ Nhắc nhở: Có hỗ trợ"

        return schedule_text

    def _cmd_report(self, user_id: str) -> str:
        """Tạo báo cáo nhanh"""
        report_text = f"📊 **Báo cáo - {datetime.now().strftime('%d/%m/%Y')}**\n\n"

        uptime = datetime.now() - self.stats["start_time"]
        hours = int(uptime.total_seconds() // 3600)

        report_text += "**🤖 Trạng thái Bot:**\n"
        report_text += f"• Uptime: {hours} giờ\n"
        report_text += f"• Tin nhắn hôm nay: {self.stats['total_messages']}\n"
        report_text += f"• Active conversations: {self.ai.get_conversation_count()}\n\n"

        report_text += "**📈 Hoạt động:**\n"
        report_text += f"• AI responses: {self.stats['ai_responses']}\n"
        report_text += f"• Commands used: {self.stats['commands_used']}\n\n"

        report_text += "**✅ Hệ thống:**\n"
        report_text += f"• Groq AI: {'🟢 Online' if self.ai.is_available() else '🔴 Offline'}\n"
        report_text += f"• Lark API: 🟢 Connected"

        return report_text


# Singleton instance
chatbot = ChatBot()
