# LLM 기반 MCP Tool-Calling 전환 계획

## 1. 개요

현재 `korean-law-mcp`의 호출 여부와 검색어는 정규식 및 고정 키워드 목록을 이용해 결정하고 있다.

현재 사용 중인 대표적인 규칙은 다음과 같다.

* `_PRECEDENT_KEYWORDS`
* `_LAW_KEYWORDS`
* `_LAW_SEARCH_TERMS`
* `_PRECEDENT_SEARCH_TERMS`
* `_PRECEDENT_BOOST_TERMS`
* `_extract_keywords()`
* `_build_mcp_query()`
* `is_precedent_only()`

이 구조에서는 개발자가 미리 지정한 단어가 사용자 질문에 포함되어 있는지를 검사한 뒤 다음 사항을 결정한다.

1. 법률 MCP를 호출할 것인지
2. `search_law`와 `search_decisions` 중 어떤 도구를 호출할 것인지
3. MCP 서버에 어떤 검색어를 전달할 것인지
4. 내부 RAG 검색을 건너뛸 것인지

하지만 이 방식은 사용자가 정확한 법률 용어를 사용하지 않으면 검색이 필요한 질문을 놓칠 수 있다.

예를 들어 다음 질문에는 `유류분`, `판례`, `법령` 같은 고정 키워드가 직접 포함되어 있지 않다.

> 돌아가신 아버지가 모든 재산을 형에게 줬는데 제가 일부를 돌려받을 수 있나요?

사람은 이 질문이 유류분과 관련된 법률 질문이라는 것을 이해할 수 있지만, 고정 키워드 방식에서는 MCP 호출이 누락되거나 부정확한 검색어가 생성될 수 있다.

따라서 고정 키워드와 정규식 기반 라우팅을 제거하고, LLM이 사용자 질문의 의미를 분석하여 MCP 도구 사용을 결정하도록 변경한다.

---

## 2. 목표

이번 변경의 핵심 목표는 다음 세 가지 판단을 모두 LLM에 맡기는 것이다.

### 2.1 MCP 호출 여부 판단

LLM이 사용자 질문을 분석하여 외부 법령 또는 판례 검색이 필요한지 판단한다.

* 신탁·상속·증여 관련 법령 확인이 필요한 경우 MCP 호출
* 실제 판결이나 대법원 판례가 필요한 경우 MCP 호출
* 법령과 판례가 모두 필요한 경우 두 도구 모두 호출
* 법률 검색이 필요하지 않거나 서비스 범위와 관련 없는 질문이면 호출하지 않음

### 2.2 Tool selection

LLM이 질문의 목적에 따라 사용할 도구를 선택한다.

* 법령 검색: `search_law`
* 판례 검색: `search_decisions`
* 법령과 판례가 모두 필요한 경우: 두 도구 모두 호출
* 외부 검색이 필요하지 않은 경우: 아무 도구도 호출하지 않음

### 2.3 Argument binding

LLM이 선택한 MCP 도구에 전달할 검색어를 직접 생성한다.

사용자의 자연어 질문 전체를 그대로 전달하지 않고, 질문의 법적 쟁점을 나타내는 짧은 검색어로 변환한다.

예시:

```text
사용자 질문:
아버지가 돌아가시기 전에 모든 재산을 형에게 증여했는데
제가 돌려받을 방법이 있는지 판례를 알려주세요.

LLM 판단:
도구: search_decisions
검색어: 유류분 반환
```

---

## 3. 핵심 설계 원칙

### 3.1 고정 키워드 규칙 제거

코드에 사람이 미리 정의한 법률 키워드 목록과 정규식 기반 분기 로직을 제거한다.

다음과 같은 방식은 사용하지 않는다.

```python
if "대법원" in query or "판례" in query:
    await search_decisions(...)
```

특정 표현을 특정 검색어로 치환하는 고정 매핑도 사용하지 않는다.

```python
{
    "재산을 돌려받다": "유류분 반환",
    "사망 후 신탁": "유언대용신탁",
}
```

어떤 법률 개념과 검색어가 적절한지는 질문마다 LLM이 동적으로 판단한다.

### 3.2 검색어 자체를 제거하는 것은 아님

법제처 검색 API는 키워드 기반 검색 엔진이므로 MCP에 최종적으로 전달되는 검색어는 여전히 필요하다.

이번 변경에서 제거하는 것은 검색어가 아니라 다음과 같은 사람 작성 규칙이다.

* 고정 키워드 목록
* 정규식 매칭
* 고정 검색어 치환표
* 키워드별 도구 선택 분기

최종 구조에서는 LLM이 사용자 질문을 분석하여 검색에 적합한 키워드를 동적으로 생성한다.

따라서 이번 구조는 다음과 같이 표현하는 것이 정확하다.

> 고정 키워드 규칙 없이 LLM이 질문마다 MCP 도구와 검색 키워드를 동적으로 결정하는 구조

### 3.3 API 제약은 Tool Description에 명시

법제처 검색 API는 공백으로 구분된 검색어를 AND 조건으로 처리한다.

따라서 다음과 같이 긴 자연어 문장을 전달하면 검색 결과가 0건이 될 가능성이 높다.

