# ============================================
# CẤU HÌNH CHÍNH - CHATBOT AI LARK
# Miễn phí 100% - Groq AI + Lark API
# ============================================

import os
from dotenv import load_dotenv

load_dotenv()

# === LARK (FEISHU) CONFIG ===
LARK_APP_ID = os.getenv("LARK_APP_ID", "")
LARK_APP_SECRET = os.getenv("LARK_APP_SECRET", "")
LARK_VERIFICATION_TOKEN = os.getenv("LARK_VERIFICATION_TOKEN", "")
LARK_ENCRYPT_KEY = os.getenv("LARK_ENCRYPT_KEY", "")

# === GROQ AI (MIỄN PHÍ - NHANH) ===
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
GROQ_TEMPERATURE = float(os.getenv("GROQ_TEMPERATURE", "0.7"))

# === FLASK CONFIG ===
DEBUG = os.getenv("DEBUG", "False").lower() == "true"
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "5000"))

# === WEBHOOK CONFIG ===
WEBHOOK_PATH = os.getenv("WEBHOOK_PATH", "/webhook/lark")

# === BOT CONFIG ===
BOT_NAME = os.getenv("BOT_NAME", "AI Assistant")
BOT_AVATAR = os.getenv("BOT_AVATAR", "")

# === WORKFLOW CONFIG ===
AUTO_SCHEDULE_ENABLED = os.getenv("AUTO_SCHEDULE_ENABLED", "true").lower() == "true"
AUTO_REMINDER_ENABLED = os.getenv("AUTO_REMINDER_ENABLED", "true").lower() == "true"
REPORT_SCHEDULE = os.getenv("REPORT_SCHEDULE", "09:00")  # Giờ gửi báo cáo hàng ngày

# === CONVERSATION CONTEXT ===
MAX_CONTEXT_MESSAGES = int(os.getenv("MAX_CONTEXT_MESSAGES", "10"))
SESSION_TIMEOUT = int(os.getenv("SESSION_TIMEOUT", "3600"))  # 1 giờ

# === CÁC NHÓM/channel ĐƯỢC PHÉP ===
ALLOWED_CHAT_IDS = [c.strip() for c in os.getenv("ALLOWED_CHAT_IDS", "").split(",") if c.strip()]

# === COMMAND PREFIX ===
COMMAND_PREFIX = os.getenv("COMMAND_PREFIX", "/ai")

# === LOGGING ===
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = "logs/chatbot.log"
