import asyncio
import json
import os
import subprocess
from typing import Any, Dict, List, Optional


def _resolve_script_path() -> str:
    """npm 전역 설치 경로에서 korean-law-mcp 진입 스크립트를 찾는다.
    (Windows에서 bin 커맨드를 직접 exec하면 .cmd 래퍼 문제로 실패해서 node+스크립트 경로 방식을 씀)
    KOREAN_LAW_MCP_SCRIPT_PATH 환경변수가 있으면 이 탐색은 건너뛴다."""
    try:
        # POSIX에서는 shell=True + 리스트 args를 같이 쓰면 셸이 첫 인자(npm)만 명령으로 보고
        # 나머지("root", "-g")는 버려서 항상 실패한다(실측 확인) — 리스트면 shell=False가 맞다.
        # Windows는 npm이 npm.cmd라 shell 경유가 필요해서(주석에 있던 원래 의도) 그 경우만 문자열+shell=True.
        result = subprocess.run(
            "npm root -g" if os.name == "nt" else ["npm", "root", "-g"],
            capture_output=True,
            text=True,
            timeout=5,
            shell=(os.name == "nt"),
        )
        npm_root = result.stdout.strip()
        candidate = os.path.join(npm_root, "korean-law-mcp", "build", "index.js")
        if npm_root and os.path.exists(candidate):
            return candidate
    except Exception:
        pass
    return ""


