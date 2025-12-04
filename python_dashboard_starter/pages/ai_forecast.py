import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
from dotenv import load_dotenv
from pathlib import Path
import os
from sqlalchemy import create_engine, text

# --------------------------------------------------------------------------------
# 1. 페이지 설정
# --------------------------------------------------------------------------------
st.set_page_config(page_title="AI 미래 혼잡도 예측", layout="wide")

# CSS 로드 (외부 파일 의존성 제거 -> 코드 내장형으로 변경)
def load_shared_css():
    st.markdown("""
    <style>
        /* [1] 전체 배경 강제 적용 (다크 모드 느낌) */
        .stApp {
            background-color: #0f172a;
            color: #f8fafc;
        }

        /* [2] 상단 여백 조정 */
        .block-container { padding-top: 2rem; }
        
        /* [3] 카드 스타일 (진한 남색 유리 질감) */
        .glass-card {
            background-color: #1e293b;
            border: 1px solid #334155;
            padding: 25px;
            border-radius: 15px;
            margin-bottom: 25px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
        }
        
        /* [4] 카드 제목 스타일 */
        .card-title {
            font-size: 1.4rem;
            font-weight: bold;
            margin-bottom: 20px;
            color: #f8fafc;
            border-left: 5px solid #38bdf8; /* 파란색 포인트 선 */
            padding-left: 15px;
        }

        /* [5] 입력창(달력/시간) 감싸는 박스 스타일 */
        .control-panel {
            background-color: rgba(56, 189, 248, 0.05); /* 아주 연한 파랑 */
            border: 2px solid #38bdf8; /* 파란색 테두리 */
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
        }
        
        /* [6] 입력창 라벨(글씨) 강제 스타일링 (잘 보이게) */
        .stDateInput label p, .stSlider label p {
            font-size: 1.1rem !important;
            font-weight: bold !important;
            color: #e2e8f0 !important; /* 밝은 회색 */
        }
    </style>
    """, unsafe_allow_html=True)

load_shared_css()

# --------------------------------------------------------------------------------
# 2. DB 연결 및 데이터 로드
# --------------------------------------------------------------------------------
ENV_PATH = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=ENV_PATH)

@st.cache_resource
def get_db_engine(db_url):
    try:
        if not db_url: return None
        engine = create_engine(db_url, pool_pre_ping=True, future=True)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return engine
    except Exception:
        return None

db_url = os.getenv("DATABASE_URL")
engine = get_db_engine(db_url)

@st.cache_data(ttl=3600)
def load_forecast_data(_engine):
    # 실제 데이터
    df_real = pd.read_sql("SELECT * FROM kim_forecast", con=_engine)
    df_real["FlightDate"] = pd.to_datetime(df_real["FlightDate"])
    df_real["Hour"] = df_real["HourRange"].str.split(" ").str[0].astype(int)
    df_real["FlightDateTime"] = df_real.apply(
        lambda row: row["FlightDate"] + pd.Timedelta(hours=row["Hour"], minutes=30), axis=1
    )
    df_real = df_real.groupby("FlightDateTime")["MaxWait"].max().reset_index()

    # 예측 데이터
    df_pred = pd.read_sql("SELECT * FROM predicted_wait", con=_engine)
    df_pred["FlightDateTime"] = pd.to_datetime(df_pred["FlightDateTime"])
    
    return df_real, df_pred

if engine is None:
    st.error("⚠️ 데이터베이스 연결 실패")
    st.stop()

# --------------------------------------------------------------------------------
# 3. 메인 화면
# --------------------------------------------------------------------------------
st.markdown(f'<h1 style="color: #38bdf8; margin-bottom: 10px;">✈️ AI 미래 혼잡도 예측 시스템</h1>', unsafe_allow_html=True)
st.markdown('<p style="color: #94a3b8; margin-bottom: 30px;">LightGBM 모델 기반의 예상 대기 시간을 분석합니다.</p>', unsafe_allow_html=True)

