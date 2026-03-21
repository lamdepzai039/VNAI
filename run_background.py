import subprocess
import os
import sys
import time
import webbrowser
import socket

def log_message(msg):
    basedir = os.path.abspath(os.path.dirname(__file__))
    log_file = os.path.join(basedir, "service_log.txt")
    timestamp = time.strftime('%H:%M:%S %d/%m/%Y')
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {msg}\n")
    print(msg)

def is_port_open(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)
        return s.connect_ex(('127.0.0.1', port)) == 0

def kill_processes():
    log_message("Đang dọn dẹp các tiến trình cũ...")
    # Kill SSH nếu còn sót lại
    subprocess.run(['taskkill', '/f', '/im', 'ssh.exe'], capture_output=True)
    try:
        # Kill Flask (app.py)
        output = subprocess.check_output(['wmic', 'process', 'where', 'name="python.exe"', 'get', 'processid,commandline'], text=True)
        for line in output.splitlines():
            if "app.py" in line:
                import re
                pid_match = re.search(r'(\d+)\s*$', line.strip())
                if pid_match:
                    pid = pid_match.group(1)
                    subprocess.run(['taskkill', '/f', '/pid', pid], capture_output=True)
                    log_message(f"Đã tắt Flask server cũ (PID: {pid})")
    except: pass
    time.sleep(1)

def check_single_instance():
    import tempfile
    lock_file = os.path.join(tempfile.gettempdir(), "vnai_local_only.lock")
    if os.path.exists(lock_file):
        try:
            os.remove(lock_file)
        except:
            sys.exit(0)
    open(lock_file, 'w').close()

def start_local_only():
    basedir = os.path.abspath(os.path.dirname(__file__))
    python_path = os.path.join(basedir, ".venv", "Scripts", "python.exe")
    app_path = os.path.join(basedir, "app.py")
    link_file = os.path.join(basedir, "LINK_TRUY_CAP_AI.txt")
    
    if not os.path.exists(python_path):
        log_message("Lỗi: Không tìm thấy môi trường ảo.")
        return

    log_message("--- KHỞI ĐỘNG AI CHẾ ĐỘ NỘI BỘ (127.0.0.1) ---")
    kill_processes()

    # 1. Khởi động Flask Server ẩn hoàn toàn
    try:
        subprocess.Popen([python_path, app_path], 
                         creationflags=0x08000000, # CREATE_NO_WINDOW
                         stdout=subprocess.DEVNULL, 
                         stderr=subprocess.DEVNULL)
        log_message("1. Server nội bộ: Đang khởi chạy...")
        
        # 2. Ghi link vào file text cho người dùng
        local_url = "http://127.0.0.1:5000/"
        with open(link_file, "w", encoding="utf-8") as f:
            f.write(f"LINK AI CỦA BẠN (Chỉ dùng trên máy này):\n\n")
            f.write(local_url)
            f.write(f"\n\nCập nhật lúc: {time.strftime('%H:%M:%S %d/%m/%Y')}")

        # 3. Chờ server sẵn sàng và tự động mở trình duyệt
        for _ in range(20):
            if is_port_open(5000):
                log_message(f"--- THÀNH CÔNG! Đã mở link: {local_url} ---")
                webbrowser.open(local_url)
                break
            time.sleep(1)
        else:
            log_message("Cảnh báo: Server khởi động hơi chậm, bạn hãy thử tải lại trang sau giây lát.")

    except Exception as e:
        log_message(f"Lỗi: {e}")

if __name__ == "__main__":
    check_single_instance()
    start_local_only()