class KoreanLawMCPClient:
    """Async MCP Client for korean-law-mcp via stdio JSON-RPC 2.0.

    korean-law-mcp는 pdfjs/onnxruntime/sharp/express 등 무거운 의존성을 require해서 콜드
    기동에만 1~2초가 걸린다(실측). 호출마다 새로 spawn+kill하면 이 기동 비용을 매번 물어
    라우터의 3초 타임아웃에 그대로 걸릴 위험이 커서, 프로세스 하나를 FastAPI 수명 동안
    띄워두고(start/aclose) 재사용한다 — 이후 호출은 실제 JSON-RPC 왕복만 남아 훨씬 빠르다.
    """

    def __init__(self, command: Optional[str] = None, args: Optional[List[str]] = None, law_oc: Optional[str] = None):
        self.command = command or os.getenv("KOREAN_LAW_MCP_COMMAND", "node")
        script_path = os.getenv("KOREAN_LAW_MCP_SCRIPT_PATH") or _resolve_script_path()
        self.args = args or [script_path]
        self.law_oc = law_oc or os.getenv("LAW_OC", "inheritors")
        self._process: Optional[asyncio.subprocess.Process] = None
        self._next_id = 1
        # 프로세스 stdin/stdout은 요청 하나가 응답을 다 읽을 때까지 다른 요청이 끼어들면 안 되므로
        # 호출을 직렬화한다 — 챗봇 트래픽 규모에서는 동시성보다 단순함이 이득 (ponytail).
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        """FastAPI startup에서 1회 호출해 MCP 서버 프로세스를 미리 띄워둔다 (콜드 기동 비용 선지불)."""
        async with self._lock:
            await self._ensure_process_locked()

    async def aclose(self) -> None:
        """FastAPI shutdown에서 호출해 자식 프로세스를 정리한다."""
        async with self._lock:
            await self._kill_process_locked()

    async def _ensure_process_locked(self) -> asyncio.subprocess.Process:
        """호출 시 self._lock을 쥐고 있어야 한다. 살아있는 프로세스가 없으면 새로 띄우고 initialize한다."""
        if self._process is not None and self._process.returncode is None:
            return self._process

        env = os.environ.copy()
        env["LAW_OC"] = self.law_oc
        process = await asyncio.create_subprocess_exec(
            self.command,
            *self.args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
        self._process = process
        self._next_id = 1

        init_req = {
            "jsonrpc": "2.0",
            "id": self._next_id,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "inheritors-rag-backend", "version": "1.0.0"},
            },
        }
        await self._write_locked(init_req)
        init_resp = await asyncio.wait_for(
            self._read_jsonrpc_response_locked(target_id=self._next_id), timeout=10.0
        )
        if not init_resp or "error" in init_resp:
            await self._kill_process_locked()
            raise RuntimeError(f"MCP Initialize failed: {init_resp}")

        await self._write_locked({"jsonrpc": "2.0", "method": "notifications/initialized"})
        return process

    async def _kill_process_locked(self) -> None:
        if self._process is None:
            return
        try:
            self._process.kill()
            await self._process.wait()
        except Exception:
            pass
        self._process = None

    async def _write_locked(self, obj: Dict[str, Any]) -> None:
        assert self._process is not None and self._process.stdin is not None
        self._process.stdin.write((json.dumps(obj) + "\n").encode("utf-8"))
        await self._process.stdin.drain()

    async def _read_jsonrpc_response_locked(self, target_id: int) -> Optional[Dict[str, Any]]:
        assert self._process is not None and self._process.stdout is not None
        stdout = self._process.stdout
        while True:
            line = await stdout.readline()
            if not line:
                return None
            try:
                data = json.loads(line.decode("utf-8").strip())
                if data.get("id") == target_id:
                    return data
            except json.JSONDecodeError:
                continue

    async def _call_tool(self, tool_name: str, arguments: Dict[str, Any], timeout: float = 3.0) -> Dict[str, Any]:
        """유지해둔(또는 죽었으면 새로 띄운) 프로세스에 tools/call을 보내고 응답을 받는다.

        요청이 하나 실패해도(타임아웃, 프로세스 죽음) 다음 요청에서 자동으로 재기동을 시도한다.
        """
        async with self._lock:
            try:
                await self._ensure_process_locked()
                self._next_id += 1
                req_id = self._next_id
                await self._write_locked(
                    {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "method": "tools/call",
                        "params": {"name": tool_name, "arguments": arguments},
                    }
                )
                resp = await asyncio.wait_for(
                    self._read_jsonrpc_response_locked(target_id=req_id), timeout=timeout
                )
                return resp or {}
            except asyncio.TimeoutError:
                return {
                    "error": "MCP_TIMEOUT",
                    "message": f"MCP tool '{tool_name}' request timed out after {timeout} seconds",
                }
            except Exception as e:
                # stdin/stdout이 깨진 상태로 남아있으면 다음 호출도 계속 실패하니 죽여서 다음
                # 호출이 새로 기동하게 한다.
                await self._kill_process_locked()
                return {"error": "MCP_ERROR", "message": str(e)}

    async def search_law(self, query: str, timeout: float = 3.0) -> List[Dict[str, Any]]:
        """Search statutes/laws using korean-law-mcp."""
        resp = await self._call_tool("search_law", {"query": query}, timeout=timeout)
        if "error" in resp:
            return [{"source_type": "statute", "title": query, "url": "", "snippet": f"검색 중 오류 발생 또는 타임아웃: {resp.get('message')}", "score": 0.0, "rank": 1}]

        result = resp.get("result", {})
        content = result.get("content", [])
        sources = []
        for i, item in enumerate(content, 1):
            text = item.get("text", "")
            sources.append({
                "source_type": "statute",
                "title": f"법령 검색: {query}",
                "url": "https://www.law.go.kr",
                "snippet": text[:500],
                "score": round(1.0 - (i * 0.1), 2),
                "rank": i,
            })
        return sources or [{"source_type": "statute", "title": query, "url": "", "snippet": "관련 법령을 찾을 수 없습니다.", "score": 0.0, "rank": 1}]

    async def search_decisions(self, query: str, domain: str = "precedent", timeout: float = 3.0) -> List[Dict[str, Any]]:
        """Search court precedents using korean-law-mcp."""
        resp = await self._call_tool("search_decisions", {"query": query, "domain": domain}, timeout=timeout)
        if "error" in resp:
            return [{"source_type": "case_law", "title": query, "url": "", "snippet": f"판례 검색 중 오류 발생 또는 타임아웃: {resp.get('message')}", "score": 0.0, "rank": 1}]

        result = resp.get("result", {})
        content = result.get("content", [])
        sources = []
        for i, item in enumerate(content, 1):
            text = item.get("text", "")
            sources.append({
                "source_type": "case_law",
                "title": f"판례 검색: {query}",
                "url": "https://glaw.scourt.go.kr",
                "snippet": text[:500],
                "score": round(1.0 - (i * 0.1), 2),
                "rank": i,
            })
        return sources or [{"source_type": "case_law", "title": query, "url": "", "snippet": "관련 판례를 찾을 수 없습니다.", "score": 0.0, "rank": 1}]

    async def verify_citations(self, text: str, timeout: float = 3.0) -> Dict[str, Any]:
        """Verify statutory/precedent citations via legal_analysis(mode=verify_citations).

        korean-law-mcp v4.6.0부터 독립 도구였던 verify_citations가 legal_analysis의 mode로
        통합됨 (실측: tools/list에 verify_citations 없음, legal_analysis만 존재).
        """
        resp = await self._call_tool(
            "legal_analysis", {"mode": "verify_citations", "text": text}, timeout=timeout
        )
        if "error" in resp:
            return {"verified": False, "details": resp.get("message")}

        result = resp.get("result", {})
        content = result.get("content", [])
        verified_text = "\n".join([item.get("text", "") for item in content])
        return {
            "verified": "NOT_FOUND" not in verified_text and "HALLUCINATION_DETECTED" not in verified_text,
            "details": verified_text,
        }


# main.py의 lifespan에서 start()/aclose()로 관리하는 단일 인스턴스 — chat_router/mcp_router가
# 각자 클라이언트를 새로 만들면 프로세스도 따로 떠서 재사용 이점이 없어지므로 이걸 공유해서 쓴다.
mcp_client = KoreanLawMCPClient()
