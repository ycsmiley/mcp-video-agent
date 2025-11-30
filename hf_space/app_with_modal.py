"""
MCP Video Agent - HF Space with Modal Backend + Security
Connects to Modal backend with authentication and rate limiting
"""

import os
import gradio as gr
import time
import hashlib
import base64
from datetime import datetime, timedelta
from collections import defaultdict

# ==========================================
# Security: Rate Limiting
# ==========================================
class RateLimiter:
    """Simple in-memory rate limiter"""
    def __init__(self, max_requests_per_hour=10):
        self.max_requests = max_requests_per_hour
        self.requests = defaultdict(list)
    
    def is_allowed(self, user_id):
        """Check if user is within rate limit"""
        now = datetime.now()
        cutoff = now - timedelta(hours=1)
        
        # Clean old requests
        self.requests[user_id] = [
            req_time for req_time in self.requests[user_id]
            if req_time > cutoff
        ]
        
        # Check limit
        if len(self.requests[user_id]) >= self.max_requests:
            return False
        
        # Record new request
        self.requests[user_id].append(now)
        return True
    
    def get_remaining(self, user_id):
        """Get remaining requests for user"""
        now = datetime.now()
        cutoff = now - timedelta(hours=1)
        recent = [t for t in self.requests[user_id] if t > cutoff]
        return max(0, self.max_requests - len(recent))

# Initialize rate limiter (configurable via environment)
MAX_REQUESTS_PER_HOUR = int(os.environ.get("MAX_REQUESTS_PER_HOUR", "10"))
rate_limiter = RateLimiter(max_requests_per_hour=MAX_REQUESTS_PER_HOUR)

# ==========================================
# Modal Connection
# ==========================================
import modal

def get_modal_function(function_name):
    """Connect to Modal function"""
    try:
        func = modal.Function.from_name("mcp-video-agent", function_name)
        return func
    except Exception as e:
        print(f"❌ Failed to connect to Modal: {e}")
        return None

# ==========================================
# Gradio Interface Logic
# ==========================================

# Cache for uploaded videos
uploaded_videos_cache = {}

