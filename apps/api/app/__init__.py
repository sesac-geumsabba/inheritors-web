import sys
from pathlib import Path

# packages/rag, packages/legal-mcp 임포트를 위해 리포 루트를 sys.path에 추가.
# (Docker/로컬 어디서 uvicorn을 띄우든 동작하도록 코드로 고정)
_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
