# -*- coding: utf-8 -*-
# api/serializers.py
"""
최적화된 DRF 시리얼라이저 - 업데이트된 모델에 맞춰 수정
- MySQL 호환성 개선된 모델 구조 반영
- 긴 텍스트 필드 지원
- 해시 기반 중복 검사 지원
"""
from rest_framework import serializers
from django.core.cache import cache
from django.conf import settings
from phrase.models import (
    RequestTable, MovieTable, DialogueTable,
    UserSearchQuery, UserSearchResult,
    # 기존 호환성을 위한 별칭
    Movie, MovieQuote
)
import logging

logger = logging.getLogger(__name__)

# ===== 공통 믹스인 클래스 =====

class MediaURLMixin:
    """미디어 URL 처리를 위한 믹스인"""
    
    def get_absolute_media_url(self, file_field, fallback_url=None):
        """파일 필드의 절대 URL 반환"""
        if file_field:
            request = self.context.get('request')
            if request:
                try:
                    return request.build_absolute_uri(file_field.url)
                except (ValueError, AttributeError):
                    pass
        return fallback_url or ''
    
    def get_poster_url(self, obj):
        """포스터 URL 반환 (우선순위: 로컬 이미지 → 외부 URL)"""
        if hasattr(obj, 'poster_image'):
            return self.get_absolute_media_url(obj.poster_image, obj.poster_url)
        elif hasattr(obj, 'movie') and hasattr(obj.movie, 'poster_image'):
            return self.get_absolute_media_url(obj.movie.poster_image, obj.movie.poster_url)
        return ''
    
    def get_video_url(self, obj):
        """비디오 URL 반환 (우선순위: 로컬 파일 → 외부 URL)"""
        return self.get_absolute_media_url(obj.video_file, obj.video_url)

class CacheOptimizedMixin:
    """캐싱 최적화를 위한 믹스인"""
    
    def get_cached_data(self, cache_key, fetch_func, timeout=300):
        """캐시된 데이터 조회 또는 생성"""
        data = cache.get(cache_key)
        if data is None:
            data = fetch_func()
            cache.set(cache_key, data, timeout)
        return data

class ValidationMixin:
    """검증 로직을 위한 믹스인"""
    
    def validate_positive_integer(self, value, field_name):
        """양수 검증"""
        if value is not None and value < 0:
            raise serializers.ValidationError(f'{field_name}은(는) 양수여야 합니다.')
        return value
    
    def validate_url_field(self, value, field_name):
        """URL 필드 검증"""
        if value:
            dangerous_patterns = ['javascript:', 'data:', 'vbscript:', 'file:']
            if any(pattern in value.lower() for pattern in dangerous_patterns):
                raise serializers.ValidationError(f'{field_name}에 안전하지 않은 URL이 포함되어 있습니다.')
        return value

# ===== 설계서 기반 최적화된 시리얼라이저 =====

class OptimizedRequestTableSerializer(serializers.ModelSerializer, ValidationMixin):
    """최적화된 요청테이블 시리얼라이저 - 업데이트된 모델 반영"""
    
    search_count = serializers.IntegerField(read_only=True)
    last_searched_at = serializers.DateTimeField(read_only=True)
    translation_quality_display = serializers.CharField(
        source='get_translation_quality_display', 
        read_only=True
    )
    
    # 전체 텍스트 필드들
    full_request_phrase = serializers.SerializerMethodField()
    full_request_korean = serializers.SerializerMethodField()
    
    class Meta:
        model = RequestTable
        fields = [
            'request_phrase', 'request_phrase_full', 'full_request_phrase',
            'request_korean', 'request_korean_full', 'full_request_korean',
            'request_hash', 'search_count', 'last_searched_at', 'result_count',
            'translation_quality', 'translation_quality_display',
            'ip_address', 'user_agent', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'created_at', 'updated_at', 'search_count', 'last_searched_at',
            'request_hash', 'result_count'
        ]
    
    def get_full_request_phrase(self, obj):
        """전체 요청구문 반환"""
        return obj.get_full_phrase()
    
    def get_full_request_korean(self, obj):
        """전체 한글구문 반환"""
        return obj.get_full_korean()
    
    def validate_request_phrase(self, value):
        """요청구문 검증"""
        if not value or not value.strip():
            raise serializers.ValidationError('요청구문은 필수입니다.')
        
        # 길이 검증 (더 긴 텍스트 허용)
        if len(value.strip()) > 2000:
            raise serializers.ValidationError('요청구문은 2000자를 초과할 수 없습니다.')
        
        return value.strip()
    
    def validate_request_korean(self, value):
        """요청한글 검증"""
        if value:
            if len(value.strip()) > 2000:
                raise serializers.ValidationError('요청한글은 2000자를 초과할 수 없습니다.')
            return value.strip()
        return value

