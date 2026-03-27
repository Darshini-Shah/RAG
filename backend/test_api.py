from youtube_transcript_api import YouTubeTranscriptApi
import sys

try:
    print("Trying YouTubeTranscriptApi.get_transcript('dQw4w9WgXcQ')...")
    ts = YouTubeTranscriptApi.get_transcript("dQw4w9WgXcQ")
    print("Success with get_transcript!")
except Exception as e:
    print(f"Error with get_transcript: {e}")

try:
    print("Trying YouTubeTranscriptApi.list_transcripts('dQw4w9WgXcQ')...")
    transcript_list = YouTubeTranscriptApi.list_transcripts("dQw4w9WgXcQ")
    # Just get the first one
    transcript = next(iter(transcript_list)).fetch()
    print("Success with list_transcripts!")
except Exception as e:
    print(f"Error with list_transcripts: {e}")
