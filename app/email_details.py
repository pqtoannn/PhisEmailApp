from PyQt6.QtWidgets import QFrame, QWidget, QVBoxLayout, QLabel, QPushButton, QTextEdit, QHBoxLayout, QProgressBar
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPalette
from app.fetch_emails import get_email_content, download_attachment
from app.database import get_email_spam_score
from app.reply_forward_dialog import ReplyForwardDialog 

class EmailDetailsWindow(QWidget):
    def __init__(self, email_id):
        super().__init__()
        self.email_id = email_id
        self.setWindowTitle("📧 Chi tiết Email")
        self.setGeometry(150, 150, 700, 600)
        self.setStyleSheet("""
            QWidget {
                background-color: #f9f9f9;
                font-family: "Segoe UI", sans-serif;
                font-size: 14px;
                color: #333333;
            }
        """)

        layout = QVBoxLayout()

        # Lấy nội dung email
        self.email_content = get_email_content(email_id)
        
        # Lấy thông tin spam score từ database
        self.spam_score = get_email_spam_score(email_id)

        # Tiêu đề email
        self.subject_label = QLabel(f"📩 {self.email_content.get('subject', 'No Subject')}", self)
        self.subject_label.setStyleSheet("font-weight: bold; font-size: 20px; color: #1976d2; margin-bottom: 5px;")
        layout.addWidget(self.subject_label)

        # Người gửi
        self.sender_label = QLabel(f"👤 {self.email_content.get('sender', 'Unknown Sender')}", self)
        self.sender_label.setStyleSheet("font-style: italic; font-size: 14px; color: gray; margin-bottom: 10px;")
        layout.addWidget(self.sender_label)

        # Thêm thông tin phân tích spam
        spam_layout = QHBoxLayout()

        spam_percent = int(self.spam_score * 100)
        spam_text = QLabel(f"⚠️ Mức độ lừa đảo: {spam_percent}%")
        
        # Đổi màu chữ dựa vào mức độ spam
        if spam_percent > 70:
            spam_text.setStyleSheet("color: red; font-weight: bold")
        elif spam_percent > 50:
            spam_text.setStyleSheet("color: orange; font-weight: bold")
        else:
            spam_text.setStyleSheet("color: green;")

        spam_layout.addWidget(spam_text)

        # Thanh tiến trình hiển thị mức độ spam
        spam_progress = QProgressBar()
        spam_progress.setRange(0, 100)
        spam_progress.setValue(spam_percent)

        if spam_percent > 70:
            spam_progress.setStyleSheet("QProgressBar::chunk { background-color: red; }")
        elif spam_percent > 50:
            spam_progress.setStyleSheet("QProgressBar::chunk { background-color: orange; }")
        else:
            spam_progress.setStyleSheet("QProgressBar::chunk { background-color: green; }")
            
        spam_layout.addWidget(spam_progress)
        layout.addLayout(spam_layout)

        # Nội dung email (body)
        self.body_frame = QFrame(self)
        self.body_frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.body_frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 8px;
                border: 1px solid #cccccc;
                padding: 10px;
            }
        """)
        frame_layout = QVBoxLayout(self.body_frame)

        self.body_text = QTextEdit(self.body_frame)
        body_content = self.email_content.get("body", "Không có nội dung")
        
        # Nếu email có file đính kèm
        attachments = self.email_content.get("attachments", [])
        if attachments:
            attachment_label = QLabel("📎 File đính kèm:")
            attachment_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
            layout.addWidget(attachment_label)

            for attachment in attachments:
                file_name = attachment["filename"]

                download_button = QPushButton(f"⬇️ {file_name}")
                download_button.clicked.connect(lambda _, att=attachment: self.download_attachment(att))
                layout.addWidget(download_button)


        # Dùng HTML format để căn đều văn bản
        html_content = f"<div style='text-align: justify;'>{body_content}</div>"
        self.body_text.setHtml(html_content)

        self.body_text.setReadOnly(True)
        frame_layout.addWidget(self.body_text)

        layout.addWidget(self.body_frame)

        button_layout = QHBoxLayout()

        self.reply_button = QPushButton("✉️ Reply")
        self.reply_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 8px;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        self.reply_button.clicked.connect(self.open_reply)

        self.forward_button = QPushButton("📤 Forward")
        self.forward_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                padding: 8px;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0b7dda;
            }
        """)
        self.forward_button.clicked.connect(self.open_forward)

        button_layout.addWidget(self.reply_button)
        button_layout.addWidget(self.forward_button)

        layout.addLayout(button_layout)

        self.setLayout(layout)

    def download_attachment(self, attachment):
        """Xử lý tải file đính kèm"""
        from PyQt6.QtWidgets import QFileDialog
        save_path, _ = QFileDialog.getSaveFileName(self, "Save Attachment", attachment["filename"])

        if save_path:
            # Gọi hàm download
            real_path = download_attachment(self.email_id, attachment["attachmentId"], save_path)
            print(f"✅ Đã tải file về: {real_path}")


    def open_reply(self):
        """Mở popup soạn Reply"""
        recipient_email = self.email_content.get('sender', '')
        subject = self.email_content.get('subject', '')
        body = self.email_content.get('body', '')

        self.dialog = ReplyForwardDialog(
            recipient_email=recipient_email,
            original_subject=subject,
            original_body=body,
            mode="reply"
        )
        self.dialog.exec()


    def open_forward(self):
        """Mở popup soạn Forward"""
        recipient_email = ""  # Forward cho người khác nên để trống cho người dùng tự điền
        subject = self.email_content.get('subject', '')
        body = self.email_content.get('body', '')

        self.dialog = ReplyForwardDialog(
            recipient_email=recipient_email,
            original_subject=subject,
            original_body=body,
            mode="forward"
        )
        self.dialog.exec()


