# ---------- imports ----------
import streamlit as st
import requests
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from streamlit_autorefresh import st_autorefresh
from dotenv import load_dotenv
from pathlib import Path
import os
from sqlalchemy import create_engine

# ✅ Streamlit 설정은 가장 먼저
st.set_page_config(page_title="AI 기반 공항 디지털 트윈 대시보드", page_icon="🛫", layout="wide")

# ✅ 자동 새로고침
st_autorefresh(interval=10_000, key="auto_refresh")

# ✅ .env 로드 및 DB 연결
ENV_PATH = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=ENV_PATH)

db_url = os.getenv("DATABASE_URL")

if not db_url:
    st.error("❌ DATABASE_URL이 비어있습니다. .env 위치/내용을 확인하세요.")
    st.stop()

# ✅ 여기서 text를 import (try 밖에서!)
from sqlalchemy import text

try:
    # DB 연결
    engine = create_engine(db_url, pool_pre_ping=True, future=True)
    
    # DB 연결 테스트 및 테이블 목록 출력
    with engine.connect() as conn:
        result = conn.execute(text("SHOW TABLES;"))
        tables = [row[0] for row in result]
        st.sidebar.write("📂 데이터베이스 테이블:", tables)

except Exception as e:
    st.sidebar.error(f"DB 연결 실패: {e}")
except Exception as e:
    st.sidebar.error(f"DB 연결 실패: {e}")

# ---------- 공통 스타일 ----------
PALETTE = ["#3B82F6", "#10B981", "#F59E0B", "#6366F1", "#EC4899", "#14B8A6", "#F97316", "#94A3B8"]
px.defaults.color_discrete_sequence = PALETTE
def fmt_pct(v): return f"{float(v):.0f}%"

# ---------- 상단 헤더 ----------
st.title("🛫 AI 기반 공항 디지털 트윈 시스템")
st.caption("실시간 모니터링 · 단기 예측 · 이상상황 경보 기반 운영 효율화")
st.markdown(f"**📅 업데이트:** {datetime.now().strftime('%Y-%m-%d %H:%M')} 기준")
st.markdown("---")

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.metric("운영 효율성 향상", "▲ 15%", "+15%")
    st.write("대기시간 단축 및 수하물 지연 감소")
with c2:
    st.metric("혼잡도 예측 정확도", "92%", "+4%")
    st.write("AI 기반 단기 혼잡도 예측")
with c3:
    st.metric("이상 상황 탐지율", "98%", "+6%")
    st.write("센서·CCTV 융합 기반 실시간 감시")
with c4:
    st.metric("승객 만족도 향상", "▲ 25%", "+25%")
    st.write("쾌적한 이용 환경 및 안전성 확보")

st.markdown("---")

# ---------- 혼잡도 섹션 (임시 API) ----------
API_NOW  = "http://127.0.0.1:8000/metrics/current_congestion"
API_HIST = "http://127.0.0.1:8000/metrics/congestion_history"
API_ZONE = "http://127.0.0.1:8000/metrics/zone_congestion"

@st.cache_data(ttl=5)
def fetch_now():
    try:
        j = requests.get(API_NOW, timeout=3).json()
        return float(j["congestion_pct"]), j.get("updated_at")
    except Exception:
        return 68.0, datetime.now().isoformat()

@st.cache_data(ttl=5)
def fetch_history():
    try:
        df = pd.DataFrame(requests.get(API_HIST, timeout=3).json())
        df["ts"] = pd.to_datetime(df["ts"])
        return df.sort_values("ts")
    except Exception:
        now = datetime.now()
        idx = pd.date_range(now - timedelta(minutes=59), periods=60, freq="min")
        base = 60
        return pd.DataFrame({"ts": idx, "pct": [base + (i%9 - 4)*2 for i in range(60)]})

@st.cache_data(ttl=5)
def fetch_zone():
    try:
        return pd.DataFrame(requests.get(API_ZONE, timeout=3).json())
    except Exception:
        return pd.DataFrame({
            "zone": ["T1-CheckIn", "T1-Security", "T1-Gate A", "T2-CheckIn", "T2-Security", "T2-Gate B"],
            "pct": [72, 55, 63, 48, 59, 77]
        })

st.subheader("실시간 혼잡도")
colL, colM, colR = st.columns([1.1, 1.2, 1.3])

