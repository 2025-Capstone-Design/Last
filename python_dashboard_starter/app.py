# ---------- imports ----------
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
from dotenv import load_dotenv
from pathlib import Path
import os
from sqlalchemy import create_engine, text

# --------------------------------------------------------------------------------
# 1. 페이지 기본 설정 (무조건 최상단)
# --------------------------------------------------------------------------------
st.set_page_config(
    page_title="GIMHAE AIRPORT DIGITAL TWIN",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

with st.sidebar:
    st.page_link("app.py", label="✈️ 메인 모니터링", icon="🏠")
    # 파일 이름 변경: 02_AI_Forecast.py -> ai_forecast.py
    st.page_link("pages/ai_forecast.py", label="🤖 AI 예측 상세", icon="📊") 
    st.markdown("---")
    st.caption("Navigation Links")

# --------------------------------------------------------------------------------
# 2. PRO-LEVEL CSS 스타일링 (경진대회용 디자인 시스템)
# --------------------------------------------------------------------------------
design_css = """
<style>
    /* ------------------------------------------------------- */
    /* [기본 레이아웃 리셋] */
    /* ------------------------------------------------------- */
    [data-testid="stAppViewContainer"] {
        padding: 0 !important;
        /* 깊이감 있는 다크 네이비 배경 */
        background: radial-gradient(circle at 10% 10%, #1e293b 0%, #020617 100%) !important;
    }
    
    [data-testid="stHeader"] {
        display: none;
    }
    
    .main .block-container {
        padding-top: 1rem !important;
        padding-bottom: 2rem !important;
        max-width: 1600px !important;
    }

    /* ------------------------------------------------------- */
    /* [타이포그래피] SF 영화 같은 폰트 설정 */
    /* ------------------------------------------------------- */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&family=JetBrains+Mono:wght@400;700&display=swap');
    
    body, p, div, span, li {
        font-family: 'Inter', sans-serif;
        color: #cbd5e1;
    }
    
    h1, h2, h3 {
        font-family: 'Inter', sans-serif;
        letter-spacing: -0.02em;
        color: #f8fafc;
    }

    /* ------------------------------------------------------- */
    /* [UI 컴포넌트] Glassmorphism 카드 (유리 질감) */
    /* ------------------------------------------------------- */
    .glass-card {
        background: rgba(15, 23, 42, 0.6);   /* 반투명 배경 */
        backdrop-filter: blur(16px);           /* 배경 블러 처리 */
        -webkit-backdrop-filter: blur(16px);
        border: 1px solid rgba(255, 255, 255, 0.08); /* 아주 얇은 테두리 */
        border-radius: 16px;
        padding: 24px;
        box-shadow: 0 4px 30px rgba(0, 0, 0, 0.2); /* 그림자 */
        margin-bottom: 20px;
        transition: transform 0.3s ease, box-shadow 0.3s ease;
    }

    .glass-card:hover {
        border-color: rgba(56, 189, 248, 0.3);
        box-shadow: 0 0 20px rgba(56, 189, 248, 0.1);
    }

    /* 헤더 스타일 */
    .card-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 20px;
        border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        padding-bottom: 12px;
    }

    .card-title {
        font-size: 1.1rem;
        font-weight: 700;
        background: linear-gradient(90deg, #fff, #94a3b8);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        display: flex;
        align-items: center;
        gap: 8px;
    }

    .card-caption {
        font-size: 0.75rem;
        color: #64748b;
        font-family: 'JetBrains Mono', monospace;
    }

    /* ------------------------------------------------------- */
    /* [커스텀 네비게이션 바] */
    /* ------------------------------------------------------- */
    .top-nav {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 16px 24px;
        background: rgba(15, 23, 42, 0.7);
        backdrop-filter: blur(10px);
        border-radius: 16px;
        border: 1px solid rgba(255, 255, 255, 0.05);
        margin-bottom: 24px;
    }

    .brand-logo {
        font-family: 'JetBrains Mono', monospace;
        font-weight: 800;
        font-size: 1.2rem;
        color: #38bdf8; /* Sky Blue */
        text-shadow: 0 0 15px rgba(56, 189, 248, 0.4);
        display: flex;
        align-items: center;
        gap: 10px;
    }

    .status-badge {
        background: rgba(16, 185, 129, 0.1);
        color: #34d399;
        padding: 4px 12px;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
        border: 1px solid rgba(16, 185, 129, 0.2);
        display: flex;
        align-items: center;
        gap: 6px;
    }

    .status-dot {
        width: 8px;
        height: 8px;
        background-color: #34d399;
        border-radius: 50%;
        box-shadow: 0 0 8px #34d399;
        animation: pulse 2s infinite;
    }

    @keyframes pulse {
        0% { opacity: 1; box-shadow: 0 0 0 0 rgba(52, 211, 153, 0.7); }
        70% { opacity: 1; box-shadow: 0 0 0 6px rgba(52, 211, 153, 0); }
        100% { opacity: 1; box-shadow: 0 0 0 0 rgba(52, 211, 153, 0); }
    }

    /* ------------------------------------------------------- */
    /* [KPI 지표 스타일] */
    /* ------------------------------------------------------- */
    .kpi-container {
        display: flex;
        flex-direction: column;
    }
    
    .kpi-label {
        font-size: 0.75rem;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 4px;
        font-weight: 600;
    }
    
    .kpi-value {
        font-family: 'JetBrains Mono', monospace;
        font-size: 1.8rem;
        font-weight: 700;
        color: #f1f5f9;
        text-shadow: 0 0 20px rgba(255, 255, 255, 0.05);
    }
    
    .kpi-sub {
        font-size: 0.8rem;
        margin-top: 4px;
        color: #94a3b8;
    }

    /* 사이드바 스타일 오버라이드 */
    [data-testid="stSidebar"] {
        background-color: #020617;
        border-right: 1px solid #1e293b;
    }
</style>
"""
st.markdown(design_css, unsafe_allow_html=True)

# --------------------------------------------------------------------------------
# 3. 환경 설정 및 DB 연결
# --------------------------------------------------------------------------------
ENV_PATH = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=ENV_PATH)

