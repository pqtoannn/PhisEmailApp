from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from app.database import save_emails_to_db, get_total_emails_count, update_spam_score, DB_PATH
import base64
import os
import json
import importlib.util
import sqlite3

SCOPES = ["https://mail.google.com/"]


def get_gmail_service():
    """ Kết nối đến Gmail API """
    creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    service = build("gmail", "v1", credentials=creds)
    return service

def refresh_emails_safely(max_results=50):
    """Refresh để lấy email mới nhất từ trên xuống, dừng khi gặp email đã có"""
    service = get_gmail_service()

    results = service.users().messages().list(
        userId="me",
        maxResults=max_results
    ).execute()

    messages = results.get("messages", [])
    if not messages:
        print("📭 Không tìm thấy email mới.")
        return 0

    # Lấy danh sách id hiện có
    existing_ids = set()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM emails")
    existing_ids.update(row[0] for row in cursor.fetchall())
    conn.close()

    added_count = 0
    for msg_meta in messages:
        email_id = msg_meta["id"]

        if email_id in existing_ids:
            print(f"⛔ Gặp email đã có ({email_id}), dừng lại.")
            break

        msg = service.users().messages().get(userId="me", id=email_id, format="full").execute()
        email_info = extract_email_info(msg)
        store_email_in_database(email_info)
        added_count += 1

    print(f"✅ Đã thêm {added_count} email mới.")
    return added_count

def extract_email_info(email_data):
    """Trích xuất thông tin cần thiết từ email data của Gmail API"""
    email_info = {
        "id": email_data.get("id", ""),
        "threadId": email_data.get("threadId", "")
    }
    
    # Trích xuất headers
    headers = email_data.get("payload", {}).get("headers", [])
    for header in headers:
        name = header.get("name", "").lower()
        value = header.get("value", "")
        
        if name == "from":
            email_info["from"] = value
        elif name == "to":
            email_info["to"] = value
        elif name == "subject":
            email_info["subject"] = value
        elif name == "date":
            email_info["date"] = value
    
    # Lấy snippet
    email_info["snippet"] = email_data.get("snippet", "")
    
    # Trích xuất nội dung
    body = ""
    try:
        payload = email_data.get("payload", {})
        if "body" in payload and "data" in payload["body"]:
            body = base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8")
        elif "parts" in payload:
            for part in payload["parts"]:
                if part.get("mimeType") == "text/plain" and "body" in part and "data" in part["body"]:
                    body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8")
                    break
    except Exception as e:
        print(f"Lỗi khi giải mã nội dung email: {e}")
    
    email_info["body"] = body
    
    # Đảm bảo các trường cơ bản tồn tại
    if "from" not in email_info:
        email_info["from"] = "Unknown"
    if "subject" not in email_info:
        email_info["subject"] = "No Subject"
    if "to" not in email_info:
        email_info["to"] = ""
    if "date" not in email_info:
        email_info["date"] = ""
    
    return email_info


