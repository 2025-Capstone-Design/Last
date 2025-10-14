-- 추천: 문자셋 통일(선택)
-- ALTER DATABASE db211702 CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
show databases;
USE db211702;
SELECT VERSION();    
SELECT sensor_id, name, area_id FROM sensor;
SELECT * FROM vision_reading ORDER BY id DESC LIMIT 5;

show tables;

-- 1) 구역
CREATE TABLE area (
  area_id      BIGINT PRIMARY KEY AUTO_INCREMENT,
  code         VARCHAR(32) NOT NULL UNIQUE,
  name         VARCHAR(128),
  area_type    ENUM('CHECKIN','SECURITY','IMMIGRATION','GATE','BAGGAGE','CONCOURSE','OTHER') NOT NULL,
  roi_json     LONGTEXT NULL
) ENGINE=InnoDB;

-- 2) 센서
CREATE TABLE sensor (
  sensor_id    BIGINT PRIMARY KEY AUTO_INCREMENT,
  area_id      BIGINT NOT NULL,
  sensor_type  ENUM('CAMERA','PEOPLE_COUNTER') NOT NULL DEFAULT 'CAMERA',
  name         VARCHAR(64),
  external_ref VARCHAR(128),
  is_active    TINYINT(1) NOT NULL DEFAULT 1,
  installed_at DATETIME NULL,
  FOREIGN KEY (area_id) REFERENCES area(area_id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- 3) 원시 지표(사람 수 등)
CREATE TABLE vision_reading (
  id           BIGINT PRIMARY KEY AUTO_INCREMENT,
  sensor_id    BIGINT NOT NULL,
  ts_utc       DATETIME(3) NOT NULL,
  metric       ENUM('PEOPLE','QUEUE_LEN','WAIT_SEC_MED','WAIT_SEC_P90') NOT NULL,
  value_double DOUBLE NOT NULL,
  extra_json   LONGTEXT NULL,
  KEY k_sensor_time (sensor_id, ts_utc),
  FOREIGN KEY (sensor_id) REFERENCES sensor(sensor_id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- 4) 평면도 점(투영 좌표)
CREATE TABLE vision_points (
  id         BIGINT PRIMARY KEY AUTO_INCREMENT,
  sensor_id  BIGINT NOT NULL,
  ts_utc     DATETIME(3) NOT NULL,
  x_fp       INT NOT NULL,
  y_fp       INT NOT NULL,
  KEY k_sensor_time (sensor_id, ts_utc),
  FOREIGN KEY (sensor_id) REFERENCES sensor(sensor_id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- 5) 1분 집계(그래프/카드)
CREATE TABLE area_minute_agg (
  area_id        BIGINT NOT NULL,
  bucket_utc     DATETIME NOT NULL,
  occupancy_avg  DOUBLE NULL,
  queue_len_p50  DOUBLE NULL,
  wait_sec_p50   DOUBLE NULL,
  PRIMARY KEY (area_id, bucket_utc),
  FOREIGN KEY (area_id) REFERENCES area(area_id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- 6) 임계치(알림)
CREATE TABLE threshold_config (
  config_id       BIGINT PRIMARY KEY AUTO_INCREMENT,
  area_id         BIGINT NOT NULL,
  metric          ENUM('OCCUPANCY','QUEUE_LEN','WAIT_SEC') NOT NULL,
  warn_threshold  DOUBLE NOT NULL,
  crit_threshold  DOUBLE NOT NULL,
  updated_at_utc  DATETIME NOT NULL,
  UNIQUE KEY uk_area_metric (area_id, metric),
  FOREIGN KEY (area_id) REFERENCES area(area_id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE iot_reading (
  id           BIGINT PRIMARY KEY AUTO_INCREMENT,
  sensor_id    BIGINT NOT NULL,
  ts_utc       DATETIME NOT NULL,
  metric       ENUM('TEMP_C','NOISE_DB','CO2_PPM','HUMIDITY') NOT NULL,
  value_double DOUBLE NOT NULL,
  KEY k_sensor_time (sensor_id, ts_utc),
  FOREIGN KEY (sensor_id) REFERENCES sensor(sensor_id) ON DELETE CASCADE
) ENGINE=InnoDB;
-- 설명: IoT 환경 센서 원시 시계열(대시보드 환경 레이어/이상치 분석 입력)

CREATE TABLE anomaly_event (
  event_id     BIGINT PRIMARY KEY AUTO_INCREMENT,
  area_id      BIGINT NOT NULL,
  sensor_id    BIGINT NULL,
  ts_utc       DATETIME NOT NULL,
  event_type   ENUM('FALL','COLLISION','RUNNING','INTRUSION','OTHER') NOT NULL,
  severity     ENUM('INFO','WARN','CRIT') NOT NULL DEFAULT 'WARN',
  snapshot_ref VARCHAR(255) NULL,    -- 이미지/클립 경로(옵션)
  details      LONGTEXT NULL,        -- 추가 메타(JSON 문자열)
  KEY k_area_time (area_id, ts_utc),
  FOREIGN KEY (area_id) REFERENCES area(area_id) ON DELETE CASCADE,
  FOREIGN KEY (sensor_id) REFERENCES sensor(sensor_id) ON DELETE SET NULL
) ENGINE=InnoDB;
-- 설명: 규칙/모델이 감지한 이상행동 단건 이벤트 로그

CREATE TABLE alert_log (
  alert_id     BIGINT PRIMARY KEY AUTO_INCREMENT,
  area_id      BIGINT NOT NULL,
  ts_utc       DATETIME NOT NULL,
  metric       ENUM('OCCUPANCY','QUEUE_LEN','WAIT_SEC','ANOMALY') NOT NULL,
  level        ENUM('WARN','CRIT') NOT NULL,
  value        DOUBLE NULL,
  message      VARCHAR(512) NOT NULL,
  delivered_to VARCHAR(128) NULL,     -- 'slack:#ops', 'webhook:xyz' 등
  status       ENUM('SENT','FAILED') NOT NULL DEFAULT 'SENT',
  FOREIGN KEY (area_id) REFERENCES area(area_id) ON DELETE CASCADE,
  KEY k_area_time (area_id, ts_utc)
) ENGINE=InnoDB;
-- 설명: 임계치/이상행동 초과 시 실제 발송 내역 추적

CREATE TABLE congestion_forecast (
  forecast_id       BIGINT PRIMARY KEY AUTO_INCREMENT,
  area_id           BIGINT NOT NULL,
  issued_at_utc     DATETIME NOT NULL,  -- 예측 생성 시각
  horizon_min       INT NOT NULL,       -- 5/10/15/30
  target_bucket_utc DATETIME NOT NULL,  -- 대상 분 버킷
  congestion_score  DOUBLE NOT NULL,    -- 0~100 등
  queue_len_pred    DOUBLE NULL,
  wait_sec_pred     DOUBLE NULL,
  model_version     VARCHAR(64) NOT NULL,
  features_note     LONGTEXT NULL,      -- 사용 피처 요약(JSON 문자열)
  UNIQUE KEY uk_target (area_id, target_bucket_utc, horizon_min),
  KEY k_issued (issued_at_utc),
  FOREIGN KEY (area_id) REFERENCES area(area_id) ON DELETE CASCADE
) ENGINE=InnoDB;
-- 설명: 단기 혼잡 예측 결과 저장(대시보드 예측 타임라인/카드)

CREATE TABLE baggage_signal (
  signal_id    BIGINT PRIMARY KEY AUTO_INCREMENT,
  area_id      BIGINT NOT NULL,        -- BAGGAGE 타입 area에 매핑
  ts_utc       DATETIME NOT NULL,
  metric       ENUM('BAGS_IN','BAGS_OUT','BELT_SPEED','CAROUSEL_OCC') NOT NULL,
  value_double DOUBLE NOT NULL,
  ref_note     LONGTEXT NULL,
  KEY k_area_time (area_id, ts_utc),
  FOREIGN KEY (area_id) REFERENCES area(area_id) ON DELETE CASCADE
) ENGINE=InnoDB;
-- 설명: 수하물 입/출고량, 벨트 속도/점유 등 원시 시계열(지연 계산의 기반)

CREATE TABLE baggage_minute_agg (
  area_id      BIGINT NOT NULL,
  bucket_utc   DATETIME NOT NULL,
  bags_in      INT DEFAULT 0,
  bags_out     INT DEFAULT 0,
  occ_avg      DOUBLE NULL,   -- 캐로셀 평균 점유율
  PRIMARY KEY (area_id, bucket_utc),
  FOREIGN KEY (area_id) REFERENCES area(area_id) ON DELETE CASCADE
) ENGINE=InnoDB;
-- 설명: 캐로셀 단위 분 집계(간단 시각화/알림 기준)

CREATE TABLE device_status (
  sensor_id    BIGINT PRIMARY KEY,
  last_seen_utc DATETIME NOT NULL,
  fps_avg      DOUBLE NULL,
  notes        VARCHAR(255) NULL,
  FOREIGN KEY (sensor_id) REFERENCES sensor(sensor_id) ON DELETE CASCADE
) ENGINE=InnoDB;
-- 설명: 카메라/카운터 “살아있음” 모니터링(죽은 센서 감지)

ALTER TABLE sensor            ADD KEY k_sensor_area (area_id);
ALTER TABLE area_minute_agg   ADD KEY k_bucket (bucket_utc);
ALTER TABLE iot_reading       ADD KEY k_metric_time (metric, ts_utc);
ALTER TABLE congestion_forecast ADD KEY k_area_target (area_id, target_bucket_utc);






-- 구역 3개
INSERT INTO area (code, name, area_type, roi_json) VALUES
('CK-A','Check-in A','CHECKIN','{"poly":[[120,80],[420,80],[420,260],[120,260]]}'),
('SEC-N1','Security N1','SECURITY','{"poly":[[460,80],[760,80],[760,260],[460,260]]}'),
('GATE-12','Gate 12','GATE','{"poly":[[120,300],[760,300],[760,520],[120,520]]}');

-- 센서 2대
INSERT INTO sensor (area_id, sensor_type, name, external_ref, installed_at)
SELECT area_id,'CAMERA','Cam-CKA','rtsp://x/y', NOW() FROM area WHERE code='CK-A';
INSERT INTO sensor (area_id, sensor_type, name, external_ref, installed_at)
SELECT area_id,'CAMERA','Cam-SECN1','rtsp://x/z', NOW() FROM area WHERE code='SEC-N1';

SELECT a.code AS area_code, vp.sensor_id, vp.ts_utc, vp.x_fp, vp.y_fp
FROM vision_points vp
JOIN sensor s ON s.sensor_id=vp.sensor_id
JOIN area a   ON a.area_id=s.area_id
WHERE vp.ts_utc >= DATE_SUB(UTC_TIMESTAMP(), INTERVAL 10 SECOND)
ORDER BY vp.ts_utc DESC;

SELECT a.code, a.name, v.value_double AS people, t.latest_ts
FROM area a
JOIN sensor s ON s.area_id=a.area_id
JOIN (
  SELECT sensor_id, MAX(ts_utc) latest_ts
  FROM vision_reading
  WHERE metric='PEOPLE'
  GROUP BY sensor_id
) t ON t.sensor_id=s.sensor_id
JOIN vision_reading v
  ON v.sensor_id=s.sensor_id AND v.ts_utc=t.latest_ts AND v.metric='PEOPLE'
ORDER BY people DESC;



SHOW TABLES;