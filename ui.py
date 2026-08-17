import gradio as gr
import requests
from typing import List, Dict

API_URL = "http://localhost:8080/api/query"


def query_rag(
        message: str,
        limit: int,
        temperature: float,
        use_hybrid: bool,
) -> tuple[str, str]:
    """
    Send request to API and get response
    """
    try:
        payload = {
            "query": message,
            "limit": limit,
            "temperature": temperature,
            "use_hybrid": use_hybrid,
        }

        response = requests.post(API_URL, json=payload, timeout=60)
        response.raise_for_status()

        data = response.json()

        answer = data.get("answer", "No response received")
        sources_html = build_sources_html(data.get("sources", []), data.get("search_mode", "dense"))

        return answer, sources_html

    except requests.exceptions.RequestException as e:
        error_msg = f"API Connection Error: {str(e)}"
        return error_msg, f"<div style='color: #ff6b6b; padding: 20px; background: #2d2d2d; border-radius: 8px;'>{error_msg}</div>"
    except Exception as e:
        error_msg = f"Unexpected Error: {str(e)}"
        return error_msg, f"<div style='color: #ff6b6b; padding: 20px; background: #2d2d2d; border-radius: 8px;'>{error_msg}</div>"


def build_sources_html(sources: List[dict], search_mode: str) -> str:
    """
    Build HTML for displaying sources with dark theme
    """
    if not sources:
        return "<div style='padding: 30px; text-align: center; color: #888; background: #1a1a1a; border-radius: 8px; font-family: Tahoma, Arial;'>📭 No sources found</div>"

    html = f"""
    <div style='font-family: Tahoma, Arial; direction: rtl; background: #1a1a1a; padding: 15px; border-radius: 8px;'>
        <div style='background: #2d2d2d; padding: 12px; border-radius: 6px; margin-bottom: 15px; color: #e0e0e0; border-left: 4px solid #4a9eff;'>
            <strong>🔍 Search Mode:</strong> <span style='color: #4a9eff;'>{search_mode}</span> | 
            <strong>📚 Sources Count:</strong> <span style='color: #4a9eff;'>{len(sources)}</span>
        </div>
    """

    for idx, source in enumerate(sources, 1):
        score = source.get('score', 0)
        text = source.get('text', 'No text available')

        doc_id = source.get('doc_id', 'Unknown')
        chunk_id = source.get('id', 'Unknown')
        tags = source.get('tags', [])[:3]
        keywords = source.get('keywords', [])[:5]

        html += f"""
        <div style='border: 1px solid #3d3d3d; border-radius: 8px; padding: 15px; margin-bottom: 15px; background: #252525;'>
            <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;'>
                <span style='font-weight: bold; color: #e0e0e0; font-size: 1.05em;'>📄 Source {idx}</span>
                <span style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 4px 12px; border-radius: 15px; font-size: 0.85em; font-weight: 600;'>
                    ⭐ Score: {score:.3f}
                </span>
            </div>

            <div style='background: #2d2d2d; padding: 14px; border-radius: 6px; margin-bottom: 12px; line-height: 1.9; color: #d0d0d0; border-right: 3px solid #667eea;'>
                {text[:500]}{'...' if len(text) > 500 else ''}
            </div>

            <div style='font-size: 0.9em; color: #a0a0a0;'>
                <div style='margin-bottom: 5px;'><strong style='color: #b0b0b0;'>📋 Document:</strong> <span style='color: #4a9eff;'>{doc_id}</span></div>
                <div style='margin-bottom: 5px;'><strong style='color: #b0b0b0;'>🔖 Chunk:</strong> <span style='color: #4a9eff;'>{chunk_id}</span></div>
        """

        if tags:
            tags_html = ' '.join([
                                     f"<span style='background: #1e4620; color: #66ff66; padding: 3px 10px; border-radius: 4px; margin-left: 5px; font-size: 0.85em;'>🏷️ {tag}</span>"
                                     for tag in tags])
            html += f"<div style='margin-top: 8px;'><strong style='color: #b0b0b0;'>Tags:</strong> {tags_html}</div>"

        if keywords:
            keywords_html = ' '.join([
                                         f"<span style='background: #4a3000; color: #ffcc66; padding: 3px 10px; border-radius: 4px; margin-left: 5px; font-size: 0.85em;'>🔑 {kw}</span>"
                                         for kw in keywords])
            html += f"<div style='margin-top: 8px;'><strong style='color: #b0b0b0;'>Keywords:</strong> {keywords_html}</div>"

        html += """
            </div>
        </div>
        """

    html += "</div>"
    return html


