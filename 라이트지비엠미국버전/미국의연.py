# =====================================================
# ✈️ LightGBM 예측 (DB → 모델 → DB 저장)
# =====================================================
import pandas as pd
import numpy as np
import lightgbm as lgb
import warnings
import os, urllib.parse
from sqlalchemy import create_engine, Integer, DateTime, Float, Column, MetaData, Table, text
from dotenv import load_dotenv

warnings.filterwarnings('ignore', category=pd.errors.SettingWithCopyWarning)
warnings.filterwarnings('ignore', category=UserWarning)

# ----------------------------------------------------
# 1️⃣ 환경 설정 및 DB 연결
# ----------------------------------------------------
load_dotenv()  # .env 파일에서 DB 환경변수 불러오기

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_USER = os.getenv("DB_USER")
DB_PASS = urllib.parse.quote_plus(os.getenv("DB_PASS"))
DB_NAME = os.getenv("DB_NAME")

DB_URL = f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(DB_URL)

# ----------------------------------------------------
# 2️⃣ DB에서 데이터 로드
# ----------------------------------------------------
TABLE_NAME = "kim_forecast"  # ✅ 학습 데이터 테이블명
TARGET = 'MaxWait'
PREDICTION_START_DATE = '2025-11-01 00:00:00'
PREDICTION_END_DATE = '2026-10-31 23:00:00'
LAGS = [24, 24 * 7]  # 시계열 Lag Feature

try:
    query = f"SELECT * FROM {TABLE_NAME};"
    df_raw = pd.read_sql(query, con=engine)
    print(f"✅ DB '{TABLE_NAME}' 테이블에서 데이터 불러오기 성공 ({df_raw.shape[0]} rows)")
except Exception as e:
    print("❌ DB 데이터 불러오기 실패:", e)
    exit()

# ----------------------------------------------------
# 3️⃣ LightGBM 학습용 데이터 전처리
# ----------------------------------------------------
df_raw['FlightDate'] = pd.to_datetime(df_raw['FlightDate'])
df_raw['Hour'] = df_raw['HourRange'].str.split(' ').str[0].astype(int)
df_raw['FlightDateTime'] = df_raw.apply(
    lambda row: row['FlightDate'] + pd.Timedelta(hours=row['Hour'], minutes=30),
    axis=1
)
df_agg = df_raw.groupby('FlightDateTime')[TARGET].max().reset_index()

df_original_for_plot = df_agg.copy().rename(columns={TARGET: 'Actual_MaxWait_Original'})
df = df_agg.rename(columns={TARGET: TARGET})

future_start_dt = pd.to_datetime(PREDICTION_START_DATE)

# 이상치 처리 (상위 1% Capping)
train_df_for_outlier = df[df['FlightDateTime'] < future_start_dt].copy()
threshold = train_df_for_outlier[TARGET].quantile(0.99)
print(f"💡 LightGBM 학습용 MaxWait 이상치 제거 임계값 (상위 1%): {threshold:.0f}분")
df[TARGET] = np.where(df[TARGET] > threshold, threshold, df[TARGET])

# 시간 관련 Feature
df['Year'] = df['FlightDateTime'].dt.year
df['Month'] = df['FlightDateTime'].dt.month
df['Day'] = df['FlightDateTime'].dt.day
df['DayOfWeek'] = df['FlightDateTime'].dt.dayofweek
df['Hour'] = df['FlightDateTime'].dt.hour
df['WeekOfYear'] = df['FlightDateTime'].dt.isocalendar().week.astype(int)

# Historical Max Feature
train_df_temp = df[df['FlightDateTime'] < future_start_dt].copy()
max_potential = train_df_temp.groupby(['DayOfWeek', 'Hour'])[TARGET].max().reset_index()
max_potential.rename(columns={TARGET: f'{TARGET}_Historical_Max'}, inplace=True)
df = pd.merge(df, max_potential, on=['DayOfWeek', 'Hour'], how='left')

# Lagged Feature
df_train_only = df[df['FlightDateTime'] < future_start_dt].copy()
for lag in LAGS:
    df_train_only[f'{TARGET}_Lag_{lag}'] = df_train_only[TARGET].shift(lag)

df = pd.merge(
    df,
    df_train_only[[f'{TARGET}_Lag_{lag}' for lag in LAGS] + ['FlightDateTime']],
    on='FlightDateTime',
    how='left'
)
df.dropna(subset=[f'{TARGET}_Lag_{lag}' for lag in LAGS], inplace=True)

