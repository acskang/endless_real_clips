# -*- coding: utf-8 -*-
# dj/phrase/utils/__init__.py
"""
유틸리티 모듈 초기화
일본어, 중국어 필드 제거 반영
"""

from .search_helpers import (
    get_client_ip,
    record_search_query,
    increment_search_count,
    get_input_type
)

from .data_processing import (
    get_existing_results_from_db,
    build_movies_context_from_db,
    ensure_korean_translations_batch
)

from .template_helpers import (
    render_search_results,
    build_error_context,
    build_success_context,
    build_translation_status_context
)

from .input_validation import (
    InputValidator,
    get_confirmation_context
)

from .clean_data import (
    clean_data_from_playphrase,
    clean_data_v4,
    extract_movie_info,
    batch_process_movies_optimized
)

from .get_movie_info import (
    get_movie_info,
    check_existing_database_data,
    PlayPhraseAPIClient
)

from .load_to_db import (
    load_to_db,
    save_movie_table_optimized,
    save_dialogue_table_optimized,
    get_search_results_from_db
)

from .translate import (
    LibreTranslator,
    translate_dialogue_batch,
    update_existing_dialogues_optimized
)

from .get_imdb_poster_url import (
    IMDBPosterExtractor,
    download_poster_image,
    get_poster_url,
    batch_update_movie_posters
)

from .search_history import (
    SearchHistoryManager
)

__all__ = [
    # 기존 utils 모듈들
    'get_client_ip',
    'record_search_query', 
    'increment_search_count',
    'get_input_type',
    'get_existing_results_from_db',
    'build_movies_context_from_db',
    'ensure_korean_translations_batch',
    'render_search_results',
    'build_error_context',
    'build_success_context',
    'build_translation_status_context',
    'InputValidator',
    'get_confirmation_context',
    
    # 통합된 application 모듈들
    'clean_data_from_playphrase',
    'clean_data_v4',
    'extract_movie_info',
    'batch_process_movies_optimized',
    'get_movie_info',
    'check_existing_database_data',
    'PlayPhraseAPIClient',
    'load_to_db',
    'save_movie_table_optimized',
    'save_dialogue_table_optimized',
    'get_search_results_from_db',
    'LibreTranslator',
    'translate_dialogue_batch',
    'update_existing_dialogues_optimized',
    'IMDBPosterExtractor',
    'download_poster_image',
    'get_poster_url',
    'batch_update_movie_posters',
    'SearchHistoryManager'
]