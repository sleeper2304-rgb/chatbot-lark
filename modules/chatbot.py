# ============================================
# MODULE CHATBOT - XỬ LÝ TIN NHẮN
# Chatbot trả lời tự động thông minh
# ============================================

import logging
import json
import re
import os
import threading
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import config
from modules.groq_ai import groq_ai
from modules.lark_client import lark_client

logger = logging.getLogger(__name__)


class TaskManager:
    """Quản lý Task đơn giản"""

    def __init__(self):
        self.data_file = "data/tasks.json"
        self.tasks: Dict[str, List[Dict]] = {}
        self._load()

    def _load(self):
        """Load tasks từ file"""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, "r", encoding="utf-8") as f:
                    self.tasks = json.load(f)
        except Exception as e:
            logger.error(f"Lỗi load tasks: {e}")
            self.tasks = {}

    def _save(self):
        """Lưu tasks vào file"""
        try:
            os.makedirs("data", exist_ok=True)
            with open(self.data_file, "w", encoding="utf-8") as f:
                json.dump(self.tasks, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Lỗi save tasks: {e}")

    def add_task(self, chat_id: str, title: str, assignee: str = None, due: str = None) -> str:
        """Thêm task mới"""
        if chat_id not in self.tasks:
            self.tasks[chat_id] = []

        task = {
            "id": f"task_{len(self.tasks[chat_id]) + 1}",
            "title": title,
            "assignee": assignee or "Chưa giao",
            "due": due or "Không có deadline",
            "status": "pending",
            "created_at": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "created_by": assignee
        }
        self.tasks[chat_id].append(task)
        self._save()
        return task["id"]

    def list_tasks(self, chat_id: str) -> List[Dict]:
        """Lấy danh sách task"""
        return self.tasks.get(chat_id, [])

    def update_task(self, chat_id: str, task_id: str, status: str) -> bool:
        """Cập nhật trạng thái task"""
        for task in self.tasks.get(chat_id, []):
            if task["id"] == task_id:
                task["status"] = status
                task["updated_at"] = datetime.now().strftime("%d/%m/%Y %H:%M")
                self._save()
                return True
        return False

    def delete_task(self, chat_id: str, task_id: str) -> bool:
        """Xóa task"""
        for i, task in enumerate(self.tasks.get(chat_id, [])):
            if task["id"] == task_id:
                self.tasks[chat_id].pop(i)
                self._save()
                return True
        return False

    def get_stats(self, chat_id: str) -> Dict:
        """Lấy thống kê task"""
        tasks = self.tasks.get(chat_id, [])
        return {
            "total": len(tasks),
            "pending": len([t for t in tasks if t.get("status") == "pending"]),
            "done": len([t for t in tasks if t.get("status") == "done"])
        }


class ReminderManager:
    """Quản lý nhắc nhở"""

    def __init__(self):
        self.data_file = "data/reminders.json"
        self.reminders: List[Dict] = []
        self._load()
        self._start_scheduler()

    def _load(self):
        """Load reminders từ file"""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, "r", encoding="utf-8") as f:
                    self.reminders = json.load(f)
        except Exception as e:
            logger.error(f"Lỗi load reminders: {e}")
            self.reminders = []

    def _save(self):
        """Lưu reminders vào file"""
        try:
            os.makedirs("data", exist_ok=True)
            with open(self.data_file, "w", encoding="utf-8") as f:
                json.dump(self.reminders, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Lỗi save reminders: {e}")

    def _start_scheduler(self):
        """Bắt đầu scheduler kiểm tra reminders"""
        def check_reminders():
            while True:
                try:
                    now = datetime.now()
                    to_remove = []
                    for reminder in self.reminders:
                        reminder_time = datetime.strptime(reminder["time"], "%d/%m/%Y %H:%M")
                        if now >= reminder_time:
                            message = f"⏰ **Nhắc nhở!**\n\n{reminder['message']}"
                            self.lark_client.send_text(reminder["chat_id"], message)
                            to_remove.append(reminder["id"])

                    for rid in to_remove:
                        self.reminders = [r for r in self.reminders if r["id"] != rid]
                        self._save()

                except Exception as e:
                    logger.error(f"Lỗi scheduler reminders: {e}")

                import time
                time.sleep(60)

        thread = threading.Thread(target=check_reminders, daemon=True)
        thread.start()

    def add_reminder(self, chat_id: str, user_id: str, time_str: str, message: str) -> str:
        """Thêm reminder"""
        reminder = {
            "id": f"rem_{len(self.reminders) + 1}",
            "chat_id": chat_id,
            "user_id": user_id,
            "message": message,
            "time": time_str,
            "created_at": datetime.now().strftime("%d/%m/%Y %H:%M")
        }
        self.reminders.append(reminder)
        self._save()
        return reminder["id"]

    def list_reminders(self, chat_id: str = None) -> List[Dict]:
        """Lấy danh sách reminders"""
        if chat_id:
            return [r for r in self.reminders if r["chat_id"] == chat_id]
        return self.reminders

    def delete_reminder(self, reminder_id: str) -> bool:
        """Xóa reminder"""
        for i, r in enumerate(self.reminders):
            if r["id"] == reminder_id:
                self.reminders.pop(i)
                self._save()
                return True
        return False

    lark_client = None  # Sẽ được set sau


class KeywordAutoReply:
    """Auto reply theo keyword"""

    def __init__(self):
        self.data_file = "data/keywords.json"
        self.rules: Dict[str, Dict[str, List[Dict]]] = {}  # {chat_id: {keyword: [responses]}}
        self._load()

    def _load(self):
        """Load keyword rules từ file"""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, "r", encoding="utf-8") as f:
                    self.rules = json.load(f)
        except Exception as e:
            logger.error(f"Lỗi load keywords: {e}")
            self.rules = {}

    def _save(self):
        """Lưu keyword rules vào file"""
        try:
            os.makedirs("data", exist_ok=True)
            with open(self.data_file, "w", encoding="utf-8") as f:
                json.dump(self.rules, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Lỗi save keywords: {e}")

    def add_keyword(self, chat_id: str, keyword: str, response: str) -> bool:
        """Thêm keyword rule"""
        if chat_id not in self.rules:
            self.rules[chat_id] = {}
        if keyword.lower() not in self.rules[chat_id]:
            self.rules[chat_id][keyword.lower()] = []
        self.rules[chat_id][keyword.lower()].append({
            "response": response,
            "created_at": datetime.now().strftime("%d/%m/%Y %H:%M")
        })
        self._save()
        return True

    def check_keyword(self, chat_id: str, text: str) -> Optional[str]:
        """Kiểm tra và trả về auto reply nếu có keyword"""
        text_lower = text.lower()
        chat_rules = self.rules.get(chat_id, {})

        for keyword, responses in chat_rules.items():
            if keyword in text_lower and responses:
                import random
                return random.choice(responses)["response"]
        return None

    def list_keywords(self, chat_id: str) -> List[Dict]:
        """Lấy danh sách keywords"""
        return [
            {"keyword": k, "responses": v}
            for k, v in self.rules.get(chat_id, {}).items()
        ]

    def delete_keyword(self, chat_id: str, keyword: str) -> bool:
        """Xóa keyword"""
        if chat_id in self.rules and keyword.lower() in self.rules[chat_id]:
            del self.rules[chat_id][keyword.lower()]
            self._save()
            return True
        return False


class AttendanceManager:
    """Quản lý điểm danh"""

    def __init__(self):
        self.data_file = "data/attendance.json"
        self.attendance: Dict[str, Dict[str, str]] = {}  # {date: {chat_id: {user_id: status}}}
        self._load()

    def _load(self):
        """Load attendance từ file"""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, "r", encoding="utf-8") as f:
                    self.attendance = json.load(f)
        except Exception as e:
            logger.error(f"Lỗi load attendance: {e}")
            self.attendance = {}

    def _save(self):
        """Lưu attendance vào file"""
        try:
            os.makedirs("data", exist_ok=True)
            with open(self.data_file, "w", encoding="utf-8") as f:
                json.dump(self.attendance, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Lỗi save attendance: {e}")

    def checkin(self, chat_id: str, user_id: str, user_name: str = None) -> bool:
        """Checkin"""
        today = datetime.now().strftime("%d/%m/%Y")
        if today not in self.attendance:
            self.attendance[today] = {}
        if chat_id not in self.attendance[today]:
            self.attendance[today][chat_id] = {}
        self.attendance[today][chat_id][user_id] = {
            "name": user_name or user_id,
            "time": datetime.now().strftime("%H:%M"),
            "status": "present"
        }
        self._save()
        return True

    def checkout(self, chat_id: str, user_id: str) -> bool:
        """Checkout"""
        today = datetime.now().strftime("%d/%m/%Y")
        if today in self.attendance and chat_id in self.attendance[today]:
            if user_id in self.attendance[today][chat_id]:
                self.attendance[today][chat_id][user_id]["status"] = "checked_out"
                self.attendance[today][chat_id][user_id]["checkout_time"] = datetime.now().strftime("%H:%M")
                self._save()
                return True
        return False

    def get_daily_report(self, chat_id: str) -> Dict:
        """Lấy báo cáo ngày"""
        today = datetime.now().strftime("%d/%m/%Y")
        members = self.attendance.get(today, {}).get(chat_id, {})
        return {
            "date": today,
            "total": len(members),
            "present": len([m for m in members.values() if m.get("status") == "present"]),
            "checked_out": len([m for m in members.values() if m.get("status") == "checked_out"]),
            "members": members
        }


class QuickNote:
    """Ghi chú nhanh"""

    def __init__(self):
        self.data_file = "data/notes.json"
        self.notes: Dict[str, List[Dict]] = {}
        self._load()

    def _load(self):
        """Load notes từ file"""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, "r", encoding="utf-8") as f:
                    self.notes = json.load(f)
        except Exception as e:
            logger.error(f"Lỗi load notes: {e}")
            self.notes = {}

    def _save(self):
        """Lưu notes vào file"""
        try:
            os.makedirs("data", exist_ok=True)
            with open(self.data_file, "w", encoding="utf-8") as f:
                json.dump(self.notes, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Lỗi save notes: {e}")

    def add_note(self, chat_id: str, content: str, user_id: str) -> str:
        """Thêm ghi chú"""
        if chat_id not in self.notes:
            self.notes[chat_id] = []
        note = {
            "id": f"note_{len(self.notes[chat_id]) + 1}",
            "content": content,
            "user_id": user_id,
            "created_at": datetime.now().strftime("%d/%m/%Y %H:%M")
        }
        self.notes[chat_id].insert(0, note)
        self._save()
        return note["id"]

    def list_notes(self, chat_id: str) -> List[Dict]:
        """Lấy danh sách ghi chú"""
        return self.notes.get(chat_id, [])[:10]

    def delete_note(self, chat_id: str, note_id: str) -> bool:
        """Xóa ghi chú"""
        for i, n in enumerate(self.notes.get(chat_id, [])):
            if n["id"] == note_id:
                self.notes[chat_id].pop(i)
                self._save()
                return True
        return False


class VoteManager:
    """Quản lý bình chọn"""

    def __init__(self):
        self.data_file = "data/votes.json"
        self.votes: Dict[str, Dict] = {}
        self._load()

    def _load(self):
        """Load votes từ file"""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, "r", encoding="utf-8") as f:
                    self.votes = json.load(f)
        except Exception as e:
            logger.error(f"Lỗi load votes: {e}")
            self.votes = {}

    def _save(self):
        """Lưu votes vào file"""
        try:
            os.makedirs("data", exist_ok=True)
            with open(self.data_file, "w", encoding="utf-8") as f:
                json.dump(self.votes, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Lỗi save votes: {e}")

    def create_vote(self, chat_id: str, question: str, options: List[str]) -> str:
        """Tạo bình chọn"""
        vote_id = f"vote_{len(self.votes) + 1}"
        self.votes[vote_id] = {
            "id": vote_id,
            "chat_id": chat_id,
            "question": question,
            "options": {opt: [] for opt in options},
            "created_at": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "created_by": None,
            "status": "open"
        }
        self._save()
        return vote_id

    def vote(self, vote_id: str, user_id: str, option: str) -> bool:
        """Bỏ phiếu"""
        if vote_id in self.votes and self.votes[vote_id]["status"] == "open":
            for opt in self.votes[vote_id]["options"]:
                if user_id in self.votes[vote_id]["options"][opt]:
                    self.votes[vote_id]["options"][opt].remove(user_id)
            if option in self.votes[vote_id]["options"]:
                self.votes[vote_id]["options"][option].append(user_id)
                self._save()
                return True
        return False

    def get_results(self, vote_id: str) -> Optional[Dict]:
        """Lấy kết quả bình chọn"""
        if vote_id in self.votes:
            v = self.votes[vote_id]
            total = sum(len(users) for users in v["options"].values())
            results = []
            for opt, users in v["options"].items():
                pct = (len(users) / total * 100) if total > 0 else 0
                results.append({
                    "option": opt,
                    "votes": len(users),
                    "percentage": round(pct, 1)
                })
            return {"question": v["question"], "total": total, "results": results}
        return None

    def list_open_votes(self, chat_id: str) -> List[Dict]:
        """Lấy danh sách vote đang mở"""
        return [v for v in self.votes.values() if v["chat_id"] == chat_id and v["status"] == "open"]


# Khởi tạo các manager
task_manager = TaskManager()
reminder_manager = ReminderManager()
keyword_manager = KeywordAutoReply()
attendance_manager = AttendanceManager()
note_manager = QuickNote()
vote_manager = VoteManager()


class ChatBot:
    """Chatbot AI thông minh cho Lark"""

    COMMANDS = {
        # AI Commands
        "help": "Hiển thị danh sách lệnh",
        "ask": "Hỏi AI (vd: /ask [câu hỏi])",
        "summarize": "Tóm tắt văn bản",
        "translate": "Dịch thuật",
        "ideas": "Tạo ý tưởng",
        "clear": "Xóa lịch sử hội thoại",

        # Task Management
        "task": "Quản lý task",
        "todo": "Quản lý task (viết tắt)",
        "tasks": "Xem danh sách task",
        "addtask": "Thêm task mới",
        "donetask": "Đánh dấu task hoàn thành",
        "deltask": "Xóa task",

        # Reminder
        "remind": "Đặt nhắc nhở",
        "reminders": "Xem danh sách nhắc nhở",
        "delremind": "Xóa nhắc nhở",

        # Attendance
        "checkin": "Điểm danh buổi sáng",
        "checkout": "Kết thúc làm việc",
        "attendance": "Xem báo cáo điểm danh",

        # Meeting
        "meeting": "Tạo lịch họp nhanh",
        "standup": "Thu thập standup hàng ngày",

        # Notes
        "note": "Tạo ghi chú nhanh",
        "notes": "Xem ghi chú",

        # Voting
        "vote": "Tạo bình chọn",
        "voting": "Bỏ phiếu",
        "voteresult": "Xem kết quả bình chọn",

        # Broadcast
        "notify": "Gửi thông báo đến nhóm",

        # Keywords
        "keyword": "Thêm auto-reply keyword",
        "keywords": "Xem danh sách keyword",
        "delkeyword": "Xóa keyword",

        # Cards
        "table": "Tạo bảng thông tin",
        "poll": "Tạo khảo sát",
        "form": "Tạo form thu thập thông tin",
        "menu": "Hiển thị menu tương tác",

        # Stats
        "stats": "Xem thống kê bot",
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
        # Set lark client cho reminder manager
        reminder_manager.lark_client = self.lark

    def process_message(self, event: Dict) -> Optional[str]:
        """Xử lý tin nhắn từ Lark"""
        try:
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
            sender_name = event.get("sender", {}).get("sender_id", {}).get("name", sender_id)
            chat_id = event.get("chat_id", "")
            message_id = event.get("message_id", "")
            text = content.get("text", "").strip()

            # Bỏ mention tags
            text = re.sub(r"<at[^>]*>.*?</at>", "", text, flags=re.DOTALL).strip()
            text = re.sub(r"<at[^>]*/>", "", text).strip()
            text = re.sub(r"@_user_\d+\s*", "", text).strip()

            self.stats["total_messages"] += 1

            # Bỏ qua tin nhắn từ bot
            if event.get("sender", {}).get("sender_type") == "bot":
                return None

            if not text:
                return None

            # Kiểm tra keyword auto-reply TRƯỚC
            auto_reply = keyword_manager.check_keyword(chat_id, text)
            if auto_reply:
                self.stats["commands_used"] += 1
                return auto_reply

            # Xử lý lệnh
            if text.startswith(config.COMMAND_PREFIX):
                return self._handle_command(text, sender_id, sender_name, chat_id, event)

            # Xử lý bằng AI
            if self.ai.is_available():
                self.stats["ai_responses"] += 1
                return self.ai.chat(sender_id, text, session_id=chat_id)
            else:
                return "Chatbot AI chưa được kích hoạt. Vui lòng liên hệ admin!"

        except Exception as e:
            logger.error(f"Lỗi xử lý tin nhắn: {e}")
            return f"Đã xảy ra lỗi: {str(e)}"

    def _handle_command(self, text: str, user_id: str, user_name: str, chat_id: str, event: Dict) -> Optional[str]:
        """Xử lý các lệnh đặc biệt"""
        self.stats["commands_used"] += 1

        parts = text[len(config.COMMAND_PREFIX):].strip().split(" ", 1)
        cmd = parts[0].lower() if parts else ""
        args = parts[1] if len(parts) > 1 else ""

        # ========== AI COMMANDS ==========
        if cmd in ["help", "h", "?"]:
            return self._cmd_help()

        elif cmd in ["ask", "a"]:
            return self._cmd_ask(args)

        elif cmd in ["summarize", "sum"]:
            return self._cmd_summarize(args, event)

        elif cmd in ["translate", "trans"]:
            return self._cmd_translate(args)

        elif cmd in ["ideas", "idea"]:
            return self._cmd_ideas(args)

        elif cmd in ["clear", "reset"]:
            return self._cmd_clear(chat_id)

        # ========== TASK COMMANDS ==========
        elif cmd in ["task", "todo", "tasks"]:
            return self._cmd_tasks(args, chat_id)

        elif cmd in ["addtask", "taskadd"]:
            return self._cmd_addtask(args, chat_id, user_name)

        elif cmd in ["donetask", "taskdone"]:
            return self._cmd_donetask(args, chat_id)

        elif cmd in ["deltask", "taskdel"]:
            return self._cmd_deltask(args, chat_id)

        # ========== REMINDER COMMANDS ==========
        elif cmd in ["remind", "nhắc"]:
            return self._cmd_remind(args, user_id, chat_id)

        elif cmd in ["reminders"]:
            return self._cmd_reminders(chat_id)

        elif cmd in ["delremind", "reminddel"]:
            return self._cmd_delremind(args, chat_id)

        # ========== ATTENDANCE COMMANDS ==========
        elif cmd in ["checkin", "diem danh"]:
            return self._cmd_checkin(user_id, user_name, chat_id)

        elif cmd in ["checkout"]:
            return self._cmd_checkout(user_id, chat_id)

        elif cmd in ["attendance"]:
            return self._cmd_attendance(chat_id)

        # ========== MEETING COMMANDS ==========
        elif cmd in ["meeting", "lich hop"]:
            return self._cmd_meeting(args, chat_id)

        elif cmd in ["standup"]:
            return self._cmd_standup(chat_id, user_id)

        # ========== NOTE COMMANDS ==========
        elif cmd in ["note", "notes"]:
            return self._cmd_note(args, user_id, chat_id)

        # ========== VOTE COMMANDS ==========
        elif cmd in ["vote", "binh chon"]:
            return self._cmd_vote(args, chat_id)

        elif cmd in ["voting", "bv"]:
            return self._cmd_voting(args, user_id)

        elif cmd in ["voteresult", "ket qua"]:
            return self._cmd_voteresult(args, chat_id)

        # ========== BROADCAST ==========
        elif cmd in ["notify", "thong bao"]:
            return self._cmd_notify(args, chat_id)

        # ========== KEYWORD COMMANDS ==========
        elif cmd in ["keyword"]:
            return self._cmd_keyword(args, chat_id)

        elif cmd in ["keywords"]:
            return self._cmd_keywords(chat_id)

        elif cmd in ["delkeyword"]:
            return self._cmd_delkeyword(args, chat_id)

        # ========== CARD COMMANDS ==========
        elif cmd in ["table", "bang"]:
            return self._cmd_table(args, chat_id)

        elif cmd in ["poll", "khao sat"]:
            return self._cmd_poll(args, chat_id)

        elif cmd in ["form"]:
            return self._cmd_form(args, chat_id)

        elif cmd in ["menu"]:
            return self._cmd_menu(chat_id)

        # ========== STATS COMMANDS ==========
        elif cmd in ["stats", "stat"]:
            return self._cmd_stats()

        elif cmd in ["report", "bao cao"]:
            return self._cmd_report(user_id, chat_id)

        else:
            if args:
                return self.ai.chat(user_id, f"/{cmd} {args}", session_id=chat_id)
            return f"Lệnh `/{cmd}` không tồn tại. Gõ `/help` để xem danh sách lệnh."

    # ========== AI METHODS ==========

    def _cmd_help(self) -> str:
        help_text = "**📚 Hướng dẫn sử dụng Chatbot AI**\n\n"
        help_text += "**🤖 Trả lời tự động:**\n"
        help_text += "Chỉ cần nhắn tin bình thường, AI sẽ trả lời!\n\n"

        categories = {
            "📊 **Quản lý Task:**": ["task", "addtask", "donetask", "deltask"],
            "⏰ **Nhắc nhở:**": ["remind", "reminders", "delremind"],
            "📋 **Điểm danh:**": ["checkin", "checkout", "attendance"],
            "📅 **Lịch họp:**": ["meeting", "standup"],
            "📝 **Ghi chú:**": ["note", "notes"],
            "🗳️ **Bình chọn:**": ["vote", "voting", "voteresult"],
            "🔔 **Thông báo:**": ["notify"],
            "🔑 **Auto-reply:**": ["keyword", "keywords", "delkeyword"],
            "📊 **Bảng & Forms:**": ["table", "poll", "form"],
            "🤖 **AI:**": ["ask", "summarize", "translate", "ideas", "clear"],
            "📈 **Thống kê:**": ["stats", "report", "menu"],
        }

        for cat_name, cmds in categories.items():
            help_text += f"{cat_name}\n"
            for c in cmds:
                desc = self.COMMANDS.get(c, "")
                help_text += f"  `/{c}` - {desc}\n"
            help_text += "\n"

        help_text += "💡 **Ví dụ:**\n"
        help_text += "• `/ask Tại sao bầu trời xanh?`\n"
        help_text += "• `/addtask Hoàn thành report | @user | 20/04`\n"
        help_text += "• `/checkin` - Điểm danh\n"
        help_text += "• `/remind 14:00 25/03 Họp team`\n"
        help_text += "• `/vote Ăn trưa gì? | Pizza | Cơm | Bún`"

        return help_text

    def _cmd_ask(self, args: str) -> str:
        if not args:
            return "Vui lòng nhập câu hỏi: `/ask [câu hỏi]`"
        return self.ai.chat("cmd_ask", args)

    def _cmd_summarize(self, args: str, event: Dict) -> str:
        quote = event.get("quote", {})
        if quote:
            return self.ai.summarize(quote.get("content", ""))
        if args:
            return self.ai.summarize(args)
        return "📝 **Tóm tắt văn bản**\n\nReply một tin nhắn và gõ `/summarize` để tóm tắt nội dung."

    def _cmd_translate(self, args: str) -> str:
        if not args:
            return "📝 **Dịch thuật**\n\n`/translate [ngôn ngữ] [văn bản]`\n\nVí dụ: `/translate English Xin chào`"
        parts = args.split(" ", 1)
        if len(parts) < 2:
            return "Vui lòng nhập: `/translate [ngôn ngữ] [văn bản]`"
        return self.ai.translate(parts[1], parts[0])

    def _cmd_ideas(self, args: str) -> str:
        if not args:
            return "💡 **Tạo ý tưởng**\n\n`/ideas [chủ đề]`\n\nVí dụ: `/ideas 5 ý tưởng marketing`"
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
        return "Không tạo được ý tưởng!"

    def _cmd_clear(self, session_id: str) -> str:
        self.ai.clear_conversation(session_id)
        return "🗑️ Đã xóa lịch sử hội thoại!"

    # ========== TASK METHODS ==========

    def _cmd_tasks(self, args: str, chat_id: str) -> str:
        """Xem danh sách task"""
        tasks = task_manager.list_tasks(chat_id)
        if not tasks:
            return "📋 **Danh sách Task**\n\nChưa có task nào!\n\nTạo task mới: `/addtask [tên task]`"

        stats = task_manager.get_stats(chat_id)
        text = f"📋 **Danh sách Task** ({stats['total']} task)\n\n"
        text += f"✅ Hoàn thành: {stats['done']} | ⏳ Đang làm: {stats['pending']}\n\n"

        pending = [t for t in tasks if t.get("status") == "pending"]
        done = [t for t in tasks if t.get("status") == "done"]

        if pending:
            text += "**⏳ Đang làm:**\n"
            for t in pending:
                text += f"• `{t['id']}` - {t['title']}\n"
                text += f"  👤 {t.get('assignee', 'Chưa giao')} | 📅 {t.get('due', 'Không có deadline')}\n\n"

        if done:
            text += "**✅ Hoàn thành:**\n"
            for t in done:
                text += f"• ~~{t['title']}~~\n"

        return text

    def _cmd_addtask(self, args: str, chat_id: str, user_name: str) -> str:
        """Thêm task mới"""
        if not args:
            return ("📝 **Thêm Task Mới**\n\n"
                   "`/addtask [tên task] | [@người giao] | [deadline]`\n\n"
                   "Ví dụ:\n"
                   "`/addtask Hoàn thành report | @Nguyen Van A | 20/04`\n"
                   "`/addtask Thiết kế landing page`")

        parts = [p.strip() for p in args.split("|")]
        title = parts[0]
        assignee = parts[1].replace("@", "") if len(parts) > 1 else user_name
        due = parts[2] if len(parts) > 2 else None

        task_id = task_manager.add_task(chat_id, title, assignee, due)

        self.lark.create_button_card(
            receive_id=chat_id,
            title=f"✅ Task mới được tạo!",
            description=f"**{title}**\n\n👤 Người phụ trách: {assignee}\n📅 Deadline: {due or 'Không có'}",
            buttons=[
                {"text": "✅ Hoàn thành", "type": "primary", "value": f"donetask_{task_id}"},
                {"text": "❌ Xóa", "type": "default", "value": f"deltask_{task_id}"}
            ]
        )
        return None

    def _cmd_donetask(self, args: str, chat_id: str) -> str:
        """Đánh dấu task hoàn thành"""
        if not args:
            return "Vui lòng nhập ID task: `/donetask [task_id]`\n\nXem danh sách: `/tasks`"
        task_id = args.strip()
        if task_manager.update_task(chat_id, task_id, "done"):
            return f"✅ Task `{task_id}` đã được đánh dấu hoàn thành!"
        return f"❌ Không tìm thấy task `{task_id}`"

    def _cmd_deltask(self, args: str, chat_id: str) -> str:
        """Xóa task"""
        if not args:
            return "Vui lòng nhập ID task: `/deltask [task_id]`"
        task_id = args.strip()
        if task_manager.delete_task(chat_id, task_id):
            return f"🗑️ Task `{task_id}` đã được xóa!"
        return f"❌ Không tìm thấy task `{task_id}`"

    # ========== REMINDER METHODS ==========

    def _cmd_remind(self, args: str, user_id: str, chat_id: str) -> str:
        """Đặt nhắc nhở"""
        if not args:
            return ("⏰ **Đặt nhắc nhở**\n\n"
                   "`/remind [thời gian] [ngày] [nội dung]`\n\n"
                   "Ví dụ:\n"
                   "`/remind 14:00 25/03 Họp team`\n"
                   "`/remind 09:00 Ngày mai Check-in`\n"
                   "`/remind 10:00 Deadline báo cáo`")

        parts = args.split(" ", 2)
        if len(parts) < 2:
            return "❌ Cú pháp: `/remind [HH:MM] [DD/MM] [nội dung]`"

        time_str = parts[0]
        date_part = parts[1] if len(parts) > 1 else datetime.now().strftime("%d/%m")
        message = parts[2] if len(parts) > 2 else "Nhắc nhở"

        # Parse ngày
        if date_part == "today":
            date_part = datetime.now().strftime("%d/%m")
        elif date_part == "tomorrow":
            date_part = (datetime.now() + timedelta(days=1)).strftime("%d/%m")

        full_time = f"{date_part} {time_str}"

        try:
            datetime.strptime(full_time, "%d/%m %H:%M")
        except ValueError:
            return "❌ Định dạng không đúng. Dùng: `/remind [HH:MM] [DD/MM] [nội dung]`"

        reminder_id = reminder_manager.add_reminder(chat_id, user_id, full_time, message)
        return f"⏰ **Nhắc nhở đã được đặt!**\n\n🕐 {full_time}\n📝 {message}\n\n(ID: {reminder_id})"

    def _cmd_reminders(self, chat_id: str) -> str:
        """Xem danh sách reminders"""
        reminders = reminder_manager.list_reminders(chat_id)
        if not reminders:
            return "⏰ **Danh sách nhắc nhở**\n\nChưa có nhắc nhở nào!"

        text = f"⏰ **Danh sách nhắc nhở** ({len(reminders)})\n\n"
        for r in reminders[:10]:
            text += f"• **{r['time']}** - {r['message']}\n"
            text += f"  ID: `{r['id']}`\n\n"
        return text

    def _cmd_delremind(self, args: str, chat_id: str) -> str:
        """Xóa reminder"""
        if not args:
            return "Vui lòng nhập ID reminder: `/delremind [id]`"
        if reminder_manager.delete_reminder(args):
            return f"🗑️ Đã xóa reminder!"
        return f"❌ Không tìm thấy reminder `{args}`"

    # ========== ATTENDANCE METHODS ==========

    def _cmd_checkin(self, user_id: str, user_name: str, chat_id: str) -> str:
        """Checkin"""
        attendance_manager.checkin(chat_id, user_id, user_name)

        card = {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {"tag": "plain_text", "content": "✅ Check-in thành công!"},
                "template": "green"
            },
            "elements": [
                {"tag": "hr"},
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"👤 **Người dùng:** {user_name}\n"
                                  f"🕐 **Giờ check-in:** {datetime.now().strftime('%H:%M:%S')}\n"
                                  f"📅 **Ngày:** {datetime.now().strftime('%d/%m/%Y')}"
                    }
                },
                {"tag": "hr"},
                {
                    "tag": "note",
                    "elements": [{"tag": "plain_text", "content": f"🤖 {config.BOT_NAME}"}]
                }
            ]
        }
        self.lark.send_interactive(chat_id, card)
        return None

    def _cmd_checkout(self, user_id: str, chat_id: str) -> str:
        """Checkout"""
        if attendance_manager.checkout(chat_id, user_id):
            return f"👋 **Checkout thành công!**\n\n🕐 Giờ checkout: {datetime.now().strftime('%H:%M:%S')}\n\nChúc bạn một ngày làm việc hiệu quả!"
        return "❌ Bạn chưa check-in hôm nay!"

    def _cmd_attendance(self, chat_id: str) -> str:
        """Xem báo cáo điểm danh"""
        report = attendance_manager.get_daily_report(chat_id)

        members_list = []
        for uid, info in report["members"].items():
            status_emoji = "✅" if info.get("status") == "present" else "👋"
            checkout_time = f" → {info.get('checkout_time', '...')}" if info.get('checkout_time') else ""
            members_list.append(f"{status_emoji} {info.get('name', uid)}: {info.get('time', '')}{checkout_time}")

        members_text = "\n".join(members_list) if members_list else "Chưa có ai check-in"

        card = {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {"tag": "plain_text", "content": f"📋 Báo cáo điểm danh - {report['date']}"},
                "template": "blue"
            },
            "elements": [
                {"tag": "hr"},
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**📊 Tổng quan:**\n"
                                  f"• Tổng check-in: {report['total']}\n"
                                  f"• Đang làm việc: {report['present']}\n"
                                  f"• Đã checkout: {report['checked_out']}"
                    }
                },
                {"tag": "hr"},
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**👥 Danh sách:**\n{members_text}"
                    }
                },
                {"tag": "hr"},
                {
                    "tag": "note",
                    "elements": [{"tag": "plain_text", "content": f"🤖 {config.BOT_NAME}"}]
                }
            ]
        }
        self.lark.send_interactive(chat_id, card)
        return None

    # ========== MEETING METHODS ==========

    def _cmd_meeting(self, args: str, chat_id: str) -> str:
        """Tạo lịch họp"""
        if not args:
            return ("📅 **Tạo lịch họp nhanh**\n\n"
                   "`/meeting [thời gian] [ngày] [chủ đề]`\n\n"
                   "Ví dụ:\n"
                   "`/meeting 14:00 25/03 Review sprint`\n"
                   "`/meeting 09:00 tomorrow Planning`")

        parts = args.split(" ", 2)
        if len(parts) < 2:
            return "❌ Cú pháp: `/meeting [HH:MM] [DD/MM] [chủ đề]`"

        time_str = parts[0]
        date_part = parts[1]
        topic = parts[2] if len(parts) > 2 else "Họp nhóm"

        if date_part == "tomorrow":
            date_part = (datetime.now() + timedelta(days=1)).strftime("%d/%m")
        elif date_part == "today":
            date_part = datetime.now().strftime("%d/%m")

        meeting_info = f"📅 **Lịch họp mới!**\n\n🕐 **Thời gian:** {date_part} lúc {time_str}\n📝 **Chủ đề:** {topic}\n\n👉 Tham gia cuộc họp nếu bạn có mặt!"

        card = {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {"tag": "plain_text", "content": "📅 Lịch họp mới"},
                "template": "purple"
            },
            "elements": [
                {"tag": "hr"},
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**📝 Chủ đề:** {topic}\n\n"
                                  f"**🕐 Thời gian:** {date_part} - {time_str}\n\n"
                                  f"**📍 Trạng thái:** Đã được tạo"
                    }
                },
                {"tag": "hr"},
                {
                    "tag": "div",
                    "elements": [
                        {"tag": "button", "text": {"tag": "plain_text", "content": "✅ Sẽ tham gia"}, "type": "primary", "value": {"action": "meeting_join"}},
                        {"tag": "button", "text": {"tag": "plain_text", "content": "❌ Không tham gia"}, "type": "default", "value": {"action": "meeting_decline"}}
                    ],
                    "layout": "right"
                },
                {"tag": "hr"},
                {
                    "tag": "note",
                    "elements": [{"tag": "plain_text", "content": f"🤖 {config.BOT_NAME}"}]
                }
            ]
        }
        self.lark.send_interactive(chat_id, card)
        return None

    def _cmd_standup(self, chat_id: str, user_id: str) -> str:
        """Thu thập standup"""
        questions = [
            "Hôm nay bạn làm gì?",
            "Có gì cần hỗ trợ không?",
            "Kế hoạch ngày mai?"
        ]
        card = {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {"tag": "plain_text", "content": f"📊 Daily Standup - {datetime.now().strftime('%d/%m/%Y')}"},
                "template": "orange"
            },
            "elements": [
                {"tag": "hr"},
                {
                    "tag": "div",
                    "text": {"tag": "lark_md", "content": "**Hãy trả lời 3 câu hỏi sau:**\n\n"}
                }
            ]
        }
        for i, q in enumerate(questions, 1):
            card["elements"].append({
                "tag": "div",
                "text": {"tag": "lark_md", "content": f"**{i}. {q}**"}
            })

        card["elements"].extend([
            {"tag": "hr"},
            {
                "tag": "div",
                "text": {"tag": "lark_md", "content": "Reply tin nhắn này với câu trả lời của bạn nhé!"}
            },
            {"tag": "hr"},
            {
                "tag": "note",
                "elements": [{"tag": "plain_text", "content": f"🤖 {config.BOT_NAME}"}]
            }
        ])
        self.lark.send_interactive(chat_id, card)
        return None

    # ========== NOTE METHODS ==========

    def _cmd_note(self, args: str, user_id: str, chat_id: str) -> str:
        """Tạo/xem ghi chú"""
        if not args:
            notes = note_manager.list_notes(chat_id)
            if not notes:
                return "📝 **Ghi chú**\n\nChưa có ghi chú nào!\n\nTạo ghi chú: `/note [nội dung]`"

            text = f"📝 **Ghi chú** ({len(notes)} ghi chú)\n\n"
            for n in notes:
                text += f"• **{n['content'][:50]}**...\n"
                text += f"  👤 {n.get('user_id', 'Unknown')} | {n['created_at']}\n\n"
            return text

        note_id = note_manager.add_note(chat_id, args, user_id)
        return f"📝 **Đã lưu ghi chú!**\n\n`{args}`\n\n(ID: {note_id})\n\nXem tất cả: `/notes`"

    # ========== VOTE METHODS ==========

    def _cmd_vote(self, args: str, chat_id: str) -> str:
        """Tạo bình chọn"""
        if not args:
            return ("🗳️ **Tạo bình chọn**\n\n"
                   "`/vote [câu hỏi] | [lựa chọn 1] | [lựa chọn 2] | [lựa chọn 3]...`\n\n"
                   "Ví dụ:\n"
                   "`/vote Ăn trưa gì? | Pizza | Cơm | Bún`")

        parts = [p.strip() for p in args.split("|")]
        if len(parts) < 3:
            return "❌ Cần ít nhất 1 câu hỏi và 2 lựa chọn."

        question = parts[0]
        options = parts[1:]

        vote_id = vote_manager.create_vote(chat_id, question, options)

        options_text = "\n".join([f"{i+1}. {opt}" for i, opt in enumerate(options)])

        card = {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {"tag": "plain_text", "content": f"🗳️ {question}"},
                "template": "purple"
            },
            "elements": [
                {"tag": "hr"},
                {
                    "tag": "div",
                    "text": {"tag": "lark_md", "content": options_text}
                },
                {"tag": "hr"},
                {
                    "tag": "note",
                    "elements": [{"tag": "plain_text", "content": f"ID: {vote_id} | 🤖 {config.BOT_NAME}"}]
                }
            ]
        }
        self.lark.send_interactive(chat_id, card)
        return None

    def _cmd_voting(self, args: str, user_id: str) -> str:
        """Bỏ phiếu"""
        if not args:
            return ("🗳️ **Bỏ phiếu**\n\n"
                   "`/voting [vote_id] [số thứ tự lựa chọn]`\n\n"
                   "Ví dụ: `/voting vote_1 2`\n\n"
                   "Xem các vote đang mở: `/voteresult`")
        return "🗳️ Đã ghi nhận phiếu bầu của bạn!"

    def _cmd_voteresult(self, args: str, chat_id: str) -> str:
        """Xem kết quả bình chọn"""
        open_votes = vote_manager.list_open_votes(chat_id)
        if not open_votes:
            return "🗳️ **Kết quả bình chọn**\n\nKhông có bình chọn nào đang mở.\n\nTạo vote: `/vote [câu hỏi] | [lựa chọn 1] | [lựa chọn 2]...`"

        text = f"🗳️ **Bình chọn đang mở** ({len(open_votes)})\n\n"
        for v in open_votes:
            text += f"**ID:** `{v['id']}`\n"
            text += f"**Câu hỏi:** {v['question']}\n"
            text += f"**Lựa chọn:** {', '.join(v['options'].keys())}\n\n"
        return text

    # ========== BROADCAST METHOD ==========

    def _cmd_notify(self, args: str, chat_id: str) -> str:
        """Gửi thông báo"""
        if not args:
            return ("🔔 **Gửi thông báo**\n\n"
                   "`/notify [nội dung thông báo]`\n\n"
                   "Ví dụ:\n"
                   "`/notify Cuộc họp bắt đầu sau 5 phút!`\n"
                   "`/notify Nhắc nhở deadline vào thứ 6!`")

        card = {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {"tag": "plain_text", "content": "🔔 Thông báo"},
                "template": "red"
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**📢 {args}**\n\n🕐 {datetime.now().strftime('%H:%M:%S')} - {datetime.now().strftime('%d/%m/%Y')}"
                    }
                },
                {"tag": "hr"},
                {
                    "tag": "note",
                    "elements": [{"tag": "plain_text", "content": f"🤖 {config.BOT_NAME}"}]
                }
            ]
        }
        self.lark.send_interactive(chat_id, card)
        return None

    # ========== KEYWORD METHODS ==========

    def _cmd_keyword(self, args: str, chat_id: str) -> str:
        """Thêm keyword auto-reply"""
        if not args:
            return ("🔑 **Thêm Auto-reply Keyword**\n\n"
                   "`/keyword [từ khóa] | [phản hồi]`\n\n"
                   "Ví dụ:\n"
                   "`/keyword hello | Chào bạn! Mình là bot!`\n"
                   "`/keyword help | Gõ /help để xem lệnh`")

        parts = args.split("|", 1)
        if len(parts) < 2:
            return "❌ Cú pháp: `/keyword [từ khóa] | [phản hồi]`"

        keyword = parts[0].strip()
        response = parts[1].strip()

        keyword_manager.add_keyword(chat_id, keyword, response)
        return f"🔑 **Đã thêm keyword!**\n\nTừ khóa: `{keyword}`\nPhản hồi: {response}\n\nBây giờ khi ai đó nhắn có chứa '{keyword}', bot sẽ tự trả lời!"

    def _cmd_keywords(self, chat_id: str) -> str:
        """Xem danh sách keyword"""
        keywords = keyword_manager.list_keywords(chat_id)
        if not keywords:
            return "🔑 **Auto-reply Keywords**\n\nChưa có keyword nào!\n\nThêm keyword: `/keyword [từ khóa] | [phản hồi]`"

        text = f"🔑 **Auto-reply Keywords** ({len(keywords)})\n\n"
        for kw in keywords:
            text += f"• **'{kw['keyword']}'** → {kw['responses'][0]['response'][:30]}...\n"
        return text

    def _cmd_delkeyword(self, args: str, chat_id: str) -> str:
        """Xóa keyword"""
        if not args:
            return "Vui lòng nhập từ khóa: `/delkeyword [từ khóa]`"
        if keyword_manager.delete_keyword(chat_id, args):
            return f"🗑️ Đã xóa keyword '{args}'!"
        return f"❌ Không tìm thấy keyword '{args}'"

    # ========== CARD METHODS ==========

    def _cmd_table(self, args: str, chat_id: str) -> str:
        """Tạo bảng"""
        if not args:
            return ("📊 **Tạo Bảng Thông Tin**\n\n"
                   "`/table [tiêu đề] | [cột 1], [cột 2] | [dòng 1 c1], [dòng 1 c2] | ...`\n\n"
                   "Ví dụ:\n"
                   "`/table Task Status | Task, Trạng thái | Design, Đang làm | Code, Xong`")
        parts = [p.strip() for p in args.split("|")]
        if len(parts) < 3:
            return "❌ Cú pháp: `/table [tiêu đề] | [cột 1], [cột 2] | [dòng 1 c1], [dòng 1 c2]`"

        self.lark.create_table_card(
            receive_id=chat_id,
            title=parts[0],
            headers=[h.strip() for h in parts[1].split(",")],
            rows=[[cell.strip() for cell in p.split(",")] for p in parts[2:]],
            footer=f"🤖 {config.BOT_NAME}"
        )
        return None

    def _cmd_poll(self, args: str, chat_id: str) -> str:
        """Tạo khảo sát"""
        if not args:
            return ("📊 **Tạo Khảo Sát**\n\n"
                   "`/poll [câu hỏi] | [lựa chọn 1] | [lựa chọn 2] | ...`\n\n"
                   "Ví dụ:\n"
                   "`/poll Bạn thích màu nào? | Xanh | Đỏ | Vàng`")
        parts = [p.strip() for p in args.split("|")]
        if len(parts) < 3:
            return "❌ Cần ít nhất 1 câu hỏi và 2 lựa chọn."
        self.lark.create_poll_card(receive_id=chat_id, question=parts[0], options=parts[1:])
        return None

    def _cmd_form(self, args: str, chat_id: str) -> str:
        """Tạo form"""
        if not args:
            return ("📝 **Tạo Form**\n\n"
                   "`/form [tiêu đề] | [câu hỏi 1] | [câu hỏi 2] | ...`\n\n"
                   "Ví dụ:\n"
                   "`/form Khảo sát | Tên của bạn? | Tuổi?`")
        parts = [p.strip() for p in args.split("|")]
        title = parts[0] if parts else "Form"
        self.lark.create_form_card(receive_id=chat_id, title=title, fields=[{"label": f, "type": "text"} for f in parts[1:]])
        return None

    def _cmd_menu(self, chat_id: str) -> str:
        """Menu chính"""
        items = [
            {"title": "📋 Quản lý Task", "description": "Thêm, xem, hoàn thành task", "value": "task"},
            {"title": "⏰ Đặt nhắc nhở", "description": "Nhắc nhở theo thời gian", "value": "remind"},
            {"title": "✅ Check-in", "description": "Điểm danh làm việc", "value": "checkin"},
            {"title": "📅 Tạo lịch họp", "description": "Tạo lịch họp nhanh", "value": "meeting"},
            {"title": "📝 Ghi chú", "description": "Lưu ghi chú nhanh", "value": "note"},
            {"title": "🗳️ Bình chọn", "description": "Tạo vote cho nhóm", "value": "vote"},
            {"title": "🔔 Thông báo", "description": "Gửi thông báo đến nhóm", "value": "notify"},
            {"title": "🔑 Auto-reply", "description": "Thiết lập keyword tự động", "value": "keyword"},
            {"title": "📊 Bảng & Form", "description": "Tạo bảng, poll, form", "value": "table"},
            {"title": "🤖 Chat AI", "description": "Trò chuyện với AI", "value": "ask"},
            {"title": "📈 Thống kê", "description": "Xem stats bot", "value": "stats"},
            {"title": "🧹 Xóa lịch sử", "description": "Bắt đầu cuộc trò mới", "value": "clear"},
        ]
        self.lark.create_list_card(receive_id=chat_id, title=f"📋 {config.BOT_NAME} - Menu", items=items, action_label="Xem tất cả lệnh")
        return None

    # ========== STATS METHODS ==========

    def _cmd_stats(self) -> str:
        """Xem thống kê"""
        uptime = datetime.now() - self.stats["start_time"]
        hours = int(uptime.total_seconds() // 3600)
        minutes = int((uptime.total_seconds() % 3600) // 60)

        return (f"📊 **Thống kê Chatbot**\n\n"
                f"⏱️ **Uptime:** {hours}h {minutes}m\n"
                f"💬 **Tổng tin nhắn:** {self.stats['total_messages']}\n"
                f"🤖 **Phản hồi AI:** {self.stats['ai_responses']}\n"
                f"⚡ **Lệnh sử dụng:** {self.stats['commands_used']}\n"
                f"💡 **Active conversations:** {self.ai.get_conversation_count()}\n\n"
                f"🟢 **Groq AI:** {'Online' if self.ai.is_available() else 'Offline'}\n"
                f"🟢 **Lark API:** Connected")

    def _cmd_report(self, user_id: str, chat_id: str) -> str:
        """Tạo báo cáo"""
        uptime = datetime.now() - self.stats["start_time"]
        hours = int(uptime.total_seconds() // 3600)

        card = {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {"tag": "plain_text", "content": f"📊 Báo cáo - {datetime.now().strftime('%d/%m/%Y')}"},
                "template": "blue"
            },
            "elements": [
                {"tag": "hr"},
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": (f"**🤖 Trạng thái Bot:**\n"
                                  f"• Uptime: {hours} giờ\n"
                                  f"• Tin nhắn: {self.stats['total_messages']}\n\n"
                                  f"**📈 Hoạt động:**\n"
                                  f"• AI responses: {self.stats['ai_responses']}\n"
                                  f"• Commands: {self.stats['commands_used']}\n\n"
                                  f"**✅ Hệ thống:**\n"
                                  f"• Groq AI: {'🟢 Online' if self.ai.is_available() else '🔴 Offline'}\n"
                                  f"• Lark API: 🟢 Connected")
                    }
                },
                {"tag": "hr"},
                {
                    "tag": "note",
                    "elements": [{"tag": "plain_text", "content": f"🤖 {config.BOT_NAME}"}]
                }
            ]
        }
        self.lark.send_interactive(chat_id, card)
        return None


# Singleton instance
chatbot = ChatBot()
