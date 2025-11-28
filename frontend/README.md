# MCP Video Agent

A video processing and question-answering agent powered by AI, built with Modal backend and Gradio frontend.

## 🌟 Features

- 🎥 **Video Upload**: Support for various video formats (MP4, AVI, MOV, etc.)
- 🤖 **AI-Powered Q&A**: Ask questions about video content using LlamaIndex
- 🚀 **Modal Backend**: Scalable serverless processing
- 🎨 **Gradio Interface**: Beautiful and intuitive web interface

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Modal account (for backend deployment)
- OpenAI API key (for embeddings and LLM)

### Backend Deployment (Modal)

1. **Set up Modal:**
   ```bash
   pip install modal
   modal setup
   ```

2. **Deploy backend:**
   ```bash
   cd backend
   modal deploy modal_app.py
   ```

3. **Set OpenAI secret in Modal:**
   ```bash
   modal secret create openai-secret OPENAI_API_KEY=your_openai_key_here
   ```

4. **Get your Modal endpoint URL** after deployment

### Frontend Deployment (Hugging Face Spaces)

1. **Create a new Hugging Face Space** with Gradio

2. **Upload the `frontend/` directory contents** to your Space

3. **Set environment variables:**
   - `MODAL_BACKEND_URL`: Your Modal endpoint URL
   - `PORT`: 7860 (default)

4. **Deploy!** Your Space will automatically install dependencies and run the app

## 📁 Project Structure

```
mcp-video-agent/
├── backend/                # Modal backend service
│   ├── modal_app.py        # Video processing & LlamaIndex logic
│   └── requirements.txt    # Backend dependencies
├── frontend/               # Gradio web interface
│   ├── app.py              # Main Gradio application
│   ├── requirements.txt    # Frontend dependencies
│   └── README.md           # This file
└── .gitignore              # Git ignore rules
```

## 🛠️ Local Development

### Backend
```bash
cd backend
pip install -r requirements.txt
modal serve modal_app.py
```

### Frontend
```bash
cd frontend
pip install -r requirements.txt
python app.py
```

## 🔧 Configuration

### Environment Variables

**Frontend:**
- `MODAL_BACKEND_URL`: URL of your deployed Modal backend
- `PORT`: Port to run the Gradio server (default: 7860)

**Backend:**
- OpenAI API key (set via Modal secrets)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test locally
5. Submit a pull request

## 📄 License

This project is open source and available under the [MIT License](LICENSE).

## 🙏 Acknowledgments

- [Modal](https://modal.com/) for serverless computing
- [LlamaIndex](https://www.llamaindex.ai/) for RAG framework
- [Gradio](https://gradio.app/) for the web interface
- [Hugging Face](https://huggingface.co/) for hosting