class OptimizedMovieTableSerializer(serializers.ModelSerializer, MediaURLMixin, CacheOptimizedMixin):
    """최적화된 영화테이블 시리얼라이저 - 업데이트된 모델 반영"""
    
    dialogue_count = serializers.SerializerMethodField()
    poster_image_url = serializers.SerializerMethodField()
    display_title = serializers.SerializerMethodField()
    view_count = serializers.IntegerField(read_only=True)
    like_count = serializers.IntegerField(read_only=True)
    data_quality_display = serializers.CharField(source='get_data_quality_display', read_only=True)
    
    # 전체 텍스트 필드들
    full_movie_title = serializers.SerializerMethodField()
    full_original_title = serializers.SerializerMethodField()
    full_director = serializers.SerializerMethodField()
    
    class Meta:
        model = MovieTable
        fields = [
            'id', 'movie_title', 'movie_title_full', 'full_movie_title',
            'original_title', 'original_title_full', 'full_original_title',
            'display_title', 'release_year', 'production_country', 
            'director', 'director_full', 'full_director', 'genre',
            'imdb_rating', 'imdb_url', 'poster_url', 'poster_image',
            'poster_image_path', 'poster_image_url', 'dialogue_count',
            'view_count', 'like_count', 'data_quality', 'data_quality_display',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'dialogue_count', 'poster_image_url', 'display_title',
            'full_movie_title', 'full_original_title', 'full_director',
            'view_count', 'like_count', 'data_quality_display',
            'created_at', 'updated_at'
        ]
    
    def get_dialogue_count(self, obj):
        """대사 개수 조회 (캐싱 적용)"""
        cache_key = f"movie_dialogue_count_{obj.id}"
        return self.get_cached_data(
            cache_key,
            lambda: obj.dialogues.filter(is_active=True).count(),
            timeout=600  # 10분 캐싱
        )
    
    def get_poster_image_url(self, obj):
        """포스터 이미지 URL 반환"""
        return self.get_poster_url(obj)
    
    def get_display_title(self, obj):
        """표시용 제목 반환"""
        return obj.get_display_title()
    
    def get_full_movie_title(self, obj):
        """전체 영화 제목 반환"""
        return obj.get_full_title()
    
    def get_full_original_title(self, obj):
        """전체 원제목 반환"""
        return obj.get_full_original_title()
    
    def get_full_director(self, obj):
        """전체 감독명 반환"""
        return obj.get_full_director()
    
    def validate_movie_title(self, value):
        """영화 제목 검증"""
        if not value or not value.strip():
            raise serializers.ValidationError('영화 제목은 필수입니다.')
        return value.strip()
    
    def validate_imdb_rating(self, value):
        """IMDB 평점 검증"""
        if value is not None and (value < 0 or value > 10):
            raise serializers.ValidationError('IMDB 평점은 0-10 사이여야 합니다.')
        return value

