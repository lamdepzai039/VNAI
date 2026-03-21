import os
import google.generativeai as genai
from dotenv import load_dotenv

def main():
    # Load environment variables from .env file
    load_dotenv()
    
    # Get the API key from environment variable
    api_key = os.getenv("GEMINI_API_KEY")
    
    if not api_key:
        print("Error: GEMINI_API_KEY not found in .env file.")
        print("Please create a .env file with 'GEMINI_API_KEY=your_api_key_here'")
        return

    # Configure the Gemini API
    genai.configure(api_key=api_key)
    
    # Initialize the model
    model = genai.GenerativeModel("gemini-1.5-flash")
    
    print("Welcome to your AI Chatbot! Type 'quit' to exit.")
    
    chat = model.start_chat(history=[])
    
    while True:
        user_input = input("You: ")
        
        if user_input.lower() in ["quit", "exit"]:
            print("Goodbye!")
            break
            
        try:
            response = chat.send_message(user_input)
            print(f"AI: {response.text}")
        except Exception as e:
            error_msg = str(e)
            if "503" in error_msg or "system under load" in error_msg.lower():
                print("Hệ thống đang quá tải (System under load). Vui lòng đợi 5-10 giây rồi thử lại!")
            else:
                print(f"Error: {e}")

if __name__ == "__main__":
    main()
