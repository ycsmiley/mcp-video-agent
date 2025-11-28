import gradio as gr
import requests
import os
from typing import Tuple, Optional

# Backend Modal URL (you'll need to set this after deploying)
MODAL_BACKEND_URL = os.getenv("MODAL_BACKEND_URL", "https://your-modal-app.modal.run")

def process_video_with_query(video_file: str, query: str = None) -> Tuple[str, str]:
    """
    Process video file and optionally ask questions about it.

    Args:
        video_file: Path to uploaded video file
        query: Optional question about the video

    Returns:
        Tuple of (status_message, answer)
    """
    try:
        # Read video file
        with open(video_file, "rb") as f:
            video_bytes = f.read()

        # Prepare request data
        data = {"video_file": video_bytes}
        if query and query.strip():
            data["query"] = query.strip()

        # Send to backend
        response = requests.post(f"{MODAL_BACKEND_URL}/process_video", data=data)

        if response.status_code == 200:
            result = response.json()
            if result["status"] == "success":
                status_msg = f"✅ Video processed successfully!\n📊 Size: {result['video_size']} bytes\n📝 Description: {result['description']}"

                if "answer" in result:
                    return status_msg, result["answer"]
                else:
                    return status_msg, "No question asked."
            else:
                return f"❌ Error: {result.get('error', 'Unknown error')}", ""
        else:
            return f"❌ HTTP Error {response.status_code}: {response.text}", ""

    except Exception as e:
        return f"❌ Error processing video: {str(e)}", ""

def create_interface() -> gr.Blocks:
    """Create the Gradio interface"""

    with gr.Blocks(title="MCP Video Agent", theme=gr.themes.Soft()) as interface:
        gr.Markdown("""
        # 🎥 MCP Video Agent

        Upload a video file and ask questions about its content using AI!

        This agent uses LlamaIndex and Modal for video processing and question answering.
        """)

        with gr.Row():
            with gr.Column(scale=1):
                video_input = gr.Video(label="Upload Video", height=300)
                query_input = gr.Textbox(
                    label="Ask a question about the video (optional)",
                    placeholder="e.g., What is happening in this video?",
                    lines=2
                )
                process_btn = gr.Button("🔍 Process Video", variant="primary", size="lg")

            with gr.Column(scale=1):
                status_output = gr.Textbox(
                    label="Processing Status",
                    interactive=False,
                    lines=5
                )
                answer_output = gr.Textbox(
                    label="AI Answer",
                    interactive=False,
                    lines=10
                )

        # Event handling
        process_btn.click(
            fn=process_video_with_query,
            inputs=[video_input, query_input],
            outputs=[status_output, answer_output]
        )

        # Examples
        gr.Examples(
            examples=[
                ["sample_video.mp4", "What objects can you see in this video?"],
                ["sample_video.mp4", "Describe the main activity happening."],
                ["sample_video.mp4", "How long is this video approximately?"],
            ],
            inputs=[video_input, query_input],
        )

        gr.Markdown("""
        ---

        **Note:** Make sure your video file is in a supported format (MP4, AVI, MOV, etc.) and under reasonable size limits.
        """)

    return interface

if __name__ == "__main__":
    interface = create_interface()
    interface.launch(
        server_name="0.0.0.0",
        server_port=int(os.getenv("PORT", 7860)),
        share=False  # Set to True for public sharing on Hugging Face Spaces
    )
