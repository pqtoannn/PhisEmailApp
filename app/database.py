import sqlite3
import os

# Đường dẫn database cần được sửa để luôn tìm thấy đúng file
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "database.db")
# Đường dẫn dự phòng nếu không tìm thấy file trong thư mục app
if not os.path.exists(DB_PATH):
    # Thử tìm trong thư mục gốc
    DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "emails.db")
    if not os.path.exists(DB_PATH) and not os.path.exists(os.path.dirname(DB_PATH)):
        # Nếu không tìm thấy, sử dụng đường dẫn mặc định
        DB_PATH = "emails.db"

print(f"Sử dụng database: {DB_PATH}")

# Hàm helper để tạo kết nối đến database
def get_db_connection():
    """Tạo và trả về kết nối đến database"""
    conn = sqlite3.connect(DB_PATH)
    return conn

def init_db():
    """Tạo database nếu chưa có"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Kiểm tra xem bảng emails đã tồn tại chưa
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='emails'")
    table_exists = cursor.fetchone()
    
    if not table_exists:
        # Tạo bảng nếu chưa tồn tại
        cursor.execute('''
            CREATE TABLE emails (
                id TEXT PRIMARY KEY,
                thread_id TEXT,
                subject TEXT,
                snippet TEXT,
                from_address TEXT,
                to_address TEXT,
                date TEXT,
                body TEXT,
                is_read INTEGER DEFAULT 0,
                spam_score REAL DEFAULT 0.0,
                is_spam INTEGER DEFAULT 0,
                is_deleted INTEGER DEFAULT 0
            )
        ''')
        print(f"Đã tạo bảng emails trong database {DB_PATH}")
    else:
        # Kiểm tra và thêm cột spam_score và is_spam nếu chưa có
        cursor.execute("PRAGMA table_info(emails)")
        columns = [col[1] for col in cursor.fetchall()]
        
        required_columns = {
            'thread_id': 'TEXT',
            'subject': 'TEXT',
            'snippet': 'TEXT',
            'from_address': 'TEXT',
            'to_address': 'TEXT',
            'date': 'TEXT',
            'body': 'TEXT',
            'is_read': 'INTEGER DEFAULT 0',
            'spam_score': 'REAL DEFAULT 0.0',
            'is_spam': 'INTEGER DEFAULT 0',
            'is_deleted': 'INTEGER DEFAULT 0'
        }
        
        for col_name, col_type in required_columns.items():
            if col_name not in columns:
                cursor.execute(f"ALTER TABLE emails ADD COLUMN {col_name} {col_type}")
                print(f"Đã thêm cột {col_name} vào bảng emails")
    
    conn.commit()
    conn.close()
    print("Khởi tạo database hoàn tất")

def save_emails_to_db(emails):
    """Lưu danh sách email vào database"""
    if not emails:
        return
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    for email in emails:
        # Thêm trường spam_score và is_spam với giá trị mặc định
        spam_score = email.get("spam_score", 0.0)
        is_spam = email.get("is_spam", 0)
        
        cursor.execute('''
            INSERT OR IGNORE INTO emails 
            (id, thread_id, subject, snippet, from_address, to_address, date, body, is_read, spam_score, is_spam, is_deleted)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (email["id"], 
              email.get("threadId", ""), 
              email.get("subject", ""), 
              email.get("snippet", ""), 
              email.get("sender", ""),
              email.get("to", ""), 
              email.get("date", ""),
              email.get("body", ""),
              0,  # is_read
              spam_score, 
              is_spam,
              0   # is_deleted
            ))
    
    conn.commit()
    conn.close()

def update_spam_score(email_id, spam_score, is_spam=None):
    """Cập nhật điểm spam cho email"""
    if not email_id:
        return
        
    # Xác định is_spam dựa trên ngưỡng nếu không được chỉ định
    if is_spam is None:
        is_spam = 1 if spam_score > 0.7 else 0
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE emails SET spam_score = ?, is_spam = ? WHERE id = ?
    ''', (spam_score, is_spam, email_id))
    
    conn.commit()
    conn.close()

def mark_as_spam(email_id, is_spam=1):
    """Đánh dấu email là spam hoặc không phải spam"""
    if not email_id:
        return
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE emails SET is_spam = ? WHERE id = ?
    ''', (is_spam, email_id))
    
    conn.commit()
    conn.close()

def get_emails_from_db(page, limit=20, show_spam=False, show_trash=False):
    if page < 1:
        page = 1
    if limit < 1:
        limit = 20

    offset = (page - 1) * limit
    conn = get_db_connection()
    cursor = conn.cursor()

    if show_trash:
        query = "SELECT id, from_address, subject, snippet, spam_score, is_spam FROM emails WHERE is_deleted = 1 ORDER BY date DESC LIMIT ? OFFSET ?"
    elif show_spam:
        query = "SELECT id, from_address, subject, snippet, spam_score, is_spam FROM emails WHERE is_spam = 1 AND (is_deleted IS NULL OR is_deleted = 0) ORDER BY date DESC LIMIT ? OFFSET ?"
    else:
        query = "SELECT id, from_address, subject, snippet, spam_score, is_spam FROM emails WHERE is_spam = 0 AND (is_deleted IS NULL OR is_deleted = 0) ORDER BY date DESC LIMIT ? OFFSET ?"

    cursor.execute(query, (limit, offset))
    emails = cursor.fetchall()
    conn.close()

    return [{
        "id": row[0],
        "sender": row[1],
        "subject": row[2],
        "snippet": row[3],
        "spam_score": row[4],
        "is_spam": row[5]
    } for row in emails]


def get_total_emails_count(show_spam=False):
    """Đếm số lượng email có trong database"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if show_spam:
        cursor.execute("SELECT COUNT(*) FROM emails WHERE is_spam = 1")
    else:
        cursor.execute("SELECT COUNT(*) FROM emails WHERE is_spam = 0")
        
    total_emails = cursor.fetchone()[0]
    conn.close()
    return total_emails

