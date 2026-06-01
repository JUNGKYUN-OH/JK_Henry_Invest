# Phase 3 — 설계

> **상태**: 확정 (2026-06-01)  
> **기반 문서**: [01_scenarios.md](./01_scenarios.md), [02_requirements.md](./02_requirements.md)

---

## 1. 전체 아키텍처

```
┌─────────────────────────────────────────────────────────┐
│                   Browser (localhost:8501)               │
└───────────────────────────┬─────────────────────────────┘
                            │ HTTP
┌───────────────────────────▼─────────────────────────────┐
│                     UI Layer (Streamlit)                  │
│   pages/: dashboard, ib_guide, vr_guide, trade_entry,   │
│           journal, statistics, settings                  │
│   components.py: 공통 UI 위젯                            │
└────────────┬──────────────────────────────┬─────────────┘
             │                              │
┌────────────▼──────────────┐  ┌────────────▼─────────────┐
│      Service Layer        │  │     Market Layer          │
│   guide_service.py        │  │   price_provider.py       │
│ - IB 가이드 생성           │  │ - yfinance 래퍼           │
│ - VR 가이드 생성           │  │ - 세션 캐시               │
│ - 체결 처리                │  │ - 수동 입력 폴백           │
│ - 통계 집계                │  └────────────┬─────────────┘
└────────────┬──────────────┘               │
             │                              │
┌────────────▼──────────────┐               │
│    Strategy Engine        │◄──────────────┘
│  (순수 함수, 부작용 없음)    │
│  infinite_buying.py       │
│  value_rebalancing.py     │
└────────────┬──────────────┘
             │
┌────────────▼──────────────┐
│    Repository Layer       │
│  repositories.py          │
│  db.py (SQLAlchemy)       │
└────────────┬──────────────┘
             │
┌────────────▼──────────────┐
│   data/jkhenry.db         │
│   (SQLite 단일 파일)        │
└───────────────────────────┘
```

**계층별 책임 원칙**:
- **UI**: 입력 수집 + 결과 표시만. 계산 로직 없음.
- **Service**: 계층 간 조율. Repository → 상태 조회 → Strategy Engine → 결과 반환.
- **Strategy Engine**: 순수 함수. DB·네트워크 접근 없음. 같은 입력 → 항상 같은 출력.
- **Repository**: SQL CRUD만. 비즈니스 로직 없음.
- **Market**: yfinance 호출 + 캐싱만. 계산 없음.

---

## 2. 디렉토리 구조

```
JK_Henry_Invest/
├── app.py                          # Streamlit 진입점 (멀티페이지 라우팅)
├── pyproject.toml                  # 패키지 설정 및 의존성
├── data/
│   └── jkhenry.db                  # SQLite DB 파일 (자동 생성)
├── docs/
│   ├── 01_scenarios.md
│   ├── 02_requirements.md
│   └── 03_design.md
├── src/
│   └── jkhenry/
│       ├── __init__.py
│       ├── config.py               # 전략 파라미터 기본값
│       ├── domain/
│       │   ├── __init__.py
│       │   ├── enums.py            # Strategy, Side, OrderType, CycleStatus, IBPhase
│       │   └── models.py           # Pydantic 모델 (IBState, VRState, OrderGuide, DailyGuide)
│       ├── strategies/
│       │   ├── __init__.py
│       │   ├── infinite_buying.py  # IB (Infinite Buying) V2.2 계산 엔진 (순수 함수)
│       │   └── value_rebalancing.py # VR (Value Rebalancing) 계산 엔진 (순수 함수)
│       ├── market/
│       │   ├── __init__.py
│       │   └── price_provider.py   # yfinance 래퍼 + 세션 캐시
│       ├── repository/
│       │   ├── __init__.py
│       │   ├── db.py               # SQLAlchemy 엔진·세션·테이블 정의
│       │   └── repositories.py     # CRUD 함수
│       ├── services/
│       │   ├── __init__.py
│       │   └── guide_service.py    # 서비스 계층 (조율)
│       └── ui/
│           ├── __init__.py
│           ├── components.py       # 공통 UI 컴포넌트
│           └── pages/
│               ├── 01_대시보드.py
│               ├── 02_포트폴리오_생성.py
│               ├── 03_IB_가이드.py
│               ├── 04_VR_가이드.py
│               ├── 05_체결_입력.py
│               ├── 06_매매_일지.py
│               └── 07_통계.py
└── tests/
    ├── test_infinite_buying.py
    ├── test_value_rebalancing.py
    └── test_repositories.py
```

