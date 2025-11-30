# 🏗️ Technical Architecture

## Overview

MCP Video Agent is a distributed application with a **Gradio frontend** (HF Space) and a **Modal serverless backend**.

---

## System Components

### 1. Frontend (Gradio on HF Space)

**File**: `hf_space/app_with_modal.py`

**Responsibilities**:
- User interface for video upload and Q&A
- Rate limiting (10 requests/hour per user)
- Session management
- Communication with Modal backend
- Audio playback and text display

**Key Features**:
```python
# Rate Limiting
class RateLimiter:
    - Tracks requests per user ID
    - 1-hour sliding window
    - Automatic cleanup of old requests

# Modal Integration
def get_modal_function(function_name):
    - Connects to Modal functions via MCP
    - Uses MODAL_TOKEN_ID and MODAL_TOKEN_SECRET

# Video Upload
def process_interaction():
    - Uploads video to Modal Volume
    - Calls analyze function
    - Calls TTS function
    - Returns audio + text response
```

---

### 2. Backend (Modal Serverless)

**File**: `backend/modal_app.py`

**Deployment**:
```bash
modal deploy backend/modal_app.py
```

**Functions**:

#### `_internal_analyze_video(query, video_filename)`
```python
Purpose: Analyze video using Gemini with context caching

Flow:
1. Load video from Modal Volume
2. Upload to Gemini Files API
3. Create context cache (first query only)
4. Generate response using cached context
5. Return analysis text

Optimizations:
- Context caching reduces cost by 90%
- Cache TTL: 1 hour
- Minimum 1024 tokens for caching
```

#### `_internal_speak_text(text, audio_filename)`
```python
Purpose: Convert text to speech

Flow:
1. Truncate text to max length (2500 chars)
2. Call ElevenLabs API
3. Save audio to Modal Volume
4. Return success status

Parameters:
- Voice: "21m00Tcm4TlvDq8ikWAM" (Rachel)
- Model: "eleven_multilingual_v2"
- Format: MP3 44.1kHz 128kbps
```

---

## Data Flow

### First Query (Cold Start)

```
User → Gradio UI → Modal Volume (upload video)
                 ↓
        Modal: _internal_analyze_video
                 ↓
        Gemini Files API (upload video)
                 ↓
        Create Context Cache (store video context)
                 ↓
        Gemini Generate (with cache)
                 ↓
        Modal: _internal_speak_text
                 ↓
        ElevenLabs TTS → Modal Volume (save audio)
                 ↓
        Gradio UI ← Audio + Text
```

**Timing**: ~8-12 seconds
**Cost**: ~$0.10 (full video processing)

### Subsequent Queries (Cache Hit)

```
User → Gradio UI → Modal: _internal_analyze_video
                 ↓
        Gemini Generate (use existing cache)
                 ↓
        Modal: _internal_speak_text
                 ↓
        ElevenLabs TTS
                 ↓
        Gradio UI ← Audio + Text
```

**Timing**: ~2-3 seconds (75% faster!)
**Cost**: ~$0.01 (90% cheaper!)

---

## Context Caching Strategy

### Why Caching Matters

Without caching, every query processes the entire video:
- ❌ Slow (10-30 seconds)
- ❌ Expensive ($0.10-0.30 per query)
- ❌ Poor UX for exploratory queries

With caching:
- ✅ Fast (2-3 seconds after first query)
- ✅ Cheap ($0.01 per cached query)
- ✅ Great UX for conversations

### Implementation

```python
# Create cache (first query)
cache = client.caches.create(
    model="gemini-2.5-flash",
    config=types.CreateCachedContentConfig(
        display_name=f"video-cache-{video_filename}",
        system_instruction="Video analysis assistant...",
        contents=[video_file],
        ttl="3600s"  # 1 hour
    )
)

# Use cache (subsequent queries)
response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=[query],
    config=types.GenerateContentConfig(
        cached_content=cache.name  # Reuse cached video context
    )
)
```

### Cache Lifecycle

1. **Creation**: First query uploads video and creates cache
2. **Active**: Cache valid for 1 hour
3. **Reuse**: All queries within 1 hour use cache
4. **Expiration**: After 1 hour, new query creates fresh cache

---

## Storage Architecture

### Modal Volume: `video-storage`

```
/data/
├── video_1234567890_abc123.mp4    # Uploaded videos
├── video_1234567891_def456.mp4
├── audio_video_1234567890_abc123.mp3  # Generated audio
└── audio_video_1234567891_def456.mp3
```

**Characteristics**:
- Persistent across function invocations
- Shared between all functions
- Automatic synchronization

**Usage Pattern**:
```python
# Upload video
subprocess.run([
    "modal", "volume", "put", "video-storage",
    local_path, f"/{unique_filename}", "--force"
])

# Download audio
subprocess.run([
    "modal", "volume", "get", "video-storage",
    f"/{audio_filename}", local_audio
])
```

---

## Security & Rate Limiting

### Rate Limiter Design

```python
class RateLimiter:
    def __init__(self, max_requests_per_hour=10):
        self.requests = defaultdict(list)  # {user_id: [timestamp, ...]}
    
    def is_allowed(self, user_id):
        now = datetime.now()
        cutoff = now - timedelta(hours=1)
        
        # Remove old requests
        self.requests[user_id] = [
            t for t in self.requests[user_id] if t > cutoff
        ]
        
        # Check limit
        if len(self.requests[user_id]) >= self.max_requests:
            return False
        
        # Record request
        self.requests[user_id].append(now)
        return True
```

