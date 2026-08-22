"""
Voice input processor for Ruma AI Assistant.
Handles speech-to-text conversion and voice command processing.
"""

import asyncio
import json
import logging
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass
import wave
import audioop
import os
import tempfile

logger = logging.getLogger(__name__)

@dataclass
class VoiceInputConfig:
    """Configuration for voice input processing."""
    sample_rate: int = 16000
    channels: int = 1
    chunk_size: int = 1024
    silence_threshold: float = 0.02
    min_silence_duration: float = 0.5
    max_recording_duration: float = 30.0
    vad_aggressiveness: int = 3

class VoiceInputProcessor:
    """Process voice input and convert to text."""
    
    def __init__(self, config: Optional[VoiceInputConfig] = None):
        self.config = config or VoiceInputConfig()
        self.is_recording = False
        self.audio_buffer = []
        self.silence_start = None
        self.recording_start = None
        self.on_text_callback: Optional[Callable[[str], None]] = None
        self.on_error_callback: Optional[Callable[[str], None]] = None
        
        # Try to import speech recognition libraries
        self.speech_recognizer = None
        self.vad = None
        
        try:
            import speech_recognition as sr
            self.speech_recognizer = sr.Recognizer()
            logger.info("Speech recognition library loaded successfully")
        except ImportError:
            logger.warning("Speech recognition library not available")
        
        try:
            import webrtcvad
            self.vad = webrtcvad.Vad(self.config.vad_aggressiveness)
            logger.info("VAD library loaded successfully")
        except ImportError:
            logger.warning("WebRTC VAD library not available")
    
    def set_callbacks(self, 
                     on_text: Callable[[str], None],
                     on_error: Callable[[str], None]):
        """Set callback functions for text and error events."""
        self.on_text_callback = on_text
        self.on_error_callback = on_error
    
    async def start_recording(self) -> bool:
        """Start voice recording."""
        if self.is_recording:
            return False
        
        self.is_recording = True
        self.audio_buffer = []
        self.silence_start = None
        self.recording_start = asyncio.get_event_loop().time()
        logger.info("Voice recording started")
        return True
    
    async def stop_recording(self) -> bool:
        """Stop voice recording and process the audio."""
        if not self.is_recording:
            return False
        
        self.is_recording = False
        logger.info("Voice recording stopped")
        
        # Process the recorded audio
        if self.audio_buffer:
            await self._process_audio()
        
        return True
    
    async def process_audio_chunk(self, audio_data: bytes) -> None:
        """Process a chunk of audio data."""
        if not self.is_recording:
            return
        
        current_time = asyncio.get_event_loop().time()
        
        # Check for maximum recording duration
        if (current_time - self.recording_start) > self.config.max_recording_duration:
            await self.stop_recording()
            return
        
        # Calculate audio energy for silence detection
        energy = audioop.rms(audio_data, 2) / 32768.0
        
        if energy < self.config.silence_threshold:
            if self.silence_start is None:
                self.silence_start = current_time
            elif (current_time - self.silence_start) > self.config.min_silence_duration:
                # Silence detected for long enough, stop recording
                await self.stop_recording()
                return
        else:
            self.silence_start = None
        
        # Add audio data to buffer
        self.audio_buffer.append(audio_data)
    
    async def _process_audio(self) -> None:
        """Process the recorded audio buffer and convert to text."""
        try:
            if not self.audio_buffer:
                return
            
            # Combine audio chunks
            audio_data = b''.join(self.audio_buffer)
            
            # Save to temporary file
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_filename = temp_file.name
                
                # Write WAV file
                with wave.open(temp_filename, 'wb') as wav_file:
                    wav_file.setnchannels(self.config.channels)
                    wav_file.setsampwidth(2)  # 16-bit
                    wav_file.setframerate(self.config.sample_rate)
                    wav_file.writeframes(audio_data)
            
            # Convert to text
            text = await self._transcribe_audio(temp_filename)
            
            # Clean up temp file
            try:
                os.unlink(temp_filename)
            except:
                pass
            
            # Call callback with text
            if text and self.on_text_callback:
                self.on_text_callback(text)
                
        except Exception as e:
            logger.error(f"Error processing audio: {e}")
            if self.on_error_callback:
                self.on_error_callback(str(e))
    
    async def _transcribe_audio(self, audio_file: str) -> Optional[str]:
        """Transcribe audio file to text."""
        if not self.speech_recognizer:
            logger.error("Speech recognizer not available")
            return None
        
        try:
            import speech_recognition as sr
            
            with sr.AudioFile(audio_file) as source:
                # Adjust for ambient noise
                self.speech_recognizer.adjust_for_ambient_noise(source, duration=0.5)
                
                # Read audio data
                audio_data = self.speech_recognizer.record(source)
                
                # Try multiple recognition methods
                text = None
                
                # Try Google Speech Recognition (free, requires internet)
                try:
                    text = self.speech_recognizer.recognize_google(audio_data)
                    logger.info(f"Transcribed text (Google): {text}")
                except sr.UnknownValueError:
                    logger.warning("Google Speech Recognition could not understand audio")
                except sr.RequestError as e:
                    logger.warning(f"Google Speech Recognition service error: {e}")
                
                # Try Whisper (local, more accurate)
                if not text:
                    try:
                        text = self.speech_recognizer.recognize_whisper(audio_data)
                        logger.info(f"Transcribed text (Whisper): {text}")
                    except:
                        logger.warning("Whisper recognition failed")
                
                return text
                
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            return None
    
    def get_audio_level(self) -> float:
        """Get current audio level from the buffer."""
        if not self.audio_buffer:
            return 0.0
        
        latest_chunk = self.audio_buffer[-1]
        return audioop.rms(latest_chunk, 2) / 32768.0
    
    def get_recording_duration(self) -> float:
        """Get current recording duration in seconds."""
        if not self.recording_start or not self.is_recording:
            return 0.0
        
        current_time = asyncio.get_event_loop().time()
        return current_time - self.recording_start
    
    def is_silent(self) -> bool:
        """Check if current audio is silent."""
        audio_level = self.get_audio_level()
        return audio_level < self.config.silence_threshold
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status of the voice processor."""
        return {
            "is_recording": self.is_recording,
            "audio_level": self.get_audio_level(),
            "recording_duration": self.get_recording_duration(),
            "is_silent": self.is_silent(),
            "buffer_size": len(self.audio_buffer),
            "speech_recognizer_available": self.speech_recognizer is not None,
            "vad_available": self.vad is not None
        }

# Global voice input processor instance
voice_processor = VoiceInputProcessor()

async def test_voice_input():
    """Test the voice input processor."""
    processor = VoiceInputProcessor()
    
    def on_text(text: str):
        print(f"Recognized text: {text}")
    
    def on_error(error: str):
        print(f"Error: {error}")
    
    processor.set_callbacks(on_text, on_error)
    
    # Test status
    status = processor.get_status()
    print(f"Voice processor status: {json.dumps(status, indent=2)}")

if __name__ == "__main__":
    asyncio.run(test_voice_input())
