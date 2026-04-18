# 🚀 Hướng dẫn Triển khai VNAI lên Cloud (Render.com)

Để AI của bạn có thể sử dụng ở mọi nơi và tự động cập nhật, hãy làm theo các bước đơn giản sau:

### **Bước 1: Cài đặt Git (Nếu chưa có)**
1. Tải và cài đặt Git tại: [git-scm.com](https://git-scm.com/downloads)
2. Sau khi cài đặt, mở Terminal trong Trae và chạy lệnh:
   ```bash
   git init
   git add .
   git commit -m "Initial commit - Ready for deploy"
   ```

### **Bước 2: Đưa code lên GitHub**
1. Truy cập [github.com](https://github.com/) và tạo một Repository mới (ví dụ: `vn-ai-assistant`).
2. Copy link repository của bạn (dạng `https://github.com/user/repo.git`).
3. Quay lại Terminal và chạy:
   ```bash
   git remote add origin <LINK_GITHUB_CUA_BAN>
   git push -u origin main
   ```

### **Bước 3: Kết nối với Render.com (Tự động hóa)**
1. Đăng ký tài khoản tại [Render.com](https://render.com/).
2. Chọn **New +** -> **Web Service**.
3. Chọn Repository GitHub bạn vừa tải lên.
4. Cấu hình các thông số sau:
   - **Name**: `vn-ai-assistant` (hoặc tên bất kỳ)
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
5. **Quan trọng: Thêm biến môi trường (Environment Variables)**
   Nhấn vào tab **Environment** và thêm các biến sau từ file `.env` của bạn:
   - `GEMINI_API_KEYS`: (Danh sách key của bạn)
   - `FLASK_SECRET_KEY`: (Một chuỗi ký tự bất kỳ để bảo mật session)
   - `PORT`: `10000` (Render sẽ tự động quản lý, nhưng bạn có thể để mặc định)

### **✨ Thành quả**
- Sau khi nhấn **Deploy**, Render sẽ cấp cho bạn một đường dẫn (ví dụ: `https://vn-ai-assistant.onrender.com`).
- **Tự động cập nhật**: Từ giờ, mỗi khi bạn sửa code trong Trae, bạn chỉ cần chạy lệnh sau để AI tự động cập nhật trên toàn thế giới:
  ```bash
  git add .
  git commit -m "Cập nhật tính năng mới"
  git push
  ```

---
*Lưu ý: Vì sử dụng SQLite, dữ liệu người dùng và lịch sử chat sẽ bị xóa mỗi khi bạn cập nhật code (deploy lại). Để lưu trữ vĩnh viễn, bạn nên nâng cấp lên cơ sở dữ liệu PostgreSQL (Render có hỗ trợ miễn phí).*