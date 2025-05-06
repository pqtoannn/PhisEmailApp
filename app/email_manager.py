from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, 
    QPushButton, QLabel, QHBoxLayout, QTabWidget, QMessageBox, QMenu,
    QListWidget, QListWidgetItem, QSplitter, QStackedWidget, QFrame, QHeaderView, QLineEdit
)
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QLabel
from PyQt6.QtCore import Qt, QPoint, QSize
from PyQt6.QtGui import QColor, QIcon, QFont
import sys
import os
from app.database import get_emails_from_db, clear_database, get_total_emails_count, mark_as_spam, mark_as_restored
from app.fetch_emails import get_latest_emails
from app.email_details import EmailDetailsWindow
from app.send_email import SendEmailWindow
from app.database import mark_as_deleted
from app.authenticate import get_current_user_email



if getattr(sys, 'frozen', False):
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

logo_path = os.path.join(BASE_DIR, "assets", "gmail_logo.png")


class EmailManagerWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("📩 Quản lý Email")
        self.setGeometry(100, 100, 1200, 700)

        # ==== Layout chính là ngang ====
        main_layout = QHBoxLayout()

        # ==== Thanh tìm kiếm ====
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Tìm kiếm theo Tiêu đề, Người gửi, Nội dung...")
        self.search_input.returnPressed.connect(self.search_emails)
        self.search_input.setStyleSheet("margin: 10px; padding: 6px; font-size: 14px;")

        # ==== Sidebar layout bên trái ====
        sidebar_layout = QVBoxLayout()

        # ==== Logo Gmail ====
        self.logo_label = QLabel()
        import os, sys
        if getattr(sys, 'frozen', False):
            BASE_DIR = sys._MEIPASS
        else:
            BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        logo_path = os.path.join(BASE_DIR, "assets", "gmail_logo")
        self.logo_label.setPixmap(QPixmap(logo_path))
        self.logo_label.setFixedHeight(80)
        self.logo_label.setScaledContents(True)
        sidebar_layout.addWidget(self.logo_label)

        # ==== Danh sách Sidebar ====
        self.sidebar = QListWidget()
        self.sidebar.setMaximumWidth(200)
        self.sidebar.setMinimumWidth(150)
        self.sidebar.setStyleSheet("""
            QListWidget {
                background-color: #e8f0fe;
                border-right: 1px solid #cccccc;
                font-size: 15px;
                font-family: "Segoe UI", sans-serif;
            }
            QListWidget::item {
                padding: 12px;
                border-bottom: 1px solid #e0e0e0;
            }
            QListWidget::item:selected {
                background-color: #1976d2;
                color: white;
                font-weight: bold;
            }
            QListWidget::item:hover {
                background-color: #bbdefb;
            }
        """)
        inbox_item = QListWidgetItem("📥 Hộp thư đến")
        inbox_item.setData(Qt.ItemDataRole.UserRole, "inbox")
        self.sidebar.addItem(inbox_item)

        spam_item = QListWidgetItem("🚫 Thư rác")
        spam_item.setData(Qt.ItemDataRole.UserRole, "spam")
        self.sidebar.addItem(spam_item)

        trash_item = QListWidgetItem("🗑️ Thùng rác")
        trash_item.setData(Qt.ItemDataRole.UserRole, "trash")
        self.sidebar.addItem(trash_item)

        self.sidebar.currentItemChanged.connect(self.on_sidebar_item_changed)
        sidebar_layout.addWidget(self.sidebar)
        sidebar_layout.addStretch()

        # ==== Hiển thị tài khoản ====
        from app.authenticate import get_current_user_email
        self.account_label = QLabel(f"👤 {get_current_user_email()}")
        self.account_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.account_label.setStyleSheet("""
            font-size: 12px;
            color: #555;
            padding: 10px;
        """)
        sidebar_layout.addWidget(self.account_label)

        # ==== Gói sidebar vào QWidget rồi add vào main_layout ====
        sidebar_container = QWidget()
        sidebar_container.setLayout(sidebar_layout)
        sidebar_container.setFixedWidth(200)
        main_layout.addWidget(sidebar_container)

        # ==== Stack các trang ====
        self.stack = QStackedWidget()
        self.inbox_page = QWidget(); self.setup_inbox_page(); self.stack.addWidget(self.inbox_page)
        self.spam_page = QWidget(); self.setup_spam_page(); self.stack.addWidget(self.spam_page)
        self.trash_page = QWidget(); self.setup_trash_page(); self.stack.addWidget(self.trash_page)
        main_layout.addWidget(self.stack)

        # ==== Nút chức năng phía dưới ====
        bottom_layout = QVBoxLayout()

        self.compose_button = QPushButton("✉️ Soạn thư mới", self)
        self.compose_button.clicked.connect(self.compose_email)
        self.compose_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 8px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        bottom_layout.addWidget(self.compose_button)

        self.logout_button = QPushButton("🔓 Đăng xuất", self)
        self.logout_button.clicked.connect(self.logout)
        self.logout_button.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                padding: 8px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
        """)
        bottom_layout.addWidget(self.logout_button)

        # ==== Layout tổng ====
        layout = QVBoxLayout()
        layout.addWidget(self.search_input)
        layout.addLayout(main_layout, 1)
        layout.addLayout(bottom_layout)
        self.setLayout(layout)

        # ==== Context menu cho bảng ====
        self.normal_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.normal_table.customContextMenuRequested.connect(self.show_normal_email_context_menu)
        self.spam_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.spam_table.customContextMenuRequested.connect(self.show_spam_email_context_menu)

        # ==== Load email mặc định ====
        self.sidebar.setCurrentRow(0)
        from app.database import get_total_emails_count
        if get_total_emails_count() == 0:
            from app.fetch_emails import get_latest_emails
            print("📥 Đang tải 20 email đầu tiên sau khi đăng nhập...")
            get_latest_emails(20)
        else:
            print("✅ Database đã có email, không cần tải lại ban đầu.")

        self.load_emails(is_spam=False)



    def setup_inbox_page(self):
        layout = QVBoxLayout()

        
        # Tiêu đề trang
        title_label = QLabel("📥 Hộp thư đến")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title_label)
        
        # Bảng danh sách email
        self.normal_table = QTableWidget()
        self.normal_table.setColumnCount(5)
        self.normal_table.setHorizontalHeaderLabels(["Người gửi", "Tiêu đề", "Xem nhanh", "Điểm AI", "Chi tiết spam"])

        self.normal_table.horizontalHeader().setStyleSheet("font-weight: bold;")
        self.normal_table.horizontalHeader().setStretchLastSection(True)
        self.normal_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        self.normal_table.setStyleSheet("""
    QTableView {
        background-color: #ffffff;
        gridline-color: #e0e0e0;
        font-size: 14px;
        font-family: "Segoe UI", sans-serif;
    }
    QHeaderView::section {
        background-color: #f1f1f1;
        font-weight: bold;
        border: 1px solid #d0d0d0;
    }
    QTableView::item {
        padding: 8px;
    }
    
    QTableView::item:hover {
        background-color: #e0e0e0;
    }
    QTableView::item:selected {
        background-color: #d0d0d0; 
    }