db_url = os.getenv("DATABASE_URL")
ws_url = "ws://127.0.0.1:8000/ws/stream"  # WebSocket 주소

engine = None
try:
    engine = create_engine(db_url, pool_pre_ping=True, future=True)
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    # 성공 시 조용히 넘어감 (UI 깔끔하게 유지)
except Exception as e:
    st.toast("⚠️ DB 연결 실패 (데모 모드)", icon="⚠️")

# --------------------------------------------------------------------------------
# 4. 상단 네비게이션 (Custom HTML)
# --------------------------------------------------------------------------------
now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

st.markdown(f"""
    <div class="top-nav">
        <div class="brand-logo">
            <span>✈️</span>
            <span>GIMHAE AIRPORT DT</span>
            <span style="color: #475569; font-weight:400; font-size: 0.9em;">// OPS_CONTROL</span>
        </div>
        <div style="display:flex; gap: 24px; align-items:center;">
            <div style="text-align:right;">
                <div style="font-size:0.7rem; color:#64748b;">SYSTEM TIME</div>
                <div style="font-family:'JetBrains Mono'; font-size:0.9rem; color:#cbd5e1;">{now_str}</div>
            </div>
            <div class="status-badge">
                <div class="status-dot"></div> LIVE
            </div>
        </div>
    </div>
""", unsafe_allow_html=True)

# --------------------------------------------------------------------------------
# 5. 메인 레이아웃 (Grid System)
# --------------------------------------------------------------------------------
# 3:1 비율로 메인 컨텐츠와 사이드 패널 분리
col_main, col_side = st.columns([3, 1], gap="medium")

