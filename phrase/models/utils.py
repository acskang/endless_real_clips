# -*- coding: utf-8 -*-
# phrase/models/utils.py
"""
모델 관련 유틸리티 함수들
파일 업로드 경로 생성, 통계, 데이터 정리 등
"""
import uuid
import logging
from django.utils import timezone
from django.db import connection

logger = logging.getLogger(__name__)

def get_poster_upload_path(instance, filename):
    """포스터 이미지 업로드 경로 생성"""
    ext = filename.split('.')[-1].lower()
    filename = f"{uuid.uuid4().hex}.{ext}"
    return f"posters/{timezone.now().year}/{timezone.now().month:02d}/{filename}"

def get_video_upload_path(instance, filename):
    """비디오 파일 업로드 경로 생성"""
    ext = filename.split('.')[-1].lower()
    filename = f"{uuid.uuid4().hex}.{ext}"
    return f"videos/{timezone.now().year}/{timezone.now().month:02d}/{filename}"

def get_model_statistics():
    """모든 모델의 통계를 한 번에 조회"""
    from .managers import get_all_statistics
    return get_all_statistics()

def cleanup_old_data(days=30):
    """오래된 데이터 정리"""
    from .user import UserSearchQuery
    from .cache import CacheInvalidation
    
    cutoff_date = timezone.now() - timezone.timedelta(days=days)
    
    old_searches = UserSearchQuery.objects.filter(created_at__lt=cutoff_date, search_count=1)
    deleted_searches = old_searches.delete()[0]
    
    deleted_cache = CacheInvalidation.objects.filter(created_at__lt=cutoff_date).delete()[0]
    
    logger.info(f"오래된 데이터 정리 완료: 검색기록 {deleted_searches}개, 캐시기록 {deleted_cache}개")
    
    return {
        'searches_deleted': deleted_searches,
        'cache_records_deleted': deleted_cache
    }

def check_mysql_compatibility():
    """MySQL 호환성 검사"""
    if connection.vendor == 'mysql':
        with connection.cursor() as cursor:
            # MySQL 버전 확인
            cursor.execute("SELECT VERSION()")
            version = cursor.fetchone()[0]
            
            # InnoDB 엔진 지원 확인
            cursor.execute("SHOW ENGINES")
            engines = cursor.fetchall()
            innodb_support = any('InnoDB' in str(engine) for engine in engines)
            
            # utf8mb4 문자셋 지원 확인
            cursor.execute("SHOW CHARACTER SET LIKE 'utf8mb4'")
            utf8mb4_support = bool(cursor.fetchone())
            
            compatibility_info = {
                'mysql_version': version,
                'innodb_support': innodb_support,
                'utf8mb4_support': utf8mb4_support,
                'recommendations': []
            }
            
            if not innodb_support:
                compatibility_info['recommendations'].append('InnoDB 엔진 활성화 필요')
            
            if not utf8mb4_support:
                compatibility_info['recommendations'].append('utf8mb4 문자셋 지원 필요')
            
            logger.info(f"MySQL 호환성 체크 완료: {compatibility_info}")
            return compatibility_info
    
    return {'message': 'MySQL이 아닌 데이터베이스입니다'}