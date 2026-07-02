CREATE DATABASE IF NOT EXISTS ob_param_lab;
USE ob_param_lab;

CREATE TABLE IF NOT EXISTS param_test_config (
  id BIGINT NOT NULL AUTO_INCREMENT,
  param_name VARCHAR(256) NOT NULL,
  category VARCHAR(64),
  original_value VARCHAR(256),
  test_value VARCHAR(256),
  workload_type VARCHAR(32),
  need_restart VARCHAR(16),
  test_round INT,
  note TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS param_perf_result (
  id BIGINT NOT NULL AUTO_INCREMENT,
  param_name VARCHAR(256) NOT NULL,
  test_value VARCHAR(256),
  workload_type VARCHAR(32),
  qps DOUBLE,
  avg_latency_ms DOUBLE,
  p95_latency_ms DOUBLE,
  p99_latency_ms DOUBLE,
  cpu_usage DOUBLE,
  memory_usage DOUBLE,
  disk_io_read DOUBLE,
  disk_io_write DOUBLE,
  error_count BIGINT,
  test_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS experiment_log (
  id BIGINT NOT NULL AUTO_INCREMENT,
  experiment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  operator_name VARCHAR(128),
  param_name VARCHAR(256),
  before_value VARCHAR(256),
  after_value VARCHAR(256),
  workload_type VARCHAR(32),
  observation TEXT,
  conclusion TEXT,
  restored_default VARCHAR(16),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS capacity_metric_snapshot (
  id BIGINT NOT NULL AUTO_INCREMENT,
  snapshot_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  cpu_usage DOUBLE,
  memory_usage DOUBLE,
  disk_io_read DOUBLE,
  disk_io_write DOUBLE,
  qps DOUBLE,
  avg_latency_ms DOUBLE,
  active_sessions BIGINT,
  note TEXT,
  PRIMARY KEY (id)
);
