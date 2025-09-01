# 🎤 Audio Agent – Architecture & Cost Flow

## 1. Flow Overview
	
![Flowchart](https://github.com/armaan4sure/Audio_Agent/blob/main/Audio_Agent.png)


## 2. Components Used

| Layer                        | Tool / Model                              | Purpose                                          |
| ---------------------------- | ----------------------------------------- | ------------------------------------------------ |
| **Frontend**                 | `streamlit` + `streamlit-mic-recorder`    | UI, audio recording, session management          |
| **Backend Audio Processing** | Azure Speech-to-Text REST API             | Converts speech to text with speaker diarization |
| **Summarization**        | OpenAI GPT-4o Mini (Chat Completions API)       | Generates concise summaries of transcripts       |
| **Orchestration**            | Python (`asyncio`, `aiohttp`)             | Handles async calls to APIs                      |
| **Persistence**              | Local storage (`Transcripts/Session_xxx`) | Saves audio, transcript, and summary             |
| **Deployment**               | Streamlit Cloud / GitHub integration      | CI/CD deployment                                 |


## 3. Expected Costs*

| Service                     | Pricing Basis                                         | Estimate (per hour of audio)                                                                                    |
| --------------------------- | ----------------------------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| **Azure Speech-to-Text**    | ~\$1 per audio hour (standard tier)                   | \$1.00                                                                                                          |
| **OpenAI GPT-5 (Chat API)** | ~\$5–10 per million tokens (depends on tier & model)  | For 1h audio → transcript ~12k words (~16k tokens). Summary prompt+response ~2k tokens. Cost ≈ \$0.10–\$0.25    |
| **Streamlit Cloud Hosting** | Free tier or ~\$25/mo for team                        | Fixed monthly                                                                                                   |
| **Storage**                 | Local / GitHub artifacts                              | Negligible                                                                                                      |


