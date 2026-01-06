"""Audio utilities for Transcribe and Polly - simplified for demo."""

import base64
import os
import tempfile
import time
import uuid

import boto3


class AudioProcessor:
    """Simple audio processor using Transcribe and Polly."""
    
    def __init__(self):
        self.region = os.environ.get("AWS_REGION", "eu-west-2")
        self.transcribe = boto3.client("transcribe", region_name=self.region)
        self.polly = boto3.client("polly", region_name=self.region)
        self.s3 = boto3.client("s3", region_name=self.region)
        self.bucket = os.environ.get("AUDIO_BUCKET", "")
    
    def transcribe_audio(self, audio_bytes: bytes, language: str = "en-GB") -> str:
        """Convert speech to text.
        
        Args:
            audio_bytes: Audio data (WAV/MP3)
            language: Language code
            
        Returns:
            Transcribed text
        """
        if not self.bucket:
            return "[Audio transcription requires S3 bucket configuration]"
        
        # Upload to S3
        job_name = f"nhs-demo-{uuid.uuid4().hex[:8]}"
        s3_key = f"transcribe/{job_name}.wav"
        
        self.s3.put_object(
            Bucket=self.bucket,
            Key=s3_key,
            Body=audio_bytes
        )
        
        # Start transcription
        self.transcribe.start_transcription_job(
            TranscriptionJobName=job_name,
            Media={"MediaFileUri": f"s3://{self.bucket}/{s3_key}"},
            MediaFormat="wav",
            LanguageCode=language
        )
        
        # Wait for completion (simplified - in production use async)
        for _ in range(30):
            result = self.transcribe.get_transcription_job(
                TranscriptionJobName=job_name
            )
            status = result["TranscriptionJob"]["TranscriptionJobStatus"]
            
            if status == "COMPLETED":
                # Get transcript
                import urllib.request
                import json
                
                uri = result["TranscriptionJob"]["Transcript"]["TranscriptFileUri"]
                with urllib.request.urlopen(uri) as resp:
                    data = json.loads(resp.read().decode())
                
                text = data["results"]["transcripts"][0]["transcript"]
                
                # Cleanup
                self._cleanup(job_name, s3_key)
                return text
            
            elif status == "FAILED":
                self._cleanup(job_name, s3_key)
                return "[Transcription failed]"
            
            time.sleep(1)
        
        self._cleanup(job_name, s3_key)
        return "[Transcription timeout]"
    
    def synthesize_speech(self, text: str, language: str = "en") -> bytes:
        """Convert text to speech.
        
        Args:
            text: Text to speak
            language: Language code
            
        Returns:
            Audio bytes (MP3)
        """
        # Map language to Polly voice
        voices = {
            "en": "Amy",      # British English
            "es": "Lucia",
            "fr": "Lea",
            "de": "Vicki",
            "it": "Bianca",
        }
        voice = voices.get(language, "Amy")
        
        # Truncate if too long
        if len(text) > 2900:
            text = text[:2900] + "..."
        
        response = self.polly.synthesize_speech(
            Text=text,
            OutputFormat="mp3",
            VoiceId=voice,
            Engine="neural"
        )
        
        return response["AudioStream"].read()
    
    def _cleanup(self, job_name: str, s3_key: str):
        """Clean up transcription resources."""
        try:
            self.transcribe.delete_transcription_job(TranscriptionJobName=job_name)
        except Exception:
            pass
        try:
            self.s3.delete_object(Bucket=self.bucket, Key=s3_key)
        except Exception:
            pass


def audio_to_base64(audio_bytes: bytes) -> str:
    """Convert audio bytes to base64 string."""
    return base64.b64encode(audio_bytes).decode("utf-8")


def base64_to_audio(b64_string: str) -> bytes:
    """Convert base64 string to audio bytes."""
    return base64.b64decode(b64_string)