try:
    df_real, df_pred = load_forecast_data(engine)
    
    # [A] 전체 추세 그래프
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title"> 전체 기간 예측 추이</div>', unsafe_allow_html=True)

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_real["FlightDateTime"], y=df_real["MaxWait"], mode="lines", name="실제 대기시간", line=dict(color="#38bdf8", width=2), opacity=0.8))
    fig.add_trace(go.Scatter(x=df_pred["FlightDateTime"], y=df_pred["Predicted_MaxWait"], mode="lines", name="AI 예측값", line=dict(color="#ef4444", width=2, dash='solid')))
    
    # [수정] 혼잡 기준선 변경 (20분 -> 100분)
    fig.add_hline(y=100, line_dash="dot", line_color="#fbbf24", annotation_text="혼잡 기준 (100분)", annotation_position="top left", annotation_font_color="#fbbf24")

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=20, r=20, t=20, b=20), height=350,
        xaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.1)', tickfont=dict(color='#cbd5e1')),
        yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.1)', tickfont=dict(color='#cbd5e1'), title="대기 시간(분)"),
        legend=dict(orientation="h", y=1.1, x=1, xanchor="right", font=dict(color="white")),
        hovermode="x unified"
    )
    st.plotly_chart(fig, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # [B] 상세 조회 (원래 디자인 복원 + 시간 기능 유지)
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">날짜 및 시간별 상세 조회</div>', unsafe_allow_html=True)
    
    if not df_pred.empty:
        min_date = df_pred["FlightDateTime"].min().date()
        max_date = df_pred["FlightDateTime"].max().date()
        
        # 컨트롤 패널 (입력창 가시성 확보)
        st.markdown('<div class="control-panel">', unsafe_allow_html=True)
        col_input1, col_input2 = st.columns([1, 2])
        with col_input1:
            selected_date = st.date_input("날짜 선택 (Date)", value=min_date, min_value=min_date, max_value=max_date)
        with col_input2:
            selected_hour = st.slider("시간 선택 (Hour)", min_value=0, max_value=23, value=12, format="%d시")
        st.markdown('</div>', unsafe_allow_html=True)

        # 데이터 필터링
        target_day_df = df_pred[df_pred["FlightDateTime"].dt.date == selected_date]
        target_exact_df = target_day_df[target_day_df["FlightDateTime"].dt.hour == selected_hour]

        # --- 💡 [복원] 원래 박스 디자인 + 시간 데이터 적용 ---
        if not target_exact_df.empty:
            # 선택한 시간의 예측값
            pred_value = target_exact_df["Predicted_MaxWait"].values[0]
            
            # (참고용) 그 날의 통계
            day_max = target_day_df["Predicted_MaxWait"].max()
            day_avg = target_day_df["Predicted_MaxWait"].mean()

            # [수정] 상태 결정 로직 변경 (100분 기준)
            if pred_value >= 130:
                s_title, s_msg, s_color, bg_color = "🚨 매우 혼잡", f"{selected_hour}시 기준, 대기 시간이 100분을 초과할 것으로 보입니다.", "#f43f5e", "rgba(244, 63, 94, 0.1)"
            elif pred_value >= 100: # [수정] 다소 혼잡 기준도 80분으로 상향 조정
                s_title, s_msg, s_color, bg_color = "⚠️ 다소 혼잡", f"{selected_hour}시 기준, 대기 줄이 평소보다 길어질 수 있습니다.", "#fbbf24", "rgba(251, 191, 36, 0.1)"
            else:
                s_title, s_msg, s_color, bg_color = "✅ 원활", f"{selected_hour}시 기준, 쾌적한 출국이 예상됩니다.", "#34d399", "rgba(52, 211, 153, 0.1)"

            # 원래 스타일 HTML 렌더링
            st.markdown(f"""
            <div style="background-color: {bg_color}; border: 2px solid {s_color}; border-radius: 12px; padding: 25px;">
                <h3 style="color: {s_color}; margin: 0; font-size: 1.8rem;">{s_title}</h3>
                <p style="color: #e2e8f0; font-size: 1.1rem; margin-top: 5px;">{s_msg}</p>
                <hr style="border-color: rgba(255,255,255,0.2); margin: 20px 0;">
                <div style="display: flex; justify-content: space-around; text-align: center;">
                    <div>
                        <span style="color:#94a3b8; font-size: 1rem;">선택 시간({selected_hour}시) 대기</span><br>
                        <span style="font-size:2.2rem; font-weight:bold; color:white">{pred_value:.0f}분</span>
                    </div>
                    <div style="border-left: 1px solid rgba(255,255,255,0.2); padding-left: 30px;">
                        <span style="color:#94a3b8; font-size: 1rem;">이 날의 최대(Peak)</span><br>
                        <span style="font-size:1.5rem; font-weight:bold; color:#cbd5e1">{day_max:.0f}분</span>
                    </div>
                    <div style="border-left: 1px solid rgba(255,255,255,0.2); padding-left: 30px;">
                        <span style="color:#94a3b8; font-size: 1rem;">이 날의 평균</span><br>
                        <span style="font-size:1.5rem; font-weight:bold; color:#cbd5e1">{day_avg:.0f}분</span>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        else:
            st.warning(f"⚠️ {selected_date} {selected_hour}시의 예측 데이터가 없습니다.")
    
    st.markdown('</div>', unsafe_allow_html=True)

except Exception as e:
    st.error(f"시스템 오류 발생: {e}")