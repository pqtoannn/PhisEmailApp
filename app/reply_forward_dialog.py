from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QLineEdit,
    QTextEdit, QPushButton, QHBoxLayout, QMessageBox, QWidget
)
from PyQt6.QtCore import Qt
from app.send_email import get_gmail_service
import os
import re


class ReplyForwardDialog(QDialog):
    def __init__(self, recipient_email, original_subject, original_body, mode="reply"):
        super().__init__()
        self.setWindowTitle("✉ Soạn thư mới")
        self.setFixedSize(600, 500)
        
        self.recipient_email = recipient_email
        self.original_subject = original_subject
        self.original_body = original_body
        self.mode = mode  # "reply" hoặc "forward"
        
        layout = QVBoxLayout()

        # Người nhận
        self.to_label = QLabel("🧑 Người nhận:")
        self.to_input = QLineEdit()
        email_only = self.extract_email(self.recipient_email)
        self.to_input.setText(email_only)

        layout.addWidget(self.to_label)
        layout.addWidget(self.to_input)

        # Tiêu đề
        self.subject_label = QLabel("📝 Tiêu đề:")
        self.subject_input = QLineEdit()
        if mode == "reply":
            self.subject_input.setText(f"Re: {self.original_subject}")
        else:
            self.subject_input.setText(f"Fwd: {self.original_subject}")
        layout.addWidget(self.subject_label)
        layout.addWidget(self.subject_input)

        # Nội dung
        self.body_label = QLabel("✉ Nội dung:")
        self.body_input = QTextEdit()

        quoted_body = "\n\n-------------------------\n" + self.original_body
        self.body_input.setText(quoted_body)

        layout.addWidget(self.body_label)
        layout.addWidget(self.body_input)

        # Nút chọn file đính kèm
        self.attach_button = QPushButton("📎 Chọn file đính kèm")
        self.attach_button.clicked.connect(self.choose_attachments)
        layout.addWidget(self.attach_button)

        # Layout hiển thị danh sách file
        self.attachments_layout = QVBoxLayout()
        layout.addLayout(self.attachments_layout)

        # Danh sách lưu đường dẫn file đính kèm
        self.attachment_paths = []



        # Nút gửi và hủy
        button_layout = QHBoxLayout()
        self.send_button = QPushButton("🚀 Gửi")
        self.cancel_button = QPushButton("❌ Hủy")
        button_layout.addWidget(self.send_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)

        self.setLayout(layout)

        # Kết nối sự kiện
        self.send_button.clicked.connect(self.send_email)
        self.cancel_button.clicked.connect(self.close)

    def extract_email(self, text):
        """Lấy đúng địa chỉ email từ chuỗi text có thể chứa tên"""
        match = re.search(r'[\w\.-]+@[\w\.-]+', text)
        if match:
            return match.group(0)
        return text  # Nếu không tìm được thì trả text ban đầu


    def choose_attachments(self):
        from PyQt6.QtWidgets import QFileDialog
        files, _ = QFileDialog.getOpenFileNames(self, "Chọn các tệp đính kèm")
        if files:
            self.attachment_paths.extend(files)
            self.update_attachment_list()


    def update_attachment_list(self):
        # Xóa giao diện cũ
        for i in reversed(range(self.attachments_layout.count())):
            widget = self.attachments_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)

        # Thêm danh sách mới
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


    def remove_attachment(self, file_path):
        if file_path in self.attachment_paths:
            self.attachment_paths.remove(file_path)
            self.update_attachment_list()


    
    def send_email(self):
        """Gửi email ngay từ popup Reply/Forward"""
        to_email = self.to_input.text()
        subject = self.subject_input.text()
        body = self.body_input.toPlainText()

        if not to_email or not subject or not body:
            QMessageBox.warning(self, "Lỗi", "Vui lòng nhập đầy đủ thông tin email!")
            return

        try:
            service = get_gmail_service()
            from email.mime.multipart import MIMEMultipart
            from email.mime.text import MIMEText
            from email.mime.base import MIMEBase
            from email import encoders
            import base64
            import os

            message = MIMEMultipart()
            message["to"] = to_email
            message["subject"] = subject

            message.attach(MIMEText(body, "plain"))

            # Gửi tất cả file đính kèm
            for path in self.attachment_paths:
                with open(path, "rb") as f:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(f.read())
                    encoders.encode_base64(part)
                    part.add_header('Content-Disposition', f'attachment; filename="{os.path.basename(path)}"')
                    message.attach(part)

            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
            service.users().messages().send(userId="me", body={"raw": raw_message}).execute()

            QMessageBox.information(self, "Gửi Email", "✅ Email đã gửi thành công!")

            self.accept()

        except Exception as e:
            print(f"Lỗi gửi email: {str(e)}")