---

## 3. 데이터 모델 (ERD)

```
Portfolio
─────────────────────────────────────────
id           INTEGER  PK autoincrement
name         TEXT     NOT NULL
ticker       TEXT     NOT NULL
strategy     TEXT     NOT NULL  -- 'IB' | 'VR'
seed_capital TEXT     NOT NULL  -- Decimal 문자열 저장
params       TEXT     NOT NULL  -- JSON 문자열 (전략별 파라미터)
status       TEXT     NOT NULL  -- 'active' | 'inactive'
created_at   TEXT     NOT NULL  -- ISO datetime

        │ 1
        │
        │ N
Cycle  (IB 전용)
─────────────────────────────────────────
id              INTEGER  PK autoincrement
portfolio_id    INTEGER  FK → Portfolio.id
cycle_num       INTEGER  NOT NULL  -- 1, 2, 3 ...
start_date      TEXT     NOT NULL  -- ISO date
end_date        TEXT               -- 종료 시 채워짐
status          TEXT     NOT NULL  -- 'active' | 'completed' | 'loss_cut'
realized_profit TEXT               -- Decimal 문자열
profit_rate     TEXT               -- Decimal 문자열
created_at      TEXT     NOT NULL

        │ 1 (Portfolio)
        │ 1 (Cycle, nullable for VR)
        │
        │ N
Trade  (매수/매도 체결 기록 — 단일 진실 원천)
─────────────────────────────────────────
id           INTEGER  PK autoincrement
portfolio_id INTEGER  FK → Portfolio.id  NOT NULL
cycle_id     INTEGER  FK → Cycle.id      -- VR은 NULL
trade_date   TEXT     NOT NULL  -- ISO date
side         TEXT     NOT NULL  -- 'BUY' | 'SELL'
order_type   TEXT     NOT NULL  -- 'LOC' | 'LIMIT' | 'MARKET'
shares       TEXT     NOT NULL  -- Decimal 문자열
price        TEXT     NOT NULL  -- Decimal 문자열
amount       TEXT     NOT NULL  -- Decimal 문자열 (= shares × price)
note         TEXT               -- 메모 (선택)
created_at   TEXT     NOT NULL

        │ 1 (Portfolio)
        │
        │ N
VrPeriod  (VR 주기별 스냅샷)
─────────────────────────────────────────
id           INTEGER  PK autoincrement
portfolio_id INTEGER  FK → Portfolio.id  NOT NULL
period_num   INTEGER  NOT NULL  -- 1, 2, 3 ...
period_date  TEXT     NOT NULL  -- 해당 주 토요일 ISO date
v_target     TEXT     NOT NULL  -- 이번 주기 목표값 V (Decimal)
cash_balance TEXT     NOT NULL  -- 현금 잔고 C (Decimal)
e_value      TEXT               -- 평가금액 E (체크 시점)
action       TEXT               -- 'BUY' | 'SELL' | 'HOLD'
v_next       TEXT     NOT NULL  -- 다음 주기 목표값
created_at   TEXT     NOT NULL
```

> **Decimal을 TEXT로 저장하는 이유**: SQLite에 REAL(float)로 저장하면 부동소수점 오류가 누적됨.
> Python `Decimal` ↔ `str` 변환으로 정확성을 보장하고 SQLAlchemy TypeDecorator로 자동 처리.

---

## 4. 도메인 모델 (Pydantic)

