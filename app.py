import os
import time
import requests
import google.generativeai as genai
from datetime import datetime
from flask import Flask, render_template, request, jsonify, session as flask_session, redirect, url_for, Response, stream_with_context
from flask_sqlalchemy import SQLAlchemy
import json
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash
from openai import OpenAI

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
SYSTEM_INSTRUCTION = """Bạn là VNAI - Trợ lý AI cao cấp được tối ưu hóa cho người Việt.
QUY TẮC QUAN TRỌNG:
1. KHẢ NĂNG THỊ GIÁC: Bạn có thể nhìn và phân tích hình ảnh cực tốt. Nếu người dùng gửi ảnh, hãy giải quyết yêu cầu của họ ngay (dịch thuật, giải toán, giải thích code...).
2. PHONG CÁCH PHẢN HỒI: Trả lời mượt mà, chuyên nghiệp, sử dụng Markdown (bảng, danh sách, in đậm) và KaTeX cho toán học.
3. CHẾ ĐỘ NGHIÊN CỨU (DEEP RESEARCH): Khi thấy tiền tố [Deep Research], hãy:
   - Trình bày như một chuyên gia phân tích dữ liệu.
   - Luôn có các mục: Tổng quan, Phân tích chi tiết, Ưu/Nhược điểm, và Kết luận.
   - Giả lập việc tìm kiếm thông tin từ nhiều nguồn tin cậy.
4. CHẾ ĐỘ LẬP TRÌNH (CODEX): Khi hỗ trợ code, hãy viết code sạch, có giải thích từng bước và tối ưu hiệu suất.
5. NGÔN NGỮ: Luôn ưu tiên Tiếng Việt trừ khi được yêu cầu khác."""

def get_ai_response(user_message, history_list, preferred_model="gpt", image_data=None):
    key = key_manager.get_working_key()
    if not key: return None

    print(f"--- Debug Vision ---")
    print(f"Model: {preferred_model}, Has Image: {image_data is not None}")

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
        
        parts.append(user_message if user_message else "Phân tích nội dung hình ảnh này.")

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
            
            # Gửi yêu cầu Vision
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
                        {"type": "text", "text": user_message if user_message else "Phân tích nội dung hình ảnh này."},
                        {"type": "image_url", "image_url": {"url": image_url}}
                    ]
                })
                completion = client.chat.completions.create(model="gpt-4o", messages=messages, temperature=0.4)
            else:
                for h in history_list:
                    messages.append({"role": h['role'], "content": h['content']})
                messages.append({"role": "user", "content": user_message})
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

def get_fallback_ai(user_message, history_list):
    # Dùng Pollinations với danh sách model đa dạng (Resilient)
    models = ["openai", "mistral", "qwen", "llama", "searchgpt"]
    
    messages = [{"role": "system", "content": SYSTEM_INSTRUCTION}]
    for h in history_list[-4:]:
        messages.append({"role": h['role'], "content": h['content']})
    messages.append({"role": "user", "content": user_message})

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
        safe_msg = quote(user_message[:500])
        r = requests.get(f"https://text.pollinations.ai/{safe_msg}?model=openai", timeout=10)
        if r.status_code == 200: return r.text
    except: pass

    return None

def get_ai_response_stream(user_message, history_list, preferred_model="gpt", image_data=None, custom_system=None):
    if custom_system is None: custom_system = SYSTEM_INSTRUCTION
    key = key_manager.get_working_key()
    if not key: yield "error:No working API key found." ; return

    try:
        if preferred_model == "gemini" and not key.startswith("sk-"):
            genai.configure(api_key=key)
            model = genai.GenerativeModel(model_name="gemini-1.5-flash", system_instruction=custom_system)
            
            parts = []
            if image_data:
                if "data:" in image_data and ";base64," in image_data:
                    mime_type = image_data.split(";")[0].split(":")[1]
                    raw_data = image_data.split(",")[1]
                else:
                    mime_type = "image/jpeg"
                    raw_data = image_data
                parts.append({"mime_type": mime_type, "data": raw_data})
            
            parts.append(user_message if user_message else "Phân tích nội dung hình ảnh này.")
            
            response = model.generate_content(parts, stream=True)
            for chunk in response:
                if chunk.text: yield chunk.text
        
        elif key.startswith("sk-"):
            client = OpenAI(api_key=key)
            messages = [{"role": "system", "content": custom_system}]
            
            if image_data:
                image_url = image_data if image_data.startswith("data:") else f"data:image/jpeg;base64,{image_data}"
                messages.append({
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_message if user_message else "Phân tích nội dung hình ảnh này."},
                        {"type": "image_url", "image_url": {"url": image_url}}
                    ]
                })
            else:
                for h in history_list:
                    messages.append({"role": h['role'], "content": h['content']})
                messages.append({"role": "user", "content": user_message})
            
            stream = client.chat.completions.create(model="gpt-4o", messages=messages, stream=True)
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        else:
            # Fallback to Pollinations
            yield get_fallback_ai(user_message, history_list)
            
    except Exception as e:
        print(f"Streaming Error: {e}")
        yield f"error: {str(e)}"

