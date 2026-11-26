"""Render demo launcher; the upstream image serves the UI and API together."""
import os
from pathlib import Path
origin = os.environ.get("RENDER_EXTERNAL_URL")
if not origin or not origin.startswith("https://"):
    raise RuntimeError("Expected Render's HTTPS service URL")
os.environ["ALLOWED_ORIGINS"] = origin
os.environ["OE_DATA_DIR"] = "/tmp/openconstructionerp-demo"
os.environ["HOME"] = "/tmp/openconstructionerp-home"
Path(os.environ["OE_DATA_DIR"]).mkdir(parents=True, exist_ok=True)
Path(os.environ["HOME"]).mkdir(parents=True, exist_ok=True)
os.execv("/app/entrypoint.sh", ["/app/entrypoint.sh"])
