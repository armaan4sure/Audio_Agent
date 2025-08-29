import os
import streamlit as st
from datetime import datetime
from streamlit_mic_recorder import mic_recorder
import assemblyai as aai

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

def save_session_files(audio_file: str, transcript: str, summary: str):
    """Save transcript and audio inside timestamped folder"""
    folder = datetime.now().strftime("%Y%m%d_%H%M%S")
    os.makedirs(folder, exist_ok=True)

    # Move/copy audio
    audio_dest = os.path.join(folder, os.path.basename(audio_file))
    os.replace(audio_file, audio_dest)

    # Save transcript
    transcript_file = os.path.join(folder, "transcript.txt")
    with open(transcript_file, "w", encoding="utf-8") as f:
        f.write("TRANSCRIPT:\n" + transcript + "\n\nSUMMARY:\n" + summary)

    return audio_dest, transcript_file, folder

# -----------------------
# Streamlit UI
# -----------------------
st.set_page_config(page_title="🎤 Audio Agent", layout="centered")
st.title("🎤 Audio Recorder + AssemblyAI")

# Record audio via mic_recorder
audio = mic_recorder(
    start_prompt="▶️ Start Recording",
    stop_prompt="⏹️ Stop Recording",
    just_once=True,
    use_container_width=True,
    key="session_recorder"
)

# When recording is done
if audio:
    out = st.session_state["session_recorder_output"]
    # wav_file = f"tmp_{out['id']}.wav"
    wav_file = "recording.wav"
    with open(wav_file, "wb") as f:
        f.write(out["bytes"])
    st.audio(out["bytes"], format="audio/wav")

    with st.spinner("Transcribing..."):
        transcript = speech_to_text(wav_file)
    with st.spinner("Summarizing..."):
        summary = summarize_text(wav_file)

    audio_dest, txt_dest, folder = save_session_files(wav_file, transcript, summary)

    st.session_state.audio_file = audio_dest
    st.session_state.txt_file = txt_dest
    st.session_state.transcript = transcript
    st.session_state.summary = summary

    st.success(f"✅ Session saved in: `{folder}`")

# Show transcript + summary if available
if "transcript" in st.session_state:
    st.subheader("📄 Transcript")
    st.text_area("Transcript", st.session_state.transcript, height=200)

if "summary" in st.session_state:
    st.subheader("📝 Summary")
    st.write(st.session_state.summary)

# Download buttons
if "audio_file" in st.session_state and "txt_file" in st.session_state:
    st.download_button("⬇️ Download Audio",
                       data=open(st.session_state.audio_file, "rb").read(),
                       file_name="recording.wav",
                       mime="audio/wav")
    st.download_button("⬇️ Download Transcript",
                       data=open(st.session_state.txt_file, "rb").read(),
                       file_name="transcript.txt",
                       mime="text/plain")

# Reset button
if st.button("🔄 Reset"):
    for k in ["audio_file", "txt_file", "transcript", "summary", "session_recorder_output"]:
        st.session_state.pop(k, None)