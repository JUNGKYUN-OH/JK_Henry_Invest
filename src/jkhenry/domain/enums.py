from enum import Enum


class Strategy(str, Enum):
    IB = "IB"  # Infinite Buying (무한매수법 V2.2)
    VR = "VR"  # Value Rebalancing (밸류 리밸런싱)


class Side(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    LOC = "LOC"               # Limit On Close (매수)
    AFTER_LIMIT = "AFTER_LIMIT"  # 장후 지정가 (매도)
    LIMIT = "LIMIT"
    MARKET = "MARKET"


class CycleStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    LOSS_CUT = "loss_cut"


class PortfolioStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class IBPhase(str, Enum):
    FIRST_HALF = "전반전"
    SECOND_HALF = "후반전"
    EXHAUSTED = "40회차소진"
