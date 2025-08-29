import streamlit as st
import assemblyai as aai
import threading, wave, os, websocket
from urllib.parse import urlencode
from datetime import datetime
import sounddevice as sd
import numpy as np
import queue

# ------------------------
# AssemblyAI Functions
# ------------------------
aai.settings.api_key = "e208c82c90d04fed9702ef373fd54158"   # replace with your API key

def speech_to_text(audio_file):
    config = aai.TranscriptionConfig(
        speech_model=aai.SpeechModel.universal,
        language_detection=True,
        speaker_labels=True
    )
    transcript = aai.Transcriber().transcribe(audio_file, config)
    if transcript.status == "error":
        return f"❌ Error: {transcript.error}"
    return "\n".join([f"Speaker {u.speaker}: {u.text}" for u in transcript.utterances])

def summarize_text(audio_file):
    transcript = aai.Transcriber().transcribe(audio_file)
    result = transcript.lemur.task(
        "Provide a brief summary of the transcript.",
        final_model=aai.LemurModel.claude_sonnet_4_20250514
    )
    return result.response


# ------------------------
# Recording Agent
# ------------------------
class RecordingAgent:
    def __init__(self, filename="recording.wav"):
        self.filename = filename
        self.frames = []
        self.stop_event = threading.Event()

        self.SAMPLE_RATE = 16000
        self.CHANNELS = 1
        self.FRAMES_PER_BUFFER = 800  # ~50ms of audio at 16kHz
        self.q = queue.Queue()

    def _save_wav(self):
        if not self.frames:
            return
        with wave.open(self.filename, "wb") as wf:
            wf.setnchannels(self.CHANNELS)
            wf.setsampwidth(2)  # 16-bit PCM
            wf.setframerate(self.SAMPLE_RATE)
            wf.writeframes(b"".join(self.frames))

    def start_recording(self):
        api_key = aai.settings.api_key
        params = {"sample_rate": self.SAMPLE_RATE}
        endpoint = f"wss://streaming.assemblyai.com/v3/ws?{urlencode(params)}"

        # Callback for sounddevice input
        def callback(indata, frames, time, status):
            if status:
                print("Status:", status)
            # Convert numpy array to bytes
            self.q.put(indata.copy().tobytes())

        # Open input stream
        self.stream = sd.InputStream(
            channels=self.CHANNELS,
            samplerate=self.SAMPLE_RATE,
            blocksize=self.FRAMES_PER_BUFFER,
            dtype="int16",
            callback=callback
        )
        self.stream.start()

        # On websocket open → start sending audio
        def on_open(ws):
            def send_audio():
                while not self.stop_event.is_set():
                    try:
                        data = self.q.get(timeout=0.1)
                    except queue.Empty:
                        continue
                    self.frames.append(data)
                    ws.send(data, websocket.ABNF.OPCODE_BINARY)
            threading.Thread(target=send_audio, daemon=True).start()

        # Create websocket connection to AssemblyAI
        self.ws_app = websocket.WebSocketApp(
            endpoint, header={"Authorization": api_key}, on_open=on_open
        )
        self.ws_thread = threading.Thread(target=self.ws_app.run_forever, daemon=True)
        self.ws_thread.start()

    def stop_recording(self):
        self.stop_event.set()
        if hasattr(self, "ws_app"):
            self.ws_app.close()
        if hasattr(self, "stream"):
            self.stream.stop()
            self.stream.close()
        self._save_wav()
        return self.filename


# ------------------------
# Streamlit UI
# ------------------------
st.title("🎤 Record → Transcribe → Summarize")

if "agent" not in st.session_state:
    st.session_state.agent = RecordingAgent()
if "recording" not in st.session_state:
    st.session_state.recording = False
if "transcript" not in st.session_state:
    st.session_state.transcript = None
if "summary" not in st.session_state:
    st.session_state.summary = None
if "audio_file" not in st.session_state:
    st.session_state.audio_file = None
if "txt_file" not in st.session_state:
    st.session_state.txt_file = None

col1, col2, col3 = st.columns(3)

if col1.button("▶️ Start Recording") and not st.session_state.recording:
    st.session_state.agent = RecordingAgent()
    st.session_state.agent.start_recording()
    st.session_state.recording = True
    st.success("Recording started...")

if col2.button("⏹ Stop Recording") and st.session_state.recording:
    audio_file = st.session_state.agent.stop_recording()
    st.session_state.recording = False
    st.session_state.audio_file = audio_file
    st.success("Recording stopped & saved!")

    with st.spinner("🔎 Transcribing..."):
        st.session_state.transcript = speech_to_text(audio_file)
    with st.spinner("📄 Summarizing..."):
        st.session_state.summary = summarize_text(audio_file)

    # Save transcript+summary
    txt_file = "transcript_summary.txt"
    with open(txt_file, "w", encoding="utf-8") as f:
        f.write("TRANSCRIPT:\n" + st.session_state.transcript + "\n\nSUMMARY:\n" + st.session_state.summary)
    st.session_state.txt_file = txt_file

# Reset button
if col3.button("🔄 Reset"):
    st.session_state.agent = RecordingAgent()
    st.session_state.recording = False
    st.session_state.transcript = None
    st.session_state.summary = None
    st.session_state.audio_file = None
    st.session_state.txt_file = None
    st.success("Session reset!")

# Show transcript & summary if available
if st.session_state.transcript:
    st.subheader("📝 Transcript")
    st.text_area("Transcript", st.session_state.transcript, height=200)
if st.session_state.summary:
    st.subheader("📄 Summary")
    st.write(st.session_state.summary)

# Download buttons if files exist
if st.session_state.audio_file and os.path.exists(st.session_state.audio_file):
    with open(st.session_state.audio_file, "rb") as f:
        st.download_button("⬇️ Download Recording (WAV)", f, "recording.wav", "audio/wav")

if st.session_state.txt_file and os.path.exists(st.session_state.txt_file):
    with open(st.session_state.txt_file, "rb") as f:
        st.download_button("⬇️ Download Transcript & Summary", f, "transcript.txt", "text/plain")
