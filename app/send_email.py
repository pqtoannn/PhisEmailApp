from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QLineEdit,
    QTextEdit, QPushButton, QFileDialog, QMessageBox, QHBoxLayout
)
import os
import base64
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

SCOPES = ["https://mail.google.com/"]


def get_gmail_service():
    creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    service = build("gmail", "v1", credentials=creds)
    return service

class SendEmailWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("📤 Gửi Email")
        self.setGeometry(100, 100, 500, 400)
        self.setStyleSheet("""
    QWidget {
        background-color: #ffffff;
        font-family: "Segoe UI", sans-serif;
        color: #333333;
    }
    QLabel {
        font-size: 14px;
        margin-bottom: 5px;
    }
    QLineEdit, QTextEdit {
        padding: 8px;
        border: 1px solid #cccccc;
        border-radius: 6px;
        background-color: #f9f9f9;
    }
    QPushButton {
        background-color: #4caf50;
        color: white;
        padding: 8px;
        border-radius: 6px;
        font-weight: bold;
    }
    QPushButton:hover {
        background-color: #43a047;
    }
""")



        layout = QVBoxLayout()

        self.to_label = QLabel("📩 Người nhận:")
        self.to_input = QLineEdit()
        layout.addWidget(self.to_label)
        layout.addWidget(self.to_input)

        self.subject_label = QLabel("📝 Tiêu đề:")
        self.subject_input = QLineEdit()
        layout.addWidget(self.subject_label)
        layout.addWidget(self.subject_input)

        self.body_label = QLabel("✉ Nội dung email:")
        self.body_input = QTextEdit()
        layout.addWidget(self.body_label)
        layout.addWidget(self.body_input)

        self.attach_button = QPushButton("📎 Đính kèm tệp")
        self.attach_button.clicked.connect(self.attach_file)
        layout.addWidget(self.attach_button)
        
        self.attachments_layout = QVBoxLayout()
        layout.addLayout(self.attachments_layout)

        self.send_button = QPushButton("🚀 Gửi Email")
        self.send_button.clicked.connect(self.send_email)
        layout.addWidget(self.send_button)


        self.setLayout(layout)
        self.attachment_paths = []

    def update_attachment_list(self):
        # Xóa hết giao diện cũ
        for i in reversed(range(self.attachments_layout.count())):
            widget = self.attachments_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)

        # Thêm các file mới
        for file_path in self.attachment_paths:
            file_name = os.path.basename(file_path)
            file_row = QHBoxLayout()

            file_label = QLabel(f"📎 {file_name}")
            remove_button = QPushButton("❌")
            remove_button.setFixedSize(30, 30)
            remove_button.clicked.connect(self.generate_remove_callback(file_path))

            file_row.addWidget(file_label)
            file_row.addWidget(remove_button)

            wrapper = QWidget()
            wrapper.setLayout(file_row)
            self.attachments_layout.addWidget(wrapper)
            
    def generate_remove_callback(self, file_path):
        def callback():
            self.remove_attachment(file_path)
        return callback

    
    def remove_attachment(self, file_path, _=None):
        if file_path in self.attachment_paths:
            self.attachment_paths.remove(file_path)
            self.update_attachment_list()

    def attach_file(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Chọn các tệp đính kèm")
        if files:
            self.attachment_paths.extend(files)
            self.update_attachment_list()

    def send_email(self):
        to_email = self.to_input.text()
        subject = self.subject_input.text()
        body = self.body_input.toPlainText()
        
        if not to_email or not subject or not body:
            QMessageBox.warning(self, "Lỗi", "Vui lòng nhập đầy đủ thông tin email!")
            return

        try:
            service = get_gmail_service()
            message = MIMEMultipart()
            message["to"] = to_email
            message["subject"] = subject
            message.attach(MIMEText(body, "plain"))

            if self.attachment_paths:
                for path in self.attachment_paths:
                    with open(path, "rb") as f:
                        part = MIMEBase("application", "octet-stream")
                        part.set_payload(f.read())
                        encoders.encode_base64(part)
                        part.add_header('Content-Disposition', f'attachment; filename="{os.path.basename(path)}"')
                        message.attach(part)




            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
            service.users().messages().send(userId="me", body={"raw": raw_message}).execute()
            QMessageBox.information(self, "Thành công", "Email đã được gửi thành công!")
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể gửi email: {str(e)}")
