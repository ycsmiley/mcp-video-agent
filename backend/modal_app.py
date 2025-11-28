import modal
import os
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, StorageContext
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.embeddings.openai import OpenAIEmbedding
import chromadb
from typing import List, Dict, Any
import tempfile
import shutil

# Modal app setup
app = modal.App("mcp-video-agent-backend")
image = modal.Image.debian_slim().pip_install_from_requirements("requirements.txt")

@app.function(image=image, secrets=[modal.Secret.from_name("openai-secret")])
@modal.web_endpoint(method="POST")
def process_video(video_file: bytes, query: str = None) -> Dict[str, Any]:
    """
    Process uploaded video file and optionally answer questions about it.

    Args:
        video_file: The uploaded video file as bytes
        query: Optional question to ask about the video content

    Returns:
        Dict containing processing results and optional answer
    """
    try:
        # Create temporary directory for processing
        with tempfile.TemporaryDirectory() as temp_dir:
            video_path = os.path.join(temp_dir, "video.mp4")

            # Save uploaded video
            with open(video_path, "wb") as f:
                f.write(video_file)

            # Here you would add video processing logic
            # For now, we'll create a simple text representation
            video_description = f"Video file processed: {len(video_file)} bytes"

            # If query provided, use LlamaIndex to answer
            if query:
                # Initialize ChromaDB client
                chroma_client = chromadb.PersistentClient(path=os.path.join(temp_dir, "chroma_db"))

                # Create collection
                chroma_collection = chroma_client.get_or_create_collection("video_content")

                # Initialize vector store
                vector_store = ChromaVectorStore(chroma_collection=chroma_collection)

                # Initialize embedding model
                embed_model = OpenAIEmbedding(model="text-embedding-3-small")

                # Create storage context
                storage_context = StorageContext.from_defaults(vector_store=vector_store)

                # Create documents (in real implementation, extract text/transcript from video)
                documents = [
                    {"text": video_description, "metadata": {"type": "video_description"}}
                ]

                # Create index
                index = VectorStoreIndex.from_documents(
                    documents,
                    storage_context=storage_context,
                    embed_model=embed_model
                )

                # Query the index
                query_engine = index.as_query_engine()
                response = query_engine.query(query)

                return {
                    "status": "success",
                    "video_size": len(video_file),
                    "description": video_description,
                    "query": query,
                    "answer": str(response)
                }
            else:
                return {
                    "status": "success",
                    "video_size": len(video_file),
                    "description": video_description
                }

    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

@app.function(image=image)
@modal.web_endpoint(method="GET")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "mcp-video-agent-backend"}
