# AI Skin Specialist

This repository contains a Gradio-based Python app for skin consultation using image uploads, patient voice transcription, and AI response generation.

## Deploying to Render

1. Create a new Python Web Service on Render.
2. Connect it to this repository and select the `main` branch.
3. Set the Build Command to:

   ```bash
   pip install -r requirements.txt
   ```

4. Set the Start Command to:

   ```bash
   python main.py
   ```

5. Add these required environment variables in Render:
   - `GROQ_API_KEY`
   - `DEEPGRAM_API_KEY`
   - `WHISPER_MODEL` (optional, defaults to `whisper-large-v3`)
   - `GROQ_MODEL` (optional, defaults to `meta-llama/llama-4-scout-17b-16e-instruct`)
   - `DEEPGRAM_TTS_MODEL` (optional, defaults to `aura-2-thalia-en`)

6. Deploy the service.

The app is configured to bind to Render's assigned `PORT` and listen on all interfaces.
