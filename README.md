# MCP Video Agent

A comprehensive video processing and question-answering system built with AI, featuring a scalable Modal backend and an intuitive Gradio frontend hosted on Hugging Face Spaces.

## 🎯 Overview

This project implements an MCP (Model Context Protocol) compatible video agent that can:

- Process uploaded video files
- Extract and index video content using LlamaIndex
- Answer questions about video content using advanced RAG (Retrieval-Augmented Generation)
- Provide a beautiful web interface for easy interaction

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Gradio UI     │    │    Modal        │    │   LlamaIndex    │
│ (Hugging Face)  │◄──►│   Backend       │◄──►│   RAG System    │
│                 │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Components

- **Frontend (Hugging Face Spaces)**: Gradio web interface for video upload and Q&A
- **Backend (Modal)**: Serverless video processing and AI inference
- **AI Stack**: LlamaIndex for RAG, OpenAI for embeddings and LLM, ChromaDB for vector storage

## 🚀 Quick Deployment

### 1. Backend (Modal)
```bash
cd backend
modal deploy modal_app.py
```

### 2. Frontend (Hugging Face Spaces)
Create a new Space and upload the `frontend/` directory.

### 3. Configuration
- Set `MODAL_BACKEND_URL` environment variable in your Hugging Face Space
- Configure OpenAI API key in Modal secrets

## 📁 Project Structure

```
mcp-video-agent/
├── backend/                # Modal backend service
│   ├── modal_app.py        # Video processing & LlamaIndex logic
│   └── requirements.txt    # Backend dependencies
├── frontend/               # Gradio web interface
│   ├── app.py              # Main Gradio application
│   ├── requirements.txt    # Frontend dependencies
│   └── README.md           # Hugging Face Space documentation
├── .gitignore              # Git ignore rules
└── README.md               # This file
```

## 🛠️ Development

See individual README files in `backend/` and `frontend/` directories for detailed setup instructions.

## 🤝 Contributing

We welcome contributions! Please see the contributing guidelines in the frontend README.

## 📄 License

MIT License - see LICENSE file for details.

## 🙏 Acknowledgments

Built with ❤️ using:
- [Modal](https://modal.com/) - Serverless computing
- [LlamaIndex](https://www.llamaindex.ai/) - RAG framework
- [Gradio](https://gradio.app/) - Web UI framework
- [Hugging Face](https://huggingface.co/) - Hosting platform
