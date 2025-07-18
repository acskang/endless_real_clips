# -*- coding: utf-8 -*-
# dj/phrase/utils/__init__.py
"""
유틸리티 모듈 초기화
"""

from .search_helpers import (
    get_client_ip,
    record_search_query,
    increment_search_count
)

from .data_processing import (
    get_existing_results_from_db,
    build_movies_context_from_db,
    ensure_korean_translations_batch
)

from .template_helpers import (
    render_search_results,
    build_error_context,
    build_success_context
)

__all__ = [
    'get_client_ip',
    'record_search_query', 
    'increment_search_count',
    'get_existing_results_from_db',
    'build_movies_context_from_db',
    'ensure_korean_translations_batch',
    'render_search_results',
    'build_error_context',
    'build_success_context'
]