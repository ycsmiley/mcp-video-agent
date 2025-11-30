"""
MCP Video Agent - Hugging Face Space Deployment
Combines Gradio frontend with direct Gemini API integration
Optimized for HF Space deployment with implicit caching
"""

import os
import gradio as gr
import time
import hashlib
import base64

# ==========================================
# Flexible API Key Loading
# ==========================================
def get_api_key(key_name):
    """Get API key from environment variables (HF Space Secrets)."""
    key = os.environ.get(key_name)
    if key:
        print(f"✅ Using {key_name} from environment")
        return key
    print(f"⚠️ {key_name} not found")
    return None

# ==========================================
# Video Analysis with Implicit Caching
# ==========================================

# Cache for uploaded Gemini files
gemini_files_cache = {}

def analyze_video_with_gemini(query: str, video_path: str):
    """
    Analyze video using Gemini 2.5 Flash with implicit caching.
    
    Args:
        query: User's question
        video_path: Local path to video file
    
    Returns:
        str: Analysis result
    """
    from google import genai
    import hashlib
    
    # Get API key
    api_key = get_api_key("GOOGLE_API_KEY")
    if not api_key:
        return "❌ Error: GOOGLE_API_KEY not set. Please configure it in Space Settings → Secrets."
    
    client = genai.Client(api_key=api_key)
    
    # Generate cache key for this video
    with open(video_path, 'rb') as f:
        video_hash = hashlib.md5(f.read()).hexdigest()
    
    cache_key = f"{video_path}_{video_hash}"
    
    try:
        # Check if we already uploaded this file
        if cache_key in gemini_files_cache:
            file_name = gemini_files_cache[cache_key]
            print(f"♻️ Using cached file: {file_name}")
            
            try:
                video_file = client.files.get(name=file_name)
                if video_file.state.name == 'ACTIVE':
                    print(f"✅ Cached file is active")
                else:
                    print(f"⚠️ Cached file state: {video_file.state.name}, re-uploading...")
                    video_file = None
            except Exception as e:
                print(f"⚠️ Cached file retrieval failed: {e}")
                video_file = None
        else:
            video_file = None
        
        # Upload if needed
        if video_file is None:
            print(f"📤 Uploading video to Gemini...")
            video_file = client.files.upload(file=video_path)
            
            # Wait for processing
            while video_file.state.name == 'PROCESSING':
                print('.', end='', flush=True)
                time.sleep(2)
                video_file = client.files.get(name=video_file.name)
            
            if video_file.state.name == 'FAILED':
                return "❌ Video processing failed"
            
            print(f"\n✅ Video uploaded: {video_file.uri}")
            
            # Cache the file reference
            gemini_files_cache[cache_key] = video_file.name
        
        # Generate content (implicit caching happens automatically)
        print(f"🧠 Analyzing with Gemini 2.5 Flash...")
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                video_file,
                f"{query}\n\nPlease provide a detailed but focused response within 300-400 words. Do NOT mention specific timestamps unless the user asks about timing."
            ]
        )
        
        # Print usage metadata
        if hasattr(response, 'usage_metadata'):
            print(f"📊 Usage: {response.usage_metadata}")
        
        if response.text:
            return response.text
        else:
            return "⚠️ No response generated. The content may have been blocked."
        
    except Exception as e:
        print(f"❌ Analysis error: {e}")
        return f"❌ Error: {str(e)}"


