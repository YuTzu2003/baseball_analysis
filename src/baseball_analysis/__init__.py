from .app import app


def main() -> None:
    """Start with: uv run uvicorn baseball_analysis.app:app --reload."""
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