class OptimizedDialogueTableSerializer(serializers.ModelSerializer, MediaURLMixin, ValidationMixin):
    """최적화된 대사테이블 시리얼라이저 - 업데이트된 모델 반영"""
    
    movie_title = serializers.CharField(source='movie.movie_title', read_only=True)
    movie_release_year = serializers.CharField(source='movie.release_year', read_only=True)
    movie_director = serializers.CharField(source='movie.director', read_only=True)
    movie_poster_url = serializers.SerializerMethodField()
    video_file_url = serializers.SerializerMethodField()
    duration_display = serializers.SerializerMethodField()
    translation_quality_display = serializers.CharField(
        source='get_translation_quality_display', 
        read_only=True
    )
    translation_method_display = serializers.CharField(
        source='get_translation_method_display', 
        read_only=True
    )
    video_quality_display = serializers.CharField(
        source='get_video_quality_display',
        read_only=True
    )
    
    # 전체 텍스트 필드들
    full_movie_title = serializers.CharField(source='movie.get_full_title', read_only=True)
    full_director = serializers.CharField(source='movie.get_full_director', read_only=True)
    
    class Meta:
        model = DialogueTable
        fields = [
            'id', 'movie', 'movie_title', 'full_movie_title', 'movie_release_year', 
            'movie_director', 'full_director', 'movie_poster_url', 
            'dialogue_phrase', 'dialogue_phrase_ko', 'dialogue_hash',
            'dialogue_start_time', 'dialogue_end_time', 'duration_seconds', 'duration_display',
            'video_url', 'video_file', 'video_file_path', 'video_file_url',
            'file_size_bytes', 'video_quality', 'video_quality_display',
            'translation_method', 'translation_method_display',
            'translation_quality', 'translation_quality_display',
            'play_count', 'like_count', 'search_vector', 'search_vector_full',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'movie_title', 'full_movie_title', 'movie_release_year', 
            'movie_director', 'full_director', 'movie_poster_url', 'video_file_url', 
            'duration_display', 'translation_quality_display', 'translation_method_display',
            'video_quality_display', 'dialogue_hash', 'search_vector', 'search_vector_full',
            'play_count', 'like_count', 'file_size_bytes', 'created_at', 'updated_at'
        ]
    
    def get_movie_poster_url(self, obj):
        """영화 포스터 URL 반환"""
        return self.get_poster_url(obj)
    
    def get_video_file_url(self, obj):
        """비디오 파일 URL 반환"""
        return self.get_video_url(obj)
    
    def get_duration_display(self, obj):
        """길이 표시용 문자열 반환"""
        return obj.get_duration_display()
    
    def validate_dialogue_phrase(self, value):
        """대사구문 검증"""
        if not value or not value.strip():
            raise serializers.ValidationError('대사구문은 필수입니다.')
        return value.strip()
    
    def validate_duration_seconds(self, value):
        """길이 검증"""
        return self.validate_positive_integer(value, '대사 길이')
    
    def validate_video_url(self, value):
        """비디오 URL 검증"""
        return self.validate_url_field(value, '비디오 URL')

class OptimizedDialogueSearchSerializer(serializers.ModelSerializer, MediaURLMixin):
    """
    최적화된 검색 결과용 시리얼라이저
    설계서 기반 + Flutter/웹 호환
    """
    name = serializers.CharField(source='movie.movie_title', read_only=True)
    startTime = serializers.CharField(source='dialogue_start_time', read_only=True)
    text = serializers.CharField(source='dialogue_phrase', read_only=True)
    posterUrl = serializers.SerializerMethodField()
    videoUrl = serializers.SerializerMethodField()
    
    # 추가 정보 (설계서 기반)
    releaseYear = serializers.CharField(source='movie.release_year', read_only=True)
    director = serializers.CharField(source='movie.director', read_only=True)
    productionCountry = serializers.CharField(source='movie.production_country', read_only=True)
    imdbUrl = serializers.CharField(source='movie.imdb_url', read_only=True)
    
    # 성능 정보
    translationQuality = serializers.CharField(source='translation_quality', read_only=True)
    playCount = serializers.IntegerField(source='play_count', read_only=True)
    
    # 전체 제목 정보
    fullMovieTitle = serializers.CharField(source='movie.get_full_title', read_only=True)
    fullDirector = serializers.CharField(source='movie.get_full_director', read_only=True)
    koreanText = serializers.CharField(source='dialogue_phrase_ko', read_only=True)
    
    class Meta:
        model = DialogueTable
        fields = [
            'name', 'fullMovieTitle', 'startTime', 'text', 'koreanText',
            'posterUrl', 'videoUrl', 'releaseYear', 'director', 'fullDirector',
            'productionCountry', 'imdbUrl', 'translationQuality', 'playCount'
        ]
    
    def get_posterUrl(self, obj):
        return self.get_poster_url(obj)
    
    def get_videoUrl(self, obj):
        return self.get_video_url(obj)

# ===== 통계 및 분석용 최적화된 시리얼라이저 =====

