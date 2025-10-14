from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session
from dotenv import load_dotenv
from db import get_db

load_dotenv()
app = FastAPI(title="Airport DT Backend")

@app.get("/health")
def health(db: Session = Depends(get_db)):
    v = db.execute(text("SELECT VERSION()")).scalar()
    return {"ok": True, "mysql_version": v}

# 1) 비전 데이터 수집
@app.post("/ingest/vision")
def ingest_vision(sensor_id: int, value: float, db: Session = Depends(get_db)):
    sql = text("""
      INSERT INTO vision_reading (sensor_id, ts_utc, metric, value_double)
      VALUES (:sid, UTC_TIMESTAMP(), 'PEOPLE', :val)
    """)
    db.execute(sql, {"sid": sensor_id, "val": value})
    db.commit()
    return {"status": "ok"}

# 2) 구역별 최근 PEOPLE 값
@app.get("/areas/{code}/latest")
def area_latest_people(code: str, db: Session = Depends(get_db)):
    sql = text("""
      SELECT a.area_id, a.code, v.sensor_id, v.ts_utc, v.value_double AS people
      FROM area a
      JOIN sensor s ON s.area_id = a.area_id
      JOIN (
        SELECT vr.sensor_id, MAX(vr.ts_utc) AS latest_ts
        FROM vision_reading vr
        WHERE vr.metric='PEOPLE'
        GROUP BY vr.sensor_id
      ) t ON t.sensor_id = s.sensor_id
      JOIN vision_reading v
        ON v.sensor_id = s.sensor_id
       AND v.ts_utc   = t.latest_ts
       AND v.metric   = 'PEOPLE'
      WHERE a.code = :code
      LIMIT 1
    """)
    r = db.execute(sql, {"code": code}).mappings().first()
    if not r:
        raise HTTPException(404, "no data")
    return dict(r)

# 3) 최근 5분 평균(라인차트용)
@app.get("/areas/{code}/trend")
def area_people_trend_5min(code: str, db: Session = Depends(get_db)):
    sql = text("""
      SELECT DATE_FORMAT(vr.ts_utc, '%Y-%m-%d %H:%i:00') AS minute_bucket,
             AVG(vr.value_double) AS people_avg
      FROM area a
      JOIN sensor s ON s.area_id = a.area_id
      JOIN vision_reading vr ON vr.sensor_id = s.sensor_id AND vr.metric='PEOPLE'
      WHERE a.code = :code
        AND vr.ts_utc >= DATE_SUB(UTC_TIMESTAMP(), INTERVAL 5 MINUTE)
      GROUP BY minute_bucket
      ORDER BY minute_bucket
    """)
    rows = db.execute(sql, {"code": code}).mappings().all()
    return [dict(r) for r in rows]
