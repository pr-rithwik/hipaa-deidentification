from app.ui import build_ui


if __name__ == "__main__":
    demo = build_ui()
    demo.launch(
        server_name="0.0.0.0",  # needed for docker
        server_port=7860
    )
