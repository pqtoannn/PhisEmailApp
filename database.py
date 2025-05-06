import sqlite3

DB_NAME = "emails.db"

def init_db():
    """Tạo database nếu chưa có"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Kiểm tra xem bảng emails đã tồn tại chưa
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='emails'")
    table_exists = cursor.fetchone()
    
    if not table_exists:
        # Tạo bảng nếu chưa tồn tại
        cursor.execute('''
            CREATE TABLE emails (
                id TEXT PRIMARY KEY,
                sender TEXT,
                subject TEXT,
                snippet TEXT,
                date TEXT,
                spam_score REAL DEFAULT 0.0,
                is_spam INTEGER DEFAULT 0
            )
        ''')
    else:
        # Kiểm tra và thêm cột spam_score và is_spam nếu chưa có
        cursor.execute("PRAGMA table_info(emails)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'spam_score' not in columns:
            cursor.execute("ALTER TABLE emails ADD COLUMN spam_score REAL DEFAULT 0.0")
        
        if 'is_spam' not in columns:
            cursor.execute("ALTER TABLE emails ADD COLUMN is_spam INTEGER DEFAULT 0")
    
    conn.commit()
    conn.close()

def save_emails_to_db(emails):
    """Lưu danh sách email vào database"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    for email in emails:
        # Thêm trường spam_score và is_spam với giá trị mặc định
        spam_score = email.get("spam_score", 0.0)
        is_spam = email.get("is_spam", 0)
        
        cursor.execute('''
            INSERT OR IGNORE INTO emails (id, sender, subject, snippet, date, spam_score, is_spam)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (email["id"], email["sender"], email["subject"], email["snippet"], email["date"], spam_score, is_spam))
    
    conn.commit()
    conn.close()

def update_spam_score(email_id, spam_score, is_spam=None):
    """Cập nhật điểm spam cho email"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Xác định is_spam dựa trên ngưỡng nếu không được chỉ định
    if is_spam is None:
        is_spam = 1 if spam_score > 0.7 else 0
    
    cursor.execute('''
        UPDATE emails SET spam_score = ?, is_spam = ? WHERE id = ?
    ''', (spam_score, is_spam, email_id))
    
    conn.commit()
    conn.close()

def mark_as_spam(email_id, is_spam=1):
    """Đánh dấu email là spam hoặc không phải spam"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE emails SET is_spam = ? WHERE id = ?
    ''', (is_spam, email_id))
    
    conn.commit()
    conn.close()

def get_emails_from_db(page, limit=20, show_spam=False):
    """Lấy email từ database với phân trang"""
    offset = (page - 1) * limit
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Lọc email theo điều kiện spam/không spam
    if show_spam:
        query = "SELECT id, sender, subject, snippet, spam_score, is_spam FROM emails WHERE is_spam = 1 ORDER BY date DESC LIMIT ? OFFSET ?"
    else:
        query = "SELECT id, sender, subject, snippet, spam_score, is_spam FROM emails WHERE is_spam = 0 ORDER BY date DESC LIMIT ? OFFSET ?"
    
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
    conn = sqlite3.connect(DB_NAME)
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
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM emails")
    conn.commit()
    conn.close()

def get_email_spam_score(email_id):
    """Lấy điểm spam của một email cụ thể"""
    conn = sqlite3.connect(DB_NAME)
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
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Xóa bảng nếu đã tồn tại
    cursor.execute("DROP TABLE IF EXISTS emails")
    
    # Tạo lại bảng với cấu trúc mới
    cursor.execute('''
        CREATE TABLE emails (
            id TEXT PRIMARY KEY,
            sender TEXT,
            subject TEXT,
            snippet TEXT,
            date TEXT,
            spam_score REAL DEFAULT 0.0,
            is_spam INTEGER DEFAULT 0
        )
    ''')
    
    conn.commit()
    conn.close()
    
    print(f"Đã xóa và tạo lại database {DB_NAME} với cấu trúc mới.")
    return True

# Khởi tạo database khi chạy chương trình
init_db()
