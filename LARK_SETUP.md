# ============================================
# HƯỚNG DẪN KẾT NỐI LARK
# ============================================

## PHƯƠNG ÁN 1: DÙNG NGROK (Test nhanh - Cần authtoken miễn phí)

### Bước 1: Lấy Ngrok Authtoken (miễn phí)

1. Truy cập: https://dashboard.ngrok.com/signup
2. Đăng ký tài khoản (dùng email)
3. Copy authtoken từ: https://dashboard.ngrok.com/get-started/your-authtoken

### Bước 2: Cấu hình Ngrok

```bash
ngrok config add-authtoken YOUR_AUTHTOKEN
```

### Bước 3: Chạy Ngrok

```bash
ngrok http 5000
```

### Bước 4: Copy URL từ Ngrok

Sau khi chạy, bạn sẽ thấy:
```
Forwarding  https://abc123.ngrok.io -> http://localhost:5000
```

Copy URL đó (ví dụ: `https://abc123.ngrok.io`)

---

## PHƯƠNG ÁN 2: DEPLOY LÊN RAILWAY (Permanent - Miễn phí)

### Bước 1: Push code lên GitHub

1. Tạo repository mới trên GitHub
2. Push code lên:

```bash
git init
git add .
git commit -m "Chatbot AI Lark"
git remote add origin https://github.com/YOUR_USERNAME/chatbot-lark.git
git push -u origin main
```

### Bước 2: Deploy lên Railway

1. Truy cập: https://railway.app
2. Đăng nhập với GitHub
3. Click "New Project" -> "Deploy from GitHub repo"
4. Chọn repository `chatbot-lark`
5. Thêm Environment Variables:
   - `LARK_APP_ID` = cli_xxx
   - `LARK_APP_SECRET` = xxx
   - `GEMINI_API_KEY` = AIza_xxx
6. Railway sẽ tự động deploy!

### Bước 3: Lấy Public URL

Sau khi deploy thành công, Railway sẽ cấp URL:
```
https://chatbot-lark.up.railway.app
```

---

## CẤU HÌNH WEBHOOK TRÊN LARK

Sau khi có URL (từ Ngrok hoặc Railway):

### Bước 1: Thêm quyền

1. Vào: https://open.feishu.cn/app
2. Chọn app của bạn
3. Vào "Quyền và phạm vi truy cập"
4. Thêm quyền:
   - `im:message:send_as_bot`
   - `im:message:receive_v1`
   - `im:chat`

### Bước 2: Cấu hình Event Subscription

1. Vào "Cấu hình sự kiện"
2. Bật "Subscribe to events from this app"
3. Trong "Request URL" nhập:
   ```
   https://YOUR_URL/webhook/lark
   ```
   Ví dụ: `https://abc123.ngrok.io/webhook/lark`
4. Click "Add Events" -> Thêm `im.message.receive_v1`
5. Save

### Bước 3: Cấu hình Message Subscription

1. Vào "Gửi tin nhắn"
2. Bật tính năng
3. Điền URL callback:
   ```
   https://YOUR_URL/webhook/lark
   ```

### Bước 4: Publish App

1. Vào "Cài đặt phiên bản"
2. Tạo phiên bản mới
3. Gửi yêu cầu kiểm duyệt (hoặc dùng test mode)

---

## TEST BOT

1. Mở Lark, thêm bot vào nhóm/chat
2. Gửi tin nhắn: `Xin chào!`
3. Bot sẽ trả lời bằng AI

---

## CÁC LỆNH BOT

| Lệnh | Mô tả |
|------|-------|
| `/help` | Xem hướng dẫn |
| `/ask [câu hỏi]` | Hỏi AI |
| `/summarize [text]` | Tóm tắt |
| `/translate [ngôn ngữ] [text]` | Dịch thuật |
| `/ideas [chủ đề]` | Tạo ý tưởng |
| `/remind [giờ] [nội dung]` | Đặt nhắc nhở |
| `/stats` | Thống kê |
| `/report` | Báo cáo |
| `/clear` | Xóa lịch sử chat |

---

## KHẮC PHỤC LỖI

### Lỗi: "Webhook not working"
- Kiểm tra URL đúng chưa (phải có /webhook/lark)
- Kiểm tra bot đã được thêm vào nhóm chưa
- Kiểm tra logs tại logs/chatbot.log

### Lỗi: "Bot không reply"
- Kiểm tra AI key đúng chưa
- Kiểm tra bot có quyền gửi tin nhắn không

### Lỗi: "Token error"
- Kiểm tra LARK_APP_ID và LARK_APP_SECRET
- Kiểm tra app đã được enable chưa
