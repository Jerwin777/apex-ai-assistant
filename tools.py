import os
import cv2
from dotenv import load_dotenv
import google.generativeai as genai
from PIL import Image

# Load environment variables
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")  # Using your variable name

# Configure Gemini client
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    print("❌ GEMINI_API_KEY not found in tools.py")

def capture_image(width: int = 1280, height: int = 720) -> Image.Image:
    """
    Captures a high-quality image from webcam with custom resolution.
    """
    cap = None
    try:
        # Try most common camera indices first
        for idx in [0, 1, 2]:
            cap = cv2.VideoCapture(idx)
            if cap.isOpened():
                # Set camera properties
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
                cap.set(cv2.CAP_PROP_FPS, 30)
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                
                # Test camera functionality
                ret, test_frame = cap.read()
                if ret and test_frame is not None:
                    # Camera warm-up
                    for _ in range(3):
                        cap.read()
                    
                    ret, frame = cap.read()
                    cap.release()
                    
                    if ret and frame is not None:
                        # Convert BGR to RGB for PIL
                        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        return Image.fromarray(rgb_frame)
                cap.release()
                
        raise RuntimeError("❌ No functional camera found")
        
    except Exception as e:
        if cap is not None and cap.isOpened():
            cap.release()
        raise RuntimeError(f"❌ Camera access failed: {e}")

def analyze_image_with_query(query: str = "What do you see in this image?", 
                           img: Image.Image = None, 
                           max_retries: int = 3) -> str:
    """
    Analyzes image using Gemini AI with retry logic and better error handling.
    """
    if not GEMINI_API_KEY:
        return "❌ GEMINI_API_KEY not found in environment variables"

    for attempt in range(max_retries):
        try:
            # Capture new image if none provided
            if img is None:
                print("📸 Capturing image from webcam...")
                img = capture_image()
            
            # Initialize Gemini model
            model = genai.GenerativeModel("gemini-1.5-flash")
            
            # Generate response
            print("🤖 Analyzing image with AI...")
            response = model.generate_content([query, img])
            
            if response and response.text:
                return response.text.strip()
            else:
                return "❌ AI returned empty response"
                
        except Exception as e:
            error_msg = str(e).lower()
            if "quota" in error_msg or "rate limit" in error_msg:
                if attempt < max_retries - 1:
                    print(f"⏳ Rate limit hit, retrying in 2 seconds... (Attempt {attempt + 1})")
                    import time
                    time.sleep(2)
                    continue
                return "❌ API quota exceeded. Please try again later."
            elif "api" in error_msg:
                return f"❌ API Error: {e}"
            else:
                if attempt < max_retries - 1:
                    print(f"🔄 Retrying... (Attempt {attempt + 1})")
                    continue
                return f"❌ Analysis failed: {e}"
    
    return "❌ Failed after multiple attempts"

def test_camera_connection() -> bool:
    """Test if camera is accessible."""
    try:
        cap = cv2.VideoCapture(0)
        if cap.isOpened():
            ret, _ = cap.read()
            cap.release()
            return ret
        return False
    except:
        return False

def save_captured_image(img: Image.Image, filename: str = "captured_image.jpg") -> str:
    """Save captured image to disk."""
    try:
        img.save(filename, quality=95)
        return f"✅ Image saved as {filename}"
    except Exception as e:
        return f"❌ Failed to save image: {e}"

def get_available_cameras() -> list:
    """Get list of available camera indices."""
    available = []
    for i in range(10):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            ret, _ = cap.read()
            if ret:
                available.append(i)
        cap.release()
    return available

if __name__ == "__main__":
    try:
        print("🧪 Testing camera and AI analysis...")
        result = analyze_image_with_query("What object is in the image?")
        print(f"✅ Test result: {result}")
    except Exception as e:
        print(f"❌ Test failed: {e}")
