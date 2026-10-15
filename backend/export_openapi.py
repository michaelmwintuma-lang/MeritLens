"""
Write the API's contract (OpenAPI) to frontend/openapi.json:   python export_openapi.py   (from the backend folder)

The frontend generates its TypeScript types from that file (npm run gen:api), so when an endpoint changes, a page
that uses it the old way fails `npm run typecheck` instead of failing in front of a user.
"""
import json
import os
from pathlib import Path

os.environ.setdefault("SKIP_ENV_FILE", "1")  # the contract doesn't depend on private settings

from app.main import app  # noqa: E402

target = Path(__file__).resolve().parents[1] / "frontend" / "openapi.json"
target.write_text(json.dumps(app.openapi(), indent=2) + "\n")
print(f"wrote {target}")