def clear_database():
    """Xóa toàn bộ email khi đăng xuất"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM emails")
    conn.commit()
    conn.close()

def get_email_spam_score(email_id):
    """Lấy điểm spam của một email cụ thể"""
    if not email_id:
        return 0.0
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT spam_score FROM emails WHERE id = ?", (email_id,))
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return result[0]
    else:
        return 0.0

def recreate_database():
    """Xóa và tạo lại database"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Xóa bảng nếu đã tồn tại
    cursor.execute("DROP TABLE IF EXISTS emails")
    
    # Tạo lại bảng với cấu trúc mới
    cursor.execute('''
        CREATE TABLE emails (
            id TEXT PRIMARY KEY,
            thread_id TEXT,
            subject TEXT,
            snippet TEXT,
            from_address TEXT,
            to_address TEXT,
            date TEXT,
            body TEXT,
            is_read INTEGER DEFAULT 0,
            spam_score REAL DEFAULT 0.0,
            is_spam INTEGER DEFAULT 0,
            is_deleted INTEGER DEFAULT 0
        )
    ''')
    
    conn.commit()
    conn.close()
    
    print(f"Đã xóa và tạo lại database {DB_PATH} với cấu trúc mới.")
    return True

# Khởi tạo database khi chạy chương trình
init_db()
    
def mark_as_deleted(email_id):
    """Đánh dấu email là đã xóa (is_deleted=1)"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        UPDATE emails
        SET is_deleted = 1
        WHERE id = ?
    ''', (email_id,))

    conn.commit()
    conn.close()

def mark_as_restored(email_id):
    """Đánh dấu email là chưa xóa (is_deleted=0)"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        UPDATE emails
        SET is_deleted = 0
        WHERE id = ?
    ''', (email_id,))

    conn.commit()
    conn.close()

def search_emails_in_db(keyword, target='inbox'):
    """Tìm kiếm email theo tiêu đề, người gửi, nội dung - phân theo mục"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Truy vấn tất cả theo tab đang chọn
    base_query = """
        SELECT id, from_address, subject, snippet, spam_score, is_spam, is_deleted
        FROM emails
        ORDER BY date DESC
    """
    cursor.execute(base_query)
    emails = cursor.fetchall()
    conn.close()

    # Tiền xử lý
    keyword_lower = keyword.lower()
    result = []

    for row in emails:
        email_id, sender, subject, snippet, spam_score, is_spam, is_deleted = row
        sender = sender or ""
        subject = subject or ""
        snippet = snippet or ""

        if (keyword_lower in sender.lower() or
            keyword_lower in subject.lower() or
            keyword_lower in snippet.lower()):

            if target == 'inbox' and is_spam == 0 and is_deleted == 0:
                result.append({
                    "id": email_id,
                    "sender": sender,
                    "subject": subject,
                    "snippet": snippet,
                    "spam_score": spam_score,
                    "is_spam": is_spam
                })
            elif target == 'spam' and is_spam == 1 and is_deleted == 0:
                result.append({
                    "id": email_id,
                    "sender": sender,
                    "subject": subject,
                    "snippet": snippet,
                    "spam_score": spam_score,
                    "is_spam": is_spam
                })
            elif target == 'trash' and is_deleted == 1:
                result.append({
                    "id": email_id,
                    "sender": sender,
                    "subject": subject,
                    "snippet": snippet,
                    "spam_score": spam_score,
                    "is_spam": is_spam
                })

    return result

def clear_all_emails():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM emails")
    conn.commit()
    cursor.execute("VACUUM")  # 🔥 Dọn rác vật lý, thu gọn file
    conn.commit()
    conn.close()









