from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QTextEdit
from PyQt6.QtCore import Qt
from app.fetch_emails import get_email_content
from app.spam_detector import SpamDetector
import re

class SpamDetailsWindow(QWidget):
    def __init__(self, email_id):
        super().__init__()
        self.setWindowTitle("🔍 Chi tiết Spam")
        self.setGeometry(150, 150, 800, 600)

        layout = QVBoxLayout()
        email_data = get_email_content(email_id)
        raw_body = email_data.get("body", "")

        # Dùng SpamDetector để lấy từ nghi ngờ
        detector = SpamDetector.get_instance()
        _, matched_keywords = detector.keyword_based_prediction(raw_body)

        # Tô đỏ các từ được đánh giá nghi ngờ
        for keyword in matched_keywords:
            raw_body = re.sub(f"(?i)\\b{re.escape(keyword)}\\b",
                f"<span style='color:red;font-weight:bold'>{keyword}</span>", raw_body)

        # Tạo label hiển thị các từ nghi ngờ
        if matched_keywords:
            matched_text = "<br>".join(f"🔴 {kw}" for kw in sorted(set(matched_keywords)))
            match_label = QLabel(f"<b>🛑 Những từ nghi ngờ trong nội dung:</b><br>{matched_text}")
            match_label.setWordWrap(True)
            layout.addWidget(match_label)


        label = QLabel(f"<b>Tiêu đề:</b> {email_data.get('subject', '')}<br><b>Người gửi:</b> {email_data.get('sender', '')}")
        label.setWordWrap(True)
        layout.addWidget(label)

        content = QTextEdit()
        content.setReadOnly(True)
        content.setHtml(f"<div style='text-align: justify;'>{raw_body}</div>")
        layout.addWidget(content)

        self.setLayout(layout)
