import torch
import torch.nn as nn
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
import nltk
import os
import pickle
import io
import re
import sys

if getattr(sys, 'frozen', False):
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Đảm bảo dữ liệu NLTK được cài đặt
if not os.path.exists("nltk_data"):
    print("[INFO] Tạo thư mục nltk_data và tải dữ liệu NLTK...")
    os.makedirs("nltk_data")
    nltk.download('punkt', download_dir="nltk_data")
    nltk.download('stopwords', download_dir="nltk_data")
try:
    nltk.data.path.append("nltk_data")
except:
    print("[WARNING] Không thể thêm nltk_data vào đường dẫn")

# ============== ĐỊNH NGHĨA LỚP VOCABULARY DÙNG TRONG HUẤN LUYỆN ================
# Định nghĩa lớp Vocabulary ở cấp độ module chính để PyTorch có thể tìm thấy
class Vocabulary:
    def __init__(self, max_size=50000):
        self.max_size = max_size
        self.token2idx = {'<pad>': 0, '<unk>': 1}
        self.idx2token = {0: '<pad>', 1: '<unk>'}
        
    def __len__(self):
        return len(self.token2idx)
        
    def __getitem__(self, token):
        return self.token2idx.get(token, 1)  # Trả về index của token, nếu không có thì trả về index của <unk>

    def build_vocab(self, texts, min_freq=1):
        """Xây dựng từ điển từ danh sách văn bản"""
        freq = {}
        for text in texts:
            for token in text:
                if token in freq:
                    freq[token] += 1
                else:
                    freq[token] = 1
        
        # Sắp xếp theo tần suất giảm dần
        sorted_tokens = sorted(freq.items(), key=lambda x: x[1], reverse=True)
        
        # Lấy những token có tần suất >= min_freq
        idx = 2  # Bắt đầu từ 2 vì 0, 1 đã được sử dụng
        for token, count in sorted_tokens:
            if count >= min_freq and idx < self.max_size:
                self.token2idx[token] = idx
                self.idx2token[idx] = token
                idx += 1
                
    def numericalize(self, text):
        """Chuyển đổi văn bản thành dãy số"""
        return [self.__getitem__(token) for token in text]

# Adapter cho Vocabulary để xử lý nhiều cấu trúc khác nhau
class VocabularyAdapter:
    def __init__(self, vocab_object):
        self.vocab_object = vocab_object
        # Xác định loại của vocab object
        if hasattr(vocab_object, 'token2idx'):
            # Đây là Vocabulary class
            self.vocab_type = 'vocab_class'
        elif isinstance(vocab_object, dict) and '<pad>' in vocab_object:
            # Đây là dictionary đơn giản token->idx
            self.vocab_type = 'dict'
        else:
            # Loại không xác định
            print(f"[WARNING] Không thể xác định loại vocabulary: {type(vocab_object)}")
            self.vocab_type = 'unknown'
            
    def __getitem__(self, token):
        if self.vocab_type == 'vocab_class':
            return self.vocab_object[token]
        elif self.vocab_type == 'dict':
            return self.vocab_object.get(token, self.vocab_object.get('<unk>', 1))
        else:
            return 1  # Trả về <unk> cho trường hợp không xác định
            
    def __len__(self):
        if self.vocab_type == 'vocab_class':
            return len(self.vocab_object)
        elif self.vocab_type == 'dict':
            return len(self.vocab_object)
        else:
            return 50000  # Giá trị mặc định

