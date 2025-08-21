import google.generativeai as genai
from tools import analyze_image_with_query
from dotenv import load_dotenv
import os
from PIL import Image

load_dotenv()

# Configure with your variable name
def configure_gemini():
    api_key = os.getenv("GEMINI_API_KEY")  # Using your variable name
    if api_key:
        genai.configure(api_key=api_key)
        return True
    return False

configure_gemini()

# Enhanced system prompt for Apex
system_prompt = """You are Apex — a witty, clever, and helpful AI assistant.
Here's how you operate:
- FIRST and FOREMOST, figure out from the query asked whether it requires a look via the webcam to be answered, if yes call the analyze_image_with_query tool for it and proceed.
- Don't ask for permission to look through the webcam, or say that you need to call the tool to take a peek — call it straight away. ALWAYS call the required tools if a photo is needed.
- When the user asks something which could only be answered by taking a photo, call the analyze_image_with_query tool.
- Always present results (if they come from a tool) in a natural, witty, and human-sounding way — like Apex is speaking, not a machine.
- Make every interaction feel smart, snappy, and personable. Got it? Let's charm your master!
"""

model = genai.GenerativeModel("gemini-1.5-flash")

def ask_apex(user_query, current_frame=None):
    """Main function to process user queries with Apex personality"""
    
    # Check if API key is available
    if not os.getenv("GEMINI_API_KEY"):
        return "❌ Gemini API key not available for AI processing"
    
    # Enhanced keyword detection for vision needs
    vision_keywords = [
        "look", "see", "image", "photo", "webcam", "camera", "recognize", 
        "analyze", "detect", "what's", "describe", "identify", "show", 
        "appearance", "wearing", "holding", "behind", "front", "color",
        "text", "read", "sign", "person", "face", "object", "thing", "do i"
    ]
    
    needs_vision = any(keyword in user_query.lower() for keyword in vision_keywords)
    
    if needs_vision and current_frame is not None:
        try:
            # Use current frame directly
            image = Image.fromarray(current_frame)
            response = model.generate_content([user_query, image])
            return f"Apex here! 👁️ Just took a look, and here's what I found:\n\n{response.text}"
        except Exception as e:
            return f"I tried to analyze the image but encountered an issue: {str(e)}"
    
    else:
        # Regular conversation without vision
        try:
            chat = model.start_chat(history=[
                {"role": "user", "parts": [system_prompt]},
            ])
            response = chat.send_message(user_query)
            return f"Apex here! 🤖 {response.text}"
        except Exception as e:
            return f"I encountered an error processing your request: {str(e)}"

# Test function
def test_apex():
    """Test function to verify Apex is working"""
    test_queries = [
        "Hello, who are you?",
        "Tell me a joke"
    ]
    
    for query in test_queries:
        print(f"\n🔹 User: {query}")
        response = ask_apex(query)
        print(f"🤖 Apex: {response}")

if __name__ == "__main__":
    test_apex()