with col_main:
    # --- [섹션 1] 실시간 모니터링 (Glass Card) ---
    st.markdown("""
        <div class="glass-card">
            <div class="card-header">
                <div class="card-title">📡 Real-Time Crowd Monitor</div>
                <div class="card-caption">WebSocket Stream • Terminal 2</div>
            </div>
    """, unsafe_allow_html=True)

    # WebSocket + Plotly HTML (다크 테마 적용)
    # 배경을 투명하게(rgba(0,0,0,0)) 처리하고 텍스트 색상을 흰색 계열로 변경
    html_card_1 = """
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>

    <div id="kpi-1" style="display:flex; gap:20px; align-items:baseline; margin-bottom:10px;">
        <div id="kpi-value-1" style="font-family:'JetBrains Mono'; font-size:28px; font-weight:700; color:#38bdf8; text-shadow: 0 0 10px rgba(56, 189, 248, 0.4);">
            Waiting..
        </div>
        <div id="kpi-count-1" style="font-family:'Inter'; font-size:12px; color:#64748b;">
            (Initializing connection...)
        </div>
    </div>

    <div id="graph-1" style="height:450px;"></div>

    <script>
      const WS_URL     = "%WS_URL%";
      const MAX_POINTS = 60;
      const MAX_PEOPLE = 30; // y축 최대값

      let count = 0;

      // 다크 테마 차트 설정
      const layout = {
        paper_bgcolor: "rgba(0,0,0,0)", // 투명 배경
        plot_bgcolor: "rgba(0,0,0,0)",  // 투명 배경
        margin: { l: 40, r: 20, t: 10, b: 40 },
        xaxis: { 
            type: "date", 
            tickformat: "%H:%M:%S", 
            showgrid: true, 
            gridcolor: "rgba(255,255,255,0.05)",
            tickfont: { color: "#94a3b8" }
        },
        yaxis: {
          range: [0, MAX_PEOPLE],
          showgrid: true,
          gridcolor: "rgba(255,255,255,0.05)",
          zerolinecolor: "rgba(255,255,255,0.1)",
          tickfont: { color: "#94a3b8" },
          fixedrange: true
        },
        showlegend: false
      };

      const trace = {
        x: [],
        y: [],
        mode: "lines",
        line: { color: "#38bdf8", width: 3, shape: 'spline' }, // 네온 블루, 부드러운 곡선
        fill: 'tozeroy',
        fillcolor: 'rgba(56, 189, 248, 0.1)', // 하단 은은한 채우기
        name: "People"
      };

      Plotly.newPlot("graph-1", [trace], layout, { responsive: true, displayModeBar: false });

      const ws = new WebSocket(WS_URL);
      
      ws.onopen  = () => {
          document.getElementById("kpi-count-1").innerText = "(Connected)";
      };
      
      ws.onmessage = (event) => {
        const msg = JSON.parse(event.data);
        const people = (typeof msg.people === "number") ? msg.people : 0;
        const now = new Date();
        count += 1;

        // KPI 업데이트
        const kpi = document.getElementById("kpi-value-1");
        kpi.innerText = `${people} PAX`;

        // 경고 색상 변경 (20명 이상 시 Red)
        if (people >= 20) {
            kpi.style.color = "#f43f5e"; // Red
            kpi.style.textShadow = "0 0 15px rgba(244, 63, 94, 0.6)";
            
            // 그래프 색상 변경
            Plotly.restyle("graph-1", { "line.color": "#f43f5e", "fillcolor": "rgba(244, 63, 94, 0.1)" }, [0]);
        } else {
            kpi.style.color = "#38bdf8"; // Blue
            kpi.style.textShadow = "0 0 10px rgba(56, 189, 248, 0.4)";
            
            // 그래프 색상 복구
            Plotly.restyle("graph-1", { "line.color": "#38bdf8", "fillcolor": "rgba(56, 189, 248, 0.1)" }, [0]);
        }

        // 그래프 데이터 추가
        Plotly.extendTraces("graph-1", { x: [[now]], y: [[people]] }, [0], MAX_POINTS);
      };
    </script>
    """
    st.components.v1.html(html_card_1.replace("%WS_URL%", ws_url), height=520)
    st.markdown("</div>", unsafe_allow_html=True)


    # --- [섹션 2] 예측 분석 (Glass Card) ---
    st.markdown("""
        <div class="glass-card">
            <div class="card-header">
                <div class="card-title">📊 AI Congestion Forecast</div>
                <div class="card-caption">Model: LightGBM v2.1</div>
            </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div style="text-align: center; padding: 40px 0;">
        <a href="ai_forecast" target="_self" 
           style="text-decoration: none;">
        <button style="
                ">
                AI 예측 시스템 자세히 보기 →
            </button>
        </a>
        </div>
""", unsafe_allow_html=True)
    
    st.markdown("</div>", unsafe_allow_html=True)

   # -----------------------------------------------
    # ✅ [대체하여 삽입할 새로운 버튼 코드]
    # -----------------------------------------------
    st.markdown("""
        <div style="text-align: center; padding: 40px 0;">
            <p style="color: #94a3b8; font-size: 1rem; margin-bottom: 20px;">
                실시간 예측 결과 및 모델 상세 분석은 별도의 분석 시스템에서 확인하세요.
            </p>
            <a href="02_AI_Forecast" target="_self" 
               style="text-decoration: none;">
                <button style="
                    background-color: #38bdf8; /* Sky Blue */
                    color: #020617;
                    border: none;
                    padding: 12px 30px;
                    border-radius: 8px;
                    font-size: 1rem;
                    font-weight: 700;
                    cursor: pointer;
                    box-shadow: 0 0 10px rgba(56, 189, 248, 0.5);
                    transition: all 0.2s;
                ">
                    AI 예측 시스템 자세히 보기 →
                </button>
            </a>
        </div>
    """, unsafe_allow_html=True)
    # -----------------------------------------------

    st.markdown("</div>", unsafe_allow_html=True)


