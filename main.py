from dotenv import load_dotenv
import os
from text_to_speech import stop_all_audio  # Add this import at the top
from text_to_speech import speak_text_with_control

# Force load environment variables first
load_dotenv()

import gradio as gr
import cv2
import numpy as np
from PIL import Image
import google.generativeai as genai
from threading import Thread
import time
import tempfile

# Import your custom modules
from ai_agent import ask_apex
from speech_to_txt import record_audio, transcribe_with_groq
from text_to_speech import speak_text

# Configure Google AI with your variable name
def configure_google_ai():
    google_key = os.getenv("GEMINI_API_KEY")  # Using your variable name
    if google_key:
        genai.configure(api_key=google_key)
        return True
    return False

configure_google_ai()

# Global variables
latest_frame = None
is_listening = False
chat_history = []

def capture_frame(frame):
    """Capture and store the current webcam frame"""
    global latest_frame
    if frame is not None:
        latest_frame = frame
        print("📸 Frame captured successfully")
    return None

def process_voice_command():
    """Process voice input and generate AI response"""
    global is_listening, chat_history, latest_frame
    
    if is_listening:
        return "🎤 Already listening...", "\n\n".join(chat_history)
    
    is_listening = True
    
    try:
        print("\n=== VOICE COMMAND PROCESSING START ===")
        
        # Step 1: Record audio
        audio_file = os.path.join(tempfile.gettempdir(), "apex_voice_recording.mp3")
        print(f"📁 Recording to: {audio_file}")
        
        recording_success = record_audio(audio_file, timeout=15, phrase_time_limit=10)
        
        if not recording_success:
            is_listening = False
            error_msg = "❌ Recording failed - please try again"
            chat_history.append(f"**System:** {error_msg}")
            return error_msg, "\n\n".join(chat_history)
        
        print("✅ Recording completed successfully")
        
        # Step 2: Transcribe speech
        print("🔄 Starting transcription...")
        try:
            user_text = transcribe_with_groq(audio_file)
            print(f"📝 Transcribed text: '{user_text}'")
        except Exception as transcription_error:
            is_listening = False
            error_msg = f"❌ Transcription failed: {str(transcription_error)}"
            chat_history.append(f"**System:** {error_msg}")
            print(f"❌ Transcription error: {transcription_error}")
            return error_msg, "\n\n".join(chat_history)
        
        if not user_text or not user_text.strip():
            is_listening = False
            error_msg = "❌ No speech detected in recording"
            chat_history.append(f"**System:** {error_msg}")
            return error_msg, "\n\n".join(chat_history)
        
        # Step 3: Get AI response
        print("🤖 Processing with AI...")
        try:
            if latest_frame is not None:
                print("📸 Using current webcam frame for vision analysis")
                ai_response = ask_apex(user_text, latest_frame)
            else:
                print("⚠️ No webcam frame available, processing without vision")
                ai_response = ask_apex(user_text)
                
            print(f"🤖 AI Response generated: {ai_response[:100]}...")
            
        except Exception as ai_error:
            is_listening = False
            error_msg = f"❌ AI processing failed: {str(ai_error)}"
            chat_history.append(f"**System:** {error_msg}")
            print(f"❌ AI error: {ai_error}")
            return error_msg, "\n\n".join(chat_history)
        
        # Step 4: Update chat history
        chat_history.append(f"**You:** {user_text}")
        chat_history.append(f"**Apex:** {ai_response}")
        
        # Step 5: Generate speech response (FIXED - using speak_text_with_control)
        print("🔊 Starting text-to-speech with emoji cleaning...")
        try:
            speak_text_with_control(ai_response)
            print("✅ TTS with emoji cleaning initiated successfully")
        except Exception as tts_error:
            print(f"⚠️ TTS failed but continuing: {tts_error}")
        
        # Step 6: Cleanup
        try:
            if os.path.exists(audio_file):
                os.remove(audio_file)
                print("🗑️ Temporary audio file cleaned up")
        except:
            pass
        
        is_listening = False
        success_msg = f"✅ Processed: {user_text}"
        print("=== VOICE COMMAND PROCESSING COMPLETE ===\n")
        
        return success_msg, "\n\n".join(chat_history)
        
    except Exception as e:
        is_listening = False
        error_msg = f"❌ Voice processing failed: {str(e)}"
        chat_history.append(f"**System:** {error_msg}")
        print(f"❌ Critical error in voice processing: {e}")
        print("=== VOICE COMMAND PROCESSING FAILED ===\n")
        return error_msg, "\n\n".join(chat_history)

def analyze_current_frame(question):
    """Analyze the current webcam frame with a question"""
    global latest_frame, chat_history
    
    if latest_frame is None:
        return "❌ Please show something to the camera first.", "\n\n".join(chat_history)
    
    try:
        print(f"🔍 Analyzing frame for: {question}")
        
        ai_response = ask_apex(question, latest_frame)
        
        chat_history.append(f"**You:** {question}")
        chat_history.append(f"**Apex:** {ai_response}")
        
        # FIXED - using speak_text_with_control with emoji cleaning
        speak_text_with_control(ai_response)
        
        return ai_response, "\n\n".join(chat_history)
        
    except Exception as e:
        error_msg = f"❌ Analysis failed: {str(e)}"
        chat_history.append(f"**System:** {error_msg}")
        print(f"❌ Analysis error: {e}")
        return error_msg, "\n\n".join(chat_history)