```text
돌아가신 아버지가 모든 재산을 형에게 줬을 때 제가 돌려받을 방법
```

이 제약은 LLM을 도입해도 사라지지 않는다.

따라서 각 도구의 설명에 다음 내용을 명확히 작성한다.

* 자연어 문장 전체를 검색어로 전달하지 않는다.
* 질문의 핵심 법률 쟁점을 추출한다.
* 검색어는 가능하면 1~3개의 핵심 법률 용어로 구성한다.
* 불필요한 조사, 일반 명사, 요청 표현은 제외한다.
* 검색 결과가 지나치게 좁아지지 않도록 꼭 필요한 단어만 사용한다.
* 질문에 없는 법률명, 사건번호 또는 판결 내용을 임의로 만들지 않는다.

이 설명은 특정 키워드에 따라 분기하는 규칙이 아니라, LLM이 도구를 올바르게 사용하기 위한 인터페이스 계약이다.

---

## 4. 목표 아키텍처

```text
사용자 질문
    ↓
OpenAI Tool-Calling LLM
    ├─ 외부 법률 검색이 필요한가?
    ├─ 법령과 판례 중 무엇이 필요한가?
    ├─ 두 도구가 모두 필요한가?
    ├─ 검색하지 않아도 되는가?
    └─ 각 도구에 어떤 검색어를 전달할 것인가?
    ↓
korean-law-mcp
    ├─ search_law
    └─ search_decisions
    ↓
외부 법률 검색 결과
    ↓
내부 RAG 검색 결과와 결합
    ↓
OpenAI 답변 생성 LLM
    ↓
최종 답변
```

OpenAI API는 다음 두 가지 역할을 담당한다.

### MCP Tool-Calling LLM

* MCP 호출 여부 판단
* 사용할 도구 선택
* MCP에 전달할 검색어 생성
* `temperature=0`
* 일관되고 결정적인 도구 선택을 우선

### 최종 답변 생성 LLM

* 내부 RAG 검색 결과와 MCP 검색 결과를 종합
* 검색된 근거를 바탕으로 최종 답변 생성
* 기존 OpenAI 답변 생성 체인 사용
* 기존 설정에 따라 `temperature=0.2` 사용 가능

두 역할에서 같은 모델을 사용할 수 있지만, 역할과 설정이 다르므로 별도의 LLM 인스턴스로 관리한다.

---

## 5. 구현 계획

### 5.1 새 모듈 생성

다음 파일을 새로 생성한다.

```text
inheritors-web/packages/rag/mcp_agent.py
```

이 모듈은 다음 책임을 가진다.

1. MCP 검색 함수를 LangChain 도구로 정의
2. Tool-Calling 전용 OpenAI LLM 생성 및 캐싱
3. 사용자 질문을 LLM에 전달
4. LLM이 반환한 `tool_calls` 검증
5. 선택된 MCP 도구 실행
6. 여러 도구가 선택되면 병렬 실행
7. 검색 결과 정리 및 반환
8. 오류 발생 시 빈 결과로 안전하게 폴백

### 5.2 MCP 함수를 LangChain Tool로 정의

기존 `mcp_client.search_law()`와 `mcp_client.search_decisions()`를 LLM이 사용할 수 있는 도구로 감싼다.

개념적인 예시는 다음과 같다.

```python
from langchain_core.tools import tool

from packages.rag import mcp_client


@tool
async def search_law_tool(query: str) -> list[dict]:
    """
    신탁, 상속, 증여와 관련된 대한민국 법령을 검색한다.

    검색 엔진은 공백으로 구분된 단어를 AND 조건으로 처리한다.
    사용자의 자연어 질문 전체를 전달하지 말고, 법적 쟁점을 나타내는
    1~3개의 핵심 법률 용어만 query에 전달한다.

    실제 판례나 법원의 판단을 찾을 때는 이 도구가 아니라
    search_decisions_tool을 사용한다.
    """
    return await mcp_client.search_law(query)


@tool
async def search_decisions_tool(query: str) -> list[dict]:
    """
    신탁, 상속, 증여와 관련된 대한민국 판례를 검색한다.

    검색 엔진은 공백으로 구분된 단어를 AND 조건으로 처리한다.
    사용자의 자연어 질문 전체를 전달하지 말고, 판례의 법적 쟁점을
    나타내는 1~3개의 핵심 법률 용어만 query에 전달한다.

    일반적인 법령 조문이나 제도 설명만 필요하면
    search_law_tool을 사용한다.
    """
    return await mcp_client.search_decisions(query)
```

실제 구현에서는 기존 `mcp_client` 함수의 정확한 인자명과 반환 타입에 맞춰 조정한다.

### 5.3 도구 입력 스키마 정의

LLM이 잘못된 형식의 검색어를 생성하지 않도록 Pydantic 스키마를 사용할 수 있다.

```python
from pydantic import BaseModel, Field


class LegalSearchInput(BaseModel):
    query: str = Field(
        description=(
            "사용자 질문의 법적 쟁점을 나타내는 검색어. "
            "자연어 문장이 아니라 1~3개의 핵심 법률 용어로 작성한다. "
            "검색 엔진이 공백 단어를 AND 조건으로 처리하므로 "
            "불필요한 단어를 포함하지 않는다."
        )
    )
```