class StatisticsSerializer(serializers.Serializer, CacheOptimizedMixin):
    """통계 정보 시리얼라이저"""
    
    total_requests = serializers.IntegerField()
    total_movies = serializers.IntegerField()
    total_dialogues = serializers.IntegerField()
    active_requests = serializers.IntegerField()
    active_movies = serializers.IntegerField()
    active_dialogues = serializers.IntegerField()
    
    # 번역 통계
    korean_translation_rate = serializers.FloatField()
    translation_quality_distribution = serializers.DictField()
    
    # 인기 통계
    popular_phrases = serializers.ListField(child=serializers.CharField(), max_length=10)
    popular_movies = serializers.ListField(child=serializers.CharField(), max_length=10)
    
    # 성능 통계
    avg_search_count = serializers.FloatField()
    avg_play_count = serializers.FloatField()
    
    # MySQL 최적화 정보
    index_usage = serializers.DictField()
    cache_hit_rate = serializers.FloatField()
    
    generated_at = serializers.DateTimeField()

class SearchAnalyticsSerializer(serializers.Serializer):
    """검색 분석 결과 시리얼라이저"""
    
    query = serializers.CharField()
    language_detected = serializers.ChoiceField(choices=[('korean', '한글'), ('english', '영어')])
    translation_used = serializers.BooleanField()
    translated_query = serializers.CharField(allow_null=True)
    search_method = serializers.ChoiceField(choices=[
        ('db_cache', 'DB 캐시'),
        ('hash_lookup', '해시 검색'),
        ('external_api', '외부 API'),
        ('hybrid', '하이브리드')
    ])
    response_time_ms = serializers.IntegerField()
    result_count = serializers.IntegerField()
    cache_hit = serializers.BooleanField()
    hash_match = serializers.BooleanField(default=False)

# ===== 기존 호환성을 위한 최적화된 시리얼라이저 =====

class LegacyMovieSerializer(serializers.ModelSerializer, MediaURLMixin):
    """기존 Movie 모델 호환성 시리얼라이저 (최적화)"""
    
    poster_image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = MovieTable
        fields = [
            'id', 'movie_title', 'imdb_url', 'poster_url', 
            'poster_image', 'poster_image_path', 'poster_image_url'
        ]
    
    def get_poster_image_url(self, obj):
        return self.get_poster_url(obj)

class LegacyMovieQuoteSerializer(serializers.ModelSerializer, MediaURLMixin):
    """기존 MovieQuote 모델 호환성 시리얼라이저 (최적화)"""
    
    movie_name = serializers.CharField(source='movie.movie_title', read_only=True)
    movie_poster_url = serializers.CharField(source='movie.poster_url', read_only=True)
    movie_poster_image = serializers.SerializerMethodField()
    video_file_url = serializers.SerializerMethodField()
    
    class Meta:
        model = DialogueTable
        fields = [
            'id', 'movie', 'movie_name', 'movie_poster_url', 'movie_poster_image',
            'dialogue_start_time', 'dialogue_phrase', 'video_url', 
            'video_file', 'video_file_path', 'video_file_url'
        ]
    
    def get_movie_poster_image(self, obj):
        return self.get_poster_url(obj)
    
    def get_video_file_url(self, obj):
        return self.get_video_url(obj)

class LegacySearchSerializer(serializers.ModelSerializer, MediaURLMixin):
    """기존 Flutter 앱 호환성을 위한 검색 시리얼라이저 (최적화)"""
    
    name = serializers.CharField(source='movie.movie_title', read_only=True)
    posterUrl = serializers.SerializerMethodField()
    videoUrl = serializers.SerializerMethodField()
    startTime = serializers.CharField(source='dialogue_start_time', read_only=True)
    text = serializers.CharField(source='dialogue_phrase', read_only=True)
    
    class Meta:
        model = DialogueTable
        fields = ['name', 'startTime', 'text', 'posterUrl', 'videoUrl']
    
    def get_posterUrl(self, obj):
        return self.get_poster_url(obj)
    
    def get_videoUrl(self, obj):
        return self.get_video_url(obj)

# ===== 고급 기능용 시리얼라이저 =====

class BulkDialogueUpdateSerializer(serializers.Serializer):
    """대사 대량 업데이트용 시리얼라이저"""
    
    ids = serializers.ListField(
        child=serializers.IntegerField(), 
        min_length=1, 
        max_length=100
    )
    translation_quality = serializers.ChoiceField(
        choices=DialogueTable._meta.get_field('translation_quality').choices,
        required=False
    )
    translation_method = serializers.ChoiceField(
        choices=DialogueTable._meta.get_field('translation_method').choices,
        required=False
    )
    video_quality = serializers.ChoiceField(
        choices=DialogueTable._meta.get_field('video_quality').choices,
        required=False
    )
    is_active = serializers.BooleanField(required=False)
    
    def validate_ids(self, value):
        """ID 목록 검증"""
        # 중복 제거
        unique_ids = list(set(value))
        
        # 존재하는 ID인지 확인
        existing_ids = set(
            DialogueTable.objects.filter(id__in=unique_ids).values_list('id', flat=True)
        )
        invalid_ids = set(unique_ids) - existing_ids
        
        if invalid_ids:
            raise serializers.ValidationError(f'존재하지 않는 ID: {list(invalid_ids)}')
        
        return unique_ids