""")

        self.normal_table.cellClicked.connect(lambda row, col: self.open_email_details(row, col, is_spam=False))
        layout.addWidget(self.normal_table)

        # Thanh phân trang
        self.normal_page = 1
        pagination_layout = QHBoxLayout()
        pagination_layout.setSpacing(10)
        pagination_layout.setContentsMargins(10, 10, 10, 10)
        pagination_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.normal_page_label = QLabel(f"Trang {self.normal_page}")
        self.normal_page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.normal_prev_button = QPushButton("⬅ Trang trước")
        self.normal_prev_button.clicked.connect(lambda: self.prev_page(is_spam=False))
        
        self.normal_next_button = QPushButton("Trang sau ➡")
        self.normal_next_button.clicked.connect(lambda: self.next_page(is_spam=False))
        
        self.normal_refresh_button = QPushButton("🔄 Refresh")
        self.normal_refresh_button.clicked.connect(self.refresh_emails)
        self.normal_refresh_button.setStyleSheet("""
            QPushButton {
                background-color: #4caf50;
                color: white;
                padding: 6px;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #43a047;
            }
        """)
        
        self.setStyleSheet("""
    QWidget {
        background-color: #f9f9f9;
        font-family: "Segoe UI", sans-serif;
        color: #333333;
    }