def clear_chat():
    """Clear the chat history and stop any playing audio"""
    global chat_history
    
    # Stop all audio first
    stop_all_audio()
    
    # Clear chat history
    chat_history = []
    
    return "✅ Chat cleared & audio stopped", "**Apex:** Ready for a new conversation!"

def test_system_components():
    """Test all system components individually"""
    print("\n🔍 SYSTEM COMPONENT TEST")
    print("=" * 40)
    
    # Test API Keys with your variable names
    print("1. Testing API Keys...")
    google_key = os.getenv("GEMINI_API_KEY")  # Your variable name
    groq_key = os.getenv("GROQ_API_KEY")
    eleven_key = os.getenv("ELEVENLABS_API_KEY")  # Your variable name
    
    print(f"   Gemini API: {'✅ Found' if google_key else '❌ Missing'}")
    print(f"   Groq API: {'✅ Found' if groq_key else '❌ Missing'}")
    print(f"   ElevenLabs API: {'✅ Found' if eleven_key else '❌ Missing'}")
    
    # Test Camera
    print("2. Testing Camera...")
    try:
        cap = cv2.VideoCapture(0)
        if cap.isOpened():
            ret, _ = cap.read()
            cap.release()
            print(f"   Camera: {'✅ Working' if ret else '❌ Not accessible'}")
        else:
            print("   Camera: ❌ Cannot open")
    except Exception as e:
        print(f"   Camera: ❌ Error - {e}")
    
    # Test Microphone
    print("3. Testing Microphone...")
    try:
        import speech_recognition as sr
        r = sr.Recognizer()
        with sr.Microphone() as source:
            print("   Microphone: ✅ Accessible")
    except Exception as e:
        print(f"   Microphone: ❌ Error - {e}")
    
    # Test Emoji Cleaning
    print("4. Testing Emoji Cleaning...")
    try:
        from text_to_speech import clean_text_for_tts
        test_text = "✅ Hello! 😊 This is a test 🚀"
        cleaned = clean_text_for_tts(test_text)
        print(f"   Original: {test_text}")
        print(f"   Cleaned: {cleaned}")
        print("   Emoji Cleaning: ✅ Working")
    except Exception as e:
        print(f"   Emoji Cleaning: ❌ Error - {e}")
    
    print("=" * 40)

# Enhanced Gradio Interface with Apex Branding
with gr.Blocks(
    title="Apex AI Assistant",
    theme=gr.themes.Soft(),
    css="""
    .gradio-container {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    .title {
        text-align: center;
        color: #ffffff;
        font-size: 2.5em;
        font-weight: bold;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        margin-bottom: 20px;
    }
    .subtitle {
        text-align: center;
        color: #f0f0f0;
        font-size: 1.2em;
        margin-bottom: 30px;
    }
    .status-box {
        background-color: rgba(255, 255, 255, 0.1);
        border-radius: 8px;
        padding: 10px;
    }
    """
) as demo:
    
    gr.HTML('<div class="title">🤖 APEX AI ASSISTANT</div>')
    gr.HTML('<div class="subtitle">Your Intelligent Voice & Vision Companion with Clean Audio</div>')
    
    with gr.Row():
        # Left Column - Webcam and Controls
        with gr.Column(scale=1):
            gr.Markdown("### 📹 **Live Vision**")
            webcam = gr.Image(
                sources=["webcam"],
                streaming=True, 
                label="Apex's Eyes", 
                mirror_webcam=True,
                height=400,
                type="numpy"
            )
            webcam.stream(fn=capture_frame, inputs=webcam, outputs=None)
            
            with gr.Row():
                voice_btn = gr.Button("🎤 Voice Command", variant="primary", size="lg")
                clear_btn = gr.Button("🗑️ Clear Chat", variant="secondary")
        
        # Right Column - Chat and Text Input
        with gr.Column(scale=1):
            gr.Markdown("### 💬 **Chat with Apex**")
            
            chat_display = gr.Textbox(
                label="Conversation History",
                lines=15,
                max_lines=20,
                value="**Apex:** Hello! I'm Apex, your AI assistant with clean voice responses. I can see through the webcam and respond to your voice commands. How can I help you today?",
                interactive=False
            )
            
            with gr.Row():
                text_input = gr.Textbox(
                    label="Type your question",
                    placeholder="Ask me anything about what I can see...",
                    scale=3
                )
                send_btn = gr.Button("📤 Send", variant="primary")
            
            status_display = gr.Textbox(
                label="Status",
                value="✅ Ready - Camera active, Emoji cleaning enabled",
                interactive=False,
                lines=2,
                elem_classes=["status-box"]
            )
    
    # Event handlers
    voice_btn.click(
        fn=process_voice_command,
        outputs=[status_display, chat_display]
    )
    
    send_btn.click(
        fn=analyze_current_frame,
        inputs=text_input,
        outputs=[status_display, chat_display]
    ).then(
        lambda: "",
        outputs=text_input
    )
    
    text_input.submit(
        fn=analyze_current_frame,
        inputs=text_input,
        outputs=[status_display, chat_display]
    ).then(
        lambda: "",
        outputs=text_input
    )
    
    clear_btn.click(
        fn=clear_chat,
        outputs=[status_display, chat_display]
    )

if __name__ == "__main__":
    # Run system test first
    test_system_components()
    
    print("\n🚀 Starting Apex AI Assistant...")
    print("✅ Webcam integration: Ready")
    print("✅ Voice commands: Ready") 
    print("✅ AI responses: Ready")
    print("✅ Text-to-speech with emoji cleaning: Ready")
    print("✅ Chat history: Ready")
    print("\n🌐 Launching web interface...")
    
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True
    )