with col_side:
    # --- 사이드 패널: 주요 지표 (KPIs) ---
    
    # KPI 1
    st.markdown("""
        <div class="glass-card">
            <div class="kpi-container">
                <div class="kpi-label">Avg. Wait Time</div>
                <div class="kpi-value" style="color: #38bdf8;">14 min</div>
                <div class="kpi-sub">▼ 2min vs Avg</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # KPI 2
    st.markdown("""
        <div class="glass-card">
            <div class="kpi-container">
                <div class="kpi-label">Gate 3 Density</div>
                <div class="kpi-value" style="color: #f43f5e;">High</div>
                <div class="kpi-sub">Requires Staff</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # KPI 3
    st.markdown("""
        <div class="glass-card">
            <div class="kpi-container">
                <div class="kpi-label">Hourly Throughput</div>
                <div class="kpi-value">2,450</div>
                <div class="kpi-sub" style="color:#a855f7;">▲ 12% Spike</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # Alerts Panel
    st.markdown("""
        <div class="glass-card" style="border: 1px solid rgba(244, 63, 94, 0.3); background: linear-gradient(145deg, rgba(244, 63, 94, 0.1), transparent);">
            <div class="card-title" style="font-size:0.9rem; margin-bottom:12px; color:#f43f5e !important;">
                🚨 System Alerts
            </div>
            <div style="font-size:0.8rem; color:#cbd5e1; margin-bottom:8px; display:flex; gap:8px;">
                <span style="color:#f43f5e;">•</span> <span>CCTV-04 Disconnected</span>
            </div>
            <div style="font-size:0.8rem; color:#cbd5e1; display:flex; gap:8px;">
                <span style="color:#f59e0b;">•</span> <span>High Congestion: Zone B</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

# --------------------------------------------------------------------------------
# 6. 푸터
# --------------------------------------------------------------------------------
st.markdown("""
    <div style="text-align: center; margin-top: 40px; border-top: 1px solid rgba(255,255,255,0.05); padding-top: 20px;">
        <span style="font-size: 0.75rem; color: #475569;">
            GIMHAE AIRPORT DIGITAL TWIN PROJECT © 2024<br>
            POWERED BY AI & WEBSOCKET STREAMING
        </span>
    </div>
""", unsafe_allow_html=True)