# ① 현재 혼잡도 — 도넛
curr_pct, updated_at = fetch_now()
with colL:
    st.markdown("#### 현재")
    fig_donut = go.Figure(data=[go.Pie(
        values=[curr_pct, 100-curr_pct],
        hole=0.7, labels=["현재", "잔여"],
        marker_colors=[PALETTE[0], "#E5E7EB"],
        textinfo="none", sort=False
    )])
    fig_donut.update_layout(
        showlegend=False, height=260, margin=dict(l=10,r=10,t=10,b=10),
        annotations=[dict(text=fmt_pct(curr_pct), x=0.5, y=0.5,
                          font=dict(size=28, color="#1F2937"), showarrow=False)]
    )
    st.plotly_chart(fig_donut, use_container_width=True)
    st.metric("지금", fmt_pct(curr_pct))
    if updated_at:
        st.caption(f"업데이트: {updated_at}")

# ② 최근 60분 추이
with colM:
    st.markdown("#### 최근 60분")
    hist = fetch_history()
    fig_area = go.Figure()
    fig_area.add_trace(go.Scatter(
        x=hist["ts"], y=hist["pct"], mode="lines",
        line=dict(width=2, color=PALETTE[0]),
        hovertemplate="%{x|%H:%M} · %{y:.0f}%<extra></extra>", name="congestion"
    ))
    fig_area.add_trace(go.Scatter(
        x=hist["ts"], y=hist["pct"], mode="lines", line=dict(width=0), showlegend=False,
        fill="tozeroy", fillcolor="rgba(59,130,246,0.18)"
    ))
    fig_area.update_layout(
        height=260, margin=dict(l=10,r=10,t=10,b=10),
        xaxis=dict(showgrid=False), yaxis=dict(range=[0,100], ticksuffix="%")
    )
    st.plotly_chart(fig_area, use_container_width=True)

# ③ 구역별 혼잡도
with colR:
    st.markdown("#### 구역별")
    zone = fetch_zone().sort_values("pct", ascending=True)
    fig_bar = px.bar(zone, x="pct", y="zone", orientation="h",
                     text=zone["pct"].map(lambda v: f"{v:.0f}%"))
    fig_bar.update_traces(marker_color=PALETTE[2], textposition="outside")
    fig_bar.update_layout(
        height=260, margin=dict(l=10,r=20,t=10,b=10),
        xaxis=dict(range=[0,100], ticksuffix="%"), yaxis_title=""
    )
    st.plotly_chart(fig_bar, use_container_width=True)

# 수동 새로고침
if st.button("🔄 새로고침"):
    st.experimental_rerun()

st.divider()

# ---------- (옵션) 샘플 데이터 탐색 ----------
with st.expander("🔬 샘플 데이터 탐색(데모)"):
    @st.cache_data
    def load_data():
        return pd.read_csv("sample_data.csv", parse_dates=["date"])
    df = load_data()

    required = {"date", "category", "value"}
    if not required.issubset(df.columns):
        st.error(f"CSV에 필요한 컬럼이 없습니다. 필요: {required} / 현재: {list(df.columns)}")
        st.stop()

    st.sidebar.header("🔍 필터")
    cats = sorted(df["category"].unique())
    cat_sel = st.sidebar.multiselect("카테고리 선택", cats, default=cats)

    dmin, dmax = df["date"].min(), df["date"].max()
    drange = st.sidebar.date_input("📅 기간 선택", (dmin, dmax), min_value=dmin, max_value=dmax)

    if isinstance(drange, (list, tuple)) and len(drange) == 2:
        st.markdown(f"**🗓️ 선택된 기간:** {drange[0].strftime('%Y년 %m월 %d일')} ~ {drange[1].strftime('%Y년 %m월 %d일')}")

    mask = df["category"].isin(cat_sel)
    if isinstance(drange, (list, tuple)) and len(drange) == 2:
        start, end = pd.to_datetime(drange[0]), pd.to_datetime(drange[1])
        mask &= df["date"].between(start, end)
    f = df.loc[mask].sort_values("date")

    a, b, c = st.columns(3)
    a.metric("행 수", len(f))
    b.metric("합계(value)", int(f["value"].sum()))
    delta = int(f["value"].iloc[-1] - f["value"].iloc[0]) if len(f) > 1 else 0
    c.metric("증감(마지막-처음)", delta)

    st.markdown("#### 시계열")
    st.plotly_chart(px.line(f, x="date", y="value", color="category", markers=False), use_container_width=True)

    st.markdown("#### 분포")
    st.plotly_chart(px.box(f, x="category", y="value", points="suspectedoutliers"), use_container_width=True)

    st.markdown("#### 데이터")
    st.dataframe(f, use_container_width=True)
