from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QLabel
import sys
import os
from app.authenticate import authenticate_gmail
from app.email_manager import EmailManagerWindow  # Import màn hình quản lý email

class LoginWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Đăng nhập Gmail")
        self.setGeometry(100, 100, 400, 200)
        self.setStyleSheet("""
    QWidget {
        background-color: #f1f8ff;
        font-family: "Segoe UI", sans-serif;
        color: #333333;
    }
    QPushButton {
        background-color: #1976d2;
        color: white;
        padding: 10px;
        border-radius: 6px;
        font-weight: bold;
    }
    QPushButton:hover {
        background-color: #1565c0;
    }
    QLabel {
        font-size: 16px;
        font-weight: bold;
        margin-bottom: 10px;
    }
""")



        layout = QVBoxLayout()

        self.label = QLabel("Nhấn nút bên dưới để đăng nhập Gmail", self)
        layout.addWidget(self.label)

        self.login_button = QPushButton("Đăng nhập Gmail", self)
        self.login_button.clicked.connect(self.login)
        layout.addWidget(self.login_button)

        self.setLayout(layout)

        # Kiểm tra nếu đã có token.json, chỉ thông báo chứ không tự động đăng nhập
        if os.path.exists("token.json"):
            self.label.setText("✅ Đã có thông tin đăng nhập Gmail. Nhấn nút để tiếp tục.")
            self.login_button.setText("Tiếp tục với tài khoản đã đăng nhập")

    def login(self):
        try:
            authenticate_gmail()
            self.label.setText("✅ Đăng nhập thành công! Chuyển đến màn hình quản lý email...")
            self.open_email_manager()  # Mở giao diện quản lý email
        except Exception as e:
            self.label.setText(f"❌ Lỗi đăng nhập: {str(e)}")

    def open_email_manager(self):
        self.email_manager = EmailManagerWindow()
        self.email_manager.show()
        self.close()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = LoginWindow()
    window.show()
    sys.exit(app.exec())
