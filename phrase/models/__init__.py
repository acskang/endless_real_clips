# -*- coding: utf-8 -*-
# phrase/models/__init__.py
"""
모델 패키지 초기화 파일
모든 모델과 유틸리티를 임포트하여 외부에서 쉽게 접근 가능하도록 함
"""

# 기본 추상 모델
from .base import BaseModel

# 커스텀 필드
from .fields import MySQLTextField, MySQLLongTextField, OptimizedCharField, SecureURLField

# 코어 모델들
from .core import RequestTable, MovieTable, DialogueTable

# 사용자 활동 모델들
from .user import UserSearchQuery, UserSearchResult

# 캐시 모델
from .cache import CacheInvalidation

# 매니저들
from .managers import (
    ActiveManager, RequestManager, MovieManager, DialogueManager,
    UserSearchQueryManager, UserSearchResultManager, CacheInvalidationManager
)

# 유틸리티 함수들
from .utils import (
    get_model_statistics,
    cleanup_old_data,
    check_mysql_compatibility,
    get_poster_upload_path,
    get_video_upload_path
)

# MySQL 헬퍼 함수들
from .mysql_helpers import (
    get_mysql_engine,
    create_prefix_index,
    check_mysql_settings,
    get_mysql_migration_operations
)

# 기존 호환성을 위한 별칭
Movie = MovieTable
MovieQuote = DialogueTable

# 신호 처리는 자동으로 임포트되도록 함
from . import signals

# 로깅
import logging
logger = logging.getLogger(__name__)
logger.info("MySQL 호환성 개선된 모델 모듈 로드 완료")

__all__ = [
    # 추상 모델
    'BaseModel',
    
    # 커스텀 필드
    'MySQLTextField',
    'MySQLLongTextField',
    'OptimizedCharField', 
    'SecureURLField',
    
    # 코어 모델
    'RequestTable',
    'MovieTable',
    'DialogueTable',
    
    # 사용자 모델
    'UserSearchQuery',
    'UserSearchResult',
    
    # 캐시 모델
    'CacheInvalidation',
    
    # 매니저
    'ActiveManager',
    'RequestManager',
    'MovieManager',
    'DialogueManager',
    'UserSearchQueryManager',
    'UserSearchResultManager',
    'CacheInvalidationManager',
    
    # 유틸리티
    'get_model_statistics',
    'cleanup_old_data',
    'check_mysql_compatibility',
    'get_poster_upload_path',
    'get_video_upload_path',
    
    # MySQL 헬퍼
    'get_mysql_engine',
    'create_prefix_index',
    'check_mysql_settings',
    'get_mysql_migration_operations',
    
    # 별칭
    'Movie',
    'MovieQuote',
]