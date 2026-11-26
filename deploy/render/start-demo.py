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
# asyncpg accepts ssl, while libpq/psycopg uses sslmode.
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
raw = urlsplit(os.environ["DATABASE_URL"])
query = dict(parse_qsl(raw.query))
query.pop("channel_binding", None)
query.pop("sslmode", None)
query.pop("ssl", None)
os.environ["PGSSLROOTCERT"] = "/etc/ssl/certs/ca-certificates.crt"
async_query = {**query, "ssl": "verify-full"}
sync_query = {**query, "sslmode": "verify-full"}
os.environ["DATABASE_URL"] = urlunsplit(("postgresql+asyncpg", raw.netloc, raw.path, urlencode(async_query), ""))
os.environ["DATABASE_SYNC_URL"] = urlunsplit(("postgresql", raw.netloc, raw.path, urlencode(sync_query), ""))
os.execv("/app/entrypoint.sh", ["/app/entrypoint.sh"])
