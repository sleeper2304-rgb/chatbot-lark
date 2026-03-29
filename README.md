# ============================================
# CHATBOT AI LARK - MIỄN PHÍ 100%
# ============================================
# Tích hợp Lark (Feishu) + Gemini AI + Workflow
# Tác giả: Chatbot Lark Team
# License: MIT - Miễn phí sử dụng và phát triển
# ============================================

# ============================================
# 📋 MỤC LỤC
# ============================================
# 1. Giới thiệu
# 2. Tính năng
# 3. Cài đặt
# 4. Cấu hình
# 5. Chạy bot
# 6. Sử dụng
# 7. API Endpoints
# 8. Troubleshooting

# ============================================
# 1. GIỚI THIỆU
# ============================================

Chatbot AI Lark là một bot thông minh, hoàn toàn MIỄN PHÍ,
tích hợp giữa nền tảng nhắn tin Lark (Feishu) với AI Gemini.

Điểm đặc biệt:
- 100% Miễn phí - Không tốn chi phí API
- AI thông minh - Gemini 2.0 Flash (free tier)
- Tự động hóa - Workflow, nhắc nhở, báo cáo
- Dễ cài đặt - Cấu hình đơn giản

# ============================================
# 2. TÍNH NĂNG
# ============================================

## 🤖 Tính năng 1: Chatbot trả lời tự động
- Trả lời tin nhắn thông minh bằng AI
- Hỗ trợ đa ngôn ngữ (Việt, Anh, Trung...)
- Các lệnh đặc biệt: /ask, /help, /ideas, /translate...

## ⚡ Tính năng 2: AI thông minh (Gemini - Miễn phí!)
- Tích hợp Google Gemini 2.0 Flash (FREE)
- 15 requests/phút, 1500 requests/ngày - Đủ dùng!
- Hỗ trợ: chat, summarize, translate, code review...

## 🔄 Tính năng 3: Workflow tự động hóa
- Báo cáo tự động hàng ngày/tuần
- Nhắc nhở theo lịch
- Tự động tạo task
- Tùy chỉnh workflow riêng

# ============================================
# 3. CÀI ĐẶT
# ============================================

## Yêu cầu:
- Python 3.9+
- pip

## Các bước cài đặt:

```bash
# 1. Clone hoặc tải project

# 2. Tạo virtual environment (khuyến nghị)
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# 3. Cài đặt thư viện
pip install -r requirements.txt

# 4. Copy và cấu hình .env
copy .env.example .env
# Sau đó chỉnh sửa .env với thông tin của bạn
```

# ============================================
# 4. CẤU HÌNH
# ============================================

## 4.1 LARK APP (Feishu)

1. Truy cập: https://open.feishu.cn/app
2. Tạo App mới
3. Lấy App ID và App Secret từ Credentials
4. Bật các quyền:
   - im:message (Gửi/nhận tin nhắn)
   - im:chat (Quản lý chat)
   - task (Tạo task)
5. Cấu hình Event Subscription:
   - Request URL: https://your-domain.com/webhook/lark
   - Subscribe to: im.message.receive_v1
6. Cấu hình Message Subscription:
   - Enable URL verification
   - Encrypt (optional)

## 4.2 GEMINI AI (Miễn phí!)

1. Truy cập: https://makersuite.google.com/app/apikey
2. Đăng nhập Google account
3. Tạo API Key mới
4. Copy và paste vào .env

## 4.3 File .env

```env
# Lark credentials
LARK_APP_ID=cli_xxxxx
LARK_APP_SECRET=xxxxx

# Gemini AI (FREE!)
GEMINI_API_KEY=AIza_xxxxx
GEMINI_MODEL=gemini-2.0-flash

# Bot settings
BOT_NAME=AI Assistant
PORT=5000
```

# ============================================
# 5. CHẠY BOT
# ============================================

## Development (local):
```bash
python main.py
```

## Production:
```bash
# Sử dụng gunicorn
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 main:app

# Hoặc sử dụng Docker
docker build -t chatbot-lark .
docker run -p 5000:5000 --env-file .env chatbot-lark
```

