# packages/legal-mcp

법원 종합법률정보 API / 법제처 법령 API 연동. 인증 방식, rate limit, 응답 포맷이 서로 다르므로
`clients/court_precedent.py`, `clients/moleg_statute.py`로 독립 관리.

동일 판례/조문 재조회 방지용 캐싱은 이 패키지 내부에 둘 것 (서버 분리 아님, 캐시 전략).
