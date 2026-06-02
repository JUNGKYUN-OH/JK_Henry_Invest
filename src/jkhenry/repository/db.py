"""SQLAlchemy 엔진, 세션, 테이블 정의."""

from decimal import Decimal
from pathlib import Path

import sqlalchemy as sa
from sqlalchemy import Column, ForeignKey, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Session

# DB 파일 위치: 프로젝트 루트 / data / jkhenry.db
# db.py 위치: src/jkhenry/repository/db.py → parents[3] = 프로젝트 루트
_PROJECT_ROOT = Path(__file__).parents[3]
DB_PATH = _PROJECT_ROOT / "data" / "jkhenry.db"


def _get_db_url() -> tuple[str, bool]:
    """
    (DB URL, is_remote) 반환.
    Streamlit secrets에 [turso] 설정이 있으면 libSQL(Turso) URL,
    없으면 로컬 SQLite URL. pytest 등 비-Streamlit 환경에서도 안전하게 동작.
    """
    try:
        import streamlit as st
        turso = st.secrets.get("turso", {})
        url = turso.get("url", "")
        token = turso.get("auth_token", "")
        if url and token:
            # sqlalchemy-libsql은 sqlite+libsql:// 프리픽스 + secure=true 필요
            if url.startswith("libsql://"):
                url = "sqlite+libsql://" + url[len("libsql://"):]
            sep = "&" if "?" in url else "?"
            return f"{url}{sep}authToken={token}&secure=true", True
    except RuntimeError:
        raise
    except Exception:
        pass
    return f"sqlite:///{DB_PATH}", False


def get_engine(db_path: Path | None = None) -> sa.Engine:
    if db_path is not None:
        # 테스트 등 명시적 경로 지정 시 로컬 SQLite 사용
        db_path.parent.mkdir(parents=True, exist_ok=True)
        return create_engine(f"sqlite:///{db_path}", echo=False)

    url, is_remote = _get_db_url()
    if not is_remote:
        # 로컬 SQLite: data/ 디렉터리 자동 생성
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return create_engine(url, echo=False)


class DecimalText(sa.TypeDecorator):
    """Decimal을 TEXT로 저장하여 부동소수점 오류 방지."""

    impl = sa.Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        return str(value) if value is not None else None

    def process_result_value(self, value, dialect):
        return Decimal(value) if value is not None else None


class Base(DeclarativeBase):
    pass


class PortfolioModel(Base):
    __tablename__ = "portfolio"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    ticker = Column(String, nullable=False)
    strategy = Column(String, nullable=False)   # 'IB' | 'VR'
    seed_capital = Column(DecimalText, nullable=False)
    params = Column(Text, nullable=False)        # JSON 문자열
    status = Column(String, nullable=False, default="active")
    created_at = Column(String, nullable=False)


class CycleModel(Base):
    __tablename__ = "cycle"

    id = Column(Integer, primary_key=True, autoincrement=True)
    portfolio_id = Column(Integer, ForeignKey("portfolio.id"), nullable=False)
    cycle_num = Column(Integer, nullable=False)
    start_date = Column(String, nullable=False)
    end_date = Column(String)
    status = Column(String, nullable=False, default="active")
    realized_profit = Column(DecimalText)
    profit_rate = Column(DecimalText)
    created_at = Column(String, nullable=False)


class TradeModel(Base):
    __tablename__ = "trade"

    id = Column(Integer, primary_key=True, autoincrement=True)
    portfolio_id = Column(Integer, ForeignKey("portfolio.id"), nullable=False)
    cycle_id = Column(Integer, ForeignKey("cycle.id"))   # VR은 NULL
    trade_date = Column(String, nullable=False)
    side = Column(String, nullable=False)        # 'BUY' | 'SELL'
    order_type = Column(String, nullable=False)  # 'LOC' | 'LIMIT' | 'MARKET'
    shares = Column(DecimalText, nullable=False)
    price = Column(DecimalText, nullable=False)
    amount = Column(DecimalText, nullable=False)
    note = Column(String)
    created_at = Column(String, nullable=False)


class VrPeriodModel(Base):
    __tablename__ = "vr_period"

    id = Column(Integer, primary_key=True, autoincrement=True)
    portfolio_id = Column(Integer, ForeignKey("portfolio.id"), nullable=False)
    period_num = Column(Integer, nullable=False)
    period_date = Column(String, nullable=False)
    v_target = Column(DecimalText, nullable=False)
    cash_balance = Column(DecimalText, nullable=False)
    e_value = Column(DecimalText)
    action = Column(String)                      # 'BUY' | 'SELL' | 'HOLD'
    v_next = Column(DecimalText, nullable=False)
    created_at = Column(String, nullable=False)


def init_db(engine: sa.Engine | None = None) -> sa.Engine:
    """테이블이 없으면 생성한다. 앱 시작 시 1회 호출."""
    eng = engine or get_engine()
    Base.metadata.create_all(eng)
    return eng


def get_session(engine: sa.Engine | None = None) -> Session:
    return Session(engine or get_engine())