# Feature Set 구성
LAGGED_FEATURES = [f'{TARGET}_Lag_{lag}' for lag in LAGS]
CONTEXTUAL_FEATURE = [f'{TARGET}_Historical_Max']
PURE_TIME_FEATURES = ['Month', 'Day', 'DayOfWeek', 'Hour', 'WeekOfYear']
ALL_FEATURES = PURE_TIME_FEATURES + LAGGED_FEATURES + CONTEXTUAL_FEATURE
CATEGORICAL_FEATURES = ['Month', 'DayOfWeek', 'Hour']
for col in CATEGORICAL_FEATURES:
    df[col] = df[col].astype('category')

# ----------------------------------------------------
# 4️⃣ LightGBM 모델 학습
# ----------------------------------------------------
train_df = df[df['FlightDateTime'] < future_start_dt].copy()
X_train = train_df[ALL_FEATURES]
y_train = train_df[TARGET]

print("🚀 LightGBM 모델 학습 시작...")
lgbm = lgb.LGBMRegressor(
    objective='rmse',
    n_estimators=1000,
    learning_rate=0.02,
    num_leaves=31,
    random_state=42,
    n_jobs=-1,
    metric='rmse',
    categorical_feature=CATEGORICAL_FEATURES,
    lambda_l1=0.5,
    lambda_l2=0.5,
    min_child_samples=30
)
lgbm.fit(X_train, y_train)
print("✅ LightGBM 모델 학습 완료.")

# ----------------------------------------------------
# 5️⃣ 예측 결과 생성
# ----------------------------------------------------
future_end_dt = pd.to_datetime(PREDICTION_END_DATE)
future_index = pd.date_range(start=future_start_dt, end=future_end_dt, freq='h')

future_df = pd.DataFrame(index=future_index)
future_df.index.name = 'FlightDateTime'

future_df['Month'] = future_df.index.month
future_df['Day'] = future_df.index.day
future_df['DayOfWeek'] = future_df.index.dayofweek
future_df['Hour'] = future_df.index.hour
future_df['WeekOfYear'] = future_df.index.isocalendar().week.astype(int)
future_df = pd.merge(
    future_df.reset_index(),
    max_potential,
    on=['DayOfWeek', 'Hour'],
    how='left'
).set_index('FlightDateTime')

all_data = pd.concat([df.set_index('FlightDateTime'), future_df])
train_df_index = df.set_index('FlightDateTime')

INITIAL_STABILIZATION_PERIOD = 24 * 7
train_df_last_168 = train_df_index.iloc[-INITIAL_STABILIZATION_PERIOD:]

print("🔄 재귀적 예측 중...")

for i in range(len(future_df)):
    current_dt = future_df.index[i]
    for lag in LAGS:
        past_dt = current_dt - pd.Timedelta(hours=lag)
        if i < INITIAL_STABILIZATION_PERIOD and past_dt in train_df_last_168.index:
            all_data.loc[current_dt, f'{TARGET}_Lag_{lag}'] = train_df_last_168.loc[past_dt, TARGET]
        elif past_dt in all_data.index:
            all_data.loc[current_dt, f'{TARGET}_Lag_{lag}'] = all_data.loc[past_dt, TARGET]

    X_future_row = all_data.loc[[current_dt], ALL_FEATURES]
    if X_future_row[LAGGED_FEATURES].isna().any(axis=1).iloc[0]:
        for lag_col in LAGGED_FEATURES:
            if X_future_row[lag_col].isna().iloc[0]:
                X_future_row.loc[X_future_row.index, lag_col] = X_future_row[f'{TARGET}_Historical_Max'].iloc[0]
    for col in CATEGORICAL_FEATURES:
        X_future_row[col] = X_future_row[col].astype('category')

    pred_value = lgbm.predict(X_future_row)[0]
    all_data.loc[current_dt, TARGET] = pred_value

final_future_predictions = all_data.loc[future_index, TARGET].reset_index().rename(columns={TARGET: 'Predicted_MaxWait'})

# ----------------------------------------------------
# 6️⃣ 예측 결과 DB 저장 (Primary Key 포함)
# ----------------------------------------------------
final_future_predictions.reset_index(inplace=True)
final_future_predictions.rename(columns={'index': 'id'}, inplace=True)
final_future_predictions['id'] = range(1, len(final_future_predictions) + 1)

metadata = MetaData()
predicted_wait_table = Table(
    "predicted_wait",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("FlightDateTime", DateTime),
    Column("Predicted_MaxWait", Float)
)

with engine.connect() as conn:
    conn.execute(text("DROP TABLE IF EXISTS predicted_wait;"))  # ✅ text() 추가
    metadata.create_all(conn)

final_future_predictions.to_sql(
    "predicted_wait",
    con=engine,
    if_exists="append",
    index=False,
    dtype={
        "id": Integer,
        "FlightDateTime": DateTime,
        "Predicted_MaxWait": Float
    }
)

print("✅ 예측 결과가 DB 테이블 'predicted_wait'에 저장되었습니다.")