def process_interaction(user_message, history, video_file, username, request: gr.Request):
    """
    Core chatbot logic with Modal backend and security.
    """
    if history is None:
        history = []
    
    # Get user identifier for rate limiting
    user_id = username  # Use authenticated username
    
    # Check rate limit
    if not rate_limiter.is_allowed(user_id):
        remaining = rate_limiter.get_remaining(user_id)
        yield history + [{"role": "assistant", "content": f"⚠️ Rate limit exceeded. You have {remaining} requests remaining this hour. Please try again later."}]
        return
    
    # Show remaining requests
    remaining = rate_limiter.get_remaining(user_id)
    print(f"💡 User {user_id}: {remaining} requests remaining this hour")
    
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
    
    # Generate unique filename
    with open(local_path, 'rb') as f:
        file_hash = hashlib.md5(f.read()).hexdigest()[:8]
    
    timestamp = int(time.time())
    unique_filename = f"video_{timestamp}_{file_hash}.mp4"
    cache_key = f"{local_path}_{file_hash}"
    
    # 2. Upload to Modal Volume if needed
    if cache_key not in uploaded_videos_cache:
        history.append({"role": "user", "content": user_message})
        history.append({"role": "assistant", "content": f"📤 Uploading video ({file_size_mb:.1f}MB)..."})
        yield history
        
        try:
            import subprocess
            result = subprocess.run(
                ["modal", "volume", "put", "video-storage", local_path, f"/{unique_filename}", "--force"],
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode != 0:
                history[-1] = {"role": "assistant", "content": f"❌ Upload failed: {result.stderr}"}
                yield history
                return
            
            uploaded_videos_cache[cache_key] = unique_filename
            print(f"✅ Video uploaded: {unique_filename}")
        except Exception as e:
            history[-1] = {"role": "assistant", "content": f"❌ Upload error: {str(e)}"}
            yield history
            return
    else:
        unique_filename = uploaded_videos_cache[cache_key]
        history.append({"role": "user", "content": user_message})
        history.append({"role": "assistant", "content": "♻️ Using cached video..."})
        yield history
    
    # 3. Analyze video via Modal
    history[-1] = {"role": "assistant", "content": "🤔 Analyzing video with Gemini..."}
    yield history
    
    try:
        analyze_fn = get_modal_function("_internal_analyze_video")
        if analyze_fn is None:
            history[-1] = {"role": "assistant", "content": "❌ Failed to connect to Modal backend. Please check deployment."}
            yield history
            return
        
        text_response = analyze_fn.remote(user_message, video_filename=unique_filename)
    except Exception as e:
        text_response = f"❌ Analysis error: {str(e)}"
    
    full_text_response = text_response
    
    # 4. Generate audio if successful
    if "❌" not in text_response and "⚠️" not in text_response:
        history[-1] = {"role": "assistant", "content": "🗣️ Generating audio response..."}
        yield history
        
        try:
            speak_fn = get_modal_function("_internal_speak_text")
            if speak_fn is None:
                history[-1] = {"role": "assistant", "content": f"⚠️ TTS unavailable.\n\n<div style='background: black; color: lime; padding: 20px; border-radius: 10px; white-space: normal; word-wrap: break-word;'>{full_text_response}</div>"}
                yield history
                return
            
            audio_filename = f"audio_{unique_filename.replace('.mp4', '.mp3')}"
            speak_fn.remote(text_response, audio_filename=audio_filename)
            
            # Download audio
            time.sleep(2)
            import subprocess
            local_audio = f"/tmp/{audio_filename}"
            
            max_retries = 3
            for retry in range(max_retries):
                result = subprocess.run(
                    ["modal", "volume", "get", "video-storage", f"/{audio_filename}", local_audio],
                    capture_output=True,
                    text=True
                )
                
                if result.returncode == 0 and os.path.exists(local_audio) and os.path.getsize(local_audio) > 1000:
                    break
                time.sleep(2)
            
            if os.path.exists(local_audio) and os.path.getsize(local_audio) > 1000:
                with open(local_audio, 'rb') as f:
                    audio_bytes = f.read()
                    audio_base64 = base64.b64encode(audio_bytes).decode()
                
                response_content = f"""🎙️ **Audio Response** ({remaining} requests remaining this hour)

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
                history[-1] = {"role": "assistant", "content": f"⚠️ Audio generation incomplete.\n\n<div style='background: black; color: lime; padding: 20px; border-radius: 10px; white-space: normal; word-wrap: break-word;'>{full_text_response}</div>"}
                yield history
        
        except Exception as e:
            history[-1] = {"role": "assistant", "content": f"❌ Audio error: {str(e)}\n\n<div style='background: black; color: lime; padding: 20px; border-radius: 10px; white-space: normal; word-wrap: break-word;'>{full_text_response}</div>"}
            yield history
    else:
        history[-1] = {"role": "assistant", "content": text_response}
        yield history


# ==========================================
# Gradio Interface with Authentication
# ==========================================

# Get credentials from environment
GRADIO_USERNAME = os.environ.get("GRADIO_USERNAME", "admin")
GRADIO_PASSWORD = os.environ.get("GRADIO_PASSWORD")

# Authentication function (optional for Hackathon/Demo)
def authenticate(username, password):
    """Authenticate users - only if password is set"""
    if GRADIO_PASSWORD is None:
        # No password set, allow anyone (good for Hackathon/Demo)
        return True
    return username == GRADIO_USERNAME and password == GRADIO_PASSWORD

with gr.Blocks(title="🎥 MCP Video Agent") as demo:
    gr.Markdown("# 🎥 MCP Video Agent")
    gr.Markdown("**🏆 MCP 1st Birthday Hackathon** | Track: MCP in Action (Consumer & Creative)")
    
    gr.Markdown(f"""
    ### ⚡ Key Innovation: Smart Frame Caching
    
    **First Query**: Video is analyzed deeply and cached (~8-12 seconds)  
    **Follow-up Queries**: Instant responses using cached context (~2-3 seconds, 90% cost reduction!)  
    **Cache Duration**: 1 hour - ask multiple questions without reprocessing
    
    ---
    
    ### 📖 How to Use
    
    1. **Upload** a video (MP4, max 100MB)
    2. **Ask** your first question - video will be analyzed and cached
    3. **Continue** asking follow-up questions - experience the speed boost!
    4. **Listen** to voice responses (powered by ElevenLabs TTS)
    
    **Pro Tip**: After your first question, try asking 2-3 more to see how fast cached responses are!
    
    ---
    
    ### 🛡️ Fair Usage Policy
    
    - **Rate Limit**: {MAX_REQUESTS_PER_HOUR} requests per hour per user
    - **Video Size**: Max 100MB
    - **Shared Resources**: This is a Hackathon demo - please use responsibly
    
    ---
    
    ### 🔧 Tech Stack
    
    - **Gemini 2.5 Flash**: Multimodal video analysis + Context Caching
    - **Modal**: Serverless backend + Persistent storage
    - **ElevenLabs**: Neural text-to-speech
    - **Gradio 6.0**: Interactive UI
    
    **Sponsor Tech Used**: ✅ Modal | ✅ Google Gemini | ✅ ElevenLabs
    """)
    
    username_state = gr.State("")
    
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
    
    # Get username from Gradio request
    def set_username(request: gr.Request):
        return request.username if hasattr(request, 'username') else "anonymous"
    
    demo.load(set_username, None, username_state)
    
    # Event handlers
    submit_btn.click(
        process_interaction,
        inputs=[msg, chatbot, video_input, username_state],
        outputs=[chatbot]
    )
    
    msg.submit(
        process_interaction,
        inputs=[msg, chatbot, video_input, username_state],
        outputs=[chatbot]
    )

# ==========================================
# Launch with Authentication
# ==========================================

if __name__ == "__main__":
    # Optional authentication (for Hackathon, usually not needed)
    auth_config = None
    if GRADIO_PASSWORD:
        auth_config = authenticate
        print(f"🔒 Authentication enabled. Username: {GRADIO_USERNAME}")
    else:
        print("🌐 Public access enabled (no authentication required)")
        print("   Rate limiting active to prevent abuse")
        print(f"   Limit: {MAX_REQUESTS_PER_HOUR} requests/hour per user")
    
    demo.launch(
        auth=auth_config,
        show_error=True,
        share=False
    )

