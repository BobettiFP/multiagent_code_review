# scripts/config.py
from pathlib import Path
from dotenv import load_dotenv
import os

# .env 파일 로드 (OPENAI_API_KEY=sk-...)
load_dotenv(dotenv_path=Path(".env"))

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY 환경변수가 없습니다.")