# ============== ĐỊNH NGHĨA LỚP MODEL DÙNG TRONG HUẤN LUYỆN ================
class LSTMModel(nn.Module):
    def __init__(self, vocab_size, embedding_dim, hidden_dim, num_layers, output_dim, dropout, bidirectional=True):
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, embedding_dim)
        self.lstm = nn.LSTM(embedding_dim, hidden_dim, num_layers, batch_first=True, 
                          dropout=dropout if num_layers > 1 else 0, bidirectional=bidirectional)
        self.fc = nn.Linear(hidden_dim * 2 if bidirectional else hidden_dim, output_dim)
        self.dropout = nn.Dropout(dropout)
        
    def forward(self, text, text_lengths=None):
        embedded = self.dropout(self.embedding(text))
        
        if text_lengths is not None:
            # Nếu có text_lengths, sử dụng pack_padded_sequence
            packed_embedded = nn.utils.rnn.pack_padded_sequence(embedded, text_lengths.cpu(), 
                                                             batch_first=True, enforce_sorted=False)
            packed_output, (hidden, cell) = self.lstm(packed_embedded)
        else:
            # Nếu không có text_lengths (như trong dự đoán), sử dụng phương pháp thay thế
            output, (hidden, cell) = self.lstm(embedded)
        
        if self.lstm.bidirectional:
            hidden = torch.cat((hidden[-2,:,:], hidden[-1,:,:]), dim=1)
        else:
            hidden = hidden[-1,:,:]
            
        hidden = self.dropout(hidden)
        output = self.fc(hidden)
        
        return output

# Hàm tiền xử lý văn bản - cải tiến phù hợp với hàm dùng để train
def preprocess_text(text):
    """Hàm tiền xử lý văn bản: loại bỏ stopwords, biến đổi về chữ thường..."""
    if not isinstance(text, str):
        return []
    
    # Chuyển về chữ thường
    text = text.lower()
    
    # Loại bỏ các ký tự đặc biệt, giữ lại chữ cái và dấu câu quan trọng
    text = re.sub(r'[^a-zA-Z\s.,!?]', '', text)
    # Chuẩn hóa khoảng trắng
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Tokenize
    tokens = word_tokenize(text)
    
    # Loại bỏ stopwords
    stop_words = set(stopwords.words('english'))
    tokens = [token for token in tokens if token not in stop_words]
    
    return tokens

# Hàm tạo từ điển mới khi không thể load từ điển từ model
def create_vocab_from_scratch():
    """Tạo từ điển cơ bản cho model khi không load được từ điển từ model"""
    vocab = Vocabulary(max_size=50000)
    
    # Danh sách từ phổ biến trong các email
    common_words = ["email", "dear", "hello", "hi", "please", "account", "bank", "password", 
                    "verify", "click", "link", "urgent", "money", "transfer", "security", 
                    "update", "information", "confirm", "payment", "credit", "card", "login",
                    "access", "online", "service", "customer", "support", "team", "help",
                    "request", "attention", "important", "notification", "alert", "warning",
                    "suspicious", "activity", "detected", "verify", "verification", "identity",
                    "secure", "protect", "fraud", "unauthorized", "transaction", "account",
                    "balance", "statement", "bill", "invoice", "receipt", "due", "date",
                    # Thêm từ vựng phổ biến trong email lừa đảo
                    "limited", "offer", "free", "gift", "prize", "winner", "won", "million",
                    "dollar", "cash", "paypal", "discount", "sale", "virus", "antivirus",
                    "lottery", "jackpot", "customer", "service", "refund", "claim", "bonus"]
    
    # Thêm vào từ điển
    for idx, word in enumerate(common_words, 2):  # Bắt đầu từ 2 vì 0, 1 đã sử dụng
        if word not in vocab.token2idx:
            vocab.token2idx[word] = idx
            vocab.idx2token[idx] = word
    
    return vocab

