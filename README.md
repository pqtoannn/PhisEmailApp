# 📧 PhisEmailApp – Ứng dụng Gmail Desktop phát hiện Email Lừa đảo

Ứng dụng desktop tích hợp AI giúp phát hiện email lừa đảo/spam, được phát triển bằng Python, PyQt6 và Gmail API. Giao diện thân thiện, phân loại thư rác tự động, hỗ trợ người dùng quản lý email an toàn và hiệu quả.

---

## 📂 External Resources

Do GitHub giới hạn kích thước tệp, các tài nguyên lớn như mô hình AI, tập dữ liệu đã được đưa lên Google Drive.

📁 Tải xuống models, dữ liệu và tài nguyên cần thiết tại:  
👉 [Google Drive Folder](https://drive.google.com/drive/folders/1ppJQCwVjqp30vEEyhFZiT18tp6SEzEKg?usp=sharing)

---

## 🗂️ Cấu trúc thư mục

```
PhisEmailApp/
├── app/                 # Mã nguồn chính
│   ├── authenticate.py     # Xác thực với Gmail API
│   ├── database.py         # Quản lý cơ sở dữ liệu SQLite
│   ├── email_details.py    # Giao diện xem chi tiết email
│   ├── email_manager.py    # Giao diện quản lý email
│   ├── fetch_emails.py     # Lấy email từ Gmail API
│   ├── login_window.py     # Giao diện đăng nhập
│   ├── send_email.py       # Gửi email mới
│   └── spam_detector.py    # Phát hiện spam bằng AI
├── main.py              # Điểm khởi chạy ứng dụng
├── requirements.txt     # Thư viện cần thiết
```

---

## ⚙️ Cài đặt và chạy ứng dụng

### 1. Tạo môi trường ảo (khuyến nghị)

```bash
python -m venv .venv
source .venv/bin/activate        # Trên macOS/Linux
.venv\Scripts\activate         # Trên Windows
```

### 2. Cài đặt thư viện

```bash
pip install -r requirements.txt
```

### 3. Thiết lập OAuth2 (nếu chưa có)

1. Truy cập [Google Cloud Console](https://console.cloud.google.com/)
2. Tạo project mới
3. Bật Gmail API
4. Tạo OAuth Client ID
5. Tải file `credentials.json` về và đặt vào thư mục gốc

---

## 🚀 Chạy ứng dụng

```bash
python main.py
```

---

## ✨ Các tính năng nổi bật

- 🔐 **Đăng nhập Gmail** bằng OAuth2
- 📩 **Xem danh sách email** với phân trang trực quan
- ⚠️ **Phân tích AI** phát hiện lừa đảo (hiển thị % spam)
- 🧠 **Tự động phân loại thư rác** nếu điểm spam > 70%
- 📨 **Gửi email mới** kèm file đính kèm
- 📑 **Xem chi tiết nội dung email**
- 🖱️ **Menu chuột phải** để đánh dấu email là spam thủ công

---

## 🛡️ Spam Detection Logic

- Mỗi email khi được tải về sẽ tự động được phân tích bởi mô hình AI
- Mức độ spam hiển thị bằng màu và phần trăm như: `-92%`
- Các email nguy hiểm được di chuyển đến thư mục Spam
- Người dùng có thể tự đánh dấu email thủ công bằng chuột phải

---

> 👨‍💻 *Dự án được phát triển trong khuôn khổ môn học và có thể mở rộng cho các ứng dụng doanh nghiệp hoặc cá nhân.*