def store_email_in_database(email_info, database_path=DB_PATH):
    """Lưu thông tin email vào cơ sở dữ liệu"""
    if not email_info:
        print("Không có thông tin email để lưu")
        return
    
    # Tạo đối tượng kết nối
    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()
    
    # Kiểm tra xem email đã tồn tại chưa
    cursor.execute("SELECT id FROM emails WHERE id = ?", (email_info["id"],))
    existing_email = cursor.fetchone()
    
    if existing_email:
        print(f"Email {email_info['id']} đã tồn tại trong cơ sở dữ liệu")
        conn.close()
        return
    
    # Chuẩn bị dữ liệu để lưu trữ
    email_id = email_info["id"]
    thread_id = email_info.get("threadId", "")
    subject = email_info.get("subject", "Không có tiêu đề")
    snippet = email_info.get("snippet", "")
    sender = email_info.get("from", "")
    receiver = email_info.get("to", "")
    date = email_info.get("date", "")
    
    # Phân tích email để tìm dấu hiệu lừa đảo
    spam_score = analyze_email_for_spam(email_info, email_id)
    is_spam = 1 if spam_score > 0.7 else 0
    
    # Lưu thông tin email vào bảng emails
    try:
        cursor.execute(
            """
            INSERT INTO emails (id, thread_id, subject, snippet, from_address, to_address, date, body, is_read, spam_score, is_spam, is_deleted)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (email_id, thread_id, subject, snippet, sender, receiver, date,
             email_info.get("body", ""), 0, spam_score, is_spam, 0)
        )
        conn.commit()
        print(f"Đã lưu email {email_id} vào cơ sở dữ liệu")
    except sqlite3.Error as e:
        print(f"Lỗi khi lưu email: {e}")
    finally:
        conn.close()

def analyze_email_for_spam(email_content, email_id, database_path=DB_PATH):
    """Phân tích nội dung email để phát hiện lừa đảo"""
    print(f"Phân tích email ID: {email_id} để tìm dấu hiệu lừa đảo...")
    
    try:
        from app.spam_detector import SpamDetector
        
        # Tải detector với đường dẫn đầy đủ
        detector = SpamDetector()
        
        # Kết hợp tiêu đề và nội dung để phân tích
        if email_content and isinstance(email_content, dict):
            subject = email_content.get('subject', '')
            body = email_content.get('body', '')
            sender = email_content.get('from', '')
            
            # Kết hợp thông tin để phân tích
            combined_text = f"From: {sender}\nSubject: {subject}\n\n{body}"
            
            # Phân tích spam
            spam_result = detector.predict(combined_text)

            # Nếu predict trả về tuple (score, keywords), lấy phần đầu
            if isinstance(spam_result, tuple):
                spam_score = spam_result[0]
            else:
                spam_score = spam_result

            print(f"Email ID {email_id}: Điểm lừa đảo = {spam_score:.2f}")

            
            # Cập nhật cơ sở dữ liệu
            conn = sqlite3.connect(database_path)
            cursor = conn.cursor()
            
            # Đánh dấu là spam nếu điểm > 0.7
            is_spam = 1 if spam_score > 0.7 else 0
            
            # Lưu điểm spam và trạng thái vào cơ sở dữ liệu
            cursor.execute(
                "UPDATE emails SET spam_score = ?, is_spam = ? WHERE id = ?",
                (spam_score, is_spam, email_id)
            )
            conn.commit()
            conn.close()
            
            return spam_score
        else:
            print(f"[ERROR] Email ID {email_id}: Không thể phân tích - không có nội dung email")
            return 0.0
    except Exception as e:
        import traceback
        print(f"[ERROR] Lỗi khi phân tích email ID {email_id}: {str(e)}")
        traceback.print_exc()
        return 0.0
    


def get_latest_emails(max_results=20):
    """Lấy thêm email mới từ Gmail API, sử dụng pageToken để phân trang"""
    from googleapiclient.errors import HttpError

    service = get_gmail_service()

    page_token = None
    token_path = "last_token.json"
    if os.path.exists(token_path):
        try:
            with open(token_path, "r") as f:
                token_data = json.load(f)
                page_token = token_data.get("nextPageToken")
        except Exception as e:
            print(f"[WARN] Không thể đọc token cũ: {e}")
            page_token = None

    try:
        if page_token:
            print(f"📨 Đang lấy email từ pageToken: {page_token}")
            results = service.users().messages().list(
                userId="me",
                maxResults=max_results,
                pageToken=page_token
            ).execute()
        else:
            print("📨 Không có pageToken, bắt đầu từ đầu...")
            results = service.users().messages().list(
                userId="me",
                maxResults=max_results
            ).execute()

    except HttpError as e:
        print("⚠️ Token cũ có thể không hợp lệ, bắt đầu lại từ đầu.")
        results = service.users().messages().list(
            userId="me",
            maxResults=max_results
        ).execute()

    messages = results.get("messages", [])
    next_token = results.get("nextPageToken")

    if not messages:
        print("📭 Không tìm thấy email mới.")
        return 0

    # Lưu hoặc xoá token mới
    if next_token:
        with open(token_path, "w") as f:
            json.dump({"nextPageToken": next_token}, f)
    else:
        if os.path.exists(token_path):
            os.remove(token_path)
        print("📭 Đã lấy hết email – không còn token tiếp theo.")

    print(f"📥 Đã tìm thấy {len(messages)} email mới.")

    count_added = 0
    for message in messages:
        email_id = message["id"]

        # Kiểm tra trùng
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM emails WHERE id = ?", (email_id,))
        if cursor.fetchone():
            print(f"⛔ Email {email_id} đã có, bỏ qua.")
            conn.close()
            continue
        conn.close()

        # Lấy chi tiết và lưu
        msg = service.users().messages().get(userId="me", id=email_id, format="full").execute()
        email_info = extract_email_info(msg)
        store_email_in_database(email_info)
        count_added += 1

    print(f"✅ Đã thêm {count_added} email mới vào database.")
    return count_added


def get_email_content(email_id):
    """ Lấy nội dung chi tiết của email và giải mã Base64 """
    # Kiểm tra nếu là email mẫu
    if email_id.startswith("spam-test"):
        # Trả về nội dung cứng cho email mẫu
        spam_emails_content = {
            "spam-test-1": {
                "subject": "URGENT: $5,000,000 inheritance waiting for you",
                "sender": "Nigerian Prince <prince@nigeria.com>",
                "body": """Dear Sir/Madam,
                
I am Prince Alyusi Islassis, the only son of the late King of Nigeria. I am writing to you because I need your urgent assistance in transferring the sum of $5,000,000 USD from Nigeria to your country.

Due to certain political circumstances and government restrictions on my family's assets, I cannot transfer these funds directly. I am seeking a foreign partner who can help me transfer this money out of Nigeria.

For your assistance, I am prepared to offer you 30% of the total funds. To proceed, I will need:
1. Your full name
2. Your bank account details
3. A small administrative fee of $1,000 to cover transfer costs

Please reply urgently as this matter is very sensitive and confidential.

Yours faithfully,
Prince Alyusi Islassis
"""
            },
            "spam-test-2": {
                "subject": "Your account has been BLOCKED - Verify NOW",
                "sender": "Bank Security <security@bank-verificati0n.com>",
                "body": """URGENT SECURITY NOTICE
                
Your bank account has been temporarily BLOCKED due to suspicious activity.

We have detected multiple unauthorized login attempts to your account from different locations. To protect your funds, we have temporarily restricted access to your account.

To verify your identity and restore access immediately, please click on the link below:

[SECURE VERIFICATION LINK]

You must complete this verification within 24 hours, or your account will be permanently suspended and your funds may be seized.

Bank Security Team
"""
            },
            "spam-test-3": {
                "subject": "CONGRATULATIONS! You've WON $10,000,000!",
                "sender": "Lottery Winner <claim@megamillions-winner.org>",
                "body": """CONGRATULATIONS!!!
                
Your email address has been randomly selected as the winner of our $10,000,000 USD International Lottery!

Your email was chosen from over 250 million email addresses worldwide. This is not a joke or scam - you have actually won!

To claim your prize, you need to:

1. Send us your full name, address, and phone number
2. Provide a copy of your ID/passport
3. Pay a small processing fee of $500 USD to cover transfer taxes

Please note that this offer is valid for 5 days only. Respond immediately to claim your millions!

Best regards,
International Lottery Commission
"""
            }
        }
        
        if email_id in spam_emails_content:
            return spam_emails_content[email_id]
        else:
            return {
                "subject": "Unknown Sample Email",
                "sender": "Unknown Sender",
                "body": "This is a sample email content."
            }

    # Nếu không phải email mẫu, lấy từ Gmail API
    service = get_gmail_service()
    email_data = service.users().messages().get(userId="me", id=email_id, format="full").execute()

    email_info = {
        "subject": "No Subject",
        "sender": "Unknown Sender",
        "body": "Không có nội dung",
    }
    attachments = []

    def find_attachments(parts_list):
        """Đệ quy tìm file đính kèm trong các parts"""
        for part in parts_list:
            filename = part.get("filename")
            body = part.get("body", {})
            mime_type = part.get("mimeType", "")

            if filename and "attachmentId" in body:
                attachments.append({
                    "filename": filename,
                    "attachmentId": body["attachmentId"]
                })

            if "parts" in part:
                find_attachments(part["parts"])


    # Lấy tiêu đề và người gửi
    for header in email_data["payload"]["headers"]:
        if header["name"] == "Subject":
            email_info["subject"] = header["value"]
        if header["name"] == "From":
            email_info["sender"] = header["value"]

    # Lấy nội dung email (dạng Base64)
    if "parts" in email_data["payload"]:
        parts = email_data["payload"]["parts"]
        find_attachments(parts)

        for part in parts:
            if part["mimeType"] == "text/plain" and "body" in part:
                body_data = part["body"].get("data")
                if body_data:
                    decoded_body = base64.urlsafe_b64decode(body_data).decode("utf-8")
                    email_info["body"] = decoded_body

    email_info["attachments"] = attachments
    return email_info

def download_attachment(email_id, attachment_id, filename, save_path="attachments"):
    """ Tải file đính kèm từ email """
    service = get_gmail_service()

    # Lấy dữ liệu file đính kèm
    attachment = service.users().messages().attachments().get(
        userId="me", messageId=email_id, id=attachment_id
    ).execute()

    # Giải mã nội dung file
    file_data = base64.urlsafe_b64decode(attachment["data"])

    # Tạo thư mục lưu file nếu chưa có
    if not os.path.exists(save_path):
        os.makedirs(save_path)

    file_path = os.path.join(save_path, filename)
    with open(file_path, "wb") as f:
        f.write(file_data)

    return file_path




