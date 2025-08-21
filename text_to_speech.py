from gtts import gTTS
import os
import subprocess
import platform
from dotenv import load_dotenv
import tempfile
import pygame
import time
import uuid
from threading import Lock, Event
import threading
import re


# Initialize pygame mixer for audio playback
pygame.mixer.init()


# Global controls
file_lock = Lock()
stop_audio_event = Event()
current_audio_thread = None


def clean_text_for_tts(text):
    """Remove emojis and clean text for better TTS output"""
    # Remove emojis using regex
    emoji_pattern = re.compile("["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map symbols
        "\U0001F1E0-\U0001F1FF"  # flags (iOS)
        "\U00002702-\U000027B0"
        "\U000024C2-\U0001F251"
        "\U00002500-\U00002BEF"  # chinese char
        "\U00002702-\U000027B0"
        "\U00002702-\U000027B0"
        "\U000024C2-\U0001F251"
        "\U0001f926-\U0001f937"
        "\U00010000-\U0010ffff"
        "\u2640-\u2642" 
        "\u2600-\u2B55"
        "\u200d"
        "\u23cf"
        "\u23e9"
        "\u231a"
        "\ufe0f"  # dingbats
        "\u3030"
        "]+", flags=re.UNICODE)
    
    # Remove emojis
    cleaned_text = emoji_pattern.sub('', text)
    
    # Clean up extra spaces and newlines
    cleaned_text = ' '.join(cleaned_text.split())
    
    # Remove common emoji-like symbols that might be missed
    symbols_to_remove = ['✅', '❌', '🔧', '🎯', '📋', '💡', '⚠️', '🔍', 
                        '🚀', '🎉', '😊', '😉', '🔊', '🔇', '🗑️', '🧪', 
                        '🔄', '🔑', '✨', '🎊', '💻', '📱', '🖥️']
    
    for symbol in symbols_to_remove:
        cleaned_text = cleaned_text.replace(symbol, '')
    
    # Final cleanup
    cleaned_text = cleaned_text.strip()
    
    print(f"🧹 Original text: {text[:50]}...")
    print(f"🧹 Cleaned text: {cleaned_text[:50]}...")
    
    return cleaned_text


def stop_all_audio():
    """Stop all currently playing audio"""
    global stop_audio_event
    
    try:
        print("🔇 Stopping all audio...")
        
        # Signal all audio threads to stop
        stop_audio_event.set()
        
        # Stop pygame mixer
        if pygame.mixer.get_init():
            pygame.mixer.music.stop()
            pygame.mixer.music.unload()
        
        # Clear the stop event for future use
        time.sleep(0.1)  # Brief pause to ensure stop takes effect
        stop_audio_event.clear()
        
        print("✅ All audio stopped")
        return True
        
    except Exception as e:
        print(f"❌ Error stopping audio: {e}")
        return False


def speak_text(text, output_path=None):
    """TTS using Google Text-to-Speech with emoji cleaning and stop control"""
    global current_audio_thread
    
    try:
        # Clean the text to remove emojis before TTS
        clean_text = clean_text_for_tts(text)
        
        # If text becomes empty after cleaning, skip TTS
        if not clean_text.strip():
            print("⚠️ Text empty after emoji cleaning - skipping TTS")
            return False
        
        print(f"🔊 Speaking with gTTS: {clean_text[:50]}...")
        
        # Check if we should stop before starting
        if stop_audio_event.is_set():
            print("🔇 Audio stop requested - canceling TTS")
            return False
        
        # Generate unique filename if none provided
        if output_path is None:
            timestamp = int(time.time() * 1000)
            unique_id = str(uuid.uuid4())[:8]
            output_path = f"apex_voice_{timestamp}_{unique_id}.mp3"
        
        # Use absolute path
        abs_path = os.path.abspath(output_path)
        
        # Thread-safe file operations
        with file_lock:
            # Check again after acquiring lock
            if stop_audio_event.is_set():
                print("🔇 Audio stop requested during file creation")
                return False
            
            # Create gTTS object with cleaned text
            tts = gTTS(text=clean_text, lang='en', slow=False)
            
            # Save to unique file
            tts.save(abs_path)
            print(f"✅ Audio saved: {abs_path}")
        
        # Check one more time before playing
        if stop_audio_event.is_set():
            print("🔇 Audio stop requested - cleaning up file")
            cleanup_audio_file(abs_path)
            return False
        
        # Play using multiple methods for reliability
        success = play_audio_with_cleanup(abs_path)
        
        if success:
            print("✅ Audio playbook completed")
            return True
        else:
            print("❌ Audio playbook failed")
            cleanup_audio_file(abs_path)
            return False
            
    except Exception as e:
        print(f"❌ gTTS Error: {e}")
        return False


