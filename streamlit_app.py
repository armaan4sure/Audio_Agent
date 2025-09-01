import os
import shutil
import streamlit as st
from datetime import datetime
from streamlit_mic_recorder import mic_recorder
import assemblyai as aai

# -----------------------
# AssemblyAI setup (keep your real key in Streamlit secrets)
# -----------------------
aai.settings.api_key = "xyz"   # replace with your API key

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
# -----------------------
# Save session files (timestamped folder)
# -----------------------
def save_session_files(audio_file: str, transcript: str, summary: str):
    """Create a timestamped folder and save recording + transcript inside it."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    folder_name = f"session_{timestamp}"
    os.makedirs(folder_name, exist_ok=True)

    audio_dest = os.path.join(folder_name, os.path.basename(audio_file))
    if os.path.exists(audio_file):
        try:
            os.replace(audio_file, audio_dest)
        except Exception:
            # fallback to copy if replace fails
            shutil.copy(audio_file, audio_dest)

    txt_dest = os.path.join(folder_name, "transcript_summary.txt")
    with open(txt_dest, "w", encoding="utf-8") as f:
        f.write("TRANSCRIPT:\n" + (transcript or "") + "\n\nSUMMARY:\n" + (summary or ""))

    return audio_dest, txt_dest, folder_name

# -----------------------
# Streamlit UI
# -----------------------
st.set_page_config(page_title="🎤 Audio Agent", layout="centered")
st.title("🎤 Record → Transcribe → Summarize")

# initialize session state items if missing
if "audio_file" not in st.session_state:
    st.session_state.audio_file = None
if "txt_file" not in st.session_state:
    st.session_state.txt_file = None
if "transcript" not in st.session_state:
    st.session_state.transcript = None
if "summary" not in st.session_state:
    st.session_state.summary = None
if "processed_sessions" not in st.session_state:
    st.session_state.processed_sessions = []

# --------------- Recorder (browser-side) ---------------
# This component stores the recorded blob into st.session_state["session_recorder_output"]
mic = mic_recorder(
    start_prompt="▶️ Start Recording",
    stop_prompt="⏹️ Stop Recording",
    just_once=True,
    use_container_width=True,
    key="session_recorder"  # component key
)

# The mic_recorder component puts the result in st.session_state["session_recorder_output"]
rec_out = st.session_state.get("session_recorder_output")

# Only process a newly-recorded blob once (avoids repeated processing on reruns)
if rec_out and isinstance(rec_out, dict):
    rec_id = rec_out.get("id")
    if rec_id and rec_id not in st.session_state.processed_sessions:
        # write the received bytes to a temporary wav file
        tmp_wav = f"tmp_{rec_id}.wav"
        with open(tmp_wav, "wb") as wf:
            wf.write(rec_out.get("bytes", b""))

        # offer playback quickly
        st.audio(rec_out.get("bytes", b""), format="audio/wav")

        # Transcribe & summarize using your existing functions
        with st.spinner("🔎 Transcribing..."):
            transcript_text = speech_to_text(tmp_wav)
        with st.spinner("📄 Summarizing..."):
            summary_text = summarize_text(tmp_wav)

        # Move the tmp wav and save transcript+summary into a timestamped folder
        audio_dest, txt_dest, folder = save_session_files(tmp_wav, transcript_text, summary_text)

        # update session state so download buttons and UI show correct files
        st.session_state.audio_file = audio_dest
        st.session_state.txt_file = txt_dest
        st.session_state.transcript = transcript_text
        st.session_state.summary = summary_text

        # mark this recording processed
        st.session_state.processed_sessions.append(rec_id)
        st.success(f"✅ Saved session in folder: {folder}")

# -----------------------
# Show transcript & summary if available
# -----------------------
if st.session_state.transcript:
    st.subheader("📝 Transcript")
    st.text_area("Transcript", st.session_state.transcript, height=200)
if st.session_state.summary:
    st.subheader("📄 Summary")
    st.write(st.session_state.summary)

# -----------------------
# Download buttons
# -----------------------
if st.session_state.audio_file and os.path.exists(st.session_state.audio_file):
    with open(st.session_state.audio_file, "rb") as af:
        st.download_button(
            "⬇️ Download Recording (WAV)",
            data=af.read(),
            file_name=os.path.basename(st.session_state.audio_file),
            mime="audio/wav",
        )

if st.session_state.txt_file and os.path.exists(st.session_state.txt_file):
    with open(st.session_state.txt_file, "rb") as tf:
        st.download_button(
            "⬇️ Download Transcript & Summary",
            data=tf.read(),
            file_name=os.path.basename(st.session_state.txt_file),
            mime="text/plain",
        )

# -----------------------
# Reset button (fixed)
# -----------------------
if st.button("🔄 Reset"):
    # safely remove keys we used for UI state; do not delete saved folders on disk
    keys_to_clear = [
        "audio_file",
        "txt_file",
        "transcript",
        "summary",
        "session_recorder_output",  # the raw recorder blob
        "session_recorder",         # component key
        "processed_sessions",
    ]
    for k in keys_to_clear:
        if k in st.session_state:
            del st.session_state[k]

    # re-initialize processed_sessions so UI continues to work after reset
    st.session_state.processed_sessions = []
    st.success("Session reset!")