스키마는 검색어의 형식과 의미를 제한하기 위한 것이다. 특정 법률 키워드 목록은 하드코딩하지 않는다.

필요하다면 실행 직전에 다음 정도의 형식 검증만 추가한다.

* 빈 문자열 거부
* 앞뒤 공백 제거
* 지나치게 긴 검색어 거부
* 동일한 도구와 동일한 검색어의 중복 호출 제거
* 문자열이 아닌 인자 거부

LLM이 만든 검색어를 사람이 작성한 키워드 규칙으로 다시 치환하거나 수정하지 않는다.

### 5.4 Tool-Calling 전용 LLM 생성

`ChatOpenAI`를 사용하여 MCP 도구 선택용 LLM을 만든다.

```python
from functools import lru_cache

from langchain_openai import ChatOpenAI


@lru_cache
def _agent_llm():
    return ChatOpenAI(
        model=MCP_AGENT_MODEL or OPENAI_MODEL,
        temperature=0,
    ).bind_tools(
        [
            search_law_tool,
            search_decisions_tool,
        ]
    )
```

`lru_cache`를 사용하여 요청마다 LLM 객체를 새로 생성하지 않도록 한다.

최종 답변 생성용 LLM과는 별도의 함수로 관리한다.

### 5.5 시스템 프롬프트 작성

LLM은 단순히 사용자 질문에 법률 관련 단어가 포함되었는지를 보는 것이 아니라, 질문의 의미와 답변에 필요한 근거를 기준으로 도구를 선택해야 한다.

시스템 프롬프트에는 다음 판단 기준을 포함한다.

```text
당신은 신탁, 상속, 증여 분야의 법률 검색 도구 선택 에이전트다.

사용자 질문을 이해하고, 정확한 답변을 위해 외부 법령 또는 판례 검색이
필요한 경우에만 제공된 도구를 호출하라.

- 현행 법령이나 법적 개념, 요건, 절차, 권리 확인이 필요하면
  search_law_tool을 호출한다.
- 실제 법원의 판단, 대법원 판례, 사건 사례 또는 판결 동향이 필요하면
  search_decisions_tool을 호출한다.
- 법령과 판례가 모두 필요하면 두 도구를 모두 호출할 수 있다.
- 신탁, 상속, 증여와 관련이 없거나 외부 법률 근거가 필요하지 않은
  질문이면 아무 도구도 호출하지 않는다.
- 사용자가 정확한 법률 용어를 사용하지 않았더라도 질문의 의미를
  분석하여 관련 법적 쟁점을 판단한다.
- 검색어는 자연어 문장이 아니라 1~3개의 핵심 법률 용어로 작성한다.
- 검색 엔진은 공백으로 구분된 단어를 모두 포함하는 문서만 찾으므로
  불필요한 단어를 넣지 않는다.
- 질문에 없는 법률명, 사건번호 또는 판결 내용을 임의로 만들어내지 않는다.
- 사용자가 법령만 또는 판례만 요청했다면 해당 요청 범위를 우선한다.
```

시스템 프롬프트에는 고정 키워드 목록을 넣지 않는다.

`대법원이라는 단어가 있으면 판례 도구를 호출하라`와 같은 문자열 매칭 규칙도 작성하지 않는다. LLM이 질문의 의도를 의미적으로 판단하도록 한다.

### 5.6 `select_and_run()` 구현

핵심 함수는 다음 형태로 구현한다.

```python
async def select_and_run(
    query: str,
) -> tuple[list[dict], set[str]]:
    ...
```

반환값은 다음 두 가지다.

```python
external_sources: list[dict]
called_tools: set[str]
```

예시:

```python
(
    [...],
    {"search_law", "search_decisions"},
)
```

함수의 실행 과정은 다음과 같다.

1. 시스템 프롬프트와 사용자 질문을 LLM에 전달
2. LLM 응답의 `tool_calls` 확인
3. 호출할 도구가 없으면 `([], set())` 반환
4. 각 tool call의 이름과 인자 검증
5. 동일한 도구와 동일한 검색어의 중복 요청 제거
6. 선택된 MCP 함수를 `asyncio.gather()`로 병렬 실행
7. 예외가 발생한 호출은 전체 요청을 중단하지 않고 제외
8. 기존과 동일하게 `score > 0`인 검색 결과만 유지
9. 검색 결과와 실제 호출된 도구 집합 반환

개념적인 구현은 다음과 같다.

```python
async def select_and_run(
    query: str,
) -> tuple[list[dict], set[str]]:
    try:
        response = await _agent_llm().ainvoke(
            [
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=query),
            ]
        )
    except Exception:
        return [], set()

    tool_calls = response.tool_calls or []

    if not tool_calls:
        return [], set()

    tasks = []
    called_tools = set()
    seen_calls = set()

    for tool_call in tool_calls:
        tool_name = tool_call["name"]
        tool_query = tool_call["args"].get("query", "").strip()

        if not tool_query:
            continue

        call_key = (tool_name, tool_query)

        if call_key in seen_calls:
            continue

        seen_calls.add(call_key)

        if tool_name == "search_law_tool":
            tasks.append(mcp_client.search_law(tool_query))
            called_tools.add("search_law")

        elif tool_name == "search_decisions_tool":
            tasks.append(mcp_client.search_decisions(tool_query))
            called_tools.add("search_decisions")

    if not tasks:
        return [], set()

    results = await asyncio.gather(
        *tasks,
        return_exceptions=True,
    )

    sources = []

    for result in results:
        if isinstance(result, Exception):
            continue

        for item in result:
            if item.get("score", 0) > 0:
                sources.append(item)

    return sources, called_tools
```