**Features**:
- Per-user tracking
- Sliding 1-hour window
- Automatic cleanup
- Configurable limit via `MAX_REQUESTS_PER_HOUR` env var

### Authentication (Optional)

For Hackathon: **Disabled** (evaluators need direct access)

For production:
```python
def authenticate(username, password):
    return username == GRADIO_USERNAME and password == GRADIO_PASSWORD

demo.launch(auth=authenticate)
```

---

## API Integration

### Google Gemini 2.5 Flash

**Configuration**:
```python
from google import genai

client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
model = "gemini-2.5-flash"
```

**Key Features Used**:
- Multimodal input (video files)
- Context caching (cost optimization)
- Safety settings (content filtering)
- Streaming responses (future enhancement)

**Costs** (per query):
- First query: ~$0.05-0.15 (full processing)
- Cached query: ~$0.005-0.015 (90% reduction)

### ElevenLabs TTS

**Configuration**:
```python
from elevenlabs.client import ElevenLabs

client = ElevenLabs(api_key=os.environ["ELEVENLABS_API_KEY"])
```

**Parameters**:
```python
audio = client.text_to_speech.convert(
    voice_id="21m00Tcm4TlvDq8ikWAM",  # Rachel voice
    model_id="eleven_multilingual_v2",
    text=text,
    output_format="mp3_44100_128"
)
```

**Costs**:
- ~$0.18 per 1000 characters
- Average response: 300-400 chars = ~$0.05-0.07

---

## Performance Optimization

### Caching Strategy

| Metric | Without Cache | With Cache | Improvement |
|--------|---------------|------------|-------------|
| Response Time | 10-12s | 2-3s | **75% faster** |
| API Cost | $0.10 | $0.01 | **90% cheaper** |
| Token Usage | ~10,000 | ~1,000 | **90% reduction** |
| User Experience | Slow | Fast | **Conversational** |

### Video Upload Optimization

- Unique filename generation (prevents overwrites)
- MD5 hash for deduplication
- File size limit (100MB)
- Cache key tracking (avoids re-upload)

### Audio Generation

- Text truncation (2500 char max)
- Retry logic (3 attempts)
- File size verification
- Base64 embedding (direct playback)

---

## Error Handling

### Frontend Errors

```python
try:
    analyze_fn = get_modal_function("_internal_analyze_video")
    if analyze_fn is None:
        return "❌ Failed to connect to Modal backend"
    
    text_response = analyze_fn.remote(query, video_filename)
except Exception as e:
    return f"❌ Analysis error: {str(e)}"
```

### Backend Errors

```python
try:
    video_file = client.files.upload(file=video_path)
    while video_file.state.name == 'PROCESSING':
        time.sleep(2)
        video_file = client.files.get(name=video_file.name)
    
    if video_file.state.name == 'FAILED':
        return "❌ Video processing failed"
except Exception as e:
    return f"❌ Upload error: {str(e)}"
```

---

## Deployment

### Prerequisites

1. **Modal Account**
   ```bash
   modal token new
   ```

2. **API Keys**
   - `GOOGLE_API_KEY` from Google AI Studio
   - `ELEVENLABS_API_KEY` from ElevenLabs

3. **Modal Secrets**
   ```bash
   modal secret create my-google-secret GOOGLE_API_KEY=xxx
   modal secret create my-elevenlabs-secret ELEVENLABS_API_KEY=xxx
   ```

### Deploy Backend

```bash
cd backend
modal deploy modal_app.py
```

### Deploy Frontend

```bash
cd hf_space
./switch_to_modal.sh
git add app.py requirements.txt README.md
git commit -m "Deploy to HF Space"
git push hf main --force
```

### Configure HF Space Secrets

In HF Space Settings → Secrets:
- `MODAL_TOKEN_ID`
- `MODAL_TOKEN_SECRET`
- `MAX_REQUESTS_PER_HOUR` (optional, default: 10)

---

## Monitoring & Debugging

### Modal Logs

```bash
# View live logs
modal app logs mcp-video-agent

# View function logs
modal function logs mcp-video-agent._internal_analyze_video
```

### HF Space Logs

Check the "Logs" tab in your HF Space dashboard

### Debugging Tips

1. **Modal connection issues**: Check token validity
2. **API errors**: Verify API keys in Modal Secrets
3. **Rate limiting**: Adjust `MAX_REQUESTS_PER_HOUR`
4. **Audio playback**: Check Base64 encoding
5. **Video upload**: Verify Modal Volume sync

---

## Future Enhancements

### Planned Features

1. **Multi-video comparison**: Analyze multiple videos simultaneously
2. **Timestamp search**: "Show me where X happens"
3. **Video summarization**: Auto-generate video summaries
4. **Custom voices**: User-selectable TTS voices
5. **Streaming responses**: Real-time text generation

### Scalability Improvements

1. **Redis cache**: Replace in-memory rate limiter
2. **Database**: Track user history and preferences
3. **CDN**: Serve audio files from CDN
4. **Load balancing**: Multiple Modal deployments

---

## Contributing

This is an open-source Hackathon project. Contributions welcome!

**GitHub**: [mcp-video-agent](https://github.com/YOUR_USERNAME/mcp-video-agent)

---

## License

MIT License - Free to use, modify, and distribute.

