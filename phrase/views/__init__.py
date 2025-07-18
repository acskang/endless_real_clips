# -*- coding: utf-8 -*-
# dj/phrase/views/__init__.py
"""
뷰 모듈 초기화
"""

from .main_views import index, process_text
from .api_views import popular_searches_api, statistics_api
from .helper_views import debug_view, korean_translation_status, bulk_translate_dialogues

__all__ = [
    'index',
    'process_text', 
    'popular_searches_api',
    'statistics_api',
    'debug_view',
    'korean_translation_status',
    'bulk_translate_dialogues'
]