def generate_speech(text: str):
    """
    Generate speech from text using ElevenLabs.
    
    Args:
        text: Text to convert to speech
    
    Returns:
        str: Path to generated audio file or None
    """
    from elevenlabs.client import ElevenLabs
    
    # Get API key
    api_key = get_api_key("ELEVENLABS_API_KEY")
    if not api_key:
        print("⚠️ ELEVENLABS_API_KEY not set, skipping TTS")
        return None
    
    try:
        # Limit text length
        max_chars = 2500
        safe_text = text[:max_chars] if len(text) > max_chars else text
        
        if len(text) > max_chars:
            safe_text = safe_text.rstrip() + "..."
            print(f"⚠️ Text truncated from {len(text)} to {max_chars} chars")
        
        print(f"🗣️ Generating speech ({len(safe_text)} chars)...")
        start_time = time.time()
        
        client = ElevenLabs(api_key=api_key)
        
        audio_generator = client.text_to_speech.convert(
            voice_id="21m00Tcm4TlvDq8ikWAM",
            output_format="mp3_44100_128",
            text=safe_text,
            model_id="eleven_multilingual_v2"
        )
        
        # Generate unique filename
        timestamp = int(time.time())
        output_path = f"response_{timestamp}.mp3"
        
        with open(output_path, "wb") as f:
            for chunk in audio_generator:
                f.write(chunk)
        
        elapsed = time.time() - start_time
        print(f"✅ Speech generated in {elapsed:.2f}s")
        return output_path
        
    except Exception as e:
        print(f"❌ TTS error: {e}")
        return None


# ==========================================
# Gradio Interface Logic
# ==========================================

# Cache for uploaded videos
uploaded_videos_cache = {}

def process_interaction(user_message, history, video_file):
    """
    Core chatbot logic for HF Space.
    """
    if history is None:
        history = []
    
    # Track latest audio
    latest_audio = None
    
    # 1. Check video upload
    if video_file is None:
        yield history + [{"role": "assistant", "content": "⚠️ Please upload a video first!"}]
        return
    
    local_path = video_file
    
    # Check file size (100MB limit)
    file_size_mb = os.path.getsize(local_path) / (1024 * 1024)
    if file_size_mb > 100:
        yield history + [{"role": "assistant", "content": f"❌ Video too large! Size: {file_size_mb:.1f}MB. Please upload a video smaller than 100MB."}]
        return
    
    # Check cache
    with open(local_path, 'rb') as f:
        file_hash = hashlib.md5(f.read()).hexdigest()[:8]
    
    cache_key = f"{local_path}_{file_hash}"
    
    if cache_key in uploaded_videos_cache:
        print(f"♻️ Video already processed")
    else:
        print(f"📹 New video: {local_path} ({file_size_mb:.1f}MB)")
        uploaded_videos_cache[cache_key] = True
    
    # 2. Show thinking message
    history.append({"role": "user", "content": user_message})
    history.append({"role": "assistant", "content": "🤔 Gemini is analyzing the video..."})
    yield history
    
    # 3. Analyze video
    try:
        text_response = analyze_video_with_gemini(user_message, local_path)
    except Exception as e:
        text_response = f"❌ Analysis error: {str(e)}"
    
    # Store full text
    full_text_response = text_response
    
    # 4. Generate audio if successful
    if "❌" not in text_response and "⚠️" not in text_response:
        history[-1] = {"role": "assistant", "content": "🗣️ Generating audio response..."}
        yield history
        
        try:
            # Generate audio
            audio_path = generate_speech(text_response)
            
            # Wait for file to be ready
            if audio_path and os.path.exists(audio_path):
                time.sleep(0.5)
                
                # Check file has content
                if os.path.getsize(audio_path) > 0:
                    # Retry logic
                    max_retries = 2
                    for retry in range(max_retries):
                        if os.path.getsize(audio_path) > 1000:  # At least 1KB
                            break
                        print(f"⏳ Retry {retry + 1}: File too small, waiting...")
                        time.sleep(2)
                    
                    # Read audio and create response
                    with open(audio_path, 'rb') as f:
                        audio_bytes = f.read()
                        audio_base64 = base64.b64encode(audio_bytes).decode()
                    
                    # Create response with embedded audio
                    response_content = f"""🎙️ **Audio Response**

<audio controls autoplay style="width: 100%; margin: 10px 0; background: #f0f0f0; border-radius: 5px;">
    <source src="data:audio/mpeg;base64,{audio_base64}" type="audio/mpeg">
</audio>

**📝 Full Text Response:**

<div style="background-color: #000000; color: #00ff00; padding: 25px; border-radius: 10px; font-family: 'Courier New', monospace; line-height: 1.8; font-size: 14px; white-space: normal; word-wrap: break-word; overflow-wrap: break-word; max-width: 100%;">
{full_text_response}
</div>"""
                    
                    history[-1] = {"role": "assistant", "content": response_content}
                    yield history
                else:
                    # Audio file is empty
                    history[-1] = {"role": "assistant", "content": f"⚠️ Audio generation produced empty file.\n\n<div style='background: black; color: lime; padding: 20px; border-radius: 10px; white-space: normal; word-wrap: break-word;'>{full_text_response}</div>"}
                    yield history
            else:
                # No audio generated
                history[-1] = {"role": "assistant", "content": f"⚠️ Audio generation skipped (API key not set).\n\n<div style='background: black; color: lime; padding: 20px; border-radius: 10px; white-space: normal; word-wrap: break-word;'>{full_text_response}</div>"}
                yield history
        
        except Exception as e:
            # Audio error
            history[-1] = {"role": "assistant", "content": f"❌ Audio error: {str(e)}\n\n<div style='background: black; color: lime; padding: 20px; border-radius: 10px; white-space: normal; word-wrap: break-word;'>{full_text_response}</div>"}
            yield history
    else:
        # Error in analysis
        history[-1] = {"role": "assistant", "content": text_response}
        yield history


