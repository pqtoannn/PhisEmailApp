import sys
import os
from PyQt6.QtWidgets import QApplication, QMessageBox
from app.login_window import LoginWindow
from app.database import recreate_database

def setup_environment():
    """Thiết lập môi trường làm việc cho ứng dụng"""
    # Đảm bảo thư mục hiện tại là thư mục gốc của ứng dụng
    app_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(app_dir)
    print(f"Thư mục làm việc hiện tại: {os.getcwd()}")
    
    # Đảm bảo các thư mục cần thiết tồn tại
    required_dirs = ["models", "data", "nltk_data"]
    for directory in required_dirs:
        if not os.path.exists(directory):
            os.makedirs(directory)

def check_model():
    """Kiểm tra xem model AI có tồn tại không và hiển thị thông báo"""
    # Kiểm tra model AI
    model_path = os.path.join("models", "best_model.pth")
    if not os.path.exists(model_path):
        print(f"CẢNH BÁO: Model AI không được tìm thấy ở {model_path}")
        print("Tính năng phát hiện email lừa đảo sẽ không hoạt động.")
        return False
    
    # Kiểm tra kích thước file để đảm bảo đó là file hợp lệ
    file_size = os.path.getsize(model_path) / (1024 * 1024)  # Kích thước theo MB
    print(f"Kích thước model: {file_size:.2f} MB")
    
    if file_size < 1:  # Nếu file nhỏ hơn 1MB thì có thể không phải là model hợp lệ
        print("CẢNH BÁO: Model AI có thể không hợp lệ (kích thước quá nhỏ)")
        return False
        
    return True

def main():
    """Hàm chính khởi chạy ứng dụng"""
    # Thiết lập môi trường làm việc
    setup_environment()
    
    # Xử lý tham số dòng lệnh
    if len(sys.argv) > 1:
        if sys.argv[1] == "--reset-db":
            recreate_database()
            print("Đã khởi tạo lại database. Vui lòng chạy lại ứng dụng mà không có tham số --reset-db")
            return
    
    # Kiểm tra model AI
    model_ok = check_model()
    
    # Khởi tạo ứng dụng
    app = QApplication(sys.argv)
    window = LoginWindow()
    
    # Hiển thị thông báo nếu model không tìm thấy
    if not model_ok:
        QMessageBox.warning(window, "Cảnh báo", 
            "Model AI không được tìm thấy hoặc không hợp lệ!\n" +
            "Tính năng phát hiện email lừa đảo sẽ không hoạt động.\n" +
            "Hãy đảm bảo file 'best_model.pth' nằm trong thư mục 'models'."
        )
    
    # Hiển thị cửa sổ đăng nhập
    window.show()
    
    # Khởi chạy vòng lặp sự kiện
    sys.exit(app.exec())

if __name__ == "__main__":
    main() 