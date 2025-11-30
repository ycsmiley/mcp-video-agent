import os
from modal import App, Image, Volume, Secret, asgi_app

# ==========================================
# Flexible API Key Loading
# ==========================================
def get_api_key(key_name):
    """Flexible API key loading for multiple environments."""
    key = os.environ.get(key_name)
    if key:
        print(f"✅ Using {key_name} from environment variable")
        return key
    print(f"⚠️ {key_name} not found in environment")
    return None

# ==========================================
# Modal Image with New Google GenAI SDK
# ==========================================
image = (
    Image.debian_slim()
    .apt_install("ffmpeg")
    .pip_install(
        "google-genai>=1.0.0",  # New unified SDK with context caching
        "elevenlabs>=1.0.0",
        "mcp",
        "fastapi",
        "uvicorn",
    )
)

app = App("mcp-video-agent")
vol = Volume.from_name("video-storage", create_if_missing=True)

# ==========================================
# Video Upload: Upload and Store Video File Reference
# ==========================================
@app.function(
    image=image,
    volumes={"/data": vol},
    secrets=[Secret.from_name("my-google-secret")],
    timeout=600
)
def _internal_create_cache(video_filename: str = "demo_video.mp4", ttl_seconds: int = 3600):
    """
    Upload video to Gemini Files API and store the reference.
    This enables implicit caching (automatic with Gemini 2.5 models).
    
    Note: Explicit context caching requires a paid API tier.
    Free tier users benefit from implicit caching automatically.
    
    Args:
        video_filename: Video file in the Modal Volume
        ttl_seconds: Not used for implicit caching, kept for API compatibility
    
    Returns:
        dict with upload info
    """
    from google import genai
    import time
    import json
    
    video_path = f"/data/{video_filename}"
    cache_info_path = f"/data/cache_info/{video_filename.replace('.mp4', '')}.json"
    
    # Wait for volume sync
    print(f"📂 Checking video: {video_path}")
    for i in range(10):
        if os.path.exists(video_path):
            break
        print(f"⏳ Waiting for volume sync... ({i+1}/10)")
        time.sleep(1)
    else:
        return {"error": f"Video not found: {video_filename}"}
    
    # Initialize client
    api_key = get_api_key("GOOGLE_API_KEY")
    if not api_key:
        return {"error": "GOOGLE_API_KEY not set"}
    
    client = genai.Client(api_key=api_key)
    
    # Check if we have an existing uploaded file
    os.makedirs("/data/cache_info", exist_ok=True)
    if os.path.exists(cache_info_path):
        try:
            with open(cache_info_path, 'r') as f:
                existing_info = json.load(f)
            
            file_name = existing_info.get("file_name")
            if file_name:
                try:
                    # Check if file still exists
                    file_info = client.files.get(name=file_name)
                    if file_info.state.name == 'ACTIVE':
                        print(f"📂 Found existing uploaded file: {file_name}")
                        return {
                            "status": "existing",
                            "file_name": file_name,
                            "file_uri": existing_info.get("file_uri"),
                            "video": video_filename,
                            "message": "Video already uploaded! Implicit caching is active."
                        }
                except Exception as e:
                    print(f"⚠️ Existing file expired or invalid: {e}")
        except Exception as e:
            print(f"⚠️ Could not read cache info: {e}")
    
    # Upload video to Gemini Files API
    print(f"📤 Uploading video to Gemini Files API...")
    video_file = client.files.upload(file=video_path)
    
    # Wait for processing
    print("⏳ Waiting for video processing...")
    while video_file.state.name == 'PROCESSING':
        print('.', end='', flush=True)
        time.sleep(2)
        video_file = client.files.get(name=video_file.name)
    
    if video_file.state.name == 'FAILED':
        return {"error": "Video processing failed"}
    
    print(f"\n✅ Video uploaded: {video_file.uri}")
    print(f"   File name: {video_file.name}")
    
    # Save file info (for implicit caching)
    cache_info = {
        "file_name": video_file.name,
        "file_uri": video_file.uri,
        "video_filename": video_filename,
        "model": "gemini-2.5-flash",
        "created_at": time.time(),
        "mode": "implicit_caching"
    }
    
    with open(cache_info_path, 'w') as f:
        json.dump(cache_info, f, indent=2)
    
    vol.commit()
    
    return {
        "status": "uploaded",
        "file_name": video_file.name,
        "file_uri": video_file.uri,
        "video": video_filename,
        "message": "Video uploaded! Gemini 2.5 will use implicit caching automatically."
    }