# ==========================================
# Gradio Interface
# ==========================================

with gr.Blocks(title="MCP Video Agent") as demo:
    gr.Markdown("# 🎥 MCP Video Agent")
    gr.Markdown("**Powered by Gemini 2.5 Flash + ElevenLabs TTS**")
    
    gr.Markdown("""
    ### 📖 How to Use
    1. Upload a video (MP4, max 100MB)
    2. Ask questions about the video
    3. Get AI-powered voice and text responses!
    
    ### 🔌 Use as MCP Server in Claude Desktop
    Add this URL to your Claude Desktop config:
    ```
    https://YOUR_USERNAME-mcp-video-agent.hf.space/sse
    ```
    
    **Note:** This Space uses the owner's API keys. For heavy usage, please:
    1. Click "Duplicate this Space"
    2. Add your own `GOOGLE_API_KEY` and `ELEVENLABS_API_KEY` in Settings → Secrets
    
    ### ⚙️ Required Secrets (in Space Settings)
    - `GOOGLE_API_KEY` - Get from [Google AI Studio](https://aistudio.google.com/apikey)
    - `ELEVENLABS_API_KEY` - Get from [ElevenLabs](https://elevenlabs.io) (optional, for TTS)
    """)
    
    with gr.Row():
        with gr.Column(scale=1):
            video_input = gr.Video(label="📹 Upload Video (MP4)", sources=["upload"])
            gr.Markdown("**Supported:** MP4, max 100MB")
        
        with gr.Column(scale=2):
            chatbot = gr.Chatbot(label="💬 Conversation", height=500)
            msg = gr.Textbox(
                label="Your question...", 
                placeholder="What is this video about?",
                lines=2
            )
            submit_btn = gr.Button("🚀 Send", variant="primary")
    
    # Examples
    gr.Examples(
        examples=[
            ["What is happening in this video?"],
            ["Describe the main content of this video."],
            ["What are the key visual elements?"],
        ],
        inputs=msg
    )
    
    # Event handlers
    submit_btn.click(
        process_interaction,
        inputs=[msg, chatbot, video_input],
        outputs=[chatbot]
    )
    
    msg.submit(
        process_interaction,
        inputs=[msg, chatbot, video_input],
        outputs=[chatbot]
    )

# ==========================================
# Launch
# ==========================================

if __name__ == "__main__":
    demo.launch(
        show_error=True,
        share=False
    )
