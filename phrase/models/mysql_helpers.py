# -*- coding: utf-8 -*-
# phrase/models/mysql_helpers.py
"""
MySQL 특화 헬퍼 함수 및 설정
마이그레이션 및 인덱스 관리를 위한 유틸리티
"""
import logging
from django.db import connection, models
# from django.db.migrations.operations.models import RunSQL
from django.db.migrations.operations.special import RunSQL

logger = logging.getLogger(__name__)

def get_mysql_engine():
    """현재 MySQL 스토리지 엔진 확인"""
    with connection.cursor() as cursor:
        cursor.execute("SELECT @@default_storage_engine")
        result = cursor.fetchone()
        return result[0] if result else None

def create_prefix_index(table_name, column_name, prefix_length=191, index_name=None):
    """MySQL TEXT 컬럼에 대한 prefix 인덱스 생성"""
    if not index_name:
        index_name = f"idx_{table_name}_{column_name}_prefix"
    
    sql = f"""
    CREATE INDEX {index_name} 
    ON {table_name} ({column_name}({prefix_length}))
    """
    
    return RunSQL(
        sql,
        reverse_sql=f"DROP INDEX {index_name} ON {table_name}"
    )

def optimize_mysql_table_settings():
    """MySQL 테이블 최적화 설정"""
    optimizations = []
    
    # 각 테이블에 대한 최적화 SQL
    tables = ['request_table', 'movie_table', 'dialogue_table']
    
    for table in tables:
        # ROW_FORMAT 설정
        optimizations.append(
            RunSQL(
                f"ALTER TABLE {table} ROW_FORMAT=DYNAMIC",
                reverse_sql=RunSQL.noop
            )
        )
        
        # 문자셋 설정
        optimizations.append(
            RunSQL(
                f"ALTER TABLE {table} CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci",
                reverse_sql=RunSQL.noop
            )
        )
    
    return optimizations

def check_mysql_settings():
    """MySQL 설정 확인 및 권장사항 반환"""
    recommendations = []
    
    with connection.cursor() as cursor:
        # innodb_large_prefix 확인
        cursor.execute("SHOW VARIABLES LIKE 'innodb_large_prefix'")
        result = cursor.fetchone()
        if result and result[1].lower() == 'off':
            recommendations.append(
                "SET GLOBAL innodb_large_prefix = ON; -- 큰 인덱스 키 지원"
            )
        
        # innodb_file_format 확인
        cursor.execute("SHOW VARIABLES LIKE 'innodb_file_format'")
        result = cursor.fetchone()
        if result and result[1].lower() != 'barracuda':
            recommendations.append(
                "SET GLOBAL innodb_file_format = Barracuda; -- DYNAMIC ROW_FORMAT 지원"
            )
        
        # 최대 인덱스 길이 확인
        cursor.execute("SHOW VARIABLES LIKE 'innodb_page_size'")
        result = cursor.fetchone()
        if result:
            page_size = int(result[1])
            max_index_length = page_size // 8
            logger.info(f"최대 인덱스 길이: {max_index_length} bytes")
    
    return recommendations

def create_fulltext_index_for_mysql(table_name, columns):
    """MySQL FULLTEXT 인덱스 생성"""
    column_list = ', '.join(columns)
    index_name = f"ft_idx_{table_name}_{'_'.join(columns)}"
    
    return RunSQL(
        f"""
        ALTER TABLE {table_name} 
        ADD FULLTEXT INDEX {index_name} ({column_list})
        """,
        reverse_sql=f"ALTER TABLE {table_name} DROP INDEX {index_name}"
    )

def get_mysql_migration_operations():
    """MySQL 특화 마이그레이션 작업 목록 반환"""
    operations = []
    
    # dialogue_table의 TEXT 컬럼에 prefix 인덱스 생성 (필요한 경우)
    # 주의: 이미 search_vector로 검색하므로 대부분 불필요
    
    # 테이블 최적화
    operations.extend(optimize_mysql_table_settings())
    
    return operations

# MySQL 관련 상수
MYSQL_MAX_INDEX_LENGTH = 3072  # InnoDB 기본값 (Barracuda format)
MYSQL_UTF8MB4_MAX_KEY_LENGTH = 191  # utf8mb4에서 안전한 최대 키 길이
MYSQL_TEXT_PREFIX_LENGTH = 100  # TEXT 인덱스용 prefix 길이

# MySQL 데이터 타입 매핑
MYSQL_TYPE_MAPPING = {
    'tiny_text': 'TINYTEXT',      # 255 bytes
    'text': 'TEXT',               # 65,535 bytes
    'medium_text': 'MEDIUMTEXT',  # 16,777,215 bytes
    'long_text': 'LONGTEXT',      # 4,294,967,295 bytes
}