```python
# domain/enums.py
class Strategy(str, Enum):
    IB = "IB"    # Infinite Buying (무한매수법 V2.2)
    VR = "VR"    # Value Rebalancing (밸류 리밸런싱)

class Side(str, Enum):
    BUY = "BUY"
    SELL = "SELL"

class OrderType(str, Enum):
    LOC = "LOC"
    LIMIT = "LIMIT"
    MARKET = "MARKET"

class CycleStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    LOSS_CUT = "loss_cut"

class IBPhase(str, Enum):
    FIRST_HALF = "전반전"     # 1 ~ half_round
    SECOND_HALF = "후반전"    # half_round+1 ~ 40
    EXHAUSTED = "40회차소진"  # 41회차 이후

# domain/models.py
class IBParams(BaseModel):
    T: int = 45
    half_round: int = 20
    buy_high_multiplier: Decimal = Decimal("1.15")
    sell_target_pct: Decimal = Decimal("0.10")

class VRParams(BaseModel):
    G: Decimal = Decimal("0.005")
    band_upper: Decimal = Decimal("0.20")
    band_lower: Decimal = Decimal("0.20")
    period_days: int = 7

class IBState(BaseModel):
    """전략 엔진 입력: IB 현재 상태"""
    seed: Decimal
    params: IBParams
    current_round: int       # 파생 (trade에서 계산해 전달)
    avg_price: Decimal       # 파생 A
    shares_held: Decimal     # 파생

class VRState(BaseModel):
    """전략 엔진 입력: VR 현재 상태"""
    params: VRParams
    v_target: Decimal        # DB 저장값
    cash_balance: Decimal    # DB 저장값
    shares_held: Decimal     # 파생

class MarketData(BaseModel):
    ticker: str
    prev_close: Decimal      # C: 전일 종가
    current_price: Decimal   # 현재가

class OrderGuide(BaseModel):
    """출력: 주문 1건"""
    label: str               # "작은수 LOC", "큰수 LOC", "매도 LOC"
    price: Decimal
    shares: Decimal
    amount: Decimal
    order_type: OrderType

class IBDailyGuide(BaseModel):
    """출력: IB (Infinite Buying) 하루 가이드"""
    phase: IBPhase
    current_round: int
    unit: Decimal
    buy_orders: list[OrderGuide]
    sell_order: OrderGuide
    messages: list[str]      # 안내 메시지 (전환 알림, 목표가 근접 등)

class VRGuide(BaseModel):
    """출력: VR (Value Rebalancing) 리밸런싱 가이드"""
    v_target: Decimal
    cash_balance: Decimal
    e_value: Decimal
    band_upper: Decimal
    band_lower: Decimal
    action: str              # "BUY" | "SELL" | "HOLD"
    order: OrderGuide | None # HOLD면 None
    messages: list[str]
    v_next: Decimal
```

---

## 5. 전략 엔진 인터페이스

```python
# strategies/infinite_buying.py

def compute_unit(seed: Decimal, T: int) -> Decimal:
    """1회 매수금 U = seed / T"""

def compute_avg_price(trades: list[Trade]) -> Decimal:
    """평단가 A = Σ(매수 amount) / Σ(매수 shares)"""

def compute_shares_held(trades: list[Trade]) -> Decimal:
    """보유 수량 = Σ매수 shares − Σ매도 shares"""

def compute_round(trades: list[Trade]) -> int:
    """현재 회차 = 매수 체결이 있는 고유 날짜 수"""

def determine_phase(current_round: int, half_round: int) -> IBPhase:
    """전반전 / 후반전 / 40회차소진 판별"""

def generate_ib_guide(state: IBState, market: MarketData) -> IBDailyGuide:
    """
    전반전: 작은수 LOC(0.5U, 평단가) + 큰수 LOC(0.5U, C×1.15)
    후반전: A > C 조건 확인 후 평단 LOC 1U (조건 불충족 시 빈 buy_orders)
    40회차소진: 매도 LOC만 안내
    항상: 매도 LOC (평단×1.10, 전량)
    """

# strategies/value_rebalancing.py

def compute_evaluation(shares: Decimal, current_price: Decimal) -> Decimal:
    """E = shares × current_price"""

def determine_vr_action(
    e: Decimal, v: Decimal, band_upper: Decimal, band_lower: Decimal
) -> str:
    """BUY | SELL | HOLD 판정"""

def generate_vr_guide(state: VRState, market: MarketData) -> VRGuide:
    """
    E 계산 → 밴드 판정 → 매수/매도 금액 계산 (현금 한도 적용) → v_next 계산
    """

def compute_v_next(v: Decimal, G: Decimal) -> Decimal:
    """V(다음) = V × (1 + G)"""
```

---

## 6. 화면 와이어프레임

### P-01. 대시보드

