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
    page_title="Runner's high AIRPORT DIGITAL TWIN",
    layout="wide",
    initial_sidebar_state="collapsed"
)

with st.sidebar:
    st.page_link("app.py", label="✈️ 메인 모니터링", icon="🏠")
    st.page_link("pages/ai_forecast.py", label="AI 예측 상세", icon="📊") 
    st.markdown("---")
    st.caption("Navigation Links")

# --------------------------------------------------------------------------------
# 2. PRO-LEVEL CSS 로드 함수 (style.css 연결)
# --------------------------------------------------------------------------------
def load_css(file_name):
    try:
        with open(file_name, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        st.error(f"⚠️ CSS 파일({file_name})을 찾을 수 없습니다.")

# style.css 파일 로드
load_css("style.css")

# --------------------------------------------------------------------------------
# 3. 환경 설정 및 DB 연결
# --------------------------------------------------------------------------------
ENV_PATH = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=ENV_PATH)

db_url = os.getenv("DATABASE_URL")
ws_url = "ws://127.0.0.1:8000/ws/stream"   # WebSocket 주소

engine = None
try:
    engine = create_engine(db_url, pool_pre_ping=True, future=True)
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
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
            <span>Runner's high AIRPORT DT</span>
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
                <div class="card-title"> 실시간 공항 혼잡도 그래프</div>
                <div class="card-caption">WebSocket Stream • Terminal 2</div>
            </div>
    """, unsafe_allow_html=True)

    # WebSocket + Plotly HTML (다크 테마 적용)
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
      const CAPACITY = 20; // ✅ 기준 수용 인원 (Threshold 계산용)
      const DANGER_THRESHOLD = CAPACITY * 0.8; // ✅ 16명 (80%)
      let maxY = 25; // ✅ Y축 초기 최대값 (Capacity + 여유분)

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
          range: [0, maxY], // ✅ 동적 Y축 적용
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

        // ✅ 경고 색상 변경 (16명 이상 시 Red)
        if (people >= DANGER_THRESHOLD) {
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

        // ✅ Y축 자동 확장 로직 (그래프 뚫고 나감 방지)
        if (people > maxY - 2) {
            maxY = people + 5;
            Plotly.relayout("graph-1", { "yaxis.range": [0, maxY] });
        }

        // 그래프 데이터 추가
        Plotly.extendTraces("graph-1", { x: [[now]], y: [[people]] }, [0], MAX_POINTS);
      };
    </script>
    """
    st.components.v1.html(html_card_1.replace("%WS_URL%", ws_url), height=520)
    st.markdown("</div>", unsafe_allow_html=True) # 섹션 1 닫기

    # -----------------------------------------------
    # ✅ "AI Congestion Forecast" 섹션 버튼
    # -----------------------------------------------
    st.markdown("""
        <div style="text-align: center; padding: 40px 0;">
            <a href="ai_forecast" target="_self" 
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

with col_side:
    # --- 사이드 패널: 주요 지표 (KPIs) ---
    
    # KPI 1 - [✅ 동적 계산 적용] 실시간 대기 시간 계산 (인원 * 0.8분)
    kpi_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&family=JetBrains+Mono:wght@400;700&display=swap');
            body {{ margin: 0; overflow: hidden; background: transparent; font-family: 'Inter', sans-serif; }}
            .glass-card {{
                background: rgba(15, 23, 42, 0.6);
                backdrop-filter: blur(16px);
                -webkit-backdrop-filter: blur(16px);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 16px;
                padding: 24px;
                box-shadow: 0 4px 30px rgba(0, 0, 0, 0.2);
                color: #cbd5e1;
            }}
            .kpi-container {{ display: flex; flex-direction: column; }}
            .kpi-label {{ font-size: 0.75rem; color: #64748b; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 4px; font-weight: 600; }}
            .kpi-value {{ font-family: 'JetBrains Mono', monospace; font-size: 1.8rem; font-weight: 700; color: #38bdf8; text-shadow: 0 0 20px rgba(255, 255, 255, 0.05); }}
            .kpi-sub {{ font-size: 0.8rem; margin-top: 4px; color: #94a3b8; }}
        </style>
    </head>
    <body>
        <div class="glass-card">
            <div class="kpi-container">
                <div class="kpi-label">Real-time Est. Wait</div>
                <div id="kpi-wait" class="kpi-value">-- min</div>
                <div id="kpi-sub" class="kpi-sub">Syncing...</div>
            </div>
        </div>
        <script>
            const ws = new WebSocket("{ws_url}");
            ws.onmessage = (event) => {{
                const data = JSON.parse(event.data);
                const people = data.people || 0;
                
                // 💡 로직: 1인당 약 48초(0.8분) 처리 시간 가정
                const waitTime = Math.ceil(people * 0.8);
                
                const el = document.getElementById("kpi-wait");
                el.innerText = waitTime + " min";
                
                // 색상 동적 변경 (15분 이상 혼잡 시 Red)
                if(waitTime >= 15) {{
                    el.style.color = "#f43f5e"; 
                    el.style.textShadow = "0 0 15px rgba(244, 63, 94, 0.6)";
                }} else {{
                    el.style.color = "#38bdf8"; 
                    el.style.textShadow = "0 0 20px rgba(255, 255, 255, 0.05)";
                }}
                
                document.getElementById("kpi-sub").innerText = "Based on " + people + " PAX";
            }};
        </script>
    </body>
    </html>
    """
    st.components.v1.html(kpi_html, height=145)

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