def play_audio_with_cleanup(file_path):
    """Play audio with automatic cleanup and stop control"""
    success = False
    
    try:
        # Method 1: Try pygame with stop control
        print("🔄 Trying pygame mixer...")
        
        # Check if we should stop
        if stop_audio_event.is_set():
            print("🔇 Stop requested - skipping playbook")
            cleanup_audio_file(file_path)
            return False
        
        # Load and play
        pygame.mixer.music.load(file_path)
        pygame.mixer.music.play()
        
        # Wait for playbook to complete with periodic stop checks
        while pygame.mixer.music.get_busy():
            if stop_audio_event.is_set():
                print("🔇 Stop requested during playbook")
                pygame.mixer.music.stop()
                pygame.mixer.music.unload()
                cleanup_audio_file(file_path)
                return False
            pygame.time.wait(100)
        
        # Stop and unload to release file handle
        pygame.mixer.music.stop()
        pygame.mixer.music.unload()
        
        print("✅ Pygame playbook successful!")
        success = True
        
    except Exception as e:
        print(f"❌ Pygame failed: {e}")
        
        # Method 2: Try system command as fallbook
        try:
            if stop_audio_event.is_set():
                cleanup_audio_file(file_path)
                return False
                
            print("🔄 Trying system command...")
            system = platform.system().lower()
            
            if system == "windows":
                subprocess.Popen(["start", "", file_path], shell=True)
                time.sleep(2)
                print("✅ Windows start command initiated!")
                success = True
            elif system == "darwin":
                subprocess.run(["open", file_path], check=True)
                print("✅ macOS open command successful!")
                success = True
            elif system == "linux":
                for player in ["aplay", "paplay", "play", "mpg123"]:
                    try:
                        subprocess.run([player, file_path], check=True, timeout=10)
                        print(f"✅ Linux {player} successful!")
                        success = True
                        break
                    except:
                        continue
                
        except Exception as e2:
            print(f"❌ System command failed: {e2}")
    
    # Schedule cleanup after delay
    if success:
        def delayed_cleanup():
            time.sleep(3)
            cleanup_audio_file(file_path)
        
        cleanup_thread = threading.Thread(target=delayed_cleanup, daemon=True)
        cleanup_thread.start()
    else:
        cleanup_audio_file(file_path)
    
    return success


def cleanup_audio_file(file_path):
    """Safely clean up audio file"""
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"🗑️ Cleaned up audio file: {file_path}")
    except Exception as e:
        print(f"⚠️ Could not cleanup file {file_path}: {e}")


def speak_text_with_control(text):
    """Wrapper function that can be controlled by main thread"""
    global current_audio_thread
    
    def audio_worker():
        speak_text(text)
    
    # Stop any existing audio
    stop_all_audio()
    
    # Start new audio thread
    current_audio_thread = threading.Thread(target=audio_worker, daemon=True)
    current_audio_thread.start()
    
    return current_audio_thread


def cleanup_old_audio_files():
    """Clean up old apex audio files"""
    try:
        current_dir = os.getcwd()
        for filename in os.listdir(current_dir):
            if filename.startswith('apex_voice_') and filename.endswith('.mp3'):
                file_path = os.path.join(current_dir, filename)
                try:
                    file_age = time.time() - os.path.getmtime(file_path)
                    if file_age > 60:
                        os.remove(file_path)
                        print(f"🗑️ Cleaned up old file: {filename}")
                except:
                    pass
    except Exception as e:
        print(f"⚠️ Cleanup error: {e}")


# Test function
def test_audio_control():
    """Test the audio control system with emoji cleaning"""
    print("🧪 Testing audio control with emoji cleaning...")
    
    # Test emoji cleaning
    test_text = "✅ This is a test message with emojis! 🎉 Delhi is the capital 😉 of India 🚀"
    thread1 = speak_text_with_control(test_text)
    
    # Wait a bit then stop
    time.sleep(2)
    print("🧪 Testing stop functionality...")
    stop_all_audio()
    
    # Start new audio
    time.sleep(1)
    thread2 = speak_text_with_control("🔊 This is a second test message without emoji sounds!")
    
    return True


if __name__ == "__main__":
    test_audio_control()
