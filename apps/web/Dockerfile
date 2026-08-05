FROM node:20-alpine AS deps
WORKDIR /app
# npm workspaces(root package.json)라 루트 lockfile만으로는 부족하다 — apps/web/package.json도
# 있어야 npm ci가 workspace를 인식해서 next 등을 node_modules/.bin에 링크한다. 없으면 빌드
# 시점에 "sh: next: not found"(exit 127)로 죽는다(실측).
COPY package.json package-lock.json ./
COPY apps/web/package.json apps/web/package.json
RUN npm ci

FROM node:20-alpine AS builder
WORKDIR /app
# NEXT_PUBLIC_* 값은 Next.js가 빌드 시점에 클라이언트 번들에 그대로 박아넣는다 — 컨테이너
# 실행 시 env로 넘겨봐야 이미 빌드된 JS에는 반영되지 않으므로 반드시 build-arg로 받는다.
ARG NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_BASE_URL=$NEXT_PUBLIC_API_BASE_URL
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
# turbo(모노레포)가 빌드하면 standalone 출력이 apps/web/ 아래로 중첩된다
# (.next/standalone/apps/web/server.js) — 루트 바로 밑이 아님(실측).
COPY --from=builder /app/apps/web/public ./apps/web/public
COPY --from=builder /app/apps/web/.next/standalone ./
COPY --from=builder /app/apps/web/.next/static ./apps/web/.next/static

EXPOSE 3000
CMD ["node", "apps/web/server.js"]
