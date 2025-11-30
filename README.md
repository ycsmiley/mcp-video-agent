# 🎥 MCP Video Agent

A powerful AI-powered video analysis system built with **Gemini 2.5 Flash**, **ElevenLabs TTS**, and **Gemini Context Caching** for intelligent video Q&A.

## 🎯 Overview

This project implements an MCP (Model Context Protocol) compatible video agent that can:

- 🎬 Analyze video content using Google's Gemini 2.5 Flash (multimodal AI)
- 🗣️ Generate voice responses using ElevenLabs Text-to-Speech
- ⚡ Leverage Gemini's Context Caching for 2-3x faster repeated queries
- 🔌 Function as an MCP Server for Claude Desktop integration
- 🌐 Provide two deployment options: Modal (backend) + Gradio (frontend), or standalone HF Space

## 🏗️ Architecture

### Option 1: Distributed (Modal + HF Space Frontend)
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Gradio UI     │    │    Modal        │    │   Gemini 2.5    │
│ (HF Space)      │◄──►│   Backend       │◄──►│  Flash + Cache  │
│                 │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Option 2: Standalone (HF Space Only)
```
┌─────────────────────────────────┐    ┌─────────────────┐
│   Gradio UI + Backend Logic     │    │   Gemini 2.5    │
│        (HF Space)                │◄──►│  Flash + Cache  │
│                                  │    │                 │
└─────────────────────────────────┘    └─────────────────┘
```

### Components

- **Frontend**: Gradio web interface for video upload and conversational Q&A
- **Backend (Optional Modal)**: Serverless video processing with persistent storage
- **AI Stack**: 
  - Google Gemini 2.5 Flash for video analysis
  - Gemini Context Caching for efficient repeated queries
  - ElevenLabs for natural voice responses

## 🚀 Quick Deployment

### Option 1: Deploy to Hugging Face Space (Recommended for Quick Start)

```bash
cd hf_space
chmod +x deploy.sh
./deploy.sh YOUR_HF_USERNAME
```

Then configure secrets in your Space Settings:
- `GOOGLE_API_KEY` (required) - Get from [Google AI Studio](https://aistudio.google.com/apikey)
- `ELEVENLABS_API_KEY` (optional) - Get from [ElevenLabs](https://elevenlabs.io)

### Option 2: Deploy Backend to Modal + Frontend to HF Space

**Backend:**
```bash
cd backend
modal deploy modal_app.py
```

**Frontend:**
```bash
cd frontend
# Set MODAL_BACKEND_URL in your HF Space settings
# Then upload frontend/ directory to your Space
```

### Configuration
- **Gemini API**: Get your API key from [Google AI Studio](https://aistudio.google.com/apikey)
- **ElevenLabs API**: Get your API key from [ElevenLabs](https://elevenlabs.io) (optional)
- **Modal Secrets**: Configure API keys using `modal secret create`

## 📁 Project Structure

```
mcp-video-agent/
├── backend/                # Modal backend (optional distributed deployment)
│   ├── modal_app.py        # Video processing + Gemini Context Caching
│   ├── requirements.txt    # Backend dependencies
│   └── cookies.txt         # (Optional) YouTube cookies for yt-dlp
├── frontend/               # Gradio interface (connects to Modal backend)
│   ├── app.py              # Main Gradio application
│   └── requirements.txt    # Frontend dependencies
├── hf_space/               # 🌟 Standalone HF Space deployment (recommended)
│   ├── app.py              # All-in-one Gradio + Backend
│   ├── requirements.txt    # Python dependencies
│   ├── README.md           # Space description
│   ├── DEPLOYMENT.md       # Deployment guide
│   ├── deploy.sh           # Automated deployment script
│   └── .gitignore          # HF Space specific ignores
├── .gitignore              # Git ignore rules
└── README.md               # This file
```

## 🔌 Use as MCP Server in Claude Desktop

After deploying to HF Space, add this to your Claude Desktop config:

**macOS/Linux:** `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "video-agent": {
      "url": "https://YOUR_USERNAME-mcp-video-agent.hf.space/sse"
    }
  }
}
```

**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

## ⚡ Performance & Costs

### Gemini 2.5 Flash with Context Caching

- **First query**: ~$0.05-0.15 per video (full processing)
- **Subsequent queries** (within 1 hour): ~$0.005-0.015 per query (90% cost reduction!)
- **Speed improvement**: 2-3x faster for cached queries

### ElevenLabs TTS

- **Cost**: ~$0.18 per 1000 characters
- **Optional**: Works fine without TTS (text-only responses)

## 🛠️ Development

### Local Testing (Frontend Only)

```bash
cd frontend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

### Local Testing (HF Space Version)

```bash
cd hf_space
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
export GOOGLE_API_KEY=your_key_here
export ELEVENLABS_API_KEY=your_key_here
python app.py
```

## 📊 Features Comparison

| Feature | Modal + Frontend | HF Space Only |
|---------|-----------------|---------------|
| Deployment Complexity | Medium | Easy |
| Video Storage | Persistent (Modal Volume) | Temporary |
| Scalability | High | Medium |
| Cost | Pay-per-use | Free tier available |
| Setup Time | ~10 min | ~5 min |
| **Recommended For** | Production | Quick demos |

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details.

## 🙏 Acknowledgments

Built with:
- [Google Gemini 2.5 Flash](https://ai.google.dev/) - Multimodal AI with Context Caching
- [ElevenLabs](https://elevenlabs.io) - Natural voice synthesis
- [Gradio](https://gradio.app/) - Beautiful web UI framework
- [Modal](https://modal.com/) - Serverless computing (optional backend)
- [Hugging Face](https://huggingface.co/) - AI community and hosting

## 📚 Documentation

- **HF Space Deployment**: See `hf_space/DEPLOYMENT.md`
- **Modal Backend**: See `backend/modal_app.py` comments
- **Frontend Integration**: See `frontend/app.py` comments

## 🆘 Support

If you encounter issues:

1. Check the logs in your HF Space dashboard
2. Verify API keys are correctly set in Secrets
3. Review `hf_space/DEPLOYMENT.md` for troubleshooting tips
4. Open an issue on GitHub with detailed error messages

---

**⭐ If you find this project helpful, please star it on GitHub!**