위 코드는 구조를 설명하기 위한 예시이며, 실제 데이터 구조와 기존 함수 반환값에 맞춰 수정한다.

---

## 6. `called_tools`와 `precedent_only`

`called_tools`에는 LLM이 선택하고 실행 대상으로 검증된 도구를 기록한다.

가능한 값은 다음과 같다.

```python
set()
{"search_law"}
{"search_decisions"}
{"search_law", "search_decisions"}
```

잘못된 도구 이름이나 빈 검색어가 전달된 호출은 `called_tools`에 포함하지 않는다.

`precedent_only`는 다음 조건을 기준으로 계산한다.

```python
precedent_only = (
    "search_decisions" in called_tools
    and "search_law" not in called_tools
)
```

의미는 다음과 같다.

| 호출된 도구       | `precedent_only` |
| ------------ | ---------------: |
| 판례만 검색       |           `True` |
| 법령만 검색       |          `False` |
| 법령과 판례 모두 검색 |          `False` |
| MCP를 호출하지 않음 |          `False` |

다만 판례 검색에 실패하거나 검색 결과가 0건인데도 `precedent_only=True`가 되면 내부 RAG까지 생략되어 답변 근거가 사라질 수 있다.

따라서 다음 정책을 적용하는 것이 안전하다.

```text
판례 도구만 선택했고 판례 결과도 존재함
→ precedent_only=True
→ 내부 RAG 생략

판례 도구만 선택했지만 호출 실패 또는 결과 없음
→ precedent_only=False
→ 내부 RAG를 폴백으로 사용
```

개념적인 계산 방식은 다음과 같다.

```python
has_case_law_source = any(
    source.get("source_type") == "case_law"
    for source in sources
)

precedent_only = (
    "search_decisions" in called_tools
    and "search_law" not in called_tools
    and has_case_law_source
)
```

실제 `source_type` 값은 현재 MCP 응답 구조에 맞춰 확인한다.

---

## 7. `chat_shared.py` 변경

대상 파일:

```text
inheritors-web/apps/api/app/chat_shared.py
```

기존 키워드 기반 상수와 함수를 제거한다.

제거 대상:

```text
_PRECEDENT_KEYWORDS
_LAW_KEYWORDS
_LAW_SEARCH_TERMS
_PRECEDENT_BOOST_TERMS
_PRECEDENT_SEARCH_TERMS
_QUERY_STOPWORDS
_TRAILING_PARTICLE_RE
_extract_keywords()
_build_mcp_query()
is_precedent_only()
```

`fetch_external_sources()`는 `mcp_agent.select_and_run()`을 호출하도록 변경한다.

변경된 반환 타입:

```python
tuple[list[dict], bool]
```

개념적인 구현은 다음과 같다.

```python
async def fetch_external_sources(
    query: str,
) -> tuple[list[dict], bool]:
    sources, called_tools = await mcp_agent.select_and_run(query)

    has_case_law_source = any(
        source.get("source_type") == "case_law"
        for source in sources
    )

    precedent_only = (
        "search_decisions" in called_tools
        and "search_law" not in called_tools
        and has_case_law_source
    )

    return sources, precedent_only
```

---

## 8. 라우터 변경

다음 두 파일을 수정한다.

```text
inheritors-web/apps/api/app/routers/chat_router.py
inheritors-web/apps/api/app/routers/chat_openai_router.py
```

기존 코드:

```python
external_sources = await fetch_external_sources(req.message)
```

변경 코드:

```python
external_sources, precedent_only = await fetch_external_sources(
    req.message
)
```

기존 코드:

```python
skip_internal=is_precedent_only(req.message)
```

변경 코드:

```python
skip_internal=precedent_only
```

두 라우터가 동일한 흐름을 사용하므로 같은 방식으로 수정한다.

---

## 9. 중복 호출 및 비정상 출력 처리

LLM은 한 번의 응답에서 동일한 도구를 여러 번 호출할 수 있다.

예시:

```text
search_law("유류분")
search_law("유류분 반환")
search_decisions("유류분 반환")
```

서로 다른 검색어가 보완적인 결과를 낼 수 있으므로, 도구 종류별로 하나의 호출만 허용할 필요는 없다.

다만 완전히 동일한 호출은 제거한다.

중복 판단 기준:

```python
(tool_name, normalized_query)
```

예시:

```text
search_law("유류분")
search_law(" 유류분 ")
```

두 호출은 동일한 요청으로 보고 한 번만 실행한다.

다음 경우에는 도구 호출을 무시한다.

* 등록되지 않은 도구 이름
* `query` 인자 누락
* 빈 검색어
* 허용 범위를 크게 초과한 검색어
* 인자 타입이 문자열이 아닌 경우

