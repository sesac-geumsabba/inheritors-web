# 배포

EC2(Ubuntu) + nginx + Let's Encrypt + Docker Compose. 이미지는 GitHub Actions가
빌드해서 GHCR(GitHub Container Registry)에 올리고, EC2는 그 이미지를 pull만 해서 띄운다.

## 1. 도메인 + HTTPS

1. 도메인 등록기관(가비아/Route53 등)에서 A 레코드 2개를 EC2 Elastic IP로 연결:
   - `theinheritors.site`
   - `www.theinheritors.site`
2. EC2 보안그룹 인바운드에 `80`, `443` (0.0.0.0/0) 허용.
3. nginx + certbot 설치, site 활성화:
   ```bash
   sudo apt update && sudo apt install -y nginx certbot python3-certbot-nginx
   sudo cp infra/nginx/web.conf /etc/nginx/sites-available/web
   sudo ln -s /etc/nginx/sites-available/web /etc/nginx/sites-enabled/
   sudo rm -f /etc/nginx/sites-enabled/default   # 있으면 server_name 매칭을 가로챌 수 있음
   sudo nginx -t && sudo systemctl reload nginx
   ```
4. 인증서 발급 (nginx 플러그인이 443/ssl 설정과 갱신 타이머까지 자동 처리):
   ```bash
   sudo certbot --nginx -d theinheritors.site -d www.theinheritors.site
   sudo certbot renew --dry-run   # 자동 갱신 확인용, 선택
   ```

`web.conf`는 `/api/`도 백엔드(8000)로 프록시한다 — 프론트가 `https://`로 뜨는데
브라우저가 `http://<IP>:8000`을 직접 부르면 mixed content로 막히기 때문에, 같은
origin(`https://www.theinheritors.site/api/...`)을 거치도록 강제한 것. 이 값은
아래 CI의 `NEXT_PUBLIC_API_BASE_URL` 빌드값과 반드시 짝이 맞아야 한다.

## 2. 이미지 빌드/버전관리 (CI)

`.github/workflows/build-images.yml` — `staging` 브랜치로 PR을 열거나 커밋을 push할
때마다 web/api 이미지를 각각 빌드해서 GHCR에 두 태그로 push:

- `<run_number>-<short_sha>` — 이 빌드를 유일하게 가리키는 버전 태그. 특정 버전 고정 배포/롤백용.
- `staging` — 이 워크플로가 마지막으로 성공한 빌드를 가리키는 floating 태그. 평소 배포는 이걸 pull.

**필요한 저장소 설정** (최초 1회, GitHub repo → Settings):
- Settings → Actions → General → Workflow permissions → **Read and write permissions**
  (GITHUB_TOKEN으로 GHCR에 push하려면 필요)
- 첫 push 후 repo → Packages에 `inheritors-web`, `inheritors-api` 패키지가 생성됨.
  기본은 private이므로 EC2에서 pull하려면 패키지를 public으로 바꾸거나(간단) 아래처럼
  PAT으로 로그인.

## 3. EC2에 배포

### 최초 1회 수동 설정

GHCR가 private인 경우만 로그인:
```bash
docker login ghcr.io -u <github-id> -p <PAT: read:packages 권한>
```

`infra/docker-compose.prod.yml` 사용. 로컬 dev용 `infra/docker-compose.yml`은 소스에서
직접 build하지만, 이건 CI가 만든 이미지를 pull만 한다 — EC2에서 Next.js/Python을 매번
빌드하면 느리고 저사양 인스턴스는 OOM 위험도 있다.

```bash
cd infra
cat > .env.prod <<EOF
GHCR_OWNER=sesac-geumsabba
WEB_TAG=staging
API_TAG=staging
EOF

docker compose --env-file .env.prod -f docker-compose.prod.yml pull
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d
```

포트: 프론트 3100→3100, 백엔드 8000→8000, DB는 컨테이너 없이
Supabase 등 외부 인스턴스를 `apps/api/.env`의 `DATABASE_URL`로 연결. (Ollama는 OpenAI
마이그레이션 이후 코드에서 더 이상 참조하지 않아 이 compose에도 없음.)

### 이후는 자동 배포 (CD)

`build-images.yml`의 `deploy` job이 이미지 build/push가 끝나면 SSH로 EC2에 붙어
위 `pull` + `up -d` 두 줄을 그대로 실행한다. `.env.prod`는 최초 설정 때 만든 게 그대로
쓰이므로(태그가 항상 `staging` 고정) 매번 다시 만들 필요 없음.

**필요한 GitHub repo secrets** (Settings → Secrets and variables → Actions):
- `EC2_HOST` — EC2 퍼블릭 IP 또는 도메인
- `EC2_SSH_USER` — 보통 `ubuntu`
- `EC2_SSH_KEY` — EC2 접속용 **배포 전용** SSH 프라이빗 키 전체 내용
  (새로 하나 파서: `ssh-keygen -t ed25519 -f deploy_key -N ""` → 공개키(`deploy_key.pub`)는
  EC2 `~/.ssh/authorized_keys`에 추가, 개인키(`deploy_key`) 내용을 이 secret에 붙여넣기.
  개인 노트북 키를 그대로 쓰지 말 것 — 유출 시 회수 범위가 커짐)
- `EC2_APP_DIR` — EC2에서 리포를 clone해둔 경로 (예: `/home/ubuntu/inheritors-web`)

주의: 트리거가 `pull_request → staging`이라 PR을 열거나 push할 때마다(머지 전에도) 이
파이프라인이 돌아 `staging` 태그가 갱신되고 EC2에 바로 반영된다 — 리뷰 전 공유 스테이징
환경이라는 전제. 머지된 것만 배포하고 싶으면 트리거를 `push: branches: [staging]`으로
바꾸면 됨.

**특정 버전 고정 배포 / 롤백**: EC2에서 `.env.prod`의 `WEB_TAG`/`API_TAG`를 원하는
`<run_number>-<short_sha>` 값으로 바꾸고 `pull` → `up -d`를 수동으로 다시 실행하면 됨
(자동 배포는 항상 `staging` 태그를 따라가므로 롤백 중엔 자동 배포를 잠시 꺼두지 않으면
다음 PR push 때 다시 최신으로 덮어써짐).

## 4. 배포 확인

```bash
docker compose -f docker-compose.prod.yml ps
curl -I https://www.theinheritors.site
```

## 관련 파일

- [infra/nginx/web.conf](../infra/nginx/web.conf) — 프론트(`/`) + 백엔드(`/api/`) 리버스 프록시
- [infra/docker-compose.yml](../infra/docker-compose.yml) — 로컬 dev (소스 build)
- [infra/docker-compose.prod.yml](../infra/docker-compose.prod.yml) — EC2 배포 (이미지 pull)
- [.github/workflows/build-images.yml](../.github/workflows/build-images.yml) — 이미지 빌드/푸시 + EC2 자동 배포 CI/CD
