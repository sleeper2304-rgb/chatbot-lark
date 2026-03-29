# ============================================
# FILE KHOI CHAY CHINH - CHATBOT AI LARK
# Mien phi 100% - Gemini AI + Lark API
# ============================================

import os
import sys
import io
import logging
import json
import codecs
from datetime import datetime
from flask import Flask, request, jsonify

# Force UTF-8 encoding for Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import config
from modules.lark_client import lark_client
from modules.gemini_ai import gemini_ai
from modules.chatbot import chatbot
from modules.workflow import workflow_engine

# Tao thu muc logs neu chua co
os.makedirs("logs", exist_ok=True)
os.makedirs("data", exist_ok=True)

# Custom UTF-8 file handler
class UTF8FileHandler(logging.FileHandler):
    def __init__(self, filename, mode='a', encoding='utf-8', **kwargs):
        super().__init__(filename, mode, encoding, **kwargs)

logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        UTF8FileHandler(config.LOG_FILE),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Tạo Flask app
app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False

# ============== FLASK ROUTES ==============

@app.route('/')
def index():
    """Trang chủ - thông tin bot"""
    return jsonify({
        "name": "Chatbot AI Lark",
        "version": "1.0.0",
        "status": "online",
        "bot_name": config.BOT_NAME,
        "ai_model": config.GEMINI_MODEL if gemini_ai.is_available() else "Not configured",
        "features": [
            "Chatbot trả lời tự động",
            "Workflow tự động hóa",
            "AI thông minh (Gemini - miễn phí)"
        ],
        "endpoints": {
            "webhook": config.WEBHOOK_PATH,
            "health": "/health",
            "stats": "/stats",
            "send": "/api/send"
        }
    })


@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "lark_api": "connected" if config.LARK_APP_ID else "not_configured",
            "gemini_ai": "online" if gemini_ai.is_available() else "offline",
            "workflow": "running" if workflow_engine._running else "stopped"
        }
    })


@app.route('/stats')
def stats():
    """Thống kê bot"""
    return jsonify({
        "bot_stats": chatbot.stats,
        "ai_conversations": gemini_ai.get_conversation_count(),
        "schedules": len(workflow_engine.schedules),
        "reminders": len(workflow_engine.reminders),
        "uptime": str(datetime.now() - chatbot.stats["start_time"])
    })


@app.route(config.WEBHOOK_PATH, methods=['POST'])
def webhook_lark():
    """
    Webhook endpoint nhận tin nhắn từ Lark
    Lark sẽ POST event vào endpoint này
    """
    try:
        # Parse request
        payload = request.get_json()
        logger.info(f"Nhận webhook: {json.dumps(payload, ensure_ascii=False)[:500]}")

        # Xử lý URL verification (Lark gửi challenge để verify)
        if payload.get("type") == "url_verification":
            challenge = payload.get("challenge", "")
            logger.info(f"URL Verification - Challenge: {challenge}")
            return jsonify({"challenge": challenge})

        # Xử lý event tin nhắn
        if "event" in payload:
            event = payload["event"]

            # Lọc theo event type
            event_type = event.get("event_type", "")

            if event_type == "im.message.receive_v1":
                # Tin nhắn mới
                message = event.get("message", {})

                # Bỏ qua một số loại tin nhắn
                msg_type = message.get("msg_type", "")
                if msg_type in ["post", "audio", "video", "file", "sticker"]:
                    logger.info(f"Bỏ qua tin nhắn type: {msg_type}")
                    return jsonify({"code": 0, "msg": "ignored"})

                # Parse nội dung tin nhắn
                content = message.get("content", "{}")
                try:
                    content = json.loads(content)
                except:
                    content = {"text": content}

                event_data = {
                    "msg_type": msg_type,
                    "content": content,
                    "message_id": message.get("message_id", ""),
                    "chat_id": message.get("chat_id", ""),
                    "sender": event.get("sender", {}),
                    "create_time": message.get("create_time", ""),
                }

                # Kiểm tra quyền truy cập
                chat_id = event_data["chat_id"]
                if config.ALLOWED_CHAT_IDS and chat_id not in config.ALLOWED_CHAT_IDS:
                    logger.info(f"Bỏ qua tin nhắn từ chat không được phép: {chat_id}")
                    return jsonify({"code": 0, "msg": "chat not allowed"})

                # Xử lý tin nhắn bằng chatbot
                response_text = chatbot.process_message(event_data)

                if response_text:
                    # Gửi phản hồi về Lark
                    sender_id = event_data["sender"].get("sender_id", {}).get("open_id", "")

                    # Nếu là chat nhóm, gửi vào chat
                    if chat_id.startswith("oc_"):
                        lark_client.send_text(chat_id, response_text)
                    else:
                        # Chat riêng - reply vào message
                        lark_client.send_text(sender_id, response_text)

                    logger.info(f"Đã gửi phản hồi đến {sender_id}")

                return jsonify({"code": 0, "msg": "success"})

        return jsonify({"code": 0, "msg": "event processed"})

    except Exception as e:
        logger.error(f"Lỗi xử lý webhook: {e}", exc_info=True)
        return jsonify({"code": 500, "msg": str(e)}), 500


