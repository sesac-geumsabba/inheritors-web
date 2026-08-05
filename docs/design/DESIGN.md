# DESIGN.md — "상속자들" 서비스 디자인 시스템 및 화면 명세

> 본 문서는 `docs/design/` 내 3개 HTML 화면 디자인 파일 (`page1.html`, `page2.html`, `page3.html`)의 코드 및 스타일 정의만을 기반으로 작성되었습니다.

---

## 1. 디자인 시스템 (Design System)

### 1.1 디자인 컨셉 & 테마
- **모바일 퍼스트 (Mobile-First Frame)**: 최대 너비 430px~480px (챗봇 720px) 중심의 모바일 뷰포트 레이아웃.
- **시니어 친화적 UX (Senior-Friendly UX)**: 고대비 타이포그래피, 가독성 높은 폰트 사이즈, 화면 상단 글자 크기 조절 옵션(`+글자 크게`, `-글자 작게`), 터치 영역 확보.
- **브랜드 정체성**: '상속자들' 핑크(`brand-pink`: `#F52D81`) 및 Soft Pink 계열 포인트 사용.

---

### 1.2 디자인 토큰 (Design Tokens / Tailwind Config)

#### Colors (컬러 팔레트)
| Token Name | Color Code (HEX/RGBA) | Description / Usage |
|---|---|---|
| `brand-pink` | `#F52D81` | 브랜드 주요 강조색, 메인 CTA 버튼 |
| `brand-pink-light` | `#FDE8F0` | 카드/섹션 연한 핑크 배경 |
| `primary` | `#b6005a` | 주요 텍스트 & 테마 컬러 |
| `primary-container` | `#e01572` | 챗봇 아이콘 및 주요 컨테이너 포인트 |
| `background` / `surface` | `#fcf9f8` | 기본 화면 배경색 |
| `surface-container-lowest` | `#ffffff` | 순백색 카드/입력창/채팅 배경 |
| `surface-container` | `#f0eded` | 사용자 말풍선 및 로딩 타일 배경 |
| `surface-container-high` | `#eae7e7` | 챗봇 말풍선 배경 |
| `on-surface` | `#1c1b1b` | 본문 기본 텍스트 색상 |
| `on-surface-variant` | `#5a3f46` | 부가 설명/서브 텍스트 색상 |
| `outline-variant` | `#e2bdc5` | 테두리 및 구분선 (Opacity 결합) |
| `error` | `#ba1a1a` | 경고/위험 요소 아이콘 및 강조 |
| `secondary-container` | `#fe9d00` | 주의 요소 아이콘 (노랑/오렌지) |

#### Typography & Fonts (타이포그래피)
- **Primary Fonts**: `Be Vietnam Pro` (제목/헤드라인), `Noto Sans KR` (본문/라벨)
- **Font Sizes**:
  - `headline-lg`: 32px (lineHeight: 44px, Bold)
  - `headline-lg-mobile`: 28px (lineHeight: 38px, Bold)
  - `headline-md`: 24px (lineHeight: 34px, Bold)
  - `body-lg`: 20px (lineHeight: 30px, Medium)
  - `body-md`: 18px (lineHeight: 28px, Regular)
  - `label-lg`: 16px (lineHeight: 24px, Bold)
  - `label-sm`: 14px (lineHeight: 20px, Medium)

#### Spacing & Components (간격 및 버튼 타겟)
- `touch-target-min`: `56px` (최소 터치 높이)
- `container-padding`: `24px` (기본 좌우 패딩)
- `stack-gap-md`: `20px` / `stack-gap-lg`: `32px`
- `gutter`: `16px`

---

## 2. 공통 UI 컴포넌트 명세

### 2.1 상단 앱바 (TopAppBar)
- 좌측: 메뉴 아이콘 (`menu`) 및 서비스명 **"상속자들"** 브랜드 타이틀 (`#e01572` 또는 `#F52D81`).
- 우측: 시니어 가독성 배려를 위한 `+글자 크게`, `-글자 작게` 조절 버튼 2종 제공.

