# JK Henry Invest — Claude 작업 지침

## 프로젝트 개요

IB(무한매수법 V2.2)와 VR(밸류 리밸런싱) 전략을 지원하는 Streamlit 대시보드 앱.

## 커밋 & 푸쉬 규칙

**주요 Feature가 완성될 때마다 반드시 커밋을 생성한다.**

- 커밋 타이밍: 기능 단위가 완성되는 시점 (버그픽스 포함)
- 커밋 메시지: `feat:` / `fix:` / `refactor:` 등 conventional commit 형식
- 푸쉬: 커밋 후 사용자에게 푸쉬 여부를 묻거나, 사용자가 요청하면 즉시 실행
- remote: `origin` → `https://github.com/JUNGKYUN-OH/JK_Henry_Invest.git` (main 브랜치)

## 기술 스택

- Python + Streamlit
- SQLite (data/jkhenry.db) — 런타임 생성, git 제외
- yfinance (시세 조회)

## 전략 규칙 요약

- **IB 매수**: LOC 주문 (전반전 작은수/큰수 각 0.5U, 후반전 1U 올인)
- **IB 매도**: LOC, 평단+10%, 전량, 매일 상시 유지
- **VR 매수/매도**: LIMIT 주문, 주 1회(토요일 오전, 금요일 종가 기준)
