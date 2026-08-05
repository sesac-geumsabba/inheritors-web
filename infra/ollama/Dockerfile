# 답변 생성 모델(EEVE-Korean 10.8B Q4, 약 6.5GB)을 이미지 레이어에 미리 구워 넣은 Ollama 서버.
# 매 컴퓨터마다 `ollama pull`을 새로 받을 필요 없이 이 이미지만 pull하면 바로 뜬다.
FROM ollama/ollama:latest

ARG MODEL=hf.co/gchrisoh/EEVE-Korean-Instruct-10.8B-v1.0-Q4_K_M-GGUF

# 빌드 중에만 서버를 잠깐 띄워 모델을 받고(레이어에 커밋됨) 끝낸다 — 런타임 ENTRYPOINT/CMD는
# 베이스 이미지 것(`ollama serve`)을 그대로 쓴다.
RUN ollama serve & \
    for i in $(seq 1 60); do ollama list >/dev/null 2>&1 && break; sleep 1; done && \
    ollama pull "${MODEL}"
