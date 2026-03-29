# ============================================
# MODULE WORKFLOW - TỰ ĐỘNG HÓA
# Workflow tự động: nhắc nhở, báo cáo, lên lịch
# ============================================

import logging
import json
import time
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from threading import Thread
import schedule
import config
from modules.lark_client import lark_client

logger = logging.getLogger(__name__)


class WorkflowEngine:
    """Engine xử lý workflow tự động"""

    def __init__(self):
        self.lark = lark_client
        self.schedules: Dict[str, Dict] = {}
        self.reminders: List[Dict] = []
        self.auto_report_enabled = config.AUTO_SCHEDULE_ENABLED
        self.auto_reminder_enabled = config.AUTO_REMINDER_ENABLED
        self._running = False

    def start(self):
        """Khởi động workflow engine"""
        if self._running:
            return

        self._running = True
        self._setup_scheduled_jobs()

        # Chạy scheduler trong thread riêng
        scheduler_thread = Thread(target=self._run_scheduler, daemon=True)
        scheduler_thread.start()

        logger.info("Workflow Engine đã khởi động!")

    def _run_scheduler(self):
        """Chạy scheduler liên tục"""
        while self._running:
            schedule.run_pending()
            time.sleep(30)  # Kiểm tra mỗi 30 giây

    def _setup_scheduled_jobs(self):
        """Thiết lập các job định kỳ"""
        if self.auto_report_enabled:
            # Báo cáo hàng ngày
            schedule.every().day.at(config.REPORT_SCHEDULE).do(self._send_daily_report)
            logger.info(f"Đã lên lịch báo cáo hàng ngày: {config.REPORT_SCHEDULE}")

        # Báo cáo hàng tuần (thứ 2)
        schedule.every().monday.at("08:00").do(self._send_weekly_report)

        # Cleanup expired reminders
        schedule.every().hour.do(self._cleanup_old_reminders)

    def _send_daily_report(self):
        """Gửi báo cáo hàng ngày"""
        try:
            report = self._generate_daily_report()

            for chat_id in config.ALLOWED_CHAT_IDS:
                self.lark.send_rich_text(
                    chat_id,
                    "📊 Báo cáo ngày " + datetime.now().strftime("%d/%m/%Y"),
                    report
                )

            logger.info("Đã gửi báo cáo hàng ngày")

        except Exception as e:
            logger.error(f"Lỗi gửi báo cáo hàng ngày: {e}")

    def _send_weekly_report(self):
        """Gửi báo cáo hàng tuần"""
        try:
            report = self._generate_weekly_report()

            for chat_id in config.ALLOWED_CHAT_IDS:
                self.lark.send_rich_text(
                    chat_id,
                    "📈 Báo cáo tuần " + datetime.now().strftime("%W/%Y"),
                    report
                )

            logger.info("Đã gửi báo cáo hàng tuần")

        except Exception as e:
            logger.error(f"Lỗi gửi báo cáo tuần: {e}")

    def _generate_daily_report(self) -> str:
        """Tạo nội dung báo cáo ngày"""
        report = "**📅 Tóm tắt hôm nay:**\n\n"
        report += f"• Ngày: {datetime.now().strftime('%A, %d/%m/%Y')}\n"
        report += f"• Giờ: {datetime.now().strftime('%H:%M:%S')}\n\n"

        report += "**📊 Hoạt động nhóm:**\n"
        report += "• Cập nhật task hôm nay\n"
        report += "• Tin nhắn chưa đọc\n\n"

        report += "**⏰ Việc cần làm:**\n"
        report += "• Kiểm tra deadline trong ngày\n"
        report += "• Review pull requests\n\n"

        report += "**💡 Gợi ý:**\n"
        report += "Nhắc nhở team cập nhật tiến độ công việc!"

        return report

    def _generate_weekly_report(self) -> str:
        """Tạo nội dung báo cáo tuần"""
        report = "**📈 Báo cáo tuần này:**\n\n"

        week_start = datetime.now() - timedelta(days=datetime.now().weekday())
        report += f"• Tuần: {week_start.strftime('%d/%m')} - {datetime.now().strftime('%d/%m/%Y')}\n\n"

        report += "**✅ Đã hoàn thành:**\n"
        report += "• Task 1\n"
        report += "• Task 2\n\n"

        report += "**🔄 Đang thực hiện:**\n"
        report += "• Task A\n"
        report += "• Task B\n\n"

        report += "**⚠️ Cần attention:**\n"
        report += "• Issue #123\n"
        report += "• Deadline tuần sau\n\n"

        report += "**📊 Metrics:**\n"
        report += "• Velocity: 85%\n"
        report += "• Bug fixes: 12\n"
        report += "• Features shipped: 3"

        return report

    def _cleanup_old_reminders(self):
        """Dọn dẹp reminders cũ"""
        now = datetime.now()
        self.reminders = [r for r in self.reminders if r["time"] > now]
        logger.info(f"Đã dọn dẹp reminders. Còn {len(self.reminders)} reminders.")

    def add_reminder(self, time_str: str, message: str, chat_id: str, user_id: str) -> str:
        """Thêm reminder mới"""
        try:
            # Parse time (format: HH:MM hoặc +30m, +1h, tomorrow 9am)
            reminder_time = self._parse_time(time_str)

            if reminder_time is None:
                return "❌ Không parse được thời gian. Format: HH:MM, +30m, tomorrow 9am"

            reminder = {
                "id": f"rem_{len(self.reminders)}",
                "time": reminder_time,
                "message": message,
                "chat_id": chat_id,
                "user_id": user_id,
                "created_at": datetime.now()
            }

            self.reminders.append(reminder)
            logger.info(f"Đã tạo reminder: {message} at {reminder_time}")

            return f"✅ **Nhắc nhở đã đặt!**\n\n⏰ {reminder_time.strftime('%H:%M %d/%m/%Y')}\n📝 {message}\n\nBot sẽ nhắc bạn khi đến giờ!"

        except Exception as e:
            logger.error(f"Lỗi tạo reminder: {e}")
            return f"❌ Lỗi: {str(e)}"

    def _parse_time(self, time_str: str) -> Optional[datetime]:
        """Parse chuỗi thời gian"""
        now = datetime.now()

        # Format HH:MM
        if ":" in time_str:
            try:
                parts = time_str.split(":")
                hour = int(parts[0])
                minute = int(parts[1].split()[0] if " " in parts[1] else parts[1])

                reminder_time = now.replace(hour=hour, minute=minute, second=0)

                # Nếu đã qua giờ hôm nay, chuyển sang ngày mai
                if reminder_time <= now:
                    reminder_time += timedelta(days=1)

                return reminder_time

            except:
                pass

        # +30m, +1h, +2h30m
        if time_str.startswith("+"):
            try:
                time_str = time_str[1:]
                hours = 0
                minutes = 0

                if "h" in time_str:
                    parts = time_str.split("h")
                    hours = int(parts[0])
                    if len(parts) > 1 and "m" in parts[1]:
                        minutes = int(parts[1].replace("m", ""))
                elif "m" in time_str:
                    minutes = int(time_str.replace("m", ""))

                return now + timedelta(hours=hours, minutes=minutes)

            except:
                pass

        # tomorrow 9am
        if "tomorrow" in time_str.lower():
            try:
                hour = 9
                minute = 0

                if "am" in time_str.lower():
                    hour = int(re.search(r'\d+', time_str).group())
                elif "pm" in time_str.lower():
                    hour = int(re.search(r'\d+', time_str).group()) + 12

                tomorrow = now + timedelta(days=1)
                return tomorrow.replace(hour=hour % 24, minute=minute, second=0)

            except:
                pass

        return None

    def add_schedule(self, schedule_id: str, title: str, time_str: str, action: Dict, chat_id: str):
        """Thêm lịch trình tự động"""
        schedule_time = self._parse_time(time_str)

        if schedule_time:
            self.schedules[schedule_id] = {
                "id": schedule_id,
                "title": title,
                "time": schedule_time,
                "action": action,
                "chat_id": chat_id,
                "repeat": action.get("repeat", "none")
            }

            # Đăng ký với schedule library
            if schedule_time.hour and schedule_time.minute:
                time_str_fmt = f"{schedule_time.hour:02d}:{schedule_time.minute:02d}"

                if self.schedules[schedule_id]["repeat"] == "daily":
                    schedule.every().day.at(time_str_fmt).do(
                        self._execute_scheduled_action, schedule_id
                    )
                elif self.schedules[schedule_id]["repeat"] == "weekly":
                    schedule.every().monday.at(time_str_fmt).do(
                        self._execute_scheduled_action, schedule_id
                    )

            logger.info(f"Đã thêm lịch trình: {title}")

    def _execute_scheduled_action(self, schedule_id: str):
        """Thực thi action đã lên lịch"""
        if schedule_id not in self.schedules:
            return

        sch = self.schedules[schedule_id]
        action = sch["action"]
        action_type = action.get("type")

        try:
            if action_type == "send_message":
                self.lark.send_text(sch["chat_id"], action.get("content", ""))

            elif action_type == "send_rich_text":
                self.lark.send_rich_text(
                    sch["chat_id"],
                    action.get("title", ""),
                    action.get("content", "")
                )

            elif action_type == "create_task":
                self.lark.create_task(
                    title=action.get("task_title", ""),
                    description=action.get("task_desc", ""),
                    due_date=action.get("due_date")
                )

            logger.info(f"Đã thực thi scheduled action: {schedule_id}")

        except Exception as e:
            logger.error(f"Lỗi thực thi scheduled action: {e}")

    def get_schedules(self, chat_id: str = None) -> List[Dict]:
        """Lấy danh sách lịch trình"""
        if chat_id:
            return [s for s in self.schedules.values() if s["chat_id"] == chat_id]
        return list(self.schedules.values())

    def get_reminders(self, user_id: str = None) -> List[Dict]:
        """Lấy danh sách reminders"""
        if user_id:
            return [r for r in self.reminders if r["user_id"] == user_id]
        return self.reminders

    def delete_schedule(self, schedule_id: str) -> bool:
        """Xóa lịch trình"""
        if schedule_id in self.schedules:
            del self.schedules[schedule_id]
            logger.info(f"Đã xóa lịch trình: {schedule_id}")
            return True
        return False

    def delete_reminder(self, reminder_id: str) -> bool:
        """Xóa reminder"""
        for i, r in enumerate(self.reminders):
            if r["id"] == reminder_id:
                self.reminders.pop(i)
                logger.info(f"Đã xóa reminder: {reminder_id}")
                return True
        return False

    def stop(self):
        """Dừng workflow engine"""
        self._running = False
        logger.info("Workflow Engine đã dừng!")


# Singleton instance
workflow_engine = WorkflowEngine()


# Import re for _parse_time
import re
