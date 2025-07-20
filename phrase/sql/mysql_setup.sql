-- phrase/sql/mysql_setup.sql
-- MySQL 데이터베이스 초기 설정 스크립트

-- 데이터베이스 생성 (필요한 경우)
-- CREATE DATABASE IF NOT EXISTS phrase_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 데이터베이스 선택
-- USE phrase_db;

-- 시스템 변수 설정 (권한이 있는 경우)
-- SET GLOBAL innodb_large_prefix = ON;
-- SET GLOBAL innodb_file_format = Barracuda;
-- SET GLOBAL innodb_file_per_table = ON;

-- 세션 변수 설정
SET NAMES utf8mb4;
SET CHARACTER SET utf8mb4;
SET character_set_connection = utf8mb4;

-- 기존 테이블이 있는 경우 ROW_FORMAT 변경
-- ALTER TABLE request_table ROW_FORMAT=DYNAMIC;
-- ALTER TABLE movie_table ROW_FORMAT=DYNAMIC;
-- ALTER TABLE dialogue_table ROW_FORMAT=DYNAMIC;

-- 기존 테이블 문자셋 변경 (필요한 경우)
-- ALTER TABLE request_table CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
-- ALTER TABLE movie_table CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
-- ALTER TABLE dialogue_table CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 사용자 권한 설정 예시
-- GRANT ALL PRIVILEGES ON phrase_db.* TO 'phrase_user'@'localhost';
-- FLUSH PRIVILEGES;

-- 최적화 관련 설정 확인
SELECT 
    @@innodb_large_prefix as 'Large Prefix',
    @@innodb_file_format as 'File Format',
    @@character_set_database as 'DB Charset',
    @@collation_database as 'DB Collation',
    @@innodb_buffer_pool_size as 'Buffer Pool Size',
    @@max_allowed_packet as 'Max Packet Size';

-- 테이블 상태 확인 (마이그레이션 후)
-- SHOW TABLE STATUS WHERE Name IN ('request_table', 'movie_table', 'dialogue_table');

-- 인덱스 확인 (마이그레이션 후)
-- SHOW INDEX FROM dialogue_table;
-- SHOW INDEX FROM movie_table;
-- SHOW INDEX FROM request_table;