# ============== LỚP SPAM DETECTOR ================
class SpamDetector:
    _instance = None  # Biến tĩnh để lưu trữ instance duy nhất
    
    @classmethod
    def get_instance(cls, model_path='models/best_model.pth'):
        """Triển khai Singleton pattern để tránh tải model nhiều lần"""
        if cls._instance is None:
            cls._instance = cls(model_path)
        return cls._instance
    
    def __init__(self, model_path='models/best_model.pth', max_len=200):
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.max_len = max_len
        self.model = None
        self.vocab = None
        
        try:
            # Đăng ký Vocabulary class với global namespace
            try:
                sys.modules['__main__'].Vocabulary = Vocabulary
            except:
                pass
            
            # Tìm model ở các vị trí khác nhau
            possible_paths = [
                model_path,
                os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'models', 'best_model.pth'),
                os.path.join(os.getcwd(), 'models', 'best_model.pth')
            ]
            
            model_file = None
            for path in possible_paths:
                if os.path.exists(path):
                    model_file = path
                    break
            
            if not model_file:
                print("[WARNING] Không tìm thấy model, sẽ sử dụng phương pháp dự phòng")
                return
                
            # Tải checkpoint
            checkpoint = None
            try:
                checkpoint = torch.load(model_file, map_location=self.device, weights_only=False)
            except:
                checkpoint = torch.load(model_file, map_location=self.device)
            
            if checkpoint is None:
                return
                
            # Lấy vocabulary từ checkpoint hoặc tạo mới
            if isinstance(checkpoint, dict) and 'vocab' in checkpoint:
                self.vocab = VocabularyAdapter(checkpoint['vocab'])
            else:
                self.vocab = VocabularyAdapter(create_vocab_from_scratch())
            
            vocab_size = len(self.vocab)
            
            # Khởi tạo model với tham số
            embedding_dim = checkpoint.get('embedding_dim', 300) if isinstance(checkpoint, dict) else 300
            hidden_dim = checkpoint.get('hidden_dim', 256) if isinstance(checkpoint, dict) else 256
            num_layers = checkpoint.get('num_layers', 2) if isinstance(checkpoint, dict) else 2
            output_dim = checkpoint.get('output_dim', 1) if isinstance(checkpoint, dict) else 1
            dropout = checkpoint.get('dropout', 0.5) if isinstance(checkpoint, dict) else 0.5
            bidirectional = checkpoint.get('bidirectional', True) if isinstance(checkpoint, dict) else True
            
            self.model = LSTMModel(
                vocab_size=vocab_size,
                embedding_dim=embedding_dim,
                hidden_dim=hidden_dim,
                num_layers=num_layers,
                output_dim=output_dim,
                dropout=dropout,
                bidirectional=bidirectional
            )
            
            # Tải trọng số
            if isinstance(checkpoint, dict) and 'model_state_dict' in checkpoint:
                self.model.load_state_dict(checkpoint['model_state_dict'])
            else:
                try:
                    self.model.load_state_dict(checkpoint)
                except:
                    print("[WARNING] Không thể tải trọng số model")
                    
            # Chuyển model sang device và đặt ở chế độ evaluation
            self.model.to(self.device)
            self.model.eval()
            
        except Exception as e:
            print(f"[ERROR] Lỗi khi tải model: {e}")
            self.model = None
            self.vocab = None
    
    def predict(self, text):
        """Dự đoán xem email có phải là spam hay không"""
        # Nếu không có model, sử dụng phương pháp fallback
        if self.model is None or self.vocab is None:
            return self.keyword_based_prediction(text)
            
        try:
            # Tiền xử lý văn bản
            processed_text = preprocess_text(text)
            
            # Kiểm tra xem văn bản có rỗng không
            if not processed_text:
                print("[WARNING] Văn bản rỗng sau khi tiền xử lý")
                return 0.1  # Trả về xác suất thấp cho văn bản rỗng
            
            # Chuyển tokens thành indices
            indices = [self.vocab[token] for token in processed_text]
            
            # Cắt hoặc padding để đạt max_len
            if len(indices) < self.max_len:
                indices = indices + [0] * (self.max_len - len(indices))  # <pad> token có index là 0
            else:
                indices = indices[:self.max_len]
            
            # Chuyển sang tensor
            text_tensor = torch.LongTensor([indices]).to(self.device)
            length_tensor = torch.LongTensor([min(len(processed_text), self.max_len)]).to(self.device)
            
            # Dự đoán
            with torch.no_grad():
                logits = self.model(text_tensor, length_tensor)
                # Xử lý trường hợp logits là float
                if isinstance(logits, float):
                    prediction = logits
                else:
                    logits = logits.squeeze()
                    prediction = torch.sigmoid(logits).item()
                    
                # Áp dụng quy tắc để cải thiện độ chính xác:
                if 0.4 <= prediction <= 0.6:
                    keyword_score = self.keyword_based_prediction(text)
                    if keyword_score > 0.7:
                        prediction = max(prediction, (prediction + keyword_score) / 2)
                    elif keyword_score < 0.3:
                        prediction = min(prediction, (prediction + keyword_score) / 2)
            
            print(f"[INFO] Dự đoán thành công với mô hình AI. Điểm spam: {prediction:.4f}")
            return prediction  # Trả về xác suất là spam (0-1)
        except Exception as e:
            print(f"[ERROR] Lỗi khi dự đoán: {e}")
            import traceback
            traceback.print_exc()
            # Nếu có lỗi, sử dụng phương pháp dự phòng dựa trên từ khóa
            return self.keyword_based_prediction(text)
    
    def keyword_based_prediction(self, text):
        """Phân tích dựa trên từ khóa khi model ML không khả dụng"""
        if not text or not isinstance(text, str):
            return 0.0
            
        # Chuyển text về chữ thường để dễ so sánh
        text = text.lower()
        
        # Danh sách các từ khóa phổ biến trong email lừa đảo/spam - CẢI TIẾN DANH SÁCH
        spam_keywords = [
            # Từ khóa liên quan đến tính khẩn cấp
            'urgent', 'immediate action', 'act now', 'limited time', 'deadline', 'expiration',
            'last chance', 'don\'t delay', 'hurry', 'khẩn cấp', 'không được bỏ lỡ',
            
            # Tiền bạc và cơ hội
            'lottery', 'winner', 'free money', 'million dollar', 'prize', 'jackpot', 'cash', 
            'investment opportunity', 'nigeria', 'inheritance', 'prince', 'loan', 'profit',
            'claim your prize', 'bank transfer', 'offshore', 'opportunity', 'fortune',
            'xổ số', 'trúng thưởng', 'tiền tỷ', 'bạn đã trúng', 'cơ hội đầu tư',
            
            # Ưu đãi và khuyến mãi đáng ngờ
            'congratulations', 'click here', 'offer', 'free', 'guaranteed', 'no risk',
            'best price', 'cash bonus', 'discount', 'special offer', 'exclusive deal',
            'limited offer', 'lifetime opportunity', 'free gift', 'premium', 'no cost',
            
            # Y tế và giảm cân
            'cialis', 'viagra', 'weight loss', 'lose weight', 'miracle cure', 'no medical exams',
            'medicine', 'drug', 'pharmacy', 'prescription', 'diet', 'fat', 'slim',
            
            # Tài chính
            'earn extra cash', 'eliminate debt', 'extra income', 'fast cash', 'for free', 
            'for just $', 'double your money', 'financial freedom', 'get rich quick',
            'debt free', 'cash advance', 'payday loan', 'installment', 'refinance',
            'for only', 'from home', 'gửi tiền', 'hidden assets', 'incredible deal',
            'money back', 'order now', 'please help', 'potential earnings', 'pure profit', 
            'risk-free', 'special promotion', 'supplies limited', 'take action now',
            'miễn phí', 'hành động ngay', 'cơ hội cuối cùng', 'thanh toán',
            
            # Bảo mật và tài khoản ngân hàng
            'verify', 'identity', 'suspicious', 'account', 'security', 'password', 
            'verify', 'bank', 'secure', 'unauthorized', 'access', 'credit card', 
            'authenticate', 'confirm', 'verification', 'validate', 'authorization',
            'bảo mật', 'ngân hàng quốc tế', 'thẻ tín dụng',
            'account blocked', 'suspended', 'verify identity', 'security alert',
            'password expired', 'login information', 'social security', 'update account',
            'suspicious activity', 'login details', 'personal details', 'credentials',
            
            # Làm việc tại nhà
            'work from home', 'no experience', 'guaranteed income', 'be your own boss',
            'make money online', 'earn money fast', 'income opportunity', 'residual income',
            
            # Các dấu hiệu lừa đảo khác
            'this is not spam', 'not spam', 'removed at any time', 'removal instructions', 
            'to be removed', 'to unsubscribe', 'this is not a scam', 'no scam', 'no spam', 
            'legitimate', 'this is legitimate', 'real thing', 'serious offer', 'serious business',
            'direct marketing', 'direct email', 'bulk email', 'mass email', 'opt in'
        ]
        
        # Đếm số lượng từ khóa xuất hiện và trọng số cho từng loại
        keyword_count = 0
        urgent_count = 0
        money_count = 0
        security_count = 0
        sensitive_info_count = 0
        matched_keywords = []

        # Phân tích ngữ cảnh sử dụng từ khóa
        for keyword in spam_keywords:
            if keyword in text:
                matched_keywords.append(keyword)
                keyword_count += 1

                if keyword in ['urgent', 'immediate action', 'act now', 'deadline', 'expiration', 'khẩn cấp']:
                    urgent_count += 1
                elif keyword in ['money', 'cash', 'bank', 'transfer', 'million', 'dollar', 'payment']:
                    money_count += 1
                elif keyword in ['security', 'secure', 'verify', 'validate', 'authenticate', 'bảo mật']:
                    security_count += 1
                elif keyword in ['password', 'credit card', 'account number', 'login', 'social security', 'thẻ tín dụng']:
                    sensitive_info_count += 1

        score = min(0.15 * keyword_count, 0.75)

        # Các yếu tố khác
        exclamation_count = text.count('!')
        if exclamation_count > 3:
            score += min(0.05 * (exclamation_count - 3), 0.15)

        words = text.split()
        uppercase_words = sum(1 for word in words if word.isupper() and len(word) > 2)
        if uppercase_words > 3:
            score += min(0.05 * (uppercase_words - 3), 0.2)

        if '$' in text or '€' in text or '£' in text or 'tiền' in text or 'đô la' in text:
            score += 0.15

        url_count = text.count('http') + text.count('www') + text.count('.com') + text.count('.net')
        if url_count > 1:
            score += min(0.1 * url_count, 0.25)

        suspicious_patterns = ['click here', 'click this link', 'nhấp vào đây', 'bấm vào liên kết']
        for pattern in suspicious_patterns:
            if pattern in text.lower():
                score += 0.15
                break

        if len(text) < 100:
            score *= (len(text) / 100)

        if urgent_count > 0:
            score += min(0.2 * urgent_count, 0.4)

        if sensitive_info_count > 0:
            score += min(0.25 * sensitive_info_count, 0.5)

        if urgent_count > 0 and sensitive_info_count > 0:
            score += 0.2

        if money_count > 0 and sensitive_info_count > 0:
            score += 0.2

        sentences = re.split(r'[.!?]', text)
        short_sentences = sum(1 for s in sentences if len(s.strip()) < 5)
        if short_sentences > len(sentences) * 0.5:
            score += 0.1

        score = min(score, 0.98)

        # 🔥 Trả về cả score và danh sách từ khóa
        return score, matched_keywords


# Hàm lấy detector đã được tối ưu (singleton)
def get_spam_detector():
    return SpamDetector.get_instance()

# Lớp fallback đơn giản khi cần thiết
class FallbackSpamDetector:
    def predict(self, text):
        """Dự đoán spam dựa trên từ khóa khi không có model AI"""
        temp_detector = SpamDetector.__new__(SpamDetector)
        temp_detector.device = torch.device('cpu')
        temp_detector.model = None 
        temp_detector.vocab = None
        return temp_detector.keyword_based_prediction(text) 