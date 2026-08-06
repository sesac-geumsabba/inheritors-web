import sys
from pathlib import Path

# packages/rag, packages/legal-mcp 임포트를 위해 리포 루트를 sys.path에 추가.
# 로컬(apps/api/app)과 Docker(/app/app, COPY로 한 단계 얕아짐)에서 깊이가 다르므로
# "packages" 폴더가 실제로 있는 조상 디렉터리를 찾아서 추가한다.
for _parent in Path(__file__).resolve().parents:
    if (_parent / "packages").is_dir():
        if str(_parent) not in sys.path:
            sys.path.insert(0, str(_parent))
        break
