import gradio as gr
from app.handlers import process_document


def build_ui() -> gr.Blocks:
    """
    Gradio UI layout.
    Keeping it simple - upload on left, results on right.
    Report table below.
    """
    with gr.Blocks(title="HIPAA De-identification System") as demo:

        gr.Markdown("""
        # HIPAA De-identification System
        Upload a medical document (PDF) to detect and redact Protected Health Information (PHI).
        Synthetic values replace the original PHI to preserve document structure.
        """)

        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("### Original Document")
                input_file = gr.File(
                    label="Upload PDF",
                    file_types=[".pdf"],
                    type="binary"
                )
                submit_btn = gr.Button("De-identify", variant="primary")

            with gr.Column(scale=1):
                gr.Markdown("### Redacted Document")
                output_file = gr.File(
                    label="Download redacted PDF",
                    type="binary"
                )

        with gr.Row():
            with gr.Column():
                gr.Markdown("### Redaction Report")
                gr.Markdown(
                    "_Shows what was detected, what it was replaced with, "
                    "and which detector caught it._"
                )
                report_table = gr.Dataframe(
                    headers=["Entity Type", "Original", "Replacement", "Detector", "Confidence"],
                    interactive=False,
                    wrap=True
                )

        with gr.Row():
            with gr.Column():
                gr.Markdown("### Redaction Report")
                report_table = gr.Dataframe(
                    headers=["Entity Type", "Original", "Replacement", "Detector", "Confidence"],
                    interactive=False,
                    wrap=True
                )
                report_csv = gr.File(label="Download report as CSV")
        # summary line - total PHI count
        summary_text = gr.Markdown("")

        submit_btn.click(
            fn=process_document,
            inputs=[input_file],
            outputs=[output_file, report_table, report_csv, summary_text]
        )

    return demo