# Build UI with dark theme
with gr.Blocks(
        title="🤖 RAG Query System",
        theme=gr.themes.Base(
            primary_hue="blue",
            secondary_hue="purple",
            neutral_hue="slate"
        ).set(
            body_background_fill="#0f0f0f",
            body_background_fill_dark="#0f0f0f",
            block_background_fill="#1a1a1a",
            block_label_background_fill="#2d2d2d",
            input_background_fill="#252525",
            button_primary_background_fill="linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
            button_primary_background_fill_hover="linear-gradient(135deg, #764ba2 0%, #667eea 100%)"
        )
) as demo:
    gr.Markdown(
        """
        # 🤖 Adonis Intelligent Q&A 
        ### 🔍 RAG System with Hybrid Search Capability for Adonis Documents
        """,
        elem_classes="header-text"
    )

    # Advanced Settings at the top
    with gr.Accordion("⚙️ Advanced Settings", open=False):
        with gr.Row():
            limit = gr.Slider(
                minimum=1,
                maximum=20,
                value=5,
                step=1,
                label="📊 Number of Sources",
                info="Number of retrieved documents"
            )
            temperature = gr.Slider(
                minimum=0.0,
                maximum=1.0,
                value=0.1,
                step=0.1,
                label="🌡️ Temperature",
                info="Model creativity (lower = more precise)"
            )

        with gr.Row():
            use_hybrid = gr.Checkbox(
                label="🔀 Use Hybrid Search",
                value=True,
                info="Combine semantic and keyword search"
            )




    with gr.Row():
        # RIGHT COLUMN → Chat (now first)
        with gr.Column(scale=3, elem_classes="chat-wrapper"):
            chatbot = gr.Chatbot(
                label="💬 Conversation",
                height=270,
                rtl=True,
                elem_classes="rtl-chat"
            )

            with gr.Row(elem_classes="input-row"):
                msg = gr.Textbox(
                    label="",
                    placeholder="ask your question...",
                    lines=2,
                    scale=4,
                    rtl=True
                )
                submit_btn = gr.Button("🚀 Send", variant="primary", scale=1)

            clear_btn = gr.Button("🗑️ Clear Chat", variant="secondary")

    # LEFT COLUMN → Sources (now below chat if column layout is vertical)
    with gr.Column(scale=1):
        sources_display = gr.HTML(
            label="📚 Sources",
            value="<div style='padding: 30px; text-align: center; color: #888; background: #1a1a1a; border-radius: 8px;'>📚 Sources will be displayed here</div>"
        )


    def respond(message: str, chat_history: List[Dict], limit: int, temperature: float,
                use_hybrid: bool):

        if not message.strip():
            yield chat_history, "<div style='color: #ff6b6b; padding: 20px; background: #2d2d2d; border-radius: 8px;'>⚠️ Please enter a question</div>"
            return

        # اضافه کردن پیام کاربر
        chat_history.append({"role": "user", "content": message})
        chat_history.append({"role": "assistant", "content": ""})

        yield chat_history, "<div style='padding: 20px;'>⏳ Generating...</div>"

        answer, sources_html = query_rag(
            message,
            limit,
            temperature,
            use_hybrid
        )

        # استریم کلمه به کلمه
        words = answer.split(" ")
        partial = ""

        for word in words:
            partial += word + " "
            chat_history[-1]["content"] = partial
            yield chat_history, "<div style='padding: 20px;'>⏳ Generating...</div>"

        yield chat_history, sources_html


    # Connect events
    submit_btn.click(
        respond,
        inputs=[msg, chatbot, limit, temperature, use_hybrid],
        outputs=[chatbot, sources_display]
    ).then(
        lambda: "",
        outputs=[msg]
    )

    msg.submit(
        respond,
        inputs=[msg, chatbot, limit, temperature, use_hybrid],
        outputs=[chatbot, sources_display]
    ).then(
        lambda: "",
        outputs=[msg]
    )

    clear_btn.click(
        lambda: ([],
                 "<div style='padding: 30px; text-align: center; color: #888; background: #1a1a1a; border-radius: 8px; font-family: Tahoma, Arial;'>📚 Sources will be displayed here</div>"),
        outputs=[chatbot, sources_display]
    )



if __name__ == "__main__":
    demo.queue()
    demo.launch(
        server_name="0.0.0.0",
        server_port=8081,
        share=False,
        css="""
            @import url('https://fonts.googleapis.com/css2?family=Vazirmatn:wght@400;600;700&display=swap');

            .gradio-container {
                font-family: 'Vazirmatn', Tahoma, Arial, sans-serif !important;
                background: #0f0f0f !important;
            }

            .header-text h1 {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
                text-align: center;
            }

            .header-text h3 {
                color: #a0a0a0;
                text-align: center;
            }

            .rtl-chat {
                direction: rtl !important;
                text-align: right !important;
            }

            .rtl-chat .message {
                direction: rtl !important;
                text-align: right !important;
            }

            .rtl-chat .message.user {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
                color: white !important;
                direction: rtl !important;
                text-align: right !important;
            }

            .rtl-chat .message.bot {
                background: #2d2d2d !important;
                color: #e0e0e0 !important;
                direction: rtl !important;
                text-align: right !important;
            }

            input, textarea {
                direction: rtl !important;
                text-align: right !important;
            }

            label {
                color: #d0d0d0 !important;
            }

            .gr-button {
                font-weight: 600 !important;
            }
        """
    )
