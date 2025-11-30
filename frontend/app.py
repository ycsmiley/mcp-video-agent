import gradio as gr
import modal
import os
import time

# --- 設定 ---
# 這裡要跟你的 backend/modal_app.py 裡面的 App 名稱一樣
APP_NAME = "mcp-video-agent"
VOLUME_NAME = "video-storage"

# Global cache for uploaded videos
# Structure: {video_path: unique_filename}
uploaded_videos_cache = {}

def process_interaction(user_message, history, video_file):
    """
    Core Gradio logic:
    1. Check if video is uploaded -> upload to Modal
    2. Call Modal's Gemini analysis
    3. Call Modal's ElevenLabs TTS
    
    Returns: (history, audio_path)
    """
    
    # Initialize history if None
    if history is None:
        history = []
    
    # Track latest audio file
    latest_audio = None
    
    # 1. Handle video upload
    if video_file is None:
        yield history + [{"role": "assistant", "content": "⚠️ Please upload a video first!"}]
        return

    local_path = video_file
    
    # Check file size (100MB limit)
    file_size_mb = os.path.getsize(local_path) / (1024 * 1024)
    if file_size_mb > 100:
        yield history + [{"role": "assistant", "content": f"❌ Video too large! Size: {file_size_mb:.1f}MB. Please upload a video smaller than 100MB."}]
        return
    
    # Check if this video is already uploaded (using cache)
    import hashlib
    with open(local_path, 'rb') as f:
        file_hash = hashlib.md5(f.read()).hexdigest()[:8]
    
    cache_key = f"{local_path}_{file_hash}"
    
    if cache_key in uploaded_videos_cache:
        # Video already uploaded, reuse existing filename
        unique_filename = uploaded_videos_cache[cache_key]
        print(f"♻️ Reusing cached video: {unique_filename} (no upload needed)")
    else:
        # New video, need to upload
        print(f"📤 Uploading new video to Modal cloud: {local_path} ({file_size_mb:.1f}MB)")
        
        # Generate unique filename
        timestamp = int(time.time())
        unique_filename = f"video_{timestamp}_{file_hash}.mp4"
        print(f"📝 Using unique filename: {unique_filename}")
        
        # Upload to Modal volume
        upload_cmd = f"modal volume put {VOLUME_NAME} '{local_path}' {unique_filename}"
        exit_code = os.system(upload_cmd)
        
        if exit_code != 0:
            yield history + [{"role": "assistant", "content": "❌ Video upload failed. Please check your network connection."}]
            return
        
        # Cache the uploaded video
        uploaded_videos_cache[cache_key] = unique_filename
        print(f"✅ Video cached for future use")

    # 2. Connect to Modal functions
    try:
        analyze_fn = modal.Function.from_name(APP_NAME, "_internal_analyze_video")
        speak_fn = modal.Function.from_name(APP_NAME, "_internal_speak_text")
        create_cache_fn = modal.Function.from_name(APP_NAME, "_internal_create_cache")
        view_cache_fn = modal.Function.from_name(APP_NAME, "_internal_view_cache")
        delete_cache_fn = modal.Function.from_name(APP_NAME, "_internal_delete_cache")
    except Exception as e:
        yield history + [{"role": "assistant", "content": f"❌ Backend connection failed: {str(e)}"}]
        return
    
    # Check for special commands
    if user_message.lower().strip() in ["/cache", "/upload"]:
        # Pre-upload video to Gemini
        history.append({"role": "user", "content": user_message})
        history.append({"role": "assistant", "content": "📤 Uploading video to Gemini... This may take 1-2 minutes."})
        yield history
        
        try:
            cache_result = create_cache_fn.remote(unique_filename)
            status = cache_result.get("status", "unknown")
            message = cache_result.get("message", "")
            
            if status == "uploaded":
                history[-1] = {"role": "assistant", "content": f"""✅ **Video Uploaded to Gemini!**

📊 **Upload Info:**
- Video: {unique_filename}
- File URI: {cache_result.get('file_uri', 'N/A')[:50]}...

🚀 **Benefits:**
- Gemini 2.5 Flash uses **implicit caching** automatically
- Subsequent queries will reuse the uploaded file
- No extra cost for caching (free tier compatible!)

💡 Just ask your questions!"""}
            elif status == "existing":
                history[-1] = {"role": "assistant", "content": f"✅ **Video Already Uploaded**\n\n{message}\n\n💡 Just ask your questions!"}
            else:
                history[-1] = {"role": "assistant", "content": f"⚠️ Upload issue: {message}"}
        except Exception as e:
            history[-1] = {"role": "assistant", "content": f"❌ Upload failed: {str(e)}"}
        
        yield history
        return
    
    if user_message.lower().strip() == "/status":
        # View cache status
        history.append({"role": "user", "content": user_message})
        history.append({"role": "assistant", "content": "📂 Checking cache status..."})
        yield history
        
        try:
            cache_info = view_cache_fn.remote(unique_filename)
            status = cache_info.get("status", "unknown")
            
            if status == "cached":
                history[-1] = {"role": "assistant", "content": f"""📊 **Cache Status: Active ✅**

- **Video:** {cache_info.get('video', 'unknown')}
- **Model:** {cache_info.get('model', 'unknown')}
- **TTL:** {cache_info.get('ttl', 'unknown')}
- **Remaining:** {cache_info.get('remaining', 'unknown')}

{cache_info.get('message', '')}"""}
            else:
                history[-1] = {"role": "assistant", "content": f"""📊 **Cache Status: Not Cached**

- **Video:** {cache_info.get('video', 'unknown')}

💡 Use `/cache` to create a context cache for faster queries!"""}
        except Exception as e:
            history[-1] = {"role": "assistant", "content": f"❌ Failed to check status: {str(e)}"}
        
        yield history
        return
    
    if user_message.lower().strip() == "/clear":
        # Delete cache
        history.append({"role": "user", "content": user_message})
        history.append({"role": "assistant", "content": "🗑️ Deleting cache..."})
        yield history
        
        try:
            result = delete_cache_fn.remote(unique_filename)
            history[-1] = {"role": "assistant", "content": f"✅ {result.get('message', 'Cache deleted')}"}
        except Exception as e:
            history[-1] = {"role": "assistant", "content": f"❌ Failed to delete cache: {str(e)}"}
        
        yield history
        return

    # Show "thinking" message
    history.append({"role": "user", "content": user_message})
    history.append({"role": "assistant", "content": "🤔 Gemini is analyzing the video..."})
    yield history

    # Execute Gemini analysis (with dynamic filename)
    try:
        text_response = analyze_fn.remote(user_message, video_filename=unique_filename)
    except Exception as e:
        text_response = f"❌ Analysis error: {str(e)}"

    # Store the full text response for later (user can click to view)
    full_text_response = text_response
    
    # 3. Call ElevenLabs TTS (if no errors or warnings)
    if "❌" not in text_response and "⚠️" not in text_response:
        # Replace the thinking message with "generating audio"
        history[-1] = {"role": "assistant", "content": "🗣️ Generating audio response..."}
        yield history
        
        try:
            # Remote TTS generation - wait for it to complete
            print("🗣️ Generating TTS on Modal...")
            tts_result = speak_fn.remote(text_response)
            print(f"TTS result: {tts_result}")
            
            # Wait for Modal Volume to sync (important!)
            print("⏳ Waiting for Modal Volume to sync...")
            time.sleep(3)  # Give Modal Volume time to sync
            
            # Download audio with unique filename
            local_audio_filename = f"audio_{unique_filename.replace('.mp4', '.mp3')}"
            download_cmd = f"modal volume get {VOLUME_NAME} response.mp3 {local_audio_filename} --force"
            print(f"📥 Downloading audio: {download_cmd}")
            exit_code = os.system(download_cmd)
            print(f"Download exit code: {exit_code}")
            
            # Wait for file to be fully written
            time.sleep(1)
            
            # Retry logic if file is empty
            max_retries = 3
            for retry in range(max_retries):
                if os.path.exists(local_audio_filename) and os.path.getsize(local_audio_filename) > 0:
                    break
                print(f"⏳ Retry {retry + 1}/{max_retries}: File not ready, waiting...")
                time.sleep(2)
                os.system(download_cmd)  # Try downloading again
            
            # Debug: Check file status
            print(f"🔍 Checking file: {local_audio_filename}")
            print(f"   Exists: {os.path.exists(local_audio_filename)}")
            if os.path.exists(local_audio_filename):
                print(f"   Size: {os.path.getsize(local_audio_filename)} bytes")
            
            # Check if file exists and has content
            if os.path.exists(local_audio_filename) and os.path.getsize(local_audio_filename) > 0:
                # Get absolute path for Gradio
                abs_audio_path = os.path.abspath(local_audio_filename)
                print(f"✅ Audio ready: {abs_audio_path} ({os.path.getsize(abs_audio_path)/1024:.1f}KB)")
                
                # Read audio file as base64 for reliable embedding
                import base64
                with open(abs_audio_path, 'rb') as audio_file:
                    audio_bytes = audio_file.read()
                    audio_base64 = base64.b64encode(audio_bytes).decode()
                
                # Create response with embedded audio using HTML5 audio tag
                # Using data URI ensures audio is part of the message and won't be overwritten
                response_content = f"""🎙️ **Audio Response**

<audio controls autoplay style="width: 100%; margin: 10px 0; background: #f0f0f0; border-radius: 5px;">
    <source src="data:audio/mpeg;base64,{audio_base64}" type="audio/mpeg">
    Your browser does not support the audio element.
</audio>

**📝 Full Text Response:**

<div style="background-color: #000000; color: #00ff00; padding: 25px; border-radius: 10px; font-family: 'Courier New', monospace; line-height: 1.8; font-size: 14px; white-space: normal; word-wrap: break-word; overflow-wrap: break-word; max-width: 100%;">
{full_text_response}
</div>"""
                
                # Update history with formatted response (audio embedded in chatbot)
                history[-1] = {
                    "role": "assistant", 
                    "content": response_content
                }
                
                # No need to return separate audio path - it's embedded in the message
                yield history
            else:
                # If audio fails, show text response with debug info
                debug_info = f"File exists: {os.path.exists(local_audio_filename)}"
                if os.path.exists(local_audio_filename):
                    debug_info += f", Size: {os.path.getsize(local_audio_filename)} bytes"
                
                history[-1] = {
                    "role": "assistant", 
                    "content": f"⚠️ Audio generation failed. ({debug_info})\n\nHere's the text response:\n\n<div style='background: black; color: lime; padding: 20px; border-radius: 10px; white-space: normal; word-wrap: break-word; overflow-wrap: break-word;'>{full_text_response}</div>"
                }
                yield history
            
        except Exception as e:
            # If error, show text response
            history[-1] = {
                "role": "assistant", 
                "content": f"❌ Audio generation failed: {str(e)}\n\n<div style='background: black; color: lime; padding: 20px; border-radius: 10px; white-space: normal; word-wrap: break-word; overflow-wrap: break-word;'>{full_text_response}</div>"
            }
            yield history
    else:
        # If there's an error or warning in the response, just show text
        history[-1] = {"role": "assistant", "content": text_response}
        yield history

