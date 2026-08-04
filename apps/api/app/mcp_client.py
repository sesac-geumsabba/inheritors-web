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
        result = subprocess.run(
            ["npm", "root", "-g"], capture_output=True, text=True, timeout=5, shell=True
        )
        npm_root = result.stdout.strip()
        candidate = os.path.join(npm_root, "korean-law-mcp", "build", "index.js")
        if npm_root and os.path.exists(candidate):
            return candidate
    except Exception:
        pass
    return ""


class KoreanLawMCPClient:
    """Async MCP Client for korean-law-mcp via stdio JSON-RPC 2.0."""

    def __init__(self, command: Optional[str] = None, args: Optional[List[str]] = None, law_oc: Optional[str] = None):
        self.command = command or os.getenv("KOREAN_LAW_MCP_COMMAND", "node")
        script_path = os.getenv("KOREAN_LAW_MCP_SCRIPT_PATH") or _resolve_script_path()
        self.args = args or [script_path]
        self.law_oc = law_oc or os.getenv("LAW_OC", "inheritors")

    async def _call_tool(self, tool_name: str, arguments: Dict[str, Any], timeout: float = 3.0) -> Dict[str, Any]:
        """Spawns the node process, initializes JSON-RPC, calls the specified MCP tool, and returns result."""
        env = os.environ.copy()
        env["LAW_OC"] = self.law_oc

        process = None
        try:
            process = await asyncio.create_subprocess_exec(
                self.command,
                *self.args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )

            # Step 1: Initialize
            init_req = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "inheritors-rag-backend", "version": "1.0.0"},
                },
            }
            if process.stdin:
                process.stdin.write((json.dumps(init_req) + "\n").encode("utf-8"))
                await process.stdin.drain()

            # Read initialize response
            init_resp = await asyncio.wait_for(self._read_jsonrpc_response(process.stdout, target_id=1), timeout=timeout)
            if not init_resp or "error" in init_resp:
                raise RuntimeError(f"MCP Initialize failed: {init_resp}")

            # Send initialized notification
            initialized_notif = {"jsonrpc": "2.0", "method": "notifications/initialized"}
            if process.stdin:
                process.stdin.write((json.dumps(initialized_notif) + "\n").encode("utf-8"))
                await process.stdin.drain()

            # Step 2: Call tool
            tool_req = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments,
                },
            }
            if process.stdin:
                process.stdin.write((json.dumps(tool_req) + "\n").encode("utf-8"))
                await process.stdin.drain()

            tool_resp = await asyncio.wait_for(self._read_jsonrpc_response(process.stdout, target_id=2), timeout=timeout)
            return tool_resp or {}

        except asyncio.TimeoutError:
            return {"error": "MCP_TIMEOUT", "message": f"MCP tool '{tool_name}' request timed out after {timeout} seconds"}
        except Exception as e:
            return {"error": "MCP_ERROR", "message": str(e)}
        finally:
            if process:
                try:
                    process.kill()
                    await process.wait()
                except Exception:
                    pass

    async def _read_jsonrpc_response(self, stdout: Optional[asyncio.StreamReader], target_id: int) -> Optional[Dict[str, Any]]:
        if not stdout:
            return None

        while True:
            line = await stdout.readline()
            if not line:
                break
            try:
                data = json.loads(line.decode("utf-8").strip())
                if data.get("id") == target_id:
                    return data
            except json.JSONDecodeError:
                continue
        return None

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
