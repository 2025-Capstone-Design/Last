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
# 1. 페이지 기본 설정 및 CSS 로드
# --------------------------------------------------------------------------------
st.set_page_config(
    page_title="AI 미래 혼잡도 예측",
    layout="wide"
)

# [CSS 로드 함수] 부모 디렉토리의 style.css 파일을 찾아서 적용
def load_shared_css():
    try:
        # 현재 파일(pages/ai_forecast.py)의 부모(pages)의 부모(root)에 있는 style.css 경로
        css_path = Path(__file__).parent.parent / "style.css"
        
        with open(css_path, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        st.error("⚠️ style.css 파일을 찾을 수 없습니다. 경로를 확인해주세요.")

load_shared_css()

# --------------------------------------------------------------------------------  
# 2. 환경 설정 및 DB 연결
# --------------------------------------------------------------------------------
# .env 파일 경로: 현재 파일의 상위(pages)의 상위(root) 폴더
ENV_PATH = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=ENV_PATH)

# 캐싱 적용을 위해 함수로 분리
@st.cache_resource
def get_db_engine(db_url):
    """DB 엔진을 생성하고 캐싱합니다."""
    try:
        if not db_url: return None
        engine = create_engine(db_url, pool_pre_ping=True, future=True)
        # 연결 확인
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return engine
    except Exception:
        return None

# DB 연결 시도
db_url = os.getenv("DATABASE_URL")
engine = get_db_engine(db_url)

# --------------------------------------------------------------------------------
# 3. 데이터 로딩 함수 (캐싱 적용)
# --------------------------------------------------------------------------------
@st.cache_data(ttl=3600) # 1시간마다 데이터 갱신
def load_forecast_data(_engine):
    """DB에서 실제 데이터와 예측 데이터를 로드 및 전처리합니다."""
    
    # 실제 데이터 로드
    df_real = pd.read_sql("SELECT * FROM kim_forecast", con=_engine)
    df_real["FlightDate"] = pd.to_datetime(df_real["FlightDate"])
    df_real["Hour"] = df_real["HourRange"].str.split(" ").str[0].astype(int)
    df_real["FlightDateTime"] = df_real.apply(
        lambda row: row["FlightDate"] + pd.Timedelta(hours=row["Hour"], minutes=30), axis=1
    )
    df_real = df_real.groupby("FlightDateTime")["MaxWait"].max().reset_index()

    # 예측 데이터 로드
    df_pred = pd.read_sql("SELECT * FROM predicted_wait", con=_engine)
    df_pred["FlightDateTime"] = pd.to_datetime(df_pred["FlightDateTime"])
    
    return df_real, df_pred

# DB 연결 실패 시 처리
if engine is None:
    st.toast("⚠️ DB 연결 실패 (데이터 로드 불가능)", icon="⚠️")


# --------------------------------------------------------------------------------
# 4. 페이지 제목 및 레이아웃
# --------------------------------------------------------------------------------
st.markdown(f'<h1 style="color: #38bdf8; font-size: 2.5rem; text-shadow: 0 0 10px rgba(56, 189, 248, 0.4); margin-bottom: 30px;">미래 혼잡도 예측 시스템</h1>', unsafe_allow_html=True)

# 2:1 비율로 그래프와 모델 성능 패널 분리
col_graph, col_stats = st.columns([2, 1], gap="large")

# --------------------------------------------------------------------------------
# 5. 그래프 섹션
# --------------------------------------------------------------------------------
with col_graph:
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title"> 과거데이터와 미래 예측 그래프 (Max Wait Minutes)</div>', unsafe_allow_html=True)

    if engine:
        try:
            # 캐싱된 함수 호출
            df_real, df_pred = load_forecast_data(engine)
            
            # Plotly 차트 생성
            fig = go.Figure()

            # 실제 데이터 (파란색)
            fig.add_trace(go.Scatter(
                x=df_real["FlightDateTime"], y=df_real["MaxWait"],
                mode="lines", name="Actual (실제 대기 시간)",
                line=dict(color="#38bdf8", width=3, shape='spline')
            ))

            # 예측 데이터 (빨간색 점선)
            fig.add_trace(go.Scatter(
                x=df_pred["FlightDateTime"], y=df_pred["Predicted_MaxWait"],
                mode="lines", name="Forecast (AI 예측)",
                line=dict(color="#ef4444", width=3, dash='dash')
            ))

            # 위험 임계치 라인 (20분)
            fig.add_hline(y=20, line_dash="dot", line_color="#f43f5e", 
                          annotation_text="CRITICAL THRESHOLD (20m)", 
                          annotation_position="top right",
                          annotation_font_color="#f43f5e")

            # 예측 구간 표시 영역
            if not df_pred.empty:
                future_start = df_pred["FlightDateTime"].min()
                future_end = df_pred["FlightDateTime"].max()
                fig.add_vrect(
                    x0=future_start, x1=future_end,
                    fillcolor="#ef4444", opacity=0.1, line_width=0
                )

            # 다크 테마 레이아웃 및 슬라이더 설정
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=40, r=40, t=30, b=30),
                height=550,
                dragmode="pan", 
                xaxis=dict(
                    showgrid=True, 
                    gridcolor='rgba(255,255,255,0.05)', 
                    tickfont=dict(color='#94a3b8'),
                    rangeslider=dict(
                        visible=True,
                        bgcolor="rgba(15, 23, 42, 0.5)",
                        bordercolor="#334155",
                        thickness=0.05
                    ),
                    type="date"
                ),
                yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)', tickfont=dict(color='#94a3b8')),
                legend=dict(font=dict(color='#cbd5e1', size=12), orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                hovermode="x unified"
            )

            # 줌/팬 설정
            st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True})

        except Exception as e:
            st.error(f"데이터 처리 중 오류 발생: {e}")
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