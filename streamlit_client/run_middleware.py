"""Launch the privacy middleware using this directory's .env settings."""

import os
import sys
from pathlib import Path

import uvicorn

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parent

os.chdir(HERE)
sys.path.insert(0, str(PROJECT_ROOT))

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=False)