@app.route('/api/send', methods=['POST'])
def api_send_message():
    """
    API endpoint để gửi tin nhắn
    Format: POST /api/send
    Body: {"receive_id": "...", "text": "...", "type": "text|rich"}
    """
    try:
        data = request.get_json()
        receive_id = data.get("receive_id")
        text = data.get("text", "")
        msg_type = data.get("type", "text")
        title = data.get("title", "")

        if not receive_id or not text:
            return jsonify({"error": "Thiếu receive_id hoặc text"}), 400

        if msg_type == "rich":
            success = lark_client.send_rich_text(receive_id, title, text)
        else:
            success = lark_client.send_text(receive_id, text)

        if success:
            return jsonify({"success": True, "message": "Đã gửi tin nhắn"})
        else:
            return jsonify({"success": False, "error": "Gửi thất bại"}), 500

    except Exception as e:
        logger.error(f"Lỗi API send: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/remind', methods=['POST'])
def api_add_reminder():
    """
    API endpoint để thêm reminder
    Format: POST /api/remind
    Body: {"time": "14:00", "message": "...", "chat_id": "...", "user_id": "..."}
    """
    try:
        data = request.get_json()
        time_str = data.get("time")
        message = data.get("message")
        chat_id = data.get("chat_id")
        user_id = data.get("user_id")

        if not all([time_str, message, chat_id, user_id]):
            return jsonify({"error": "Thiếu tham số"}), 400

        result = workflow_engine.add_reminder(time_str, message, chat_id, user_id)
        return jsonify({"success": True, "result": result})

    except Exception as e:
        logger.error(f"Lỗi API remind: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/workflow/schedule', methods=['POST'])
def api_add_schedule():
    """
    API endpoint để thêm lịch trình tự động
    """
    try:
        data = request.get_json()
        schedule_id = data.get("id", f"sch_{len(workflow_engine.schedules)}")
        title = data.get("title", "")
        time_str = data.get("time")
        action = data.get("action", {})
        chat_id = data.get("chat_id", "")

        if not all([title, time_str, chat_id]):
            return jsonify({"error": "Thiếu tham số"}), 400

        workflow_engine.add_schedule(schedule_id, title, time_str, action, chat_id)

        return jsonify({
            "success": True,
            "schedule_id": schedule_id,
            "message": f"Đã thêm lịch trình: {title}"
        })

    except Exception as e:
        logger.error(f"Lỗi API schedule: {e}")
        return jsonify({"error": str(e)}), 500


# ============== MAIN ==============

def print_banner():
    """In banner khởi động"""
    banner = """
+================================================================+
|                                                                |
|     CHATBOT AI LARK - MIEN PHI 100%                           |
|                                                                |
|     * Gemini AI (Free Tier)                                   |
|     * Chat tu dong tren Lark                                   |
|     * Workflow tu dong hoa                                    |
|                                                                |
+================================================================+

[*] Cau hinh:
   - Bot Name: {config.BOT_NAME}
   - AI Model: {config.GEMINI_MODEL}
   - Port: {config.PORT}
   - Debug: {config.DEBUG}

[*] Endpoints:
   - Webhook: http://localhost:{config.PORT}{config.WEBHOOK_PATH}
   - Health: http://localhost:{config.PORT}/health
   - API: http://localhost:{config.PORT}/api/*

[+] Khoi dong thanh cong!
    """
    print(banner.format(config=config))


def verify_config():
    """Kiem tra cau hinh truoc khi chay"""
    errors = []

    if not config.LARK_APP_ID or not config.LARK_APP_SECRET:
        errors.append("! Chua cau hinh LARK_APP_ID va LARK_APP_SECRET")

    if not config.GEMINI_API_KEY:
        errors.append("! Chua cau hinh GEMINI_API_KEY (AI se khong hoat dong)")

    if errors:
        print("\n".join(errors))
        print("\n[*] Vui long cap nhat file .env de bot hoat dong!\n")


def main():
    """Ham main khoi chay bot"""
    print_banner()

    # Kiem tra cau hinh
    verify_config()

    # Khoi dong workflow engine
    if config.AUTO_SCHEDULE_ENABLED or config.AUTO_REMINDER_ENABLED:
        workflow_engine.start()
        logger.info("Workflow Engine da khoi dong")

    # Khoi chay Flask app
    logger.info(f"Khoi chay Flask server tai http://{config.HOST}:{config.PORT}")

    app.run(
        host=config.HOST,
        port=config.PORT,
        debug=config.DEBUG,
        threaded=True
    )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[*] Bot dang dung...")
        workflow_engine.stop()
        print("[*] Tam biet!")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Loi khong mong muon: {e}", exc_info=True)
        sys.exit(1)