### 2.2 하단 네비게이션 바 (BottomNavBar)
- 4개 탭 구조:
  1. **내 정보** (`person`)
  2. **챗봇** (`chat`)
  3. **리포트** (`description`)
  4. **뒤로가기** (`arrow_back`)
- 현재 활성화된 탭은 브랜드 컬러 배경(`primary-container` 또는 `brand-pink`) 처리 및 스케일 강조 효과.

---

## 3. 화면별 구성 & 디자인 명세

### 3.1 화면 1: 온보딩 화면 (`page1.html`)
- **타이틀**: `상속자들 - 온보딩`
- **핵심 컴포넌트 & 인터랙션**:
  1. **TopAppBar**: 브랜드 타이틀 "상속자들" 노출.
  2. **ScrollExpand 카드 섹션**:
     - 스크롤 진행도에 맞춰 카드의 패딩, 테두리 라운드, 배경색이 동적으로 확장 변형되는 인터랙션 포함.
     - 메인 그래픽 미디어 및 스크롤 힌트(`keyboard_arrow_down`) 바운스 애니메이션 제공.
     - 스크롤에 따라 "안전하고 편안한 상속 준비" 타이틀 패드인 노출.
  3. **환영 메시지**:
     - `brand-pink-light/50` 배경의 라운드 카드 안 "안녕하세요! 안전하고 편안한 상속 준비, 상속자들이 도와드릴게요." 안내.
  4. **하단 고정 CTA 버튼**:
     - `brand-pink` 색상 Full-Width 버튼 "시작하기" + 우측 화살표 아이콘 (`arrow_forward`).

---

### 3.2 화면 2: 챗봇 대화 화면 (`page2.html`)
- **타이틀**: `상속자들 - 챗봇`
- **핵심 컴포넌트**:
  1. **챗봇 아바타 ('느리')**:
     - 원형 프로필 아바타 이미지 + 캐릭터 명칭 "상속자들" 표기.
  2. **대화 말풍선**:
     - **챗봇 메시지**: 좌측 `surface-container-high` 배경, 라운드 카드 (좌상단 모서리 직각).
     - **사용자 메시지**: 우측 `surface-container` 배경, 라운드 카드 (우하단 모서리 직각).
  3. **퀵 추천 질문 태그 (Quick Response Buttons)**:
     - 분홍색 테두리 캡슐형 버튼: `판례 조회`, `신탁 내용 검색`, `맞춤 상담 신청`.
  4. **실시간 타이핑 인디케이터 (Typing Indicator)**:
     - 챗봇 응답 대기 시 점 3개가 펄스 애니메이션되는 로딩 요소.
  5. **하단 입력 영역 (Chat Input Area)**:
     - 파일/기능 추가 버튼(`add`), 다중행 지원 입력창(`textarea`), 전송 버튼(`send`).

---

### 3.3 화면 3: 자산승계 리포트 화면 (`page3.html`)
- **타이틀**: `자산승계 리포트`
- **핵심 컴포넌트**:
  1. **페이지 헤더**: "자산승계 리포트" 제목 및 분석 요약 서문.
  2. **현재 자산 현황 요약 카드**:
     - `account_balance` 아이콘 헤더.
     - 부동산(아파트), 현금 및 예금 항목별 금액 표시 및 구분선.
     - 총 추정 자산 강조 (예: `약 15억 원`).
  3. **법률적 위험 요소 (주의) 카드**:
     - `warning` 및 `priority_high` 빨간색 아이콘 강조.
     - 유류분 반환 청구 소송 위험, 상속세 납부 재원 부족 등 위험 목록 분리 제시.
  4. **하단 네비게이션 바 (BottomNavBar)**:
     - 컨테이너 맨 최하단 고정 배치 (`shrink-0 w-full`).
     - 내 정보, 챗봇, 리포트(활성화 강조), 뒤로가기 버튼 구성.