## Deploy lên Cloud miễn phí:

### Railway (Recommended - Free tier tốt):
1. GitHub repo -> Connect to Railway
2. Add .env variables
3. Deploy!

### Render:
1. Create Web Service
2. Connect GitHub repo
3. Set start command: `gunicorn main:app`
4. Add environment variables

### Heroku:
```bash
heroku create chatbot-lark
heroku config:set LARK_APP_ID=xxx
heroku config:set LARK_APP_SECRET=xxx
heroku config:set GEMINI_API_KEY=xxx
git push heroku main
```

# ============================================
# 6. SỬ DỤNG
# ============================================

## Cách sử dụng cơ bản:

### Trò chuyện với AI:
```
User: Xin chào!
Bot: Xin chào! Mình là AI Assistant...

User: Giải thích về machine learning
Bot: Machine learning là...
```

### Các lệnh đặc biệt:

| Lệnh | Mô tả | Ví dụ |
|------|-------|-------|
| /help | Xem help | /help |
| /ask [câu hỏi] | Hỏi AI | /ask Tại sao trời xanh? |
| /summarize [text] | Tóm tắt | /summarize [reply tin nhắn] |
| /translate [lang] [text] | Dịch thuật | /translate English xin chào |
| /ideas [topic] | Tạo ý tưởng | /ideas 5 ý tưởng marketing |
| /remind [time] [msg] | Nhắc nhở | /remind 14:00 Họp team |
| /stats | Xem thống kê | /stats |
| /report | Báo cáo nhanh | /report |
| /clear | Xóa lịch sử chat | /clear |

## Workflow tự động:

Bot tự động:
- Gửi báo cáo ngày lúc 09:00
- Gửi báo cáo tuần vào thứ 2
- Nhắc nhở khi có reminder

# ============================================
# 7. API ENDPOINTS
# ============================================

Bot cung cấp REST API:

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| GET | / | Thông tin bot |
| GET | /health | Health check |
| GET | /stats | Thống kê |
| POST | /webhook/lark | Webhook Lark |
| POST | /api/send | Gửi tin nhắn |
| POST | /api/remind | Thêm reminder |
| POST | /api/workflow/schedule | Thêm lịch trình |

### Ví dụ gọi API:

```bash
# Gửi tin nhắn
curl -X POST http://localhost:5000/api/send \
  -H "Content-Type: application/json" \
  -d '{"receive_id": "oc_xxx", "text": "Hello!", "type": "text"}'

# Thêm reminder
curl -X POST http://localhost:5000/api/remind \
  -H "Content-Type: application/json" \
  -d '{"time": "14:00", "message": "Họp team", "chat_id": "oc_xxx", "user_id": "ou_xxx"}'
```

# ============================================
# 8. TROUBLESHOOTING
# ============================================

## Lỗi thường gặp:

### 1. "Gemini API not configured"
→ Thêm GEMINI_API_KEY vào .env

### 2. "Lark token error"
→ Kiểm tra LARK_APP_ID và LARK_APP_SECRET

### 3. "Webhook not working"
→ Kiểm tra:
   - URL webhook phải public (dùng ngrok để test local)
   - Event subscription đã được enable
   - Challenge verification passed

### 4. "Bot không reply"
→ Kiểm tra:
   - Bot đã được thêm vào group?
   - Chat ID có trong ALLOWED_CHAT_IDS?
   - Log file để xem lỗi chi tiết

## Debug local:

```bash
# Chạy với debug mode
DEBUG=True python main.py

# Xem log
tail -f logs/chatbot.log

# Test webhook với ngrok
ngrok http 5000
# Copy URL ngrok vào Lark webhook config
```

# ============================================
# 📞 HỖ TRỢ
# ============================================

- Issue: GitHub Issues
- Email: support@chatbotlark.dev

# ============================================
# 📄 LICENSE
# ============================================

MIT License - Miễn phí sử dụng cho mục đích cá nhân và thương mại

---

Made with ❤️ - Chatbot AI Lark Team
