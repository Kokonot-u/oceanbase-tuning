CREATE DATABASE IF NOT EXISTS week2_bench_wang;
USE week2_bench_wang;
CREATE TABLE IF NOT EXISTS test_conn (
  id INT PRIMARY KEY,
  name VARCHAR(100),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
INSERT INTO test_conn(id, name) VALUES (1, 'real week2 connection from wzh docker obclient')
ON DUPLICATE KEY UPDATE name=VALUES(name);
SELECT * FROM test_conn;