# ==========================================
# Context Cache: Query with Cache
# ==========================================
@app.function(
    image=image,
    volumes={"/data": vol},
    secrets=[Secret.from_name("my-google-secret")],
    timeout=600,
    max_containers=5  # Limit concurrent containers for cost control
)
def _internal_analyze_video(query: str, video_filename: str = "demo_video.mp4"):
    """
    Analyze video using Context Cache (if available) or direct upload (fallback).
    
    Args:
        query: User's question
        video_filename: Video file in the volume
    
    Returns:
        str: Analysis result
    """
    from google import genai
    from google.genai import types
    import json
    import time
    
    video_path = f"/data/{video_filename}"
    cache_info_path = f"/data/cache_info/{video_filename.replace('.mp4', '')}.json"
    
    # Wait for volume sync
    print(f"📂 Checking video: {video_filename}")
    for i in range(10):
        if os.path.exists(video_path):
            break
        print(f"⏳ Waiting for volume sync... ({i+1}/10)")
        time.sleep(1)
    else:
        files = os.listdir("/data") if os.path.exists("/data") else []
        return f"❌ Error: Video not found: {video_filename}\nFiles in /data: {files[:10]}"
    
    # Initialize client
    api_key = get_api_key("GOOGLE_API_KEY")
    if not api_key:
        return "❌ Error: GOOGLE_API_KEY not set"
    
    client = genai.Client(api_key=api_key)
    
    # ==========================================
    # Try to use pre-uploaded file (implicit caching)
    # ==========================================
    video_file = None
    
    if os.path.exists(cache_info_path):
        try:
            with open(cache_info_path, 'r') as f:
                cache_info = json.load(f)
            
            file_name = cache_info.get("file_name")
            
            if file_name:
                print(f"📂 Found pre-uploaded file: {file_name}")
                
                # Try to get the existing file
                try:
                    video_file = client.files.get(name=file_name)
                    if video_file.state.name == 'ACTIVE':
                        print(f"✅ Using cached file (implicit caching active)")
                    else:
                        print(f"⚠️ File state: {video_file.state.name}, re-uploading...")
                        video_file = None
                except Exception as e:
                    print(f"⚠️ Could not retrieve file: {e}")
                    video_file = None
            
        except Exception as e:
            print(f"⚠️ Cache info read failed: {e}")
    
    # ==========================================
    # Upload video if not already uploaded
    # ==========================================
    if video_file is None:
        print(f"🎬 Uploading video to Gemini...")
        
        video_file = client.files.upload(file=video_path)
        
        # Wait for processing
        while video_file.state.name == 'PROCESSING':
            print('.', end='', flush=True)
            time.sleep(2)
            video_file = client.files.get(name=video_file.name)
        
        if video_file.state.name == 'FAILED':
            return "❌ Video processing failed"
        
        print(f"\n✅ Video uploaded: {video_file.uri}")
        
        # Save file info for future use
        os.makedirs("/data/cache_info", exist_ok=True)
        cache_info = {
            "file_name": video_file.name,
            "file_uri": video_file.uri,
            "video_filename": video_filename,
            "model": "gemini-2.5-flash",
            "created_at": time.time(),
            "mode": "implicit_caching"
        }
        with open(cache_info_path, 'w') as f:
            json.dump(cache_info, f, indent=2)
        vol.commit()
    
    # ==========================================
    # Generate content using the file
    # ==========================================
    try:
        print(f"🧠 Analyzing with Gemini 2.5 Flash...")
        
        # Generate content (implicit caching happens automatically)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                video_file,
                f"{query}\n\nPlease provide a concise response within 150-200 words. Be direct and informative. Do NOT mention specific timestamps unless asked."
            ]
        )
        
        # Print usage metadata to see caching info
        if hasattr(response, 'usage_metadata'):
            print(f"📊 Usage: {response.usage_metadata}")
        
        if response.text:
            return response.text
        else:
            return "⚠️ No response generated. The content may have been blocked."
        
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        return f"❌ Error: {str(e)}"


# ==========================================
# View Cache Info
# ==========================================
@app.function(
    image=image,
    volumes={"/data": vol},
    timeout=60
)
def _internal_view_cache(video_filename: str = "demo_video.mp4"):
    """View the cache status for a video."""
    import json
    
    cache_info_path = f"/data/cache_info/{video_filename.replace('.mp4', '')}.json"
    
    if not os.path.exists(cache_info_path):
        return {
            "status": "no_cache",
            "video": video_filename,
            "message": "No cache found. Use /cache to create one."
        }
    
    try:
        with open(cache_info_path, 'r') as f:
            cache_info = json.load(f)
        
        import time
        created_at = cache_info.get("created_at", 0)
        ttl = cache_info.get("ttl_seconds", 3600)
        expires_at = created_at + ttl
        remaining = expires_at - time.time()
        
        return {
            "status": "cached",
            "video": video_filename,
            "cache_name": cache_info.get("cache_name"),
            "model": cache_info.get("model"),
            "ttl": f"{ttl} seconds",
            "remaining": f"{max(0, int(remaining))} seconds" if remaining > 0 else "expired",
            "message": "Cache is active! Queries will be faster and cheaper."
        }
    except Exception as e:
        return {"error": str(e)}


