# db.py
import os
import urllib.parse
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# ✅ .env 불러오기
load_dotenv()

# ✅ 환경 변수 가져오기
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_USER = os.getenv("DB_USER")
DB_PASS = urllib.parse.quote_plus(os.getenv("DB_PASS"))
DB_NAME = os.getenv("DB_NAME")

# ✅ SQLAlchemy DB URL 생성
DB_URL = f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(DB_URL)

# ---------------------------------------------------
# ✅ DB 연결 테스트
# ---------------------------------------------------
def test_connection():
    """DB 연결 확인"""
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT NOW();"))
            print("✅ DB 연결 성공:", list(result))
    except Exception as e:
        print("❌ DB 연결 실패:", e)


# ---------------------------------------------------
# ✅ CSV → MySQL 업로드
# ---------------------------------------------------
def upload_csv_to_db(csv_path, table_name):
    """CSV 파일을 MySQL 테이블로 업로드 (기존 테이블 덮어쓰기)"""
    try:
        df = pd.read_csv(csv_path, encoding='utf-8-sig')
        print(f"📄 CSV 불러오기 성공: {csv_path}")
        print(f"컬럼: {list(df.columns)}")

        # 기존 테이블 제거
        with engine.begin() as conn:
            conn.execute(text(f"DROP TABLE IF EXISTS {table_name};"))
            print(f"🗑 기존 '{table_name}' 테이블 삭제됨.")

        # 기본키용 id 컬럼 추가
        df.insert(0, 'id', range(1, len(df) + 1))
        df.to_sql(table_name, con=engine, if_exists='replace', index=False)
        print(f"✅ '{table_name}' 테이블 업로드 완료.")
    except Exception as e:
        print("❌ 업로드 중 오류:", e)


# ---------------------------------------------------
# 실행 예시
# ---------------------------------------------------
if __name__ == "__main__":
    test_connection()
    # upload_csv_to_db("Awt.cbp.gov_LAX_2024-11-01_to_2025-10-31.csv", "passenger_forecast")
