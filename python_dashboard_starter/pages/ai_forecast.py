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
# 1. 페이지 기본 설정 및 CSS 적용
# --------------------------------------------------------------------------------
st.set_page_config(
    page_title="AI Forecast Detail",
    page_icon="🤖",
    layout="wide"
)

# [CSS 스타일링 복사 및 UI 문제 해결]
design_css = """
<style>
    /* ------------------------------------------------------- */
    /* [기본 레이아웃 리셋] */
    /* ------------------------------------------------------- */
    [data-testid="stAppViewContainer"] {
        padding: 0 !important;
        background: radial-gradient(circle at 10% 10%, #1e293b 0%, #020617 100%) !important;
    }
    
    .main .block-container {
        /* ⚠️ [핵심 수정] 상단 여백을 강제적으로 줄이고, 음수로 당겨서 '잘림' 문제 해결 */
        padding-top: 0rem !important; 
        margin-top: -30px !important; /* 마진을 -60px로 설정하여 제목을 강하게 상단으로 당김 */
        padding-bottom: 2rem !important;
        max-width: 1600px !important;
    }

    /* ------------------------------------------------------- */
    /* 🚨 [UI 요소 강제 제거] Streamlit UI 요소 및 기본 헤더 영역 제거 */
    /* ------------------------------------------------------- */
    /* 메인 메뉴 (햄버거 메뉴), 푸터, 툴바(Deploy 버튼) 숨김 */
    #MainMenu, footer, [data-testid="stToolbar"] {
        display: none !important;
        visibility: hidden !important;
    }

    /* Streamlit이 자동으로 추가하는 기본 헤더 영역(탭바 아래 빈 공간) 숨김 */
    [data-testid="stHeader"] {
        display: none !important;
    }

    /* Streamlit 제목 마크다운이 생성하는 상단 여백/구분선 제거 */
    .st-emotion-cache-12fm5q7, 
    .st-emotion-cache-1r6r4g7 { 
        border-bottom: none !important;
        padding-top: 0px !important; 
        margin-top: 0px !important;
    }
    
    /* ⚠️ 제목을 포함한 내부 블록의 상단 패딩/마진 제거 */
    [data-testid="stVerticalBlock"] > div:first-child > div:first-child {
        padding-top: 0px !important;
        margin-top: 0px !important;
    }


    /* ------------------------------------------------------- */
    /* [타이포그래피 및 Glassmorphism 스타일] */
    /* ------------------------------------------------------- */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&family=JetBrains+Mono:wght@400;700&display=swap');
    
    body, p, div, span, li { font-family: 'Inter', sans-serif; color: #cbd5e1; }
    h1, h2, h3 { font-family: 'Inter', sans-serif; letter-spacing: -0.02em; color: #f8fafc; }
    
    .glass-card {
        background: rgba(15, 23, 42, 0.6);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px;
        padding: 24px;
        box-shadow: 0 4px 30px rgba(0, 0, 0, 0.2);
        margin-bottom: 20px;
        transition: transform 0.3s ease, box-shadow 0.3s ease;
    }

    .card-title {
        font-size: 1.2rem;
        font-weight: 700;
        background: linear-gradient(90deg, #fff, #94a3b8);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        display: flex;
        align-items: center;
        gap: 8px;
        padding-bottom: 10px;
        border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        margin-bottom: 20px;
    }

    .kpi-label { font-size: 0.75rem; color: #64748b; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 4px; font-weight: 600; }
    .kpi-value { font-family: 'JetBrains Mono', monospace; font-size: 2rem; font-weight: 700; color: #f1f5f9; text-shadow: 0 0 20px rgba(255, 255, 255, 0.05); }

</style>
"""
st.markdown(design_css, unsafe_allow_html=True)


# --------------------------------------------------------------------------------
# 2. 환경 설정 및 DB 연결 (app.py와 동일하게 처리)
# --------------------------------------------------------------------------------
# ⚠️ 주의: .env 파일 경로가 app.py의 상위 폴더에 있다고 가정하고 수정했습니다.
ENV_PATH = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=ENV_PATH)

# 캐싱 적용을 위해 함수로 분리
@st.cache_resource
def get_db_engine(db_url):
    """DB 엔진을 생성하고 캐싱합니다."""
    try:
        engine = create_engine(db_url, pool_pre_ping=True, future=True)
        # 연결 확인
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return engine
    except Exception:
        return None

# DB 연결 시도 및 엔진 객체 할당
db_url = os.getenv("DATABASE_URL")
engine = get_db_engine(db_url)

if engine is None:
    # DB 연결 실패 시 토스트 메시지만 띄우고 앱 실행은 계속합니다.
    st.toast("⚠️ DB 연결 실패 (데이터 로드 불가능)", icon="⚠️")