class SearchOptimizationSerializer(serializers.Serializer):
    """검색 최적화 설정 시리얼라이저"""
    
    cache_enabled = serializers.BooleanField(default=True)
    cache_timeout = serializers.IntegerField(default=300, min_value=60, max_value=3600)
    max_results = serializers.IntegerField(default=50, min_value=1, max_value=100)
    include_inactive = serializers.BooleanField(default=False)
    quality_threshold = serializers.ChoiceField(
        choices=[('poor', '미흡 이상'), ('fair', '보통 이상'), ('good', '양호 이상'), ('excellent', '우수만')],
        default='fair'
    )
    translation_required = serializers.BooleanField(default=False)
    use_hash_lookup = serializers.BooleanField(default=True)
    use_full_text_search = serializers.BooleanField(default=True)

# ===== MySQL 최적화 관련 시리얼라이저 =====

class MySQLOptimizationSerializer(serializers.Serializer):
    """MySQL 최적화 정보 시리얼라이저"""
    
    table_name = serializers.CharField()
    index_usage = serializers.DictField()
    query_performance = serializers.DictField()
    recommendations = serializers.ListField(child=serializers.CharField())
    charset_info = serializers.DictField()
    engine_info = serializers.CharField()

# ===== 시리얼라이저 팩토리 함수 =====

def get_optimized_serializer(model_name, context=None, **kwargs):
    """최적화된 시리얼라이저 팩토리 함수"""
    
    serializer_mapping = {
        'request': OptimizedRequestTableSerializer,
        'movie': OptimizedMovieTableSerializer,
        'dialogue': OptimizedDialogueTableSerializer,
        'search': OptimizedDialogueSearchSerializer,
        'legacy_movie': LegacyMovieSerializer,
        'legacy_quote': LegacyMovieQuoteSerializer,
        'legacy_search': LegacySearchSerializer,
        'statistics': StatisticsSerializer,
        'analytics': SearchAnalyticsSerializer,
        'mysql_optimization': MySQLOptimizationSerializer,
    }
    
    serializer_class = serializer_mapping.get(model_name)
    if not serializer_class:
        raise ValueError(f'알 수 없는 모델: {model_name}')
    
    return serializer_class(context=context, **kwargs)

# ===== 성능 모니터링용 시리얼라이저 =====

class PerformanceMetricsSerializer(serializers.Serializer):
    """성능 메트릭 시리얼라이저"""
    
    query_count = serializers.IntegerField()
    query_time_ms = serializers.FloatField()
    cache_hit_rate = serializers.FloatField()
    serialization_time_ms = serializers.FloatField()
    total_response_time_ms = serializers.FloatField()
    memory_usage_mb = serializers.FloatField()
    
    # MySQL 특화 메트릭
    mysql_index_hits = serializers.IntegerField()
    mysql_full_scan_count = serializers.IntegerField()
    hash_lookup_hits = serializers.IntegerField()
    
    # 상세 분석
    slow_queries = serializers.ListField(child=serializers.CharField())
    cache_misses = serializers.ListField(child=serializers.CharField())
    optimization_suggestions = serializers.ListField(child=serializers.CharField())

# ===== 로깅 및 디버깅 =====

def log_serializer_performance(serializer_name, start_time, end_time, data_count):
    """시리얼라이저 성능 로깅"""
    duration_ms = (end_time - start_time) * 1000
    logger.info(
        f"📊 [Serializer] {serializer_name}: {data_count}개 처리, "
        f"{duration_ms:.2f}ms 소요"
    )
    
    if duration_ms > 1000:  # 1초 이상
        logger.warning(f"🐌 [Serializer] {serializer_name} 성능 저하 감지: {duration_ms:.2f}ms")

logger.info("✅ MySQL 호환성 개선된 시리얼라이저 로드 완료")