import os
import time
import requests
import google.generativeai as genai
from datetime import datetime
from flask import Flask, render_template, request, jsonify, session as flask_session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash
from openai import OpenAI
try:
    from googlesearch import search
except ImportError:
    search = None

# Load environment
basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

print("--- VNAI: HE THONG DANG KHOI DONG ---")
print(f"--- VNAI: PORT DUOC CAP = {os.environ.get('PORT')} ---")

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "super-secret-key-123")

# Database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'ai_chatbot.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    conversations = db.relationship('Conversation', backref='user', lazy=True)

class Conversation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), default="Cuộc trò chuyện mới")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    messages = db.relationship('Message', backref='conversation', lazy=True, cascade="all, delete-orphan")

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    role = db.Column(db.String(20), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversation.id'), nullable=False)

with app.app_context():
    db.create_all()

# --- AI Key Manager ---
class AIKeyManager:
    def __init__(self):
        gemini_keys = os.getenv("GEMINI_API_KEYS", "").split(",")
        openai_keys = [k for k in [os.getenv("GEMINI_API_KEY")] if k and k.startswith("sk-")]
        self.keys = [k.strip() for k in (gemini_keys + openai_keys) if k.strip()]
        self.cooldowns = {}

    def get_working_key(self):
        now = time.time()
        for key in self.keys:
            if key not in self.cooldowns or now > self.cooldowns[key]:
                return key
        return None

    def mark_cooldown(self, key, seconds=60):
        self.cooldowns[key] = time.time() + seconds

key_manager = AIKeyManager()

def perform_web_search(query, num_results=5):
    """Thực hiện tìm kiếm trên web và trả về các đoạn nội dung ngắn"""
    if not search:
        return "Lỗi: Thư viện googlesearch chưa được cài đặt."
    
    print(f"--- Đang tìm kiếm trên web: {query} ---")
    results = []
    try:
        # Lấy các URL từ Google
        search_results = search(query, num_results=num_results, lang="vi")
        for url in search_results:
            results.append(url)
        
        if not results:
            return "Không tìm thấy kết quả nào trên web."
            
        context = "Dưới đây là một số nguồn tin từ web:\n"
        for i, url in enumerate(results, 1):
            context += f"{i}. Nguồn: {url}\n"
        return context
    except Exception as e:
        print(f"Lỗi tìm kiếm: {e}")
        return f"Lỗi tìm kiếm: {str(e)}"

SYSTEM_INSTRUCTION = """Bạn là một trợ lý AI thông minh, đa năng. 
QUY TẮC QUAN TRỌNG NHẤT: 
1. BẠN CÓ KHẢ NĂNG NHÌN VÀ PHÂN TÍCH HÌNH ẢNH. 
- Khi người dùng gửi ảnh, bạn PHẢI phân tích và trả lời dựa trên nội dung ảnh đó.
2. BẠN CÓ KHẢ NĂNG TÌM KIẾM THÔNG TIN TRÊN WEB.
- Khi người dùng yêu cầu tìm kiếm hoặc hỏi về thông tin mới nhất/thực tế, hãy sử dụng dữ liệu từ kết quả tìm kiếm được cung cấp.
- Tuyệt đối KHÔNG ĐƯỢC trả lời là 'không thể xem ảnh' hay 'không có chức năng dịch ảnh'.
- Nếu là văn bản (Tiếng Trung, Anh...), hãy dịch sang Tiếng Việt.
- Nếu là code/toán, hãy giải chi tiết.
Hãy luôn trả lời bằng Tiếng Việt mượt mà."""

def get_ai_response(user_message, history_list, preferred_model="gpt", image_data=None, search_context=None):
    key = key_manager.get_working_key()
    if not key: return None

    # Nếu có dữ liệu tìm kiếm, gộp vào message
    final_user_message = user_message
    if search_context:
        final_user_message = f"Dữ liệu tìm kiếm được từ Web:\n{search_context}\n\nCâu hỏi của người dùng: {user_message}"

    print(f"--- Debug Vision ---")
    print(f"Model: {preferred_model}, Has Image: {image_data is not None}, Has Search: {search_context is not None}")

    try:
        # Chuẩn bị dữ liệu cho Gemini
        parts = []
        if image_data:
            try:
                # Xử lý Base64 chuẩn cho Gemini
                mime_type = "image/jpeg"
                if "data:" in image_data and ";base64," in image_data:
                    parts_img = image_data.split(",")
                    mime_type = parts_img[0].split(";")[0].split(":")[1]
                    raw_data = parts_img[1]
                else:
                    raw_data = image_data
                
                parts.append({
                    "mime_type": mime_type,
                    "data": raw_data
                })
                print(f"Đã nạp ảnh vào parts (Mime: {mime_type})")
            except Exception as img_err:
                print(f"Lỗi chuẩn bị ảnh Gemini: {img_err}")
        
        parts.append(final_user_message if final_user_message else "Phân tích nội dung hình ảnh này.")

        # Cấu hình tham số
        generation_config = {
            "temperature": 0.4,
            "top_p": 0.95,
            "max_output_tokens": 8192,
        }

        # Nếu người dùng chọn Gemini và ta có Key Gemini
        if preferred_model == "gemini" and not key.startswith("sk-"):
            genai.configure(api_key=key)
            model = genai.GenerativeModel(
                model_name="gemini-1.5-flash",
                system_instruction=SYSTEM_INSTRUCTION
            )
            
            # Gửi yêu cầu Vision/Search
            response = model.generate_content(parts, generation_config=generation_config)
            return response.text
        
        # Nếu người dùng chọn GPT hoặc chỉ có Key OpenAI
        elif key.startswith("sk-"):
            client = OpenAI(api_key=key)
            messages = [{"role": "system", "content": SYSTEM_INSTRUCTION}]
            
            if image_data:
                # Chuẩn bị URL Base64 cho OpenAI
                image_url = image_data if image_data.startswith("data:") else f"data:image/jpeg;base64,{image_data}"
                
                messages.append({
                    "role": "user",
                    "content": [
                        {"type": "text", "text": final_user_message if final_user_message else "Phân tích nội dung hình ảnh này."},
                        {"type": "image_url", "image_url": {"url": image_url}}
                    ]
                })
                completion = client.chat.completions.create(model="gpt-4o", messages=messages, temperature=0.4)
            else:
                for h in history_list:
                    messages.append({"role": h['role'], "content": h['content']})
                messages.append({"role": "user", "content": final_user_message})
                completion = client.chat.completions.create(model="gpt-4o", messages=messages, temperature=0.4)
            
            return completion.choices[0].message.content
        
        # Mặc định Fallback về Gemini Flash
        else:
            genai.configure(api_key=key)
            model = genai.GenerativeModel(
                model_name="gemini-1.5-flash",
                system_instruction=SYSTEM_INSTRUCTION
            )
            response = model.generate_content(parts, generation_config=generation_config)
            return response.text

    except Exception as e:
        print(f"Lỗi Key {key[:10]}: {e}")
        key_manager.mark_cooldown(key)
        return None

def get_fallback_ai(user_message, history_list, search_context=None):
    # Dùng Pollinations với danh sách model đa dạng (Resilient)
    models = ["searchgpt", "openai", "mistral", "qwen", "llama"]
    
    final_user_message = user_message
    if search_context:
        final_user_message = f"Dữ liệu tìm kiếm được từ Web:\n{search_context}\n\nCâu hỏi của người dùng: {user_message}"

    messages = [{"role": "system", "content": SYSTEM_INSTRUCTION}]
    for h in history_list[-4:]:
        messages.append({"role": h['role'], "content": h['content']})
    messages.append({"role": "user", "content": final_user_message})

    # Thử gọi Pollinations POST
    for m in models:
        try:
            print(f"Thử dự phòng {m}...")
            r = requests.post("https://text.pollinations.ai/", 
                              json={"messages": messages, "model": m, "stream": False}, 
                              timeout=12)
            if r.status_code == 200 and r.text.strip():
                return r.text
        except: continue

    # Cứu cánh cuối cùng: Pollinations GET (Dành cho tin nhắn ngắn)
    try:
        from urllib.parse import quote
        safe_msg = quote(final_user_message[:500])
        r = requests.get(f"https://text.pollinations.ai/{safe_msg}?model=openai", timeout=10)
        if r.status_code == 200: return r.text
    except: pass

    return None

# --- Routes ---
@app.route("/")
def index():
    try:
        if 'user_id' not in flask_session: return render_template("login.html")
        return render_template("index.html", user_name=flask_session.get('user_name'))
    except Exception as e:
        return f"Lỗi Render Template: {str(e)}", 500

@app.route("/ping")
def ping():
    return "VNAI Server is Running!", 200

@app.errorhandler(404)
def page_not_found(e):
    return f"VNAI Flask 404: Không tìm thấy đường dẫn này -> {request.path}", 404

@app.route("/login", methods=["POST"])
def login():
    data = request.json
    user = User.query.filter_by(email=data.get("email")).first()
    if user and check_password_hash(user.password_hash, data.get("password")):
        flask_session['user_id'] = user.id
        flask_session['user_name'] = user.name
        return jsonify({"status": "success"})
    return jsonify({"error": "Sai email hoặc mật khẩu"}), 401

@app.route("/register", methods=["POST"])
def register():
    data = request.json
    if User.query.filter_by(email=data.get("email")).first():
        return jsonify({"error": "Email đã tồn tại"}), 400
    user = User(name=data.get("name"), email=data.get("email"), password_hash=generate_password_hash(data.get("password")))
    db.session.add(user)
    db.session.commit()
    return jsonify({"status": "success"})

@app.route("/logout")
def logout():
    flask_session.clear()
    return redirect(url_for('index'))

@app.route("/history")
def history():
    if 'user_id' not in flask_session: return jsonify([]), 401
    convs = Conversation.query.filter_by(user_id=flask_session['user_id']).order_by(Conversation.created_at.desc()).all()
    return jsonify([{"id": c.id, "title": c.title} for c in convs])

@app.route("/messages/<int:id>")
def messages(id):
    if 'user_id' not in flask_session: return jsonify([]), 401
    msgs = Message.query.filter_by(conversation_id=id).order_by(Message.timestamp.asc()).all()
    return jsonify([{"content": m.content, "role": m.role} for m in msgs])

@app.route("/chat", methods=["POST"])
def chat():
    if 'user_id' not in flask_session: return jsonify({"error": "Unauthorized"}), 401
    
    data = request.json
    msg_text = data.get("message")
    image_data = data.get("image")
    conv_id = data.get("conversation_id")
    only_save = data.get("only_save", False)

    if conv_id:
        conv = Conversation.query.get(conv_id)
    else:
        conv = Conversation(user_id=flask_session['user_id'])
        db.session.add(conv)
        db.session.commit()

    # Save user message (if there's an image, we could store its placeholder or base64, but for now we just save text)
    user_msg = Message(content=msg_text if msg_text else "[Hình ảnh]", role='user', conversation_id=conv.id)
    db.session.add(user_msg)
    db.session.commit()

    if only_save:
        return jsonify({"conversation_id": conv.id, "title": conv.title})

    # AI Logic for Fallback
    history = Message.query.filter_by(conversation_id=conv.id).order_by(Message.timestamp.desc()).limit(10).all()
    history_list = [{"role": m.role, "content": m.content} for m in reversed(history[:-1])]
    
    preferred_model = data.get("selected_model", "gpt")
    
    # Logic Web Search (Deep Research)
    search_context = None
    if msg_text and ("[Deep Research]" in msg_text or "tìm trên mạng" in msg_text.lower() or "search web" in msg_text.lower()):
        search_query = msg_text.replace("[Deep Research]", "").strip()
        search_context = perform_web_search(search_query)

    ai_resp = get_ai_response(msg_text, history_list, preferred_model, image_data, search_context)
    
    if not ai_resp:
        print("Tất cả Key chính đều lỗi hoặc hết hạn mức. Đang thử Pollinations...")
        ai_resp = get_fallback_ai(msg_text, history_list, search_context)

    if ai_resp:
        # Làm sạch đáp án (xóa các thông báo lỗi nếu AI vô tình trả về)
        if len(ai_resp.strip()) < 5 and ("error" in ai_resp.lower() or "bận" in ai_resp):
            return jsonify({"error": "AI bận"}), 503
            
        ai_msg = Message(content=ai_resp, role='assistant', conversation_id=conv.id)
        db.session.add(ai_msg)
        if conv.title == "Cuộc trò chuyện mới": conv.title = msg_text[:30] + "..."
        db.session.commit()
        return jsonify({"response": ai_resp, "conversation_id": conv.id})
    
    return jsonify({"error": "Hệ thống AI đang bảo trì. Vui lòng thử lại sau vài giây!"}), 503

@app.route("/save_ai_message", methods=["POST"])
def save_ai_message():
    data = request.json
    conv = Conversation.query.get(data.get("conversation_id"))
    if conv:
        ai_msg = Message(content=data.get("content"), role='assistant', conversation_id=conv.id)
        db.session.add(ai_msg)
        if conv.title == "Cuộc trò chuyện mới": conv.title = data.get("content")[:30] + "..."
        db.session.commit()
    return jsonify({"status": "success"})

@app.route("/rename_conversation/<int:id>", methods=["POST"])
def rename_conversation(id):
    if 'user_id' not in flask_session: return jsonify({"error": "Unauthorized"}), 401
    data = request.json
    conv = Conversation.query.get(id)
    if conv and conv.user_id == flask_session['user_id']:
        conv.title = data.get("title")
        db.session.commit()
        return jsonify({"status": "success"})
    return jsonify({"error": "Không tìm thấy đoạn chat"}), 404

@app.route("/delete_conversation/<int:id>", methods=["DELETE"])
def delete_conversation(id):
    if 'user_id' not in flask_session: return jsonify({"error": "Unauthorized"}), 401
    conv = Conversation.query.get(id)
    if conv and conv.user_id == flask_session['user_id']:
        db.session.delete(conv)
        db.session.commit()
        return jsonify({"status": "success"})
    return jsonify({"error": "Không tìm thấy đoạn chat"}), 404

if __name__ == '__main__':
    # Lấy port từ biến môi trường (cho Cloud) hoặc mặc định 5000 (cho Local)
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
