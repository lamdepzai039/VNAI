import os
from pyngrok import ngrok
from app import app
from dotenv import load_dotenv

load_dotenv()

def start_ai_online():
    # 1. Thiet lap cong (Port)
    port = 5000
    
    # 2. Mo ket noi ra Internet (Public Tunnel)
    # Ngrok se cho ban mot link mien phi co dang: https://xxxx-xxxx.ngrok-free.app
    print("\n" + "="*50)
    print("🚀 DANG KHOI TAO LINK TRUY CAP AI TOAN CAU...")
    print("="*50)
    
    try:
        public_url = ngrok.connect(port).public_url
        print(f"\n✅ AI CUA BAN DA ONLINE!")
        print(f"👉 LINK TRUY CAP: {public_url}")
        print("\n(Hay gui link nay cho ban be hoac mo tren dien thoai)")
        print("="*50 + "\n")
        
        # Luu link vao file de ban de tim
        with open("LINK_TRUY_CAP_AI.txt", "w", encoding="utf-8") as f:
            f.write(f"Link truy cap AI cua ban (Cap nhat luc {os.popen('date /t').read().strip()}): \n{public_url}")

        # 3. Chay Flask App
        app.run(port=port, debug=False, use_reloader=False)
        
    except Exception as e:
        print(f"❌ LOI KET NOI: {e}")
        print("Co the ban can Authtoken tu ngrok.com (Mien phi)")

if __name__ == "__main__":
    start_ai_online()