# --- Routes ---
@app.route("/generate_title/<int:conv_id>", methods=["POST"])
def generate_title(conv_id):
    if 'user_id' not in flask_session: return jsonify({"error": "Unauthorized"}), 401
    
    conv = Conversation.query.get(conv_id)
    if not conv or conv.user_id != flask_session['user_id']:
        return jsonify({"error": "Not found"}), 404
        
    # Lấy tin nhắn đầu tiên của user để tạo tiêu đề
    first_msg = Message.query.filter_by(conversation_id=conv_id, role='user').first()
    if not first_msg: return jsonify({"status": "no_messages"})
    
    key = key_manager.get_working_key()
    if not key: return jsonify({"error": "No key"}), 500
    
    try:
        title_prompt = f"Tạo một tiêu đề cực kỳ ngắn gọn (tối đa 5 từ) cho cuộc trò chuyện bắt đầu bằng câu này: '{first_msg.content}'. Trả lời chỉ bằng tiêu đề, không thêm gì khác."
        
        if key.startswith("sk-"):
            client = OpenAI(api_key=key)
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": title_prompt}],
                max_tokens=20
            )
            new_title = resp.choices[0].message.content.strip().strip('"')
        else:
            genai.configure(api_key=key)
            model = genai.GenerativeModel("gemini-1.5-flash")
            resp = model.generate_content(title_prompt)
            new_title = resp.text.strip().strip('"')
            
        if new_title:
            conv.title = new_title
            db.session.commit()
            return jsonify({"title": new_title})
            
    except Exception as e:
        print(f"Auto-title error: {e}")
        
    return jsonify({"status": "failed"})

@app.route("/chat_stream", methods=["POST"])
def chat_stream():
    if 'user_id' not in flask_session: return jsonify({"error": "Unauthorized"}), 401
    
    data = request.json
    msg_text = data.get("message")
    image_data = data.get("image")
    conv_id = data.get("conversation_id")
    preferred_model = data.get("selected_model", "gpt")
    personalization = data.get("personalization", {})

    # Tích hợp cá nhân hóa vào SYSTEM_INSTRUCTION
    custom_system = SYSTEM_INSTRUCTION
    if personalization:
        instr = personalization.get("instructions", "")
        nickname = personalization.get("nickname", "")
        job = personalization.get("job", "")
        bio = personalization.get("bio", "")
        tone = personalization.get("tone", "default")
        
        personal_block = "\n\n--- THÔNG TIN CÁ NHÂN HÓA NGƯỜI DÙNG ---\n"
        if nickname: personal_block += f"- Tên gọi người dùng: {nickname}\n"
        if job: personal_block += f"- Nghề nghiệp: {job}\n"
        if bio: personal_block += f"- Thông tin thêm: {bio}\n"
        if tone != "default":
            tones = {"professional": "Chuyên nghiệp", "friendly": "Thân thiện", "direct": "Thẳng thắn", "creative": "Sáng tạo"}
            personal_block += f"- Phong cách phản hồi: {tones.get(tone, tone)}\n"
        if instr: personal_block += f"- Hướng dẫn đặc biệt: {instr}\n"
        
        custom_system += personal_block

    if not conv_id:
        conv = Conversation(user_id=flask_session['user_id'])
        db.session.add(conv)
        db.session.commit()
        conv_id = conv.id
    else:
        conv = Conversation.query.get(conv_id)

    # Save user message
    user_msg = Message(content=msg_text if msg_text else "[Hình ảnh]", role='user', conversation_id=conv_id)
    db.session.add(user_msg)
    db.session.commit()

    # Get history
    history = Message.query.filter_by(conversation_id=conv_id).order_by(Message.timestamp.desc()).limit(10).all()
    history_list = [{"role": m.role, "content": m.content} for m in reversed(history[:-1])]

    def generate():
        full_response = ""
        # Sử dụng custom_system thay vì SYSTEM_INSTRUCTION mặc định
        for chunk in get_ai_response_stream(msg_text, history_list, preferred_model, image_data, custom_system):
            if chunk.startswith("error:"):
                yield f"data: {json.dumps({'error': chunk[6:]})}\n\n"
                return
            full_response += chunk
            yield f"data: {json.dumps({'content': chunk, 'conversation_id': conv_id})}\n\n"
        
        # Save AI response at the end
        with app.app_context():
            ai_msg = Message(content=full_response, role='assistant', conversation_id=conv_id)
            db.session.add(ai_msg)
            current_conv = Conversation.query.get(conv_id)
            if current_conv.title == "Cuộc trò chuyện mới" and msg_text:
                current_conv.title = msg_text[:30] + "..."
            db.session.commit()
            yield f"data: {json.dumps({'done': True, 'title': current_conv.title})}\n\n"

    return Response(stream_with_context(generate()), mimetype='text/event-stream')

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
    ai_resp = get_ai_response(msg_text, history_list, preferred_model, image_data)
    
    if not ai_resp:
        print("Tất cả Key chính đều lỗi hoặc hết hạn mức. Đang thử Pollinations...")
        ai_resp = get_fallback_ai(msg_text, history_list)

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