형식 검증은 안전장치이며 LLM이 선택한 검색어를 고정 키워드 규칙으로 다시 변환하지 않는다.

---

## 10. OpenAI 최종 답변 생성

최종 답변 생성에도 OpenAI API를 사용한다.

전체 실행 흐름은 다음과 같다.

```text
사용자 질문
    ↓
OpenAI Tool-Calling LLM
    ├─ MCP 호출 필요 여부 판단
    ├─ 법령·판례 도구 선택
    └─ MCP 검색어 생성
    ↓
korean-law-mcp
    ├─ 법령 검색
    └─ 판례 검색
    ↓
내부 RAG 검색 결과와 MCP 검색 결과 결합
    ↓
OpenAI 답변 생성 LLM
    ↓
최종 답변
```

OpenAI API는 두 가지 역할을 담당한다.

### MCP Tool-Calling LLM

* MCP 검색 필요 여부 판단
* `search_law`와 `search_decisions` 중 사용할 도구 선택
* 각 도구에 전달할 검색어 생성
* 도구 선택의 일관성을 위해 `temperature=0` 사용
* 빠르고 비용이 낮은 모델 사용 권장

### 최종 답변 생성 LLM

* 내부 RAG 검색 결과와 MCP 외부 검색 결과 종합
* 검색된 근거를 바탕으로 사용자 답변 생성
* 기존 OpenAI 답변 생성 체인 사용
* 기존 설정에 따라 `temperature=0.2` 사용 가능

두 역할에서 같은 OpenAI 모델을 사용할 수 있지만, 역할과 설정이 다르므로 별도의 LLM 인스턴스로 관리한다.

---

## 11. 오류 처리 및 폴백

LLM 또는 MCP가 실패해도 전체 채팅 요청이 중단되지 않도록 한다.

다음 오류를 처리한다.

* `OPENAI_API_KEY` 누락
* Tool-Calling LLM 호출 실패
* LLM의 잘못된 tool call 형식
* MCP 서버 연결 실패
* MCP 도구 실행 중 timeout
* 일부 도구만 실패
* MCP가 빈 결과 반환
* 예상하지 못한 MCP 응답 형식
* 최종 답변 생성용 OpenAI 호출 실패

### Tool-Calling 또는 MCP 실패

Tool-Calling이나 MCP 검색이 실패하면 기본적으로 다음 값을 반환한다.

```python
([], set())
```

이 경우 다음과 같이 동작한다.

* 외부 법령·판례 소스는 없음
* 내부 RAG 검색은 계속 수행
* MCP 오류로 전체 요청을 중단하지 않음
* 서버 로그에는 실패 원인 기록
* 내부 RAG 검색 결과를 OpenAI 답변 생성 LLM에 전달

여러 MCP 도구를 호출한 경우 하나가 실패해도 다른 도구의 성공 결과는 유지한다.

```python
results = await asyncio.gather(
    *tasks,
    return_exceptions=True,
)
```

### 최종 답변 생성 실패

최종 OpenAI 답변 생성 호출까지 실패한 경우에는 기존 API의 오류 처리 정책에 따라 사용자에게 일반화된 오류 응답을 반환한다.

내부 예외 메시지, API 키 또는 서버 내부 정보는 사용자에게 그대로 노출하지 않는다.

---

## 12. 대화 문맥 처리

현재 질문만 Tool-Calling LLM에 전달하면 후속 질문의 의미를 파악하지 못할 수 있다.

예시:

```text
이전 질문:
유언대용신탁의 수익자는 누가 될 수 있어?

현재 질문:
관련 판례도 알려줘.
```

현재 질문인 `관련 판례도 알려줘`만 전달하면 무엇과 관련된 판례인지 판단하기 어렵다.

후속 질문을 지원하려면 다음 방법 중 하나를 적용한다.

* 최근 대화 일부를 Tool-Calling LLM에 함께 전달
* 현재 질문을 독립적인 검색 질문으로 재작성한 뒤 전달
* 기존 파이프라인에서 생성한 대화 요약을 함께 전달

권장 방식은 최근 대화 전체가 아니라, 현재 질문을 이해하는 데 필요한 최소한의 최근 문맥만 제공하는 것이다.

개념적인 입력 구조:

```python
messages = [
    SystemMessage(content=SYSTEM_PROMPT),
    HumanMessage(
        content=(
            f"최근 대화:\n{recent_context}\n\n"
            f"현재 사용자 질문:\n{query}"
        )
    ),
]
```

대화 문맥을 전달하더라도 MCP 검색어에는 대화 전체를 넣지 않는다. LLM이 문맥을 이해한 뒤 1~3개의 핵심 법률 용어만 도구 인자로 생성하도록 한다.

---

## 13. 성능 및 비용 고려

기존 방식은 키워드와 정규식만 사용했기 때문에 MCP 호출 판단을 위한 추가 LLM 호출이 없었다.

변경 후에는 채팅 요청마다 MCP Tool-Calling 판단을 위한 OpenAI 호출이 최대 한 번 추가된다.

예상 영향:

