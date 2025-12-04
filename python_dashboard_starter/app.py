import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
from dotenv import load_dotenv
from pathlib import Path
import os
import streamlit.components.v1 as components

# --------------------------------------------------------------------------------
# 1. 페이지 기본 설정
# --------------------------------------------------------------------------------
st.set_page_config(
    page_title="Runner's high AIRPORT DIGITAL TWIN",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# CSS 로드 (메인 페이지용)
def load_css():
    st.markdown("""
    <style>
        /* 전체 배경 */
        .stApp {
            background-color: #0f172a;
            color: #cbd5e1;
        }
        /* 상단 네비게이션 스타일 */
        .top-nav {
            display: flex; 
            justify-content: space-between; 
            align-items: center; 
            padding: 15px 20px;
            background: rgba(30, 41, 59, 0.5);
            border-bottom: 1px solid rgba(255,255,255,0.1);
            margin-bottom: 20px;
            border-radius: 10px;
        }
        .brand-logo span {
            font-size: 1.2rem;
            font-weight: bold;
            color: #f8fafc;
            margin-right: 10px;
        }
        .status-badge {
            background: rgba(34, 197, 94, 0.1);
            color: #22c55e;
            padding: 5px 10px;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: bold;
            display: flex;
            align-items: center;
            gap: 5px;
        }
        .status-dot {
            width: 8px;
            height: 8px;
            background-color: #22c55e;
            border-radius: 50%;
        }
        /* 메인 화면 카드 스타일 */
        .glass-card {
            background: #1e293b;
            border: 1px solid #334155;
            border-radius: 12px;
            overflow: hidden;
        }
    </style>
    """, unsafe_allow_html=True)

load_css()

# WebSocket 주소 (FastAPI 서버)
WS_URL = "ws://127.0.0.1:8000/ws/stream"

# --------------------------------------------------------------------------------
# 2. 상단 네비게이션
# --------------------------------------------------------------------------------
now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
st.markdown(f"""
    <div class="top-nav">
        <div class="brand-logo">
            <span>✈️</span>
            <span>Runner's high AIRPORT DT</span>
            <span style="color: #64748b; font-weight:400; font-size: 0.9em;">// OPS_CONTROL</span>
        </div>
        <div style="display:flex; gap: 24px; align-items:center;">
            <div style="text-align:right;">
                <div style="font-size:0.7rem; color:#64748b;">SYSTEM TIME</div>
                <div style="font-family:'JetBrains Mono', monospace; font-size:0.9rem; color:#cbd5e1;">{now_str}</div>
            </div>
            <div class="status-badge">
                <div class="status-dot"></div> LIVE
            </div>
        </div>
    </div>
""", unsafe_allow_html=True)

# --------------------------------------------------------------------------------
# 3. 그래프 생성 함수 (HTML/JS)
# --------------------------------------------------------------------------------
def make_graph_html(cam_id, title):
    """
    cam_id에 해당하는 그래프 HTML/JS 코드를 생성하는 함수
    ★ 중요: iframe 내부이므로 CSS를 여기에 직접 포함시켜야 스타일이 적용됩니다.
    """
    return f"""
    <html>
    <head>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&family=JetBrains+Mono:wght@400;700&display=swap');
            
            body {{
                margin: 0;
                padding: 0;
                background-color: transparent;
                font-family: 'Inter', sans-serif;
                color: #cbd5e1; /* 기본 글씨 색상 */
            }}
            /* 카드 스타일 직접 정의 */
            .glass-card {{
                background: #1e293b; /* 배경색 지정 */
                border: 1px solid #334155;
                border-radius: 12px;
                padding: 20px;
                box-sizing: border-box;
            }}
            .card-header {{
                margin-bottom: 15px;
            }}
            .card-title {{
                font-size: 1.1rem;
                font-weight: 700;
                color: #f8fafc; /* 제목 하얀색 */
                margin-bottom: 4px;
            }}
            .card-caption {{
                font-size: 0.8rem;
                color: #94a3b8; /* 설명 회색 */
                font-weight: 500;
            }}
        </style>
        <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    </head>
    <body>
        <div class="glass-card">
            <div class="card-header">
                <div class="card-title">{title}</div>
                <div class="card-caption">WebSocket Stream • CAM {cam_id}</div>
            </div>

            <div id="kpi-box-{cam_id}" style="display:flex; gap:20px; align-items:baseline; margin-bottom:10px;">
                <div id="kpi-value-{cam_id}" style="font-family:'JetBrains Mono'; font-size:28px; font-weight:700; color:#38bdf8; text-shadow: 0 0 10px rgba(56, 189, 248, 0.4);">
                    Wait..
                </div>
                <div id="kpi-sub-{cam_id}" style="font-family:'Inter'; font-size:12px; color:#64748b;">
                    (Connecting..)
                </div>
            </div>

            <div id="graph-{cam_id}" style="height:220px;"></div>
        </div>

        <script>
            (function() {{
                const WS_URL = "{WS_URL}";
                const CAM_ID = {cam_id};
                const MAX_POINTS = 50;
                
                // 설정
                const DANGER_THRESHOLD = 4; // 4명 이상 혼잡
                let maxY = 10;              // 기본 Y축

                const layout = {{
                    paper_bgcolor: "rgba(0,0,0,0)",
                    plot_bgcolor: "rgba(0,0,0,0)",
                    margin: {{ l: 30, r: 10, t: 10, b: 30 }},
                    xaxis: {{ type: "date", tickformat: "%H:%M:%S", showgrid: true, gridcolor: "rgba(255,255,255,0.05)", tickfont: {{ color: "#64748b" }} }},
                    yaxis: {{ range: [0, maxY], showgrid: true, gridcolor: "rgba(255,255,255,0.05)", tickfont: {{ color: "#64748b" }}, fixedrange: true }},
                    showlegend: false
                }};

                const trace = {{
                    x: [], y: [], mode: "lines",
                    line: {{ color: "#38bdf8", width: 3, shape: 'spline' }},
                    fill: 'tozeroy', fillcolor: 'rgba(56, 189, 248, 0.1)'
                }};
                
                Plotly.newPlot("graph-{cam_id}", [trace], layout, {{ responsive: true, displayModeBar: false }});

                const ws = new WebSocket(WS_URL);
                
                ws.onmessage = (event) => {{
                    const msg = JSON.parse(event.data);
                    
                    if (msg.cam_id == CAM_ID) {{
                        const people = msg.people || 0;
                        const now = new Date();

                        // 1. 숫자 업데이트
                        document.getElementById("kpi-value-{cam_id}").innerText = people + " 명";
                        
                        // 2. 색상 경고
                        const kpi = document.getElementById("kpi-value-{cam_id}");
                        const sub = document.getElementById("kpi-sub-{cam_id}");

                        if (people >= DANGER_THRESHOLD) {{
                            kpi.style.color = "#f43f5e";
                            sub.innerText = "혼잡 (High Traffic)";
                            sub.style.color = "#f43f5e";
                            Plotly.restyle("graph-{cam_id}", {{ "line.color": "#f43f5e", "fillcolor": "rgba(244, 63, 94, 0.1)" }}, [0]);
                        }} else {{
                            kpi.style.color = "#38bdf8";
                            sub.innerText = "원활 (Normal)";
                            sub.style.color = "#64748b";
                            Plotly.restyle("graph-{cam_id}", {{ "line.color": "#38bdf8", "fillcolor": "rgba(56, 189, 248, 0.1)" }}, [0]);
                        }}

                        // 3. Y축 자동조절
                        if (people > maxY - 1) {{
                            maxY = people + 3;
                            Plotly.relayout("graph-{cam_id}", {{ "yaxis.range": [0, maxY] }});
                        }} 

                        // 4. 그래프 그리기
                        Plotly.extendTraces("graph-{cam_id}", {{ x: [[now]], y: [[people]] }}, [0], MAX_POINTS);
                    }}
                }};
            }})();
        </script>
    </body>
    </html>
    """

# --------------------------------------------------------------------------------
# 4. 메인 화면 레이아웃
# --------------------------------------------------------------------------------
col_main, col_side = st.columns([3, 1], gap="medium")

with col_main:
    col1, col2 = st.columns(2, gap="large")

    # === [왼쪽] CAMERA 1 ===
    with col1:
        st.markdown('<div class="glass-card" style="padding:15px; margin-bottom:20px;">', unsafe_allow_html=True)
        st.markdown('<div style="color:#94a3b8; font-size:0.9rem; font-weight:700; margin-bottom:10px;">🔴 LIVE CAM 01 (Gate A)</div>', unsafe_allow_html=True)
        # 이미지 태그 대신 실제 환경에서는 st.image나 비디오 스트림 URL을 사용하세요.
        # 여기서는 레이아웃 예시를 위해 플레이스홀더를 사용합니다.
        st.markdown(
            f'<img src="http://127.0.0.1:8000/video_feed/1" width="100%" style="border-radius:8px; min-height:200px; background:#000;">', 
            unsafe_allow_html=True
        )
        st.markdown('</div>', unsafe_allow_html=True)
        # 높이를 조금 더 넉넉하게 줍니다 (카드 내부 패딩 고려)
        components.html(make_graph_html(cam_id=1, title="Gate A 혼잡도"), height=400)

    # === [오른쪽] CAMERA 2 ===
    with col2:
        st.markdown('<div class="glass-card" style="padding:15px; margin-bottom:20px;">', unsafe_allow_html=True)
        st.markdown('<div style="color:#94a3b8; font-size:0.9rem; font-weight:700; margin-bottom:10px;">🔴 LIVE CAM 02 (Gate B)</div>', unsafe_allow_html=True)
        st.markdown(
            f'<img src="http://127.0.0.1:8000/video_feed/2" width="100%" style="border-radius:8px; min-height:200px; background:#000;">', 
            unsafe_allow_html=True
        )
        st.markdown('</div>', unsafe_allow_html=True)
        components.html(make_graph_html(cam_id=2, title="Gate B 혼잡도"), height=400)

# --------------------------------------------------------------------------------
# 5. 사이드 패널
# --------------------------------------------------------------------------------
with col_side:
    kpi_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&family=JetBrains+Mono:wght@400;700&display=swap');
            body {{ margin: 0; overflow: hidden; background: transparent; font-family: 'Inter', sans-serif; }}
            .glass-card {{
                background: #1e293b;
                border: 1px solid #334155;
                border-radius: 16px;
                padding: 24px;
                box-shadow: 0 4px 30px rgba(0, 0, 0, 0.2);
                color: #cbd5e1;
            }}
            .kpi-row {{ margin-bottom: 20px; }}
            .kpi-row:last-child {{ margin-bottom: 0; }}
            
            .kpi-label {{ 
                font-size: 0.75rem; 
                color: #64748b; 
                text-transform: uppercase; 
                letter-spacing: 0.05em; 
                margin-bottom: 5px; 
                font-weight: 600;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }}
            .kpi-value {{ 
                font-family: 'JetBrains Mono', monospace; 
                font-size: 1.8rem; 
                font-weight: 700; 
                color: #38bdf8; 
                text-shadow: 0 0 20px rgba(56, 189, 248, 0.05); 
                transition: color 0.3s ease;
            }}
            .kpi-sub {{ font-size: 0.75rem; margin-top: 2px; color: #94a3b8; opacity: 0.8; }}
            
            /* 구분선 */
            .divider {{ 
                height: 1px; 
                background: rgba(255,255,255,0.1); 
                margin: 20px 0; 
            }}
        </style>
    </head>
    <body>
        <div class="glass-card">
            
            <div class="kpi-row">
                <div class="kpi-label">
                    <span>GATE A</span> <span style="font-size:0.6rem; opacity:0.5;">CAM 1</span>
                </div>
                <div id="wait-1" class="kpi-value">-- min</div>
                <div id="sub-1" class="kpi-sub">Waiting for data...</div>
            </div>

            <div class="divider"></div>

            <div class="kpi-row">
                <div class="kpi-label">
                    <span>GATE B</span> <span style="font-size:0.6rem; opacity:0.5;">CAM 2</span>
                </div>
                <div id="wait-2" class="kpi-value">-- min</div>
                <div id="sub-2" class="kpi-sub">Waiting for data...</div>
            </div>

        </div>

        <script>
            const ws = new WebSocket("{WS_URL}");
            
            ws.onmessage = (event) => {{
                const msg = JSON.parse(event.data);
                const camId = msg.cam_id;
                const people = msg.people || 0;
                
                // 대기시간 계산 (1인당 0.8분)
                const waitTime = Math.ceil(people * 1.5);
                
                // 업데이트할 Element 찾기 (wait-1 또는 wait-2)
                const valEl = document.getElementById("wait-" + camId);
                const subEl = document.getElementById("sub-" + camId);
                
                if(valEl) {{
                    valEl.innerText = waitTime + " min";
                    subEl.innerText = "Current Load: " + people + " PAX";
                    
                    // 색상 변경 로직 (4명 이상 = 빨간색)
                    if(people >= 4) {{
                        valEl.style.color = "#f43f5e"; // Red
                        valEl.style.textShadow = "0 0 15px rgba(244, 63, 94, 0.6)";
                        subEl.style.color = "#f43f5e";
                    }} else {{
                        valEl.style.color = "#38bdf8"; // Blue
                        valEl.style.textShadow = "0 0 20px rgba(56, 189, 248, 0.05)";
                        subEl.style.color = "#94a3b8";
                    }}
                }}
            }};
        </script>
    </body>
    </html>
    """
    st.components.v1.html(kpi_html, height=280)

    # 버튼
    st.markdown("""
        <div style="text-align: center; margin-top: 20px;">
            <a href="ai_forecast" target="_self" style="text-decoration: none;">
                <button style="
                    width: 100%;
                    background-color: rgba(56, 189, 248, 0.1);
                    color: #38bdf8;
                    border: 1px solid #38bdf8;
                    padding: 12px 0;
                    border-radius: 8px;
                    font-weight: 700;
                    cursor: pointer;
                    transition: all 0.3s ease;
                " onmouseover="this.style.backgroundColor='rgba(56, 189, 248, 0.2)'" onmouseout="this.style.backgroundColor='rgba(56, 189, 248, 0.1)'">
                    AI 예측 상세 →
                </button>
            </a>
        </div>
    """, unsafe_allow_html=True)

# --------------------------------------------------------------------------------
# 6. 푸터
# --------------------------------------------------------------------------------
st.markdown("""
    <div style="text-align: center; margin-top: 40px; border-top: 1px solid rgba(255,255,255,0.05); padding-top: 20px;">
        <span style="font-size: 0.75rem; color: #475569;">
            AIRPORT DIGITAL TWIN DASHBOARD © 2024
        </span>
    </div>
""", unsafe_allow_html=True)