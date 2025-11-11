# ---------- imports ----------
import streamlit as st
from datetime import datetime
from dotenv import load_dotenv
from pathlib import Path
import os
from sqlalchemy import create_engine, text

# ✅ Streamlit 설정은 가장 먼저
st.set_page_config(page_title="AI 기반 공항 디지털 트윈 대시보드", page_icon="🛫", layout="wide")

# ✅ .env 로드 및 DB 연결
ENV_PATH = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=ENV_PATH)

db_url = os.getenv("DATABASE_URL")

if not db_url:
    st.error("❌ DATABASE_URL이 비어있습니다. .env 위치/내용을 확인하세요.")
    st.stop()

# ✅ DB 연결 및 테이블 목록 사이드바에 표시
try:
    engine = create_engine(db_url, pool_pre_ping=True, future=True)
    with engine.connect() as conn:
        result = conn.execute(text("SHOW TABLES;"))
        tables = [row[0] for row in result]
        st.sidebar.write("📂 데이터베이스 테이블:", tables)
except Exception as e:
    st.sidebar.error(f"DB 연결 실패: {e}")

# ---------- 상단 헤더 ----------
st.title("🛫 AI 기반 공항 디지털 트윈 시스템")
st.caption("실시간 모니터링 · 단기 예측 · 이상상황 경보 기반 운영 효율화")
st.markdown(f"**📅 업데이트:** {datetime.now().strftime('%Y-%m-%d %H:%M')} 기준")
st.markdown("---")

# ---------- 실시간 혼잡도 섹션 (WebSocket) ----------
st.subheader("📡 실시간 혼잡도 모니터링")

# ✅ FastAPI WebSocket 서버 주소 (필요시 수정)
ws_url = "ws://127.0.0.1:8000/ws/stream"

# ✅ Streamlit 컴포넌트로 JavaScript 삽입 (Plotly는 CDN 사용)
# ✅ HTML을 f-string 없이 만들고, WS_URL만 치환
html = """
  <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>

<!-- KPI -->
<div id="kpi" style="
    display:flex; gap:16px; align-items:baseline; margin:8px 4px 12px 4px;
    font-family: ui-sans-serif,system-ui,AppleSDGothicNeo,Segoe UI,Roboto,Helvetica,Arial;">
  <div id="kpi-value" style="font-size:32px; font-weight:800; color:#2563EB;">
    현재 인원: --명
  </div>
  <div id="kpi-count" style="font-size:14px; color:#6B7280;">
    (수신 0건)
  </div>
</div>

<div id="graph" style="height:520px;"></div>
<script>
  const WS_URL     = "%WS_URL%";
  const MAX_POINTS = 60;     // 최근 포인트 유지
  const MAX_PEOPLE = 20;     // y축 상한(명) — 시연용 고정

  let count = 0;

  const layout = {
    title: "실시간 인원 추이",
    xaxis: { title: "시간", type: "date", tickformat: "%-I:%M %p", showgrid: false, tickfont: { size: 12 } },
    yaxis: {
      title: "인원(명)",
      range: [0, MAX_PEOPLE],
      dtick: 5,
      gridcolor: "#E5E7EB",
      zerolinecolor: "#CBD5E1",
      fixedrange: true
    },
    margin: { l: 60, r: 20, t: 50, b: 50 },
    plot_bgcolor: "#ffffff",
    paper_bgcolor: "#ffffff",
    showlegend: false
  };

  const trace = {
    x: [],
    y: [],             // 사람 수(명)
    text: [],          // 호버 텍스트 "N명"
    mode: "lines+markers",
    line: { color: "#2563EB", width: 3 },
    marker: { size: 6, color: "#2563EB" },
    name: "인원",
    cliponaxis: true,
    hovertemplate: "%{text}<extra></extra>"
  };

  Plotly.newPlot("graph", [trace], layout, { responsive: true, displayModeBar: false });

  const ws = new WebSocket(WS_URL);
  ws.onopen  = () => console.log("✅ WebSocket 연결");
  ws.onerror = (e) => console.error("❌ WebSocket 오류:", e);

  ws.onmessage = (event) => {
    const msg = JSON.parse(event.data);

    // 필수 입력값: people(명), congestion(%)
    const people = (typeof msg.people === "number") ? msg.people : 0;
    const pct    = (typeof msg.congestion === "number") ? msg.congestion : 0;

    const now = new Date();
    count += 1;

    // 그래프가 축을 절대 뚫지 않도록 표시값 클램프
    const yDisplay = Math.max(0, Math.min(MAX_PEOPLE - 0.001, people));

    // 호버 텍스트: 퍼센트 미표시(명만)
    const txt = `${people.toLocaleString()}명`;

    // 데이터 추가
    Plotly.extendTraces("graph", { x: [[now]], y: [[yDisplay]], text: [[txt]] }, [0], MAX_POINTS);

    // 퍼센트 기준(80%)으로 색상/경보 표시 — UI엔 % 안 보임
    // 20명 스케일 기준 퍼센트(시연 스케일)로 경보 판단
    const dangerPct = (people / MAX_PEOPLE) * 100;
    const danger = dangerPct >= 80;

    const color  = danger ? "#EF4444" : "#2563EB";

    Plotly.restyle("graph", { "line.color": color, "marker.color": color }, [0]);

    // 경보 주석
    const ann = danger ? [{
      x: now, y: yDisplay,
      text: "🚨 혼잡!",
      showarrow: true, arrowhead: 7, ax: 0, ay: -40,
      font: { color: "#EF4444", size: 14 }
    }] : [];
    Plotly.relayout("graph", { annotations: ann });

    // KPI 갱신(명만 표기)
    const kpi = document.getElementById("kpi-value");
    const cnt = document.getElementById("kpi-count");
    kpi.textContent = `현재 인원: ${people.toLocaleString()}명`;
    kpi.style.color = color;
    cnt.textContent  = `(수신 ${count}건)`;
  };
</script>

"""
st.components.v1.html(html.replace("%WS_URL%", ws_url), height=600)


