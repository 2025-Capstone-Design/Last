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

# ---------- 혼잡도 섹션 (WebSocket 실시간 버전) ----------
st.subheader("📡 실시간 혼잡도 모니터링")

# ✅ FastAPI WebSocket 서버 주소
ws_url = "ws://127.0.0.1:8000/ws/stream"


# ✅ Streamlit 컴포넌트로 JavaScript 삽입
st.components.v1.html(f"""
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <div id="graph" style="height:400px;"></div>
    <script>
    const ws = new WebSocket("{ws_url}");
    let xData = [];
    let yData = [];
    const MAX_POINTS = 60; // 최근 60초 유지

    ws.onopen = () => console.log("✅ WebSocket 연결 성공");
    ws.onerror = (err) => console.error("❌ WebSocket 오류:", err);

    ws.onmessage = function(event) {{
        const msg = JSON.parse(event.data);
        const now = new Date().toLocaleTimeString();
        const congestion = msg.congestion;

        // 데이터 누적
        xData.push(now);
        yData.push(congestion);
        if (xData.length > MAX_POINTS) {{
            xData.shift();
            yData.shift();
        }}

        // ⚠️ 혼잡도에 따라 색상 변경 (80% 이상 = 빨강)
        let lineColor = congestion >= 80 ? "#EF4444" : "#3B82F6";

        const trace = {{
            x: xData,
            y: yData,
            mode: "lines+markers",
            line: {{ color: lineColor, width: 3 }},
            marker: {{ size: 6, color: lineColor }},
            name: "혼잡도 (%)"
        }};

        const annotations = congestion >= 80 ? [{{
            x: now,
            y: congestion,
            text: "🚨 혼잡!",
            showarrow: true,
            arrowhead: 7,
            ax: 0,
            ay: -40,
            font: {{ color: "#EF4444", size: 14 }}
        }}] : [];

        const layout = {{
            title: "실시간 혼잡도 변화 (경보 기준 80%)",
            xaxis: {{ title: "시간" }},
            yaxis: {{ title: "혼잡도 (%)", range: [0, 100] }},
            margin: {{ l: 50, r: 20, t: 50, b: 50 }},
            plot_bgcolor: "#f9fafb",
            paper_bgcolor: "#f9fafb",
            annotations: annotations
        }};

        Plotly.newPlot("graph", [trace], layout, {{responsive: true}});
    }};
    </script>
""", height=430)




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