* OpenAI API 호출 비용 증가
* MCP 검색이 필요하지 않은 질문에도 판단용 LLM 호출 발생
* 최종 답변 전 단계의 응답 지연 증가
* 키워드 규칙으로 처리하지 못하던 질문의 검색 정확도 개선 가능
* 다양한 자연어 표현에 대한 대응력 향상

이번 목표는 MCP 판단 전체를 LLM에 맡기는 것이므로, LLM 호출 전에 키워드 기반 사전 필터를 두지 않는다.

대신 비용과 지연을 줄이기 위해 다음 방법을 적용할 수 있다.

* Tool-Calling에 빠르고 비용이 낮은 OpenAI 모델 사용
* `temperature=0` 적용
* 짧고 명확한 시스템 프롬프트 사용
* 불필요한 대화 이력을 넣지 않고 최소한의 문맥만 전달
* LLM이 직접 답변하지 않고 `tool_calls`만 반환하도록 유도
* 동일한 도구와 검색어의 중복 호출 제거
* LLM과 MCP 호출에 적절한 timeout 설정

---

## 14. 환경변수

OpenAI API 키는 MCP Tool-Calling과 최종 답변 생성에 모두 필요하다.

예시:

```env
OPENAI_API_KEY=your-openai-api-key
OPENAI_MODEL=gpt-4o
MCP_AGENT_MODEL=gpt-4o-mini
```

각 환경변수의 역할은 다음과 같다.

* `OPENAI_API_KEY`: OpenAI API 인증
* `OPENAI_MODEL`: 최종 답변 생성 모델
* `MCP_AGENT_MODEL`: MCP 도구 선택 및 검색어 생성 모델

`MCP_AGENT_MODEL`이 설정되지 않은 경우 `OPENAI_MODEL`을 사용하도록 구성할 수 있다.

```python
mcp_agent_model = MCP_AGENT_MODEL or OPENAI_MODEL
```

이렇게 구성하면 두 역할에 같은 모델을 사용할 수도 있고, 각각 다른 모델을 사용할 수도 있다.

예시:

```env
OPENAI_MODEL=gpt-4o
MCP_AGENT_MODEL=gpt-4o-mini
```

* `gpt-4o`: 최종 답변 생성
* `gpt-4o-mini`: MCP 도구 선택 및 검색어 생성

환경변수를 새로 추가할 경우 다음 파일도 함께 수정한다.

* `.env.example`
* 환경변수 설정 클래스
* 개발 환경 설정 문서
* 배포 환경 설정
* PR 설명

실제 프로젝트에서 사용하는 환경변수명이 다르다면 기존 코드의 이름에 맞춰 작성한다.

---

## 15. 테스트 계획

테스트는 결정적인 단위 테스트와 실제 외부 시스템을 사용하는 통합 테스트로 분리한다.

### 15.1 단위 테스트

새 테스트 파일:

```text
inheritors-web/apps/api/tests/test_mcp_agent.py
```

단위 테스트에서는 실제 OpenAI와 실제 MCP 서버에 의존하지 않는다.

LLM 응답의 `tool_calls`와 `mcp_client` 함수를 모킹하여 다음을 검증한다.

#### 법령 도구만 선택한 경우

LLM 응답:

```python
[
    {
        "name": "search_law_tool",
        "args": {"query": "유류분"},
    }
]
```

검증 항목:

* `search_law()`가 한 번 호출됨
* `search_decisions()`는 호출되지 않음
* 법령 검색 결과가 반환됨
* `called_tools == {"search_law"}`

#### 판례 도구만 선택한 경우

LLM 응답:

```python
[
    {
        "name": "search_decisions_tool",
        "args": {"query": "유류분 반환"},
    }
]
```

검증 항목:

* `search_decisions()`가 한 번 호출됨
* `search_law()`는 호출되지 않음
* `called_tools == {"search_decisions"}`
* 판례 결과가 존재하면 `precedent_only=True`

#### 두 도구를 선택한 경우

검증 항목:

* 법령과 판례 검색이 모두 실행됨
* 결과가 하나의 리스트로 합쳐짐
* `called_tools == {"search_law", "search_decisions"}`
* `precedent_only=False`

#### 도구를 선택하지 않은 경우

LLM 응답:

```python
[]
```

검증 항목:

```python
sources == []
called_tools == set()
```

#### 일부 MCP 호출이 실패한 경우

검증 항목:

* 성공한 도구의 결과는 유지됨
* 실패한 도구 때문에 전체 요청이 중단되지 않음
* 예외가 사용자 요청까지 전달되지 않음

#### Tool-Calling LLM 호출이 실패한 경우

검증 항목:

```python
sources == []
called_tools == set()
```

#### 중복 도구 호출이 발생한 경우

검증 항목:

* 동일한 도구와 동일한 검색어는 한 번만 실행
* 서로 다른 검색어는 각각 실행 가능

#### 검색 점수 필터링

검증 항목:

* `score > 0`인 결과만 유지
* `score <= 0`인 결과는 제외

#### 판례 검색 결과가 없는 경우

검증 항목:

* 판례 도구가 선택되었더라도 결과가 없으면 `precedent_only=False`
* 내부 RAG 검색이 폴백으로 실행됨

