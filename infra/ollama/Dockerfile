# 답변 생성 모델(EEVE-Korean 10.8B Q4, 약 6.5GB)을 이미지 레이어에 미리 구워 넣은 Ollama 서버.
# 매 컴퓨터마다 `ollama pull`을 새로 받을 필요 없이 이 이미지만 pull하면 바로 뜬다.
FROM ollama/ollama:latest AS builder

ARG MODEL=hf.co/gchrisoh/EEVE-Korean-Instruct-10.8B-v1.0-Q4_K_M-GGUF

# 빌드 중에만 서버를 잠깐 띄워 모델을 받고(레이어에 커밋됨) 끝낸다 — 런타임 ENTRYPOINT/CMD는
# 베이스 이미지 것(`ollama serve`)을 그대로 쓴다.
RUN ollama serve & \
    for i in $(seq 1 60); do ollama list >/dev/null 2>&1 && break; sleep 1; done && \
    ollama pull "${MODEL}"

# ollama/ollama 베이스 이미지는 CUDA/Jetpack GPU 백엔드를 통째로 들고 있어(~3.5GB, 실측)
# CPU 전용 배포(예: AWS Graviton/t4g)에서는 전부 죽은 용량이다. builder 스테이지의 라이브
# 파일시스템에서 미리 지워둬야 한다 — 최종 스테이지에서 지우면 이미 COPY된 뒤라 의미 없고,
# base 이미지 레이어 자체를 최종 스테이지가 그대로 이어받으면(FROM ollama/ollama) 레이어를
# 나중에 지워도 그 레이어의 바이트가 pull 대상에서 안 빠져서 반드시 이 순서(builder에서 rm
# → 깨끗한 FROM에 COPY --from)여야 실제로 용량이 준다.
RUN rm -rf /usr/lib/ollama/cuda_v12 /usr/lib/ollama/cuda_v13 \
           /usr/lib/ollama/cuda_jetpack5 /usr/lib/ollama/cuda_jetpack6

FROM ubuntu:24.04
COPY --from=builder /bin/ollama /bin/ollama
COPY --from=builder /usr/lib/ollama /usr/lib/ollama
COPY --from=builder /root/.ollama /root/.ollama

ENV OLLAMA_HOST=0.0.0.0:11434
EXPOSE 11434
ENTRYPOINT ["/bin/ollama"]
CMD ["serve"]