# --- Interface Design (Gradio 6) ---
with gr.Blocks(title="MCP Video Agent") as demo:
    gr.Markdown("# 🎥 MCP Video Agent (Gemini 2.5 Flash + ElevenLabs)")
    gr.Markdown("""Upload a video and ask me anything about it!

**💡 Commands:**
- `/upload` - Pre-upload video to Gemini (faster subsequent queries)
- `/status` - Check upload status
- `/clear` - Clear uploaded file

**How it works:**
1. Upload a video
2. (Optional) Use `/upload` to pre-upload to Gemini
3. Ask questions - Gemini 2.5 uses implicit caching automatically!
""")
    
    with gr.Row():
        with gr.Column(scale=1):
            # Video upload area
            video_input = gr.Video(label="Upload Video (MP4)", sources=["upload"])
        
        with gr.Column(scale=2):
            # Chat window (Gradio 6.0.1) - audio will be embedded in messages
            chatbot = gr.Chatbot(label="Conversation", height=500)
            msg = gr.Textbox(label="Your question...", placeholder="What is this video about?")
            submit_btn = gr.Button("Send", variant="primary")

    # 事件綁定 - 只需要更新 chatbot (audio embedded in messages)
    submit_btn.click(
        process_interaction, 
        inputs=[msg, chatbot, video_input], 
        outputs=[chatbot]
    )
    
    # 按下 Enter 也能發送
    msg.submit(
        process_interaction, 
        inputs=[msg, chatbot, video_input], 
        outputs=[chatbot]
    )

if __name__ == "__main__":
    # Launch with file serving enabled for local audio files
    demo.launch(
        allowed_paths=[os.getcwd()],  # Allow serving files from current directory
        show_error=True
    )