### 15.2 LLM Tool-Selection 통합 테스트

실제 OpenAI API를 사용하는 테스트는 단위 테스트와 분리한다.

환경변수 또는 별도 마커를 이용하여 필요할 때만 실행하도록 한다.

예시:

```bash
pytest -m integration
```

#### 법령 중심 질문

```text
유류분이 무엇이고 누가 청구할 수 있어?
```

기대 결과:

* `search_law` 호출
* 법령 검색어가 자연어 문장 전체가 아닌 짧은 법률 용어로 생성됨

#### 판례 전용 질문

```text
법령 설명은 제외하고 유류분 반환과 관련된 대법원 판례만 알려줘.
```

기대 결과:

* `search_decisions` 호출
* `search_law` 미호출
* 판례 검색 결과가 있으면 `precedent_only=True`

#### 법령과 판례가 모두 필요한 질문

```text
유언대용신탁이 유류분에 미치는 영향과 관련 판례를 함께 알려줘.
```

기대 결과:

* `search_law` 호출
* `search_decisions` 호출
* `precedent_only=False`

#### 법률 용어가 직접 포함되지 않은 질문

```text
아버지가 생전에 재산을 형에게 전부 줬는데 제가 돌려받을 수 있는 부분이 있나요?
```

기대 결과:

* LLM이 질문의 의미를 분석
* 적절한 법령 또는 판례 도구 선택
* 고정 키워드가 없어도 MCP 검색 수행

#### 서비스 범위와 무관한 질문

```text
부동산 재건축 절차를 알려줘.
```

기대 결과:

* 신탁·상속·증여 서비스 범위와 관련이 없다고 판단
* MCP 도구 호출 없음

실제 LLM은 질문에 따라 법령과 판례를 모두 필요하다고 판단할 수 있다.

따라서 판례 전용 동작을 검증할 때는 다음처럼 범위를 명시한 질문을 사용한다.

```text
법령 설명은 제외하고 판례만 알려줘.
```

### 15.3 실제 서버 E2E 검증

현재 실행 중인 환경을 기준으로 확인한다.

```text
FastAPI: http://localhost:8000
Next.js: http://localhost:3000
```

확인 항목:

1. 질문 전송이 정상적으로 완료되는가
2. `event: sources`에 외부 출처가 포함되는가
3. 법령 결과의 `source_type`이 `statute`로 표시되는가
4. 판례 결과의 `source_type`이 `case_law`로 표시되는가
5. 관련 없는 질문에서 외부 소스가 생성되지 않는가
6. 판례 전용 질문에서 내부 RAG 청크가 섞이지 않는가
7. MCP 오류 시에도 내부 RAG 기반 답변이 생성되는가
8. 최종 답변이 OpenAI API를 통해 정상적으로 생성되는가

---

## 16. 로깅 및 관찰 가능성

LLM이 도구 선택을 담당하면 잘못된 판단의 원인을 확인할 수 있는 로그가 중요하다.

민감한 정보가 포함되지 않는 범위에서 다음 항목을 기록한다.

```text
LLM이 선택한 도구
LLM이 생성한 검색어
각 MCP 호출 성공 여부
각 도구의 검색 결과 개수
최종 외부 소스 개수
precedent_only 값
Tool-Calling LLM 오류 유형
MCP 오류 유형
최종 답변 생성 오류 유형
```

예시:

```text
mcp_agent tool=search_law query="유류분" results=5
mcp_agent tool=search_decisions query="유류분 반환" results=3
mcp_agent called_tools=["search_law", "search_decisions"]
mcp_agent precedent_only=false
```

프로덕션에서 사용자 질문 전체를 로그에 남기는 것이 개인정보 정책에 맞는지 확인한다.

필요하면 질문 원문 대신 요청 ID, 선택된 도구, 검색어 및 결과 개수만 기록한다.

---

## 17. 구현 단계

### 1단계: 현재 MCP 인터페이스 확인

* `mcp_client.search_law()` 인자 확인
* `mcp_client.search_decisions()` 인자 확인
* 각 함수의 반환 타입 확인
* `score` 및 `source_type` 필드 확인
* timeout과 예외 처리 방식 확인

### 2단계: `mcp_agent.py` 생성

* 입력 스키마 작성
* LangChain Tool 정의
* Tool-Calling 전용 OpenAI LLM 구성
* 시스템 프롬프트 작성
* `select_and_run()` 구현
* 중복 제거 구현
* 병렬 실행 및 오류 폴백 구현

### 3단계: `chat_shared.py` 정리

* 고정 키워드 상수 제거
* 정규식 기반 검색어 생성 함수 제거
* 기존 `is_precedent_only()` 제거
* `fetch_external_sources()`를 LLM 에이전트 기반으로 변경
* 검색 실패 시 내부 RAG 폴백 정책 적용

### 4단계: 라우터 수정

* `chat_router.py` 반환값 언패킹 변경
* `chat_openai_router.py` 반환값 언패킹 변경
* `skip_internal=precedent_only` 적용

### 5단계: 단위 테스트 작성

* LLM 응답 모킹
* MCP 클라이언트 모킹
* 도구별 선택 검증
* 병렬 실행 검증
* 중복 제거 검증
* 오류 폴백 검증
* `precedent_only` 검증