```
┌────────────────────────────────────────────────────────────┐
│ 💼 JK Henry Invest                       [+ 새 포트폴리오]  │
├────────────────────────────────────────────────────────────┤
│  ┌───────────────────────┐  ┌───────────────────────┐      │
│  │ TQQQ                  │  │ QQQ                   │      │
│  │ IB (Infinite Buying)  │  │ VR (Value Rebalancing)│      │
│  │───────────────────────│  │───────────────────────│      │
│  │ 전반전 12 / 20회차    │  │ V  $10,200            │      │
│  │ 평단가  $62.10        │  │ E  $11,500  ▲상단     │      │
│  │ 현재가  $64.30        │  │ C  $5,000             │      │
│  │ 손익    +3.5% ✅      │  │ 매도 가이드 ⚠️        │      │
│  │         [가이드 보기]  │  │        [가이드 보기]  │      │
│  └───────────────────────┘  └───────────────────────┘      │
└────────────────────────────────────────────────────────────┘
```

---

### P-02. 포트폴리오 생성

```
┌────────────────────────────────────────────────────────────┐
│ 새 포트폴리오 생성                                           │
├────────────────────────────────────────────────────────────┤
│  이름          [TQQQ 무한매수              ]                │
│  티커          [TQQQ                      ]                │
│  투자 기법     ( IB (Infinite Buying)  ● )                 │
│               ( VR (Value Rebalancing) ○ )                 │
│                                                            │
│  ── IB (Infinite Buying) 설정 ────────────────────────     │
│  총 시드 (USD) [4,500                     ]                │
│  분할 횟수     [45   ] (1unit = $100.00)                   │
│  전반전 경계   [20   ] 회차                                 │
│  큰수 배율     [1.15 ] (전일 종가 × 배율)                   │
│  매도 목표     [0.10 ] (+10%)                              │
│                                                            │
│                          [취소]    [생성]                   │
└────────────────────────────────────────────────────────────┘
```

---

### P-03. IB (Infinite Buying) 가이드

```
┌────────────────────────────────────────────────────────────┐
│ TQQQ — IB (Infinite Buying) 가이드                         │
│                    ◀ 전반전  12 / 20회차 ▶                 │
│ 전일 종가: $61.20   평단가: $62.10   1unit: $100.00        │
├─────────────────────────┬──────────────────────────────────┤
│  📥 오늘 매수 주문        │  📤 매도 LOC (매일 유지)          │
├─────────────────────────┼──────────────────────────────────┤
│  작은수 LOC              │  가격:  $68.31 (평단 +10%)        │
│  가격:  $62.10 (평단가)  │  수량:  32.14주 (전량)            │
│  수량:  0.80주           │  유형:  LOC                       │
│  금액:  $50.00           │                                  │
│                         │  ─────────────────────────────   │
│  큰수 LOC                │  💡 현재가 $64.30                │
│  가격:  $70.38           │     목표가까지 +6.2% 남음         │
│         (종가 × 1.15)    │                                  │
│  수량:  0.71주           │                                  │
│  금액:  $50.00           │                                  │
├─────────────────────────┤                                  │
│  합계:  $100.00 (1unit)  │                                  │
└─────────────────────────┴──────────────────────────────────┘
│  [체결 입력하기]          시세 갱신: 2026-06-01 09:32        │
└────────────────────────────────────────────────────────────┘
```

> **후반전 + 조건 불충족 시** (A ≤ C):
> ```
> 📥 오늘 매수 없음
> 평단가($62.10) ≤ 전일 종가($63.00) — 후반전 진입 조건 미충족
> ```

---

### P-04. VR (Value Rebalancing) 가이드

```
┌────────────────────────────────────────────────────────────┐
│ QQQ — VR (Value Rebalancing) 가이드                        │
│                              기준일: 2026-05-31 (토)       │
├────────────────────────────────────────────────────────────┤
│   목표값 V   $10,200.00     현금 C    $5,000.00            │
│   평가금액 E $11,500.00     다음 V    $10,251.00           │
├────────────────────────────────────────────────────────────┤
│   하단 $8,160          V $10,200       상단 $12,240        │
│   ────────[▼]─────────────[●]──────────────[▲]────────    │
│                                          ★ E $11,500       │
├────────────────────────────────────────────────────────────┤
│   판정: 밴드 내 ✅ — 이번 주는 매수/매도 없음                │
│                                                            │
│   [주기 완료 처리 (V 갱신)]                                 │
└────────────────────────────────────────────────────────────┘
```

