# JK Henry Invest

IB(무한매수법 V2.2)와 VR(밸류 리밸런싱) 전략을 지원하는 개인용 투자 대시보드.

---

## 외부 시스템 구성

이 프로젝트는 아래 5개의 외부 시스템으로 구성됩니다.

### 1. Streamlit Cloud — 앱 호스팅
- **역할**: Python 앱을 웹 브라우저에서 실행할 수 있도록 무료로 배포
- **URL**: https://jkhenryinvest.streamlit.app
- **관리**: https://share.streamlit.io
- **핵심 설정**: `Secrets` 탭에서 DB 연결 정보, Google OAuth 키 관리
- **연동**: GitHub 저장소의 `main` 브랜치에 push하면 자동 재배포

### 2. GitHub — 소스코드 저장소
- **역할**: 소스코드 버전 관리 및 Streamlit Cloud 배포 트리거
- **저장소**: https://github.com/JUNGKYUN-OH/JK_Henry_Invest
- **브랜치**: `main` (배포 브랜치)
- **연동**: push → Streamlit Cloud 자동 재배포

### 3. Turso — 원격 데이터베이스
- **역할**: 포트폴리오·매매 기록·사용자 세션을 영구 저장하는 SQLite 호환 DB
- **관리**: https://app.turso.tech
- **DB 이름**: `jkhenryinvest`
- **드라이버**: `libsql-experimental` (Python)
- **연동**: `src/jkhenry/repository/db.py`에서 연결, Streamlit Secrets의 `[turso]` 섹션에서 URL·토큰 주입
- **테이블**:
  - `portfolio` — 포트폴리오 목록
  - `cycle` — IB 사이클 기록
  - `trade` — 체결 기록
  - `vr_period` — VR 기간별 기록
  - `user_session` — Google 로그인 세션 (30일 만료)

### 4. Google Cloud — OAuth 인증
- **역할**: Google 계정으로 로그인하는 OAuth 2.0 인증 제공
- **관리**: https://console.cloud.google.com
- **프로젝트**: `My First Project` (또는 생성한 프로젝트명)
- **설정 경로**: API 및 서비스 → 사용자 인증 정보 → OAuth 2.0 클라이언트
- **승인된 리디렉션 URI**:
  - `https://jkhenryinvest.streamlit.app/` (운영)
  - `https://jkhenryinvest.streamlit.app/oauth2callback` (구버전 호환)
- **연동**: Streamlit Secrets의 `[auth.google]` 섹션에 client_id·client_secret 저장

### 5. yfinance — 시세 데이터
- **역할**: Yahoo Finance API를 통해 ETF·주식 실시간/과거 시세 조회
- **라이브러리**: `yfinance`
- **연동**: `src/jkhenry/market/price_provider.py`

---

## 인증 흐름

```
사용자 → Google 로그인 버튼 클릭
       → Google OAuth 인증 화면
       → 인증 완료 → 앱으로 리디렉션 (?code=...)
       → 앱이 code를 access_token으로 교환 (httpx)
       → Google에서 이메일·이름 조회
       → Turso DB에 세션 토큰 저장 (30일)
       → URL에 ?_s=TOKEN 유지
       → F5 새로고침 시 URL 토큰 → Turso DB 검증 → 자동 로그인
```

---

## Streamlit Secrets 구조

Streamlit Cloud `Settings → Secrets`에 아래 형식으로 등록:

```toml
[auth]
redirect_uri  = "https://jkhenryinvest.streamlit.app/"
cookie_secret = "<랜덤 32자 문자열>"

[auth.google]
client_id     = "<Google OAuth 클라이언트 ID>"
client_secret = "<Google OAuth 클라이언트 보안 비밀>"
server_metadata_url = "https://accounts.google.com/.well-known/openid-configuration"

[allowed_users]
emails = ["<허용할 Google 이메일>"]

[turso]
url        = "libsql://<db명>-<계정>.aws-ap-northeast-1.turso.io"
auth_token = "<Turso 발급 JWT 토큰>"
```

---

## 사용자 추가 방법

새로운 Google 계정에 접근 권한을 부여하려면 **두 곳** 을 모두 수정해야 합니다.

### Step 1 — Google Cloud에 테스트 사용자 등록

> 앱 소유자 계정은 자동 허용되므로 등록 불필요. 다른 사람 계정만 추가.

1. [console.cloud.google.com](https://console.cloud.google.com) 접속
2. 왼쪽 상단 햄버거 메뉴 → **API 및 서비스** 선택
3. **OAuth 동의 화면** 선택
4. 왼쪽 메뉴 **대상** 클릭
5. 스크롤 내려 **테스트 사용자** 섹션 → **사용자 추가**
6. 추가할 Google 이메일 입력 → 저장

### Step 2 — Streamlit Cloud Secrets에 이메일 추가

1. [share.streamlit.io](https://share.streamlit.io) → 앱 → **Settings → Secrets**
2. `[allowed_users]` 섹션에 이메일 추가

```toml
[allowed_users]
emails = [
  "jungkyun98@googlemail.com",
  "추가할계정@gmail.com"
]
```

3. **Save** 클릭 → 즉시 적용 (재배포 불필요)

### 두 설정의 역할

| 설정 | 역할 | 누락 시 |
|------|------|---------|
| Google Cloud 테스트 사용자 | Google이 해당 계정의 로그인 자체를 허용 | Google 화면에서 "액세스 차단됨" 오류 |
| Streamlit Secrets `allowed_users` | 앱이 로그인 후 접근 권한 검증 | 로그인은 되지만 앱에서 "접근 권한 없음" 표시 |

---

## 로컬 개발

```bash
# 의존성 설치
pip install -r requirements.txt

# 실행 (Secrets 없으면 인증 없이 동작)
streamlit run app.py
```

로컬에서 `.streamlit/secrets.toml`을 생성하면 Turso·Google 연동도 테스트 가능.
이 파일은 `.gitignore`에 의해 커밋되지 않습니다.

---

## 기술 스택

| 분류 | 라이브러리 |
|------|-----------|
| 프레임워크 | Streamlit |
| DB ORM | SQLAlchemy |
| DB 드라이버 | libsql-experimental (Turso) |
| HTTP 클라이언트 | httpx (OAuth 토큰 교환) |
| 시세 조회 | yfinance |
| 데이터 처리 | pandas, pydantic |