### 6단계: 통합 테스트

* 실제 OpenAI Tool Calling 확인
* 실제 `korean-law-mcp` 검색 확인
* 대표 질문별 도구 선택 확인
* LLM이 생성한 검색어 품질 확인

### 7단계: E2E 검증

* FastAPI 요청 테스트
* Next.js 화면 테스트
* SSE의 `event: sources` 확인
* 내부 RAG와 외부 소스 결합 확인
* 판례 전용 질문 동작 확인
* OpenAI 최종 답변 생성 확인

### 8단계: 문서화

* MCP Tool-Calling과 최종 답변 생성에 OpenAI API를 사용한다는 점 기록
* 필수 환경변수 작성
* MCP 검색 오류 시 내부 RAG 폴백 동작 기록
* 최종 답변 생성 오류 처리 방식 기록
* 테스트 실행 방법 기록
* 추가 LLM 호출에 따른 비용과 응답 지연 가능성 기록
* PR 설명에 전체 구조 변경 내용 작성

---

## 18. 변경 파일

```text
inheritors-web/packages/rag/mcp_agent.py
```

* 새 파일
* MCP 도구 정의
* OpenAI Tool-Calling LLM 구성
* 도구 선택 및 MCP 실행 로직 구현

```text
inheritors-web/apps/api/app/chat_shared.py
```

* 키워드 및 정규식 기반 로직 제거
* `fetch_external_sources()`를 LLM 기반으로 변경
* `precedent_only` 계산 로직 변경

```text
inheritors-web/apps/api/app/routers/chat_router.py
```

* `fetch_external_sources()` 반환값 언패킹 변경
* `skip_internal=precedent_only` 적용

```text
inheritors-web/apps/api/app/routers/chat_openai_router.py
```

* `fetch_external_sources()` 반환값 언패킹 변경
* `skip_internal=precedent_only` 적용

```text
inheritors-web/apps/api/tests/test_mcp_agent.py
```

* 새 테스트 파일
* Tool-Calling 및 MCP 실행 단위 테스트 작성

필요한 경우 다음 파일도 수정한다.

```text
.env.example
환경변수 설정 모듈
requirements.txt 또는 pyproject.toml
개발 및 배포 문서
```

---

## 19. 완료 기준

다음 조건을 모두 충족하면 구현이 완료된 것으로 본다.

* 고정 법률·판례 키워드 목록이 제거됨
* 정규식 기반 MCP 라우팅이 제거됨
* 고정 검색어 매핑이 제거됨
* LLM이 MCP 호출 여부를 판단함
* LLM이 법령·판례 도구를 선택함
* LLM이 MCP 검색어를 동적으로 생성함
* 한 응답에서 여러 MCP 도구를 선택할 수 있음
* 여러 도구가 병렬로 실행됨
* 동일한 MCP 요청이 중복 실행되지 않음
* 관련 없는 질문에서는 MCP가 호출되지 않음
* 정확한 법률 용어가 없는 질문도 의미를 분석해 검색함
* LLM 또는 MCP 오류가 앱 전체 오류로 이어지지 않음
* MCP 검색 실패 시 내부 RAG 검색이 계속 동작함
* 판례 전용 질문에서 기존 `skip_internal` 동작이 유지됨
* 판례 결과가 없으면 내부 RAG를 폴백으로 사용함
* 단위 테스트가 외부 API 없이 안정적으로 통과함
* 실제 OpenAI 및 MCP 통합 테스트가 별도로 존재함
* 최종 답변이 OpenAI API를 통해 생성됨
* OpenAI 관련 필수 환경변수가 문서화됨

---

## 20. 최종 정리

이번 변경은 단순히 MCP 검색어만 LLM으로 생성하는 작업이 아니다.

기존에 사람이 작성한 키워드 및 정규식 규칙이 담당하던 다음 판단 전체를 LLM에 이전하는 작업이다.

1. MCP 검색이 필요한지 판단
2. 법령과 판례 중 어떤 도구가 필요한지 판단
3. 두 도구를 모두 사용할지 판단
4. 아무 도구도 사용하지 않을지 판단
5. 각 도구에 전달할 검색어 생성

고정 키워드는 제거하지만 법제처 검색 API의 AND 검색 제약까지 제거되는 것은 아니다. 따라서 해당 제약은 Tool Description과 입력 스키마에 명확히 작성한다.

최종적으로 목표하는 구조는 다음과 같다.

```text
사용자 자연어 질문
→ OpenAI LLM의 의미 기반 판단
→ Tool selection
→ Argument binding
→ MCP 법령·판례 검색
→ 내부 RAG 및 외부 검색 결과 결합
→ OpenAI 답변 생성 LLM
→ 최종 답변
```

이를 통해 사용자가 정확한 법률 용어를 모르더라도 질문의 의미를 바탕으로 적절한 법령과 판례를 검색할 수 있다.

또한 새로운 표현이 추가될 때마다 개발자가 키워드 목록을 수정해야 하는 문제를 줄이고, MCP가 전제하는 LLM 기반 Tool-Calling 구조에 맞게 시스템을 개선할 수 있다.