""")


        pagination_layout.addWidget(self.normal_prev_button)
        pagination_layout.addWidget(self.normal_page_label)
        pagination_layout.addWidget(self.normal_next_button)
        pagination_layout.addWidget(self.normal_refresh_button)
        
        self.normal_fetch_button = QPushButton("📥 Lấy thêm email")
        self.normal_fetch_button.clicked.connect(self.fetch_more_emails)
        self.normal_fetch_button.setStyleSheet("""
            QPushButton {
                background-color: #1976d2;
                color: white;
                padding: 6px;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1565c0;
            }
        """)
        pagination_layout.addWidget(self.normal_fetch_button)


        layout.addLayout(pagination_layout)
        self.inbox_page.setLayout(layout)
        
        
        
    def setup_spam_page(self):
        layout = QVBoxLayout()
        
        # Tiêu đề trang
        title_label = QLabel("🚫 Thư rác")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #d32f2f; margin-bottom: 10px;")
        layout.addWidget(title_label)
        
        # Bảng danh sách email spam
        self.spam_table = QTableWidget()
        self.spam_table.setColumnCount(5)
        self.spam_table.setHorizontalHeaderLabels(["Người gửi", "Tiêu đề", "Xem nhanh", "Điểm AI", "Chi tiết spam"])

        self.spam_table.horizontalHeader().setStyleSheet("font-weight: bold;")
        self.spam_table.horizontalHeader().setStretchLastSection(True)
        self.spam_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        self.spam_table.setStyleSheet("""
            QTableView {
                background-color: #ffffff;
                gridline-color: #e0e0e0;
                font-size: 14px;
                font-family: "Segoe UI", sans-serif;
            }
            QHeaderView::section {
                background-color: #f1f1f1;
                font-weight: bold;
                border: 1px solid #d0d0d0;
            }
            QTableView::item {
                padding: 8px;
            }
            
            QTableView::item:hover {
                background-color: #e0e0e0;
            }
            QTableView::item:selected {
                background-color: #d0d0d0;
            }
        """)
        self.spam_table.cellClicked.connect(lambda row, col: self.open_email_details(row, col, is_spam=True))
        layout.addWidget(self.spam_table)

        # Thanh phân trang
        self.spam_page_num = 1
        pagination_layout = QHBoxLayout()
        pagination_layout.setSpacing(10)
        pagination_layout.setContentsMargins(10, 10, 10, 10)

        
        self.spam_page_label = QLabel(f"Trang {self.spam_page_num}")
        self.spam_page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.spam_prev_button = QPushButton("⬅ Trang trước")
        self.spam_prev_button.clicked.connect(lambda: self.prev_page(is_spam=True))
        
        self.spam_next_button = QPushButton("Trang sau ➡")
        self.spam_next_button.clicked.connect(lambda: self.next_page(is_spam=True))
        
        self.spam_refresh_button = QPushButton("🔄 Refresh")
        self.spam_refresh_button.clicked.connect(lambda: self.refresh_emails(is_spam=True))
        self.spam_refresh_button.setStyleSheet("""
            QPushButton {
                background-color: #4caf50;
                color: white;
                padding: 6px;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #43a047;
            }
        """)

        pagination_layout.addWidget(self.spam_prev_button)
        pagination_layout.addWidget(self.spam_page_label)
        pagination_layout.addWidget(self.spam_next_button)
        pagination_layout.addWidget(self.spam_refresh_button)
        
        layout.addLayout(pagination_layout)
        self.spam_page.setLayout(layout)
        
    def open_spam_details(self, email):
        from app.spam_details_window import SpamDetailsWindow
        self.spam_detail_window = SpamDetailsWindow(email["id"])
        self.spam_detail_window.show()

    def fetch_more_emails(self):
        from app.fetch_emails import get_latest_emails
        from PyQt6.QtWidgets import QMessageBox

        print("📥 Đang lấy thêm 20 email từ Gmail API...")
        num_added = get_latest_emails(20)

        if num_added > 0:
            QMessageBox.information(self, "✅ Lấy email thành công", f"Đã thêm {num_added} email mới.")
        else:
            QMessageBox.information(self, "📭 Không có email mới", "Tất cả email đã được tải. Không còn email mới để lấy.")

        self.load_emails(is_spam=False)



    def setup_trash_page(self):
        layout = QVBoxLayout()

        title_label = QLabel("🗑️ Thùng rác")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #f44336; margin-bottom: 10px;")
        layout.addWidget(title_label)

        self.trash_table = QTableWidget()
        self.trash_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.trash_table.customContextMenuRequested.connect(self.show_trash_email_context_menu)

        self.trash_table.setColumnCount(5)
        self.trash_table.setHorizontalHeaderLabels(["Người gửi", "Tiêu đề", "Xem nhanh", "Điểm AI", "Chi tiết spam"])

        self.trash_table.horizontalHeader().setStyleSheet("font-weight: bold;")
        self.trash_table.setStyleSheet("QTableView::item {padding: 5px;}")
        self.trash_table.cellClicked.connect(lambda row, col: self.open_email_details(row, col, is_spam=False, is_trash=True))
        layout.addWidget(self.trash_table)

        self.trash_page_num = 1
        pagination_layout = QHBoxLayout()
        pagination_layout.setSpacing(10)
        pagination_layout.setContentsMargins(10, 10, 10, 10)


        self.trash_page_label = QLabel(f"Trang {self.trash_page_num}")
        self.trash_page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.trash_prev_button = QPushButton("⬅ Trang trước")
        self.trash_prev_button.clicked.connect(lambda: self.prev_page(is_spam=False, is_trash=True))

        self.trash_next_button = QPushButton("Trang sau ➡")
        self.trash_next_button.clicked.connect(lambda: self.next_page(is_spam=False, is_trash=True))

        self.trash_refresh_button = QPushButton("🔄 Refresh")
        self.trash_refresh_button.clicked.connect(lambda: self.refresh_emails(is_spam=False, is_trash=True))

        pagination_layout.addWidget(self.trash_prev_button)
        pagination_layout.addWidget(self.trash_page_label)
        pagination_layout.addWidget(self.trash_next_button)
        pagination_layout.addWidget(self.trash_refresh_button)

        layout.addLayout(pagination_layout)
        self.trash_page.setLayout(layout)


    def on_sidebar_item_changed(self, current, previous):
        if current:
            item_type = current.data(Qt.ItemDataRole.UserRole)
            if item_type == "inbox":
                self.stack.setCurrentIndex(0)
                self.load_emails(is_spam=False)
            elif item_type == "spam":
                self.stack.setCurrentIndex(1)
                self.load_emails(is_spam=True)
            elif item_type == "trash":
                self.stack.setCurrentIndex(2)
                self.load_emails(is_trash=True)

    def show_normal_email_context_menu(self, position):
        if not self.normal_table.rowCount():
            return
            
        # Lấy hàng được click
        row = self.normal_table.indexAt(position).row()
        if row < 0:
            return
            
        menu = QMenu(self)

        mark_spam_action = menu.addAction("🚫 Đánh dấu là thư rác")
        delete_action = menu.addAction("🗑️ Xóa email")

        action = menu.exec(self.normal_table.viewport().mapToGlobal(position))

        if action == mark_spam_action:
            email_id = self.current_normal_emails[row]["id"]
            mark_as_spam(email_id, is_spam=1)
            self.load_emails(is_spam=False)

        elif action == delete_action:
            email_id = self.current_normal_emails[row]["id"]
            self.delete_email(email_id)


    def show_spam_email_context_menu(self, position):
        if not self.spam_table.rowCount():
            return
            
        # Lấy hàng đã chọn
        row = self.spam_table.indexAt(position).row()
        if row < 0:
            return
            
        # Tạo menu
        menu = QMenu(self)
        not_spam_action = menu.addAction("✅ Không phải thư rác")
        
        # Hiển thị menu và xử lý hành động
        action = menu.exec(self.spam_table.viewport().mapToGlobal(position))
        
        if action == not_spam_action:
            email_id = self.current_spam_emails[row]["id"]
            mark_as_spam(email_id, is_spam=0)
            self.load_emails(is_spam=True)  # Tải lại danh sách email spam

    def show_trash_email_context_menu(self, position):
        if not self.trash_table.rowCount():
            return
            
        row = self.trash_table.indexAt(position).row()
        if row < 0:
            return

        menu = QMenu(self)

        restore_action = menu.addAction("♻️ Khôi phục Email")

        action = menu.exec(self.trash_table.viewport().mapToGlobal(position))

        if action == restore_action:
            email_id = self.current_trash_emails[row]["id"]
            self.restore_email(email_id)

    def restore_email(self, email_id):
        """Khôi phục email"""
        from app.database import mark_as_restored

        mark_as_restored(email_id)
        print(f"♻️ Đã khôi phục email {email_id}")
        self.load_emails(is_trash=True)  # Refresh Trash page


    def load_emails(self, is_spam=False, is_trash=False):
        """ Hiển thị email theo trang và loại (spam/normal) """
        if is_spam:
            # Load email spam
            self.current_spam_emails = get_emails_from_db(self.spam_page_num, show_spam=True)
            self.spam_table.setRowCount(len(self.current_spam_emails))
            
            for row, email in enumerate(self.current_spam_emails):
                self.spam_table.setItem(row, 0, QTableWidgetItem(email["sender"]))
                self.spam_table.setItem(row, 1, QTableWidgetItem(email["subject"]))
                
                snippet = email["snippet"][:50] + "..." if len(email["snippet"]) > 50 else email["snippet"]
                self.spam_table.setItem(row, 2, QTableWidgetItem(snippet))
                
                # Hiển thị phần trăm spam
                spam_percent = int(email["spam_score"] * 100)
                spam_item = QTableWidgetItem(f"{spam_percent}%")

                if spam_percent > 70:
                    spam_item.setForeground(QColor(255, 0, 0))  # Đỏ đậm
                elif spam_percent > 50:
                    spam_item.setForeground(QColor(255, 140, 0))  # Cam
                else:
                    spam_item.setForeground(QColor(34, 139, 34))  # Xanh lá đậm
                spam_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

                spam_item.setForeground(QColor(255, 0, 0))  # Màu đỏ
                self.spam_table.setItem(row, 3, spam_item)
                
                detail_button = QPushButton("🔍 Chi tiết")
                detail_button.setFixedSize(80, 26)  # hoặc 90 x 24 tùy thiết kế
                detail_button.setStyleSheet("""
                    QPushButton {
                        background-color: #e3f2fd;
                        color: #1976d2;
                        padding: 4px 10px;
                        font-size: 13px;
                        border: 1px solid #bbdefb;
                        border-radius: 6px;
                    }
                    QPushButton:hover {
                        background-color: #bbdefb;
                    }
                """)
                detail_button.clicked.connect(lambda _, email=email: self.open_spam_details(email))
                self.spam_table.setCellWidget(row, 4, detail_button)

            
            self.spam_page_label.setText(f"Trang {self.spam_page_num}")
            self.spam_table.resizeColumnsToContents()
        elif is_trash:
                # Load email đã xóa
            self.current_trash_emails = get_emails_from_db(self.trash_page_num, show_spam=False, show_trash=True)
            self.trash_table.setRowCount(len(self.current_trash_emails))

            for row, email in enumerate(self.current_trash_emails):
                self.trash_table.setItem(row, 0, QTableWidgetItem(email["sender"]))
                self.trash_table.setItem(row, 1, QTableWidgetItem(email["subject"]))
                
                snippet = email["snippet"][:50] + "..." if len(email["snippet"]) > 50 else email["snippet"]
                self.trash_table.setItem(row, 2, QTableWidgetItem(snippet))
                
                spam_percent = int(email["spam_score"] * 100)
                spam_item = QTableWidgetItem(f"{spam_percent}%")
                spam_item.setForeground(QColor(128, 128, 128))
                self.trash_table.setItem(row, 3, spam_item)
                
                detail_button = QPushButton("🔍 Chi tiết")
                detail_button.setFixedSize(80, 26)  # hoặc 90 x 24 tùy thiết kế
                detail_button.setStyleSheet("""
                    QPushButton {
                        background-color: #e3f2fd;
                        color: #1976d2;
                        padding: 4px 10px;
                        font-size: 13px;
                        border: 1px solid #bbdefb;
                        border-radius: 6px;
                    }
                    QPushButton:hover {
                        background-color: #bbdefb;
                    }
                """)
                detail_button.clicked.connect(lambda _, email=email: self.open_spam_details(email))
                self.trash_table.setCellWidget(row, 4, detail_button)

            self.trash_page_label.setText(f"Trang {self.trash_page_num}")
            self.trash_table.resizeColumnsToContents()
        else:
            # Load email thường
            self.current_normal_emails = get_emails_from_db(self.normal_page, show_spam=False)
            self.normal_table.setRowCount(len(self.current_normal_emails))
            
            for row, email in enumerate(self.current_normal_emails):
                self.normal_table.setItem(row, 0, QTableWidgetItem(email["sender"]))
                self.normal_table.setItem(row, 1, QTableWidgetItem(email["subject"]))
                
                snippet = email["snippet"][:50] + "..." if len(email["snippet"]) > 50 else email["snippet"]
                self.normal_table.setItem(row, 2, QTableWidgetItem(snippet))
                
                # Hiển thị phần trăm spam
                spam_percent = int(email["spam_score"] * 100)
                spam_item = QTableWidgetItem(f"-{spam_percent}%")
                
                # Đổi màu theo mức độ spam
                if spam_percent > 50:
                    spam_item.setForeground(QColor(255, 165, 0))  # Màu cam
                else:
                    spam_item.setForeground(QColor(0, 128, 0))  # Màu xanh lá
                    
                self.normal_table.setItem(row, 3, spam_item)
                
                detail_button = QPushButton("🔍 Chi tiết")
                detail_button.setFixedSize(80, 26)  # hoặc 90 x 24 tùy thiết kế
                detail_button.setStyleSheet("""
                    QPushButton {
                        background-color: #e3f2fd;
                        color: #1976d2;
                        padding: 4px 10px;
                        font-size: 13px;
                        border: 1px solid #bbdefb;
                        border-radius: 6px;
                    }
                    QPushButton:hover {
                        background-color: #bbdefb;
                    }
                """)
                detail_button.clicked.connect(lambda _, email=email: self.open_spam_details(email))
                self.normal_table.setCellWidget(row, 4, detail_button)
            
            self.normal_page_label.setText(f"Trang {self.normal_page}")
            self.normal_table.resizeColumnsToContents()
            print(f"Đang load email: Spam={is_spam}, Trash={is_trash}")


    def open_email_details(self, row, col, is_spam=False, is_trash=False):
        """ Mở màn hình xem chi tiết email khi người dùng nhấp vào """

        if is_trash:
            if not self.current_trash_emails or row >= len(self.current_trash_emails):
                return
            email_id = self.current_trash_emails[row]["id"]

        elif is_spam:
            if not self.current_spam_emails or row >= len(self.current_spam_emails):
                return
            email_id = self.current_spam_emails[row]["id"]

        else:
            if not self.current_normal_emails or row >= len(self.current_normal_emails):
                return
            email_id = self.current_normal_emails[row]["id"]

        self.email_details_window = EmailDetailsWindow(email_id)
        self.email_details_window.show()


    def delete_email(self, email_id):
        """Xử lý xóa email"""
        from app.database import mark_as_deleted

        mark_as_deleted(email_id)
        print(f"🗑️ Đã đánh dấu xóa email {email_id}")
        self.load_emails(is_spam=False)  # Refresh lại danh sách

    def search_emails(self):
        keyword = self.search_input.text().strip()
        if not keyword:
            self.load_emails(is_spam=False)  # fallback
            return

        from app.database import search_emails_in_db

        current_index = self.stack.currentIndex()
        if current_index == 0:  # Inbox
            target = 'inbox'
        elif current_index == 1:  # Spam
            target = 'spam'
        else:  # Trash
            target = 'trash'

        results = search_emails_in_db(keyword, target)

        if target == 'inbox':
            self.current_normal_emails = results
            self.normal_table.setRowCount(len(results))
            table = self.normal_table
        elif target == 'spam':
            self.current_spam_emails = results
            self.spam_table.setRowCount(len(results))
            table = self.spam_table
        else:
            self.current_trash_emails = results
            self.trash_table.setRowCount(len(results))
            table = self.trash_table

        for row, email in enumerate(results):
            table.setItem(row, 0, QTableWidgetItem(email["sender"]))
            table.setItem(row, 1, QTableWidgetItem(email["subject"]))
            snippet = email["snippet"][:50] + "..." if len(email["snippet"]) > 50 else email["snippet"]
            table.setItem(row, 2, QTableWidgetItem(snippet))

            spam_percent = int(email["spam_score"] * 100)
            spam_item = QTableWidgetItem(f"{spam_percent}%")
            spam_item.setForeground(QColor(128, 128, 128))
            table.setItem(row, 3, spam_item)

            # Nút Chi tiết
            detail_button = QPushButton("Chi tiết")
            detail_button.setFixedSize(80, 26)
            detail_button.setStyleSheet("""
                QPushButton {
                    background-color: #e3f2fd;
                    color: #1976d2;
                    padding: 4px 10px;
                    font-size: 13px;
                    border: 1px solid #bbdefb;
                    border-radius: 6px;
                }
                QPushButton:hover {
                    background-color: #bbdefb;
                }
            """)
            detail_button.clicked.connect(lambda _, email=email: self.open_spam_details(email))
            from PyQt6.QtWidgets import QHBoxLayout, QWidget
            button_container = QWidget()
            button_layout = QHBoxLayout(button_container)
            button_layout.addWidget(detail_button)
            button_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            button_layout.setContentsMargins(0, 0, 0, 0)
            table.setCellWidget(row, 4, button_container)

        table.resizeColumnsToContents()



    def compose_email(self):
        """ Mở màn hình soạn thư mới """
        self.send_email_window = SendEmailWindow()
        self.send_email_window.show()
    
    def prev_page(self, is_spam=False):
        if is_spam:
            if self.spam_page_num > 1:
                self.spam_page_num -= 1
                self.load_emails(is_spam=True)
        else:
            if self.normal_page > 1:
                self.normal_page -= 1
                self.load_emails(is_spam=False)

    def next_page(self, is_spam=False):
        """Chuyển sang trang tiếp theo, lấy thêm email nếu cần"""
        if is_spam:
            total_emails = get_total_emails_count(show_spam=True)
            if self.spam_page_num * 20 < total_emails:
                self.spam_page_num += 1
                self.load_emails(is_spam=True)
        else:
            total_emails = get_total_emails_count(show_spam=False)
            
            self.normal_page += 1
            self.load_emails(is_spam=False)

    def refresh_emails(self):
        from app.fetch_emails import refresh_emails_safely
        from PyQt6.QtWidgets import QMessageBox

        print("🔄 Đang kiểm tra email mới trên Gmail API...")
        num_added = refresh_emails_safely(50)

        if num_added > 0:
            QMessageBox.information(self, "✅ Đã làm mới hộp thư", f"Đã thêm {num_added} email mới.")
        else:
            QMessageBox.information(self, "📬 Hộp thư đã cập nhật", "Không có email mới.")

        self.load_emails(is_spam=False)

    def logout(self):
        """ Đăng xuất, xóa database và token.json """
        from app.login_window import LoginWindow  # Import LoginWindow để quay lại màn hình đăng nhập

        # Xóa database
        clear_database()
        
        # Xóa token.json (nếu có)
        if os.path.exists("token.json"):
            os.remove("token.json")
        
        if os.path.exists("last_token.json"):
            os.remove("last_token.json")


        print("Đã xóa dữ liệu và token, quay lại màn hình đăng nhập.")
        from app.database import clear_all_emails
        # Xóa dữ liệu trong db
        clear_all_emails()
        print("🗑️ Đã xóa toàn bộ email trong database.")
        # Đóng cửa sổ hiện tại và quay lại màn hình đăng nhập
        self.close()
        self.login_window = LoginWindow()
        self.login_window.show()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = EmailManagerWindow()
    window.show()
    sys.exit(app.exec())