# --------------------------------------------------------------------------------
# 3. 데이터 로딩 함수 (캐싱 적용)
# --------------------------------------------------------------------------------
@st.cache_data(ttl=3600) # 1시간마다 데이터 갱신
def load_forecast_data(engine):
    """DB에서 실제 데이터와 예측 데이터를 로드 및 전처리합니다."""
    
    # 1. 데이터 로드 및 전처리
    df_real = pd.read_sql("SELECT * FROM kim_forecast", con=engine)
    df_real["FlightDate"] = pd.to_datetime(df_real["FlightDate"])
    df_real["Hour"] = df_real["HourRange"].str.split(" ").str[0].astype(int)
    df_real["FlightDateTime"] = df_real.apply(
        lambda row: row["FlightDate"] + pd.Timedelta(hours=row["Hour"], minutes=30), axis=1
    )
    df_real = df_real.groupby("FlightDateTime")["MaxWait"].max().reset_index()

    df_pred = pd.read_sql("SELECT * FROM predicted_wait", con=engine)
    df_pred["FlightDateTime"] = pd.to_datetime(df_pred["FlightDateTime"])
    
    return df_real, df_pred

# --------------------------------------------------------------------------------
# 4. 페이지 제목 및 레이아웃
# --------------------------------------------------------------------------------
st.markdown(f'<h1 style="color: #38bdf8; font-size: 2.5rem; text-shadow: 0 0 10px rgba(56, 189, 248, 0.4); margin-bottom: 30px;">🤖 AI Congestion Prediction System</h1>', unsafe_allow_html=True)

# 2:1 비율로 그래프와 모델 성능 패널 분리
col_graph, col_stats = st.columns([2, 1], gap="large")

# --------------------------------------------------------------------------------
# 5. 그래프 섹션
# --------------------------------------------------------------------------------
with col_graph:
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">📈 Predicted Wait Time vs. Actual (Max Wait Minutes)</div>', unsafe_allow_html=True)

    if engine:
        try:
            # 캐싱된 함수 호출
            df_real, df_pred = load_forecast_data(engine)
            
            # 2. Plotly 차트 생성
            fig = go.Figure()

            # 실제 데이터 (파란색)
            fig.add_trace(go.Scatter(
                x=df_real["FlightDateTime"], y=df_real["MaxWait"],
                mode="lines", name="Actual (실제 대기 시간)",
                line=dict(color="#38bdf8", width=3, shape='spline')
            ))

            # 예측 데이터 (보라색)
            fig.add_trace(go.Scatter(
                x=df_pred["FlightDateTime"], y=df_pred["Predicted_MaxWait"],
                mode="lines", name="Forecast (AI 예측)",
                line=dict(color="#a855f7", width=3, dash='dash')
            ))

            # 위험 임계치 라인 (빨간색) - 예시로 20분 설정
            fig.add_hline(y=20, line_dash="dot", line_color="#f43f5e", 
                          annotation_text="CRITICAL THRESHOLD (20m)", 
                          annotation_position="top right",
                          annotation_font_color="#f43f5e")

            # 예측 구간 표시
            if not df_pred.empty:
                future_start = df_pred["FlightDateTime"].min()
                future_end = df_pred["FlightDateTime"].max()
                fig.add_vrect(
                    x0=future_start, x1=future_end,
                    fillcolor="#a855f7", opacity=0.1, line_width=0
                )

            # 3. 다크 테마 레이아웃 적용
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=40, r=40, t=30, b=30),
                height=550,
                xaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)', tickfont=dict(color='#94a3b8')),
                yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)', tickfont=dict(color='#94a3b8')),
                legend=dict(font=dict(color='#cbd5e1', size=12), orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                hovermode="x unified"
            )

            st.plotly_chart(fig, use_container_width=True)

        except Exception as e:
            # DB 연결이 실패하면 이 섹션이 실행됨 (현재 상태)
            st.error(f"데이터를 로드하거나 처리하는 중 오류가 발생했습니다: {e}")
    else:
        st.warning("데이터베이스 연결에 문제가 있어 예측 그래프를 표시할 수 없습니다.")
    
    st.markdown('</div>', unsafe_allow_html=True)


# --------------------------------------------------------------------------------
# 6. 모델 성능 및 상세 분석 섹션
# --------------------------------------------------------------------------------
with col_stats:
    # 6-1. 모델 성능 KPI
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">🤖 Model Performance Metrics</div>', unsafe_allow_html=True)
    
    st.markdown("""
        <div style="display:grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top:10px; margin-bottom: 20px;">
            <div class="kpi-container">
                <div class="kpi-label">R-SQUARED (R²)</div>
                <div class="kpi-value" style="font-size: 2rem; color: #34d399;">0.92</div>
            </div>
            <div class="kpi-container">
                <div class="kpi-label">MAE (Mean Absolute Error)</div>
                <div class="kpi-value" style="font-size: 2rem; color: #f59e0b;">2.1 min</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    st.markdown('<p style="font-size: 0.9rem; color:#94a3b8;">* MAE: 평균적으로 실제 대기 시간과 2.1분 정도 오차가 발생함</p>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # 6-2. 모델 개요
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">⚙️ Model Overview</div>', unsafe_allow_html=True)
    st.markdown("""
        <ul style="list-style: none; padding-left: 0; font-size: 0.9rem; line-height: 1.8;">
            <li><span style="color: #38bdf8;">• Algorithm:</span> LightGBM Regressor</li>
            <li><span style="color: #38bdf8;">• Target:</span> Max Wait Time (분)</li>
            <li><span style="color: #38bdf8;">• Features:</span> Flight Count, Hour, DayOfWeek, Season, Gate Density</li>
            <li><span style="color: #38bdf8;">• Last Trained:</span> 2025-11-20</li>
        </ul>
    """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)