> **상단 이탈 시**:
> ```
> 판정: 상단 이탈 ⚠️
> 📤 매도 가이드
>   매도 금액: $1,300.00  (E - V)
>   매도 수량: 2.86주  (@$455.50)
>   주문 유형: 지정가 또는 시장가
> ```

---

### P-05. 체결 입력

```
┌────────────────────────────────────────────────────────────┐
│ 체결 기록 입력 — TQQQ / IB (Infinite Buying)               │
├────────────────────────────────────────────────────────────┤
│  날짜        [2026-06-01        ▼]                         │
│  구분        ( 매수 ●)  ( 매도 ○)                          │
│  주문 유형   [LOC              ▼]                          │
│  체결 수량   [0.80              ]  주                      │
│  체결 단가   [62.10             ]  USD                     │
│  금액 (자동) $49.68                                        │
│  메모        [                  ]  (선택)                  │
│                                                            │
│  미체결 건은 입력하지 않습니다 (회차 유지됨)                 │
│                                                            │
│              [취소]      [저장]                            │
├────────────────────────────────────────────────────────────┤
│  저장 후 → 평단가: $62.10  보유: 32.14주  13회차           │
└────────────────────────────────────────────────────────────┘
```

---

### P-06. 매매 일지

```
┌────────────────────────────────────────────────────────────┐
│ 매매 일지                                                   │
│ 포트폴리오: [전체 ▼]   기간: [2026-01-01] ~ [2026-06-01]   │
├────┬────────────┬───────┬──────────────────────┬──────┬────┤
│ ID │ 날짜        │ 종목  │ 기법                  │ 구분  │ 수량│
├────┼────────────┼───────┼──────────────────────┼──────┼────┤
│ 45 │ 2026-06-01 │ TQQQ │ IB (Infinite Buying) │ 매수  │0.80│
│ 44 │ 2026-05-31 │ TQQQ │ IB (Infinite Buying) │ 매수  │0.71│
│ 43 │ 2026-05-30 │ QQQ  │ VR (Value Rebalancing)│ 매도  │2.86│
├────┴────────────┴───────┴──────────────────────┴──────┴────┤
│                                          [CSV 내보내기]     │
└────────────────────────────────────────────────────────────┘
```

---

### P-07. 통계

```
┌────────────────────────────────────────────────────────────┐
│ 수익률 통계                                                  │
│ [TQQQ — IB (Infinite Buying)          ▼]                   │
├───────────────────┬────────────────────────────────────────┤
│ 완료 사이클        │  5회                                   │
│ 수익 사이클        │  4회 (승률 80%)                        │
│ 누적 손익          │ +$1,240.50                             │
│ 평균 수익률/사이클  │ +8.3%                                  │
├───────────────────┴────────────────────────────────────────┤
│ 사이클 │ 기간                    │ 수익금    │ 수익률        │
├────────┼─────────────────────────┼───────────┼──────────────┤
│   5    │ 2026-04-01 ~ 2026-05-20 │ +$320.00  │ +10.2%       │
│   4    │ 2026-02-10 ~ 2026-03-28 │ +$298.50  │  +9.8%       │
│   3    │ 2025-11-01 ~ 2026-01-15 │  -$180.00 │  -5.9% ❌    │
└────────────────────────────────────────────────────────────┘
```

---

## 7. 핵심 기술 결정사항

| 항목 | 결정 | 이유 |
|------|------|------|
| Decimal 저장 | SQLite TEXT로 저장, TypeDecorator로 자동 변환 | float 부동소수점 오류 방지 |
| 평단가·회차 계산 | 매번 trade에서 파생 계산 (DB 저장 안 함) | 단일 진실 원천, 체결 수정 시 자동 반영 |
| 시세 캐시 | `st.session_state`에 저장 (Streamlit 세션 단위) | 화면 이동 시 중복 API 호출 방지 |
| 전략 엔진 | 순수 함수 (외부 의존 없음) | 단위테스트 독립 실행 가능 |
| Streamlit 멀티페이지 | `pages/` 디렉토리 컨벤션 사용 | 별도 라우팅 코드 불필요 |
| ORM | SQLAlchemy Core (테이블 정의) + 직접 쿼리 | 추상화 최소화, 단순성 우선 |
| UI 기법 표기 | "IB (Infinite Buying)", "VR (Value Rebalancing)" | 약자만 쓰면 의미 불명확 |

---

> **Phase 3 확정 → Phase 4 구현으로 진행 가능합니다.**