# ---------- 예측 혼잡도 시각화 (DB에서 불러오기) ----------
st.markdown("---")
st.subheader("📊 실제 혼잡도 vs 예측 혼잡도 비교")

import plotly.graph_objects as go
import pandas as pd

try:
    # ✅ 실제 데이터
    df_real = pd.read_sql("SELECT * FROM kim_forecast", con=engine)
    df_real["FlightDate"] = pd.to_datetime(df_real["FlightDate"])
    df_real["Hour"] = df_real["HourRange"].str.split(" ").str[0].astype(int)
    df_real["FlightDateTime"] = df_real.apply(
        lambda row: row["FlightDate"] + pd.Timedelta(hours=row["Hour"], minutes=30), axis=1
    )
    df_real = df_real.groupby("FlightDateTime")["MaxWait"].max().reset_index()
    df_real.rename(columns={"MaxWait": "Actual_MaxWait"}, inplace=True)

    # ✅ 예측 데이터
    df_pred = pd.read_sql("SELECT * FROM predicted_wait", con=engine)
    df_pred["FlightDateTime"] = pd.to_datetime(df_pred["FlightDateTime"])

    # ✅ 그래프 생성
    fig = go.Figure()

    # 실제값 (파란색)
    fig.add_trace(go.Scatter(
        x=df_real["FlightDateTime"], y=df_real["Actual_MaxWait"],
        mode="lines", name="실제 혼잡도", line=dict(color="#1D4ED8", width=2)
    ))

    # 예측값 (빨간색)
    fig.add_trace(go.Scatter(
        x=df_pred["FlightDateTime"], y=df_pred["Predicted_MaxWait"],
        mode="lines", name="예측 혼잡도", line=dict(color="#E63946", width=2)
    ))

    # 구간 표시
    future_start = df_pred["FlightDateTime"].min()
    future_end = df_pred["FlightDateTime"].max()
    fig.add_vrect(
        x0=future_start, x1=future_end,
        fillcolor="red", opacity=0.08, line_width=0,
        annotation_text="예측 구간", annotation_position="top right"
    )

    fig.update_layout(
        title="✈️ 실제 vs 예측 혼잡도 (LightGBM 모델)",
        xaxis_title="날짜",
        yaxis_title="최대 대기시간 (분)",
        template="plotly_white",
        hovermode="x unified",
        height=600,
        legend_title_text="데이터 종류",
    )

    # ✅ 좌우 스크롤 (Zoom/Slider)
    fig.update_xaxes(
        rangeslider_visible=True,
        rangeselector=dict(
            buttons=list([
                dict(count=1, label="1개월", step="month", stepmode="backward"),
                dict(count=6, label="6개월", step="month", stepmode="backward"),
                dict(step="all", label="전체")
            ])
        )
    )

    st.plotly_chart(fig, use_container_width=True)

except Exception as e:
    st.error(f"❌ 데이터 불러오기 실패: {e}")