# ==========================================
# Delete Cache
# ==========================================
@app.function(
    image=image,
    volumes={"/data": vol},
    secrets=[Secret.from_name("my-google-secret")],
    timeout=60
)
def _internal_delete_cache(video_filename: str = "demo_video.mp4"):
    """Delete the cache for a video."""
    from google import genai
    import json
    
    cache_info_path = f"/data/cache_info/{video_filename.replace('.mp4', '')}.json"
    
    if not os.path.exists(cache_info_path):
        return {"status": "no_cache", "message": "No cache to delete"}
    
    try:
        with open(cache_info_path, 'r') as f:
            cache_info = json.load(f)
        
        api_key = get_api_key("GOOGLE_API_KEY")
        if api_key:
            client = genai.Client(api_key=api_key)
            cache_name = cache_info.get("cache_name")
            if cache_name:
                try:
                    client.caches.delete(name=cache_name)
                    print(f"✅ Deleted cache: {cache_name}")
                except Exception as e:
                    print(f"⚠️ Could not delete remote cache: {e}")
        
        # Remove local cache info
        os.remove(cache_info_path)
        vol.commit()
        
        return {"status": "deleted", "message": "Cache deleted successfully"}
    except Exception as e:
        return {"error": str(e)}


# ==========================================
# TTS Function
# ==========================================
@app.function(
    image=image,
    volumes={"/data": vol},
    secrets=[Secret.from_name("my-elevenlabs-secret")],
    timeout=600,
    max_containers=5  # Limit concurrent TTS containers
)
def _internal_speak_text(text: str, audio_filename: str = "response.mp3"):
    from elevenlabs.client import ElevenLabs
    import time
    
    max_chars = 2500
    
    # Remove mode prefix from TTS
    if text.startswith("[Cached Mode") or text.startswith("[Direct Mode"):
        text = text.split("]\n\n", 1)[-1] if "]\n\n" in text else text
    
    if len(text) > max_chars:
        safe_text = text[:max_chars].rstrip() + "..."
        print(f"⚠️ Text truncated from {len(text)} to {max_chars} chars")
    else:
        safe_text = text
    
    print(f"🗣️ Generating speech ({len(safe_text)} chars)...")
    print(f"📁 Output file: {audio_filename}")
    start_time = time.time()
    
    try:
        api_key = get_api_key("ELEVENLABS_API_KEY")
        if not api_key:
            return "❌ Error: ELEVENLABS_API_KEY not set"
        
        client = ElevenLabs(api_key=api_key)
        
        audio_generator = client.text_to_speech.convert(
            voice_id="21m00Tcm4TlvDq8ikWAM",
            output_format="mp3_44100_128",
            text=safe_text,
            model_id="eleven_multilingual_v2"
        )
        
        # Use dynamic filename
        output_path = f"/data/{audio_filename}"
        with open(output_path, "wb") as f:
            for chunk in audio_generator:
                f.write(chunk)
        
        vol.commit()
        
        elapsed = time.time() - start_time
        print(f"✅ Speech generated in {elapsed:.2f}s: {output_path}")
        return output_path
    
    except Exception as e:
        print(f"❌ TTS failed: {e}")
        return str(e)


# ==========================================
# MCP Server Interface (TEMPORARILY DISABLED FOR COST CONTROL)
# ==========================================
# To enable: uncomment the code below and redeploy with `modal deploy backend/modal_app.py`
# 
# @app.function(image=image)
# @asgi_app()
# def mcp_server():
#     from mcp.server.fastapi import FastMCP
#     
#     mcp = FastMCP("VideoAgent")
# 
#     @mcp.tool()
#     async def analyze_video_tool(question: str) -> str:
#         """Analyze the video using cached context or direct upload."""
#         print(f"📡 MCP Request: Analyze Video - {question}")
#         return _internal_analyze_video.remote(question)
# 
#     @mcp.tool()
#     async def create_cache_tool(video_filename: str = "demo_video.mp4") -> str:
#         """Create a context cache for faster video queries."""
#         print(f"📡 MCP Request: Create Cache - {video_filename}")
#         result = _internal_create_cache.remote(video_filename)
#         return f"Cache status: {result.get('status', 'unknown')} - {result.get('message', '')}"
# 
#     @mcp.tool()
#     async def speak_text_tool(text_to_speak: str) -> str:
#         """Convert text to speech using ElevenLabs."""
#         print(f"📡 MCP Request: Speak Text")
#         return _internal_speak_text.remote(text_to_speak)
# 
#     return mcp.app

# Note: MCP Server is temporarily disabled to prevent unauthorized API usage.
# The HF Space Gradio interface is the primary way to use this application.
# Contact the developer if you need MCP access for evaluation.


# ==========================================
# Local Test Entry Point
# ==========================================
@app.local_entrypoint()
def main():
    print("🚀 Testing Gemini Context Caching System...")
    
    # Test cache creation
    print("\n--- Creating Cache ---")
    cache_result = _internal_create_cache.remote("demo_video.mp4")
    print(f"Cache result: {cache_result}")
    
    # Test query
    print("\n--- Query with Cache ---")
    text_result = _internal_analyze_video.remote("What is happening in this video?")
    print(f"📝 Result: {text_result}")
    
    # Test TTS
    if "❌" not in text_result:
        print("\n--- TTS ---")
        audio_path = _internal_speak_text.remote(text_result)
        os.system("modal volume get video-storage response.mp3 .")
        print("✨ response.mp3 downloaded!")
