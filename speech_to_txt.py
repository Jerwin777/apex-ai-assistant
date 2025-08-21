import logging
import os
from io import BytesIO
import speech_recognition as sr
from pydub import AudioSegment
from groq import Groq

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def record_audio(file_path, timeout=20, phrase_time_limit=None):
    """
    Record audio from the microphone and save it as an MP3 file.
    """
    recognizer = sr.Recognizer()

    try:
        print("🎤 Initializing microphone...")
        with sr.Microphone() as source:
            print("🔧 Adjusting for ambient noise...")
            recognizer.adjust_for_ambient_noise(source, duration=1)
            print("✅ Ready! Start speaking now...")

            audio_data = recognizer.listen(
                source, 
                timeout=timeout, 
                phrase_time_limit=phrase_time_limit
            )
            print("✅ Recording complete.")

            # Convert and save audio
            wav_data = audio_data.get_wav_data()
            audio_segment = AudioSegment.from_wav(BytesIO(wav_data))
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(file_path) if os.path.dirname(file_path) else '.', exist_ok=True)
            
            # Export with quality settings
            audio_segment.export(file_path, format="mp3", parameters=["-ar", "16000"])
            
            print(f"✅ Audio saved: {file_path} ({len(audio_segment)}ms)")
            return True
            
    except sr.WaitTimeoutError:
        print("❌ No speech detected within timeout period")
        return False
    except Exception as e:
        print(f"❌ Recording error: {e}")
        logging.error(f"Error recording audio: {e}")
        return False

def transcribe_with_groq(audio_filepath):
    """
    Transcribe an audio file using Groq's Whisper model.
    """
    GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY not found in environment variables.")

    # Validate file exists and has content
    if not os.path.exists(audio_filepath):
        raise FileNotFoundError(f"❌ Audio file not found: {audio_filepath}")
    
    file_size = os.path.getsize(audio_filepath)
    if file_size == 0:
        raise ValueError(f"❌ Audio file is empty: {audio_filepath}")
    
    print(f"📁 File found: {audio_filepath} ({file_size} bytes)")

    try:
        client = Groq(api_key=GROQ_API_KEY)
        stt_model = "whisper-large-v3"
        
        print("🔄 Sending to Groq for transcription...")
        
        with open(audio_filepath, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                model=stt_model,
                file=audio_file,
                language="en"
            )
        
        result_text = transcription.text.strip()
        print(f"✅ Transcription successful: '{result_text}'")
        return result_text
        
    except Exception as e:
        print(f"❌ Transcription failed: {e}")
        logging.error(f"Groq transcription error: {e}")
        raise

# Test function
def test_recording_and_transcription():
    """Test the complete audio pipeline"""
    test_file = "test_recording.mp3"
    
    print("=== Testing Audio Pipeline ===")
    
    # Test recording
    success = record_audio(test_file, timeout=5, phrase_time_limit=3)
    if not success:
        print("❌ Recording test failed")
        return False
    
    # Test transcription
    try:
        text = transcribe_with_groq(test_file)
        print(f"🎉 Pipeline test successful: '{text}'")
        return True
    except Exception as e:
        print(f"❌ Pipeline test failed: {e}")
        return False

if __name__ == "__main__":
    test_recording_and_transcription()
