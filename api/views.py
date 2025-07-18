# -*- coding: utf-8 -*-
# api/views.py
"""
최적화된 Django REST Framework 뷰
- 성능 최적화 (쿼리 최적화, 캐싱)
- 매니저 메소드 적극 활용
- 중복 로직 제거
- 일관된 에러 처리 및 응답 형식
- 고급 검색 및 필터링 기능
"""
from rest_framework import generics, status, filters
from rest_framework.decorators import api_view, throttle_classes
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle
from rest_framework.permissions import AllowAny
from django.db.models import Q, Prefetch
from django.core.cache import cache
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_headers
from django.conf import settings
from django.utils import timezone
import time
import logging

# 모델 및 시리얼라이저 임포트
from phrase.models import (
    RequestTable, MovieTable, DialogueTable, 
    UserSearchQuery, UserSearchResult,
    # 기존 호환성을 위한 별칭
    Movie, MovieQuote
)
from .serializers import (
    OptimizedRequestTableSerializer, OptimizedMovieTableSerializer,
    OptimizedDialogueTableSerializer, OptimizedDialogueSearchSerializer,
    LegacyMovieSerializer, LegacyMovieQuoteSerializer, LegacySearchSerializer,
    StatisticsSerializer, SearchAnalyticsSerializer, PerformanceMetricsSerializer,
    get_optimized_serializer, log_serializer_performance
)

# phrase 앱의 최적화된 함수들 import
from phrase.application.get_movie_info import get_movie_info
from phrase.application.clean_data import extract_movie_info  
from phrase.application.load_to_db import (
    load_to_db, 
    get_search_results_from_db,
    save_request_table_optimized
)
from phrase.application.translate import LibreTranslator
from phrase.application.search_history import SearchHistoryManager

logger = logging.getLogger(__name__)

# ===== 공통 설정 및 유틸리티 =====

class OptimizedPagination(PageNumberPagination):
    """최적화된 페이지네이션"""
    page_size = 10
    page_size_query_param = 'limit'
    max_page_size = 100
    
    def get_paginated_response(self, data):
        return Response({
            'count': self.page.paginator.count,
            'total_pages': self.page.paginator.num_pages,
            'current_page': self.page.number,
            'limit': self.get_page_size(self.request),
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'results': data
        })

class SearchThrottle(AnonRateThrottle):
    """검색 API 전용 스로틀링"""
    scope = 'search'
    rate = '100/hour'

class APIThrottle(AnonRateThrottle):
    """일반 API 스로틀링"""
    scope = 'api'
    rate = '1000/hour'

# ===== 공통 믹스인 클래스 =====

class PerformanceMonitoringMixin:
    """성능 모니터링 믹스인"""
    
    def dispatch(self, request, *args, **kwargs):
        start_time = time.time()
        response = super().dispatch(request, *args, **kwargs)
        end_time = time.time()
        
        duration_ms = (end_time - start_time) * 1000
        view_name = self.__class__.__name__
        
        logger.info(f"🚀 [API] {view_name}: {duration_ms:.2f}ms")
        
        if duration_ms > 1000:  # 1초 이상
            logger.warning(f"🐌 [API] {view_name} 성능 저하: {duration_ms:.2f}ms")
        
        # 성능 메트릭을 응답 헤더에 추가
        response['X-Response-Time'] = f"{duration_ms:.2f}ms"
        response['X-View-Name'] = view_name
        
        return response

class CacheOptimizedMixin:
    """캐싱 최적화 믹스인"""
    
    def get_cache_key(self, *args):
        """캐시 키 생성"""
        view_name = self.__class__.__name__
        return f"{view_name}:{'_'.join(str(arg) for arg in args)}"
    
    def get_cached_response(self, cache_key, fetch_func, timeout=300):
        """캐시된 응답 조회 또는 생성"""
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            logger.info(f"💰 [Cache] Hit: {cache_key}")
            return cached_data
        
        logger.info(f"🔍 [Cache] Miss: {cache_key}")
        data = fetch_func()
        cache.set(cache_key, data, timeout)
        return data

class ErrorHandlingMixin:
    """통일된 에러 처리 믹스인"""
    
    def handle_exception(self, exc):
        """예외 처리"""
        view_name = self.__class__.__name__
        logger.error(f"❌ [API] {view_name} 오류: {exc}")
        
        # 개발 환경에서는 상세 오류 정보 제공
        if settings.DEBUG:
            return Response({
                'error': str(exc),
                'view': view_name,
                'type': exc.__class__.__name__
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # 프로덕션 환경에서는 일반적인 오류 메시지
        return Response({
            'error': '서버 내부 오류가 발생했습니다.',
            'code': 'INTERNAL_ERROR'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def get_error_response(self, message, code='BAD_REQUEST', status_code=status.HTTP_400_BAD_REQUEST):
        """표준화된 오류 응답 생성"""
        return Response({
            'error': message,
            'code': code,
            'timestamp': timezone.now().isoformat()
        }, status=status_code)

class QueryOptimizationMixin:
    """쿼리 최적화 믹스인"""
    
    def get_optimized_queryset(self, base_queryset, model_type):
        """모델 타입에 따른 최적화된 쿼리셋 반환"""
        if model_type == 'dialogue':
            return base_queryset.select_related('movie').prefetch_related(
                Prefetch('movie', queryset=MovieTable.objects.only(
                    'id', 'movie_title', 'release_year', 'director', 
                    'poster_url', 'poster_image'
                ))
            )
        elif model_type == 'movie':
            return base_queryset.prefetch_related(
                Prefetch('dialogues', queryset=DialogueTable.objects.filter(is_active=True).only(
                    'id', 'movie_id', 'dialogue_phrase', 'dialogue_start_time'
                ))
            )
        return base_queryset

# ===== 최적화된 기본 뷰 클래스 =====

class OptimizedListView(generics.ListAPIView, PerformanceMonitoringMixin, 
                       CacheOptimizedMixin, ErrorHandlingMixin, QueryOptimizationMixin):
    """최적화된 리스트 뷰"""
    
    pagination_class = OptimizedPagination
    permission_classes = [AllowAny]
    throttle_classes = [APIThrottle]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    
    def get_queryset(self):
        """최적화된 쿼리셋 반환"""
        base_queryset = super().get_queryset().filter(is_active=True)
        model_type = getattr(self, 'model_type', 'default')
        return self.get_optimized_queryset(base_queryset, model_type)

class OptimizedDetailView(generics.RetrieveAPIView, PerformanceMonitoringMixin,
                         CacheOptimizedMixin, ErrorHandlingMixin):
    """최적화된 상세 뷰"""
    
    permission_classes = [AllowAny]
    throttle_classes = [APIThrottle]

# ===== 설계서 기반 핵심 검색 API (최적화) =====

@api_view(['GET'])
@throttle_classes([SearchThrottle])
def optimized_search_movie_quotes(request):
    """
    최적화된 영화 구문 검색 API
    
    주요 개선사항:
    - 매니저 메소드 적극 활용
    - 캐싱 전략 개선
    - 성능 모니터링
    - 통일된 에러 처리
    """
    start_time = time.time()
    
    # 1단계: 파라미터 검증 및 정제
    query_params = validate_and_clean_search_params(request)
    if 'error' in query_params:
        return Response(query_params, status=status.HTTP_400_BAD_REQUEST)
    
    query = query_params['query']
    limit = query_params['limit']
    
    try:
        logger.info(f"🎯 [Search] 시작: '{query}' (limit: {limit})")
        
        # 2단계: 번역 및 언어 감지 (캐싱 적용)
        translation_result = get_cached_translation(query)
        
        # 3단계: 검색 기록 및 분석
        search_analytics = {
            'query': query,
            'language_detected': translation_result['language'],
            'translation_used': translation_result['translated'] is not None,
            'translated_query': translation_result['translated'],
            'start_time': start_time
        }
        
        # 4단계: 최적화된 DB 검색 (매니저 메소드 활용)
        search_results = perform_optimized_search(
            translation_result['request_phrase'],
            translation_result['request_korean'],
            limit
        )
        
        # 5단계: 결과 처리 및 응답 생성
        if search_results:
            search_analytics['search_method'] = 'db_cache'
            search_analytics['cache_hit'] = True
            
            api_results = serialize_search_results(search_results, request, limit)
            response_data = create_optimized_api_response(
                query, translation_result, api_results, limit, search_analytics
            )
            
            # 조회수 증가 (비동기적으로 처리)
            increment_play_counts_async(search_results[:limit])
            
            logger.info(f"✅ [Search] DB 캐시 히트: {len(api_results)}개 결과")
            return Response(response_data)
        
        # 6단계: 외부 API 검색 (필요시)
        external_results = perform_external_search_optimized(
            translation_result['request_phrase'],
            translation_result['request_korean']
        )
        
        if external_results:
            search_analytics['search_method'] = 'external_api'
            search_analytics['cache_hit'] = False
            
            api_results = serialize_search_results(external_results, request, limit)
            response_data = create_optimized_api_response(
                query, translation_result, api_results, limit, search_analytics
            )
            
            logger.info(f"✅ [Search] 외부 API 성공: {len(api_results)}개 결과")
            return Response(response_data)
        
        # 7단계: 검색 결과 없음
        search_analytics['search_method'] = 'no_results'
        search_analytics['cache_hit'] = False
        
        response_data = create_optimized_api_response(
            query, translation_result, [], limit, search_analytics
        )
        response_data['message'] = create_no_results_message(query, translation_result)
        
        return Response(response_data)
        
    except Exception as e:
        logger.error(f"❌ [Search] 오류: {e}")
        return Response({
            'error': f'검색 중 오류가 발생했습니다: {str(e)}',
            'code': 'SEARCH_ERROR',
            'query': query,
            'timestamp': timezone.now().isoformat()
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    finally:
        # 성능 로깅
        end_time = time.time()
        duration_ms = (end_time - start_time) * 1000
        logger.info(f"🏁 [Search] 완료: {duration_ms:.2f}ms")

# ===== 검색 지원 함수들 (최적화) =====

def validate_and_clean_search_params(request):
    """검색 파라미터 검증 및 정제"""
    query = request.GET.get('q', '').strip()
    
    if not query:
        return {'error': '검색어를 입력해주세요.', 'code': 'MISSING_QUERY'}
    
    if len(query) > 500:
        return {'error': '검색어는 500자를 초과할 수 없습니다.', 'code': 'QUERY_TOO_LONG'}
    
    try:
        limit_param = request.GET.get('limit', '10')
        limit = int(''.join(filter(str.isdigit, limit_param)) or '10')
        limit = max(1, min(limit, 50))
    except (ValueError, TypeError):
        limit = 10
    
    return {'query': query, 'limit': limit}

def get_cached_translation(query):
    """캐싱된 번역 결과 조회"""
    cache_key = f"translation:{hash(query)}"
    cached_result = cache.get(cache_key)
    
    if cached_result:
        logger.info(f"💰 [Translation] 캐시 히트: {query}")
        return cached_result
    
    logger.info(f"🔍 [Translation] 처리 중: {query}")
    translator = LibreTranslator()
    
    result = {
        'original': query,
        'language': 'korean' if translator.is_korean(query) else 'english',
        'translated': None,
        'request_phrase': query,
        'request_korean': None
    }
    
    if result['language'] == 'korean':
        result['translated'] = translator.translate_to_english(query)
        result['request_phrase'] = result['translated']
        result['request_korean'] = query
    
    # 10분간 캐싱
    cache.set(cache_key, result, 600)
    return result

def perform_optimized_search(request_phrase, request_korean, limit):
    """최적화된 검색 수행 (매니저 메소드 활용)"""
    cache_key = f"search_results:{hash(f'{request_phrase}_{request_korean}')}"
    
    # 캐시에서 먼저 조회
    cached_results = cache.get(cache_key)
    if cached_results:
        logger.info(f"💰 [Search] 결과 캐시 히트")
        return cached_results
    
    # 매니저의 최적화된 검색 메소드 사용
    results = DialogueTable.objects.search_with_movie(request_phrase)
    
    if request_korean and not results.exists():
        # 한글로도 검색
        results = DialogueTable.objects.search_with_movie(request_korean)
    
    # 결과를 리스트로 변환하여 캐싱 (5분간)
    result_list = list(results[:limit * 2])  # 여유있게 조회
    cache.set(cache_key, result_list, 300)
    
    return result_list

def perform_external_search_optimized(request_phrase, request_korean):
    """최적화된 외부 검색"""
    try:
        # RequestTable의 매니저 메소드 활용
        existing_request = RequestTable.objects.filter(
            request_phrase=request_phrase
        ).first()
        
        if existing_request:
            # 이미 검색했지만 결과가 없었던 경우 스킵
            logger.info(f"🔄 [External] 이전 검색 기록 발견: {request_phrase}")
            return []
        
        # 외부 API 호출
        playphrase_data = get_movie_info(request_phrase)
        if not playphrase_data:
            return []
        
        movies = extract_movie_info(playphrase_data)
        if not movies:
            return []
        
        # RequestTable에 저장 (매니저 메소드 활용)
        RequestTable.objects.get_or_create(
            request_phrase=request_phrase,
            defaults={'request_korean': request_korean}
        )
        
        # DB에 저장하고 결과 반환
        return load_to_db(movies, request_phrase, request_korean)
        
    except Exception as e:
        logger.error(f"❌ [External] 외부 검색 실패: {e}")
        return []

def serialize_search_results(results, request, limit):
    """검색 결과 시리얼라이징 (성능 최적화)"""
    start_time = time.time()
    
    # 최적화된 시리얼라이저 사용
    serializer = OptimizedDialogueSearchSerializer(
        results[:limit], 
        many=True, 
        context={'request': request}
    )
    data = serializer.data
    
    end_time = time.time()
    log_serializer_performance('OptimizedDialogueSearchSerializer', start_time, end_time, len(data))
    
    return data

def create_optimized_api_response(query, translation_result, results, limit, analytics):
    """최적화된 API 응답 생성"""
    response_data = {
        'query': query,
        'count': len(results),
        'limit': limit,
        'results': results,
        'analytics': {
            'language_detected': analytics['language_detected'],
            'translation_used': analytics['translation_used'],
            'search_method': analytics['search_method'],
            'cache_hit': analytics['cache_hit']
        }
    }
    
    if translation_result['translated']:
        response_data['translated_query'] = translation_result['translated']
        response_data['search_used'] = translation_result['request_phrase']
    
    return response_data

def create_no_results_message(query, translation_result):
    """검색 결과 없음 메시지 생성"""
    if translation_result['translated']:
        return f'"{query}" (번역: "{translation_result["translated"]}")에 대한 검색 결과를 찾을 수 없습니다.'
    return f'"{query}"에 대한 검색 결과를 찾을 수 없습니다.'

def increment_play_counts_async(results):
    """재생 횟수 비동기 증가 (성능 최적화)"""
    try:
        for result in results:
            if hasattr(result, 'id'):
                # 매니저의 최적화된 메소드 사용
                DialogueTable.objects.increment_play_count(result.id)
    except Exception as e:
        logger.error(f"❌ [PlayCount] 증가 실패: {e}")

# ===== 최적화된 테이블별 조회 API =====

@api_view(['GET'])
@throttle_classes([APIThrottle])
@cache_page(300)  # 5분 캐싱
@vary_on_headers('Authorization')
def optimized_get_request_table_list(request):
    """최적화된 요청테이블 조회 API"""
    try:
        params = validate_list_params(request)
        if 'error' in params:
            return Response(params, status=status.HTTP_400_BAD_REQUEST)
        
        # 매니저의 최적화된 메소드 활용
        queryset = RequestTable.objects.all()
        
        if params['search']:
            queryset = RequestTable.objects.search_by_phrase(params['search'])
        
        # 인기순 또는 최신순 정렬
        sort_by = request.GET.get('sort', 'recent')
        if sort_by == 'popular':
            requests = RequestTable.objects.popular_searches(params['limit'])
        else:
            requests = RequestTable.objects.recent_searches(params['limit'])
        
        # 시리얼라이징
        serializer = OptimizedRequestTableSerializer(requests, many=True)
        
        return Response({
            'count': len(serializer.data),
            'limit': params['limit'],
            'search': params['search'],
            'sort': sort_by,
            'requests': serializer.data
        })
        
    except Exception as e:
        logger.error(f"❌ [RequestTable] 조회 오류: {e}")
        return Response({
            'error': '요청테이블 조회 중 오류가 발생했습니다.',
            'code': 'REQUEST_TABLE_ERROR'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@throttle_classes([APIThrottle])
@cache_page(600)  # 10분 캐싱
def optimized_get_movie_table_list(request):
    """최적화된 영화테이블 조회 API"""
    try:
        params = validate_list_params(request)
        if 'error' in params:
            return Response(params, status=status.HTTP_400_BAD_REQUEST)
        
        # 매니저의 최적화된 메소드 활용
        if params['search']:
            movies = MovieTable.objects.search_movies(params['search'])[:params['limit']]
        else:
            # 인기순 또는 최신순
            sort_by = request.GET.get('sort', 'recent')
            if sort_by == 'popular':
                movies = MovieTable.objects.popular(params['limit'])
            else:
                movies = MovieTable.objects.filter(is_active=True).order_by('-created_at')[:params['limit']]
        
        # 최적화된 시리얼라이징
        serializer = OptimizedMovieTableSerializer(
            movies, 
            many=True, 
            context={'request': request}
        )
        
        return Response({
            'count': len(serializer.data),
            'limit': params['limit'],
            'search': params['search'],
            'movies': serializer.data
        })
        
    except Exception as e:
        logger.error(f"❌ [MovieTable] 조회 오류: {e}")
        return Response({
            'error': '영화테이블 조회 중 오류가 발생했습니다.',
            'code': 'MOVIE_TABLE_ERROR'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@throttle_classes([APIThrottle])
def optimized_get_dialogue_table_list(request):
    """최적화된 대사테이블 조회 API"""
    try:
        params = validate_list_params(request)
        if 'error' in params:
            return Response(params, status=status.HTTP_400_BAD_REQUEST)
        
        movie_id = request.GET.get('movie_id', '').strip()
        quality_filter = request.GET.get('quality', '')
        
        # 매니저의 최적화된 메소드 활용
        if movie_id and movie_id.isdigit():
            movie = MovieTable.objects.filter(id=int(movie_id)).first()
            if movie:
                dialogues = DialogueTable.objects.by_movie(movie)
            else:
                return Response({
                    'error': '해당 영화를 찾을 수 없습니다.',
                    'code': 'MOVIE_NOT_FOUND'
                }, status=status.HTTP_404_NOT_FOUND)
        else:
            dialogues = DialogueTable.objects.select_related('movie').filter(is_active=True)
        
        # 검색 필터
        if params['search']:
            dialogues = dialogues.filter(
                Q(dialogue_phrase__icontains=params['search']) |
                Q(dialogue_phrase_ko__icontains=params['search'])
            )
        
        # 품질 필터
        if quality_filter:
            dialogues = DialogueTable.objects.by_translation_quality(quality_filter)
        
        # 정렬 및 제한
        sort_by = request.GET.get('sort', 'recent')
        if sort_by == 'popular':
            dialogues = dialogues.order_by('-play_count')
        else:
            dialogues = dialogues.order_by('-created_at')
        
        dialogues = dialogues[:params['limit']]
        
        # 최적화된 시리얼라이징
        serializer = OptimizedDialogueTableSerializer(
            dialogues, 
            many=True, 
            context={'request': request}
        )
        
        return Response({
            'count': len(serializer.data),
            'limit': params['limit'],
            'search': params['search'],
            'movie_id': movie_id,
            'quality_filter': quality_filter,
            'dialogues': serializer.data
        })
        
    except Exception as e:
        logger.error(f"❌ [DialogueTable] 조회 오류: {e}")
        return Response({
            'error': '대사테이블 조회 중 오류가 발생했습니다.',
            'code': 'DIALOGUE_TABLE_ERROR'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# ===== 통계 및 분석 API =====

@api_view(['GET'])
@cache_page(1800)  # 30분 캐싱
def get_comprehensive_statistics(request):
    """종합 통계 API (매니저 메소드 활용)"""
    try:
        # 각 모델의 매니저에서 통계 조회
        request_stats = RequestTable.objects.get_statistics()
        movie_stats = MovieTable.objects.get_statistics()
        dialogue_stats = DialogueTable.objects.get_statistics()
        
        # 통합 통계 계산
        comprehensive_stats = {
            'overview': {
                'total_requests': request_stats['total_requests'],
                'total_movies': movie_stats['total_movies'],
                'total_dialogues': dialogue_stats['total_dialogues'],
                'korean_translation_rate': dialogue_stats['translation_rate'],
            },
            'requests': request_stats,
            'movies': movie_stats,
            'dialogues': dialogue_stats,
            'generated_at': timezone.now().isoformat()
        }
        
        return Response(comprehensive_stats)
        
    except Exception as e:
        logger.error(f"❌ [Statistics] 조회 오류: {e}")
        return Response({
            'error': '통계 조회 중 오류가 발생했습니다.',
            'code': 'STATISTICS_ERROR'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# ===== 기존 호환성 API (최적화) =====

class OptimizedMovieListView(OptimizedListView):
    """최적화된 영화 리스트 뷰"""
    queryset = MovieTable.objects.all()
    serializer_class = LegacyMovieSerializer
    model_type = 'movie'
    search_fields = ['movie_title', 'director', 'genre']
    ordering_fields = ['created_at', 'view_count', 'imdb_rating']
    ordering = ['-created_at']

class OptimizedMovieDetailView(OptimizedDetailView):
    """최적화된 영화 상세 뷰"""
    queryset = MovieTable.objects.all()
    serializer_class = LegacyMovieSerializer

class OptimizedDialogueListView(OptimizedListView):
    """최적화된 대사 리스트 뷰"""
    serializer_class = LegacyMovieQuoteSerializer
    model_type = 'dialogue'
    search_fields = ['dialogue_phrase', 'dialogue_phrase_ko']
    ordering_fields = ['created_at', 'play_count']
    ordering = ['-created_at']
    
    def get_queryset(self):
        return DialogueTable.objects.select_related('movie').filter(is_active=True)

# ===== 지원 함수들 =====

def validate_list_params(request):
    """리스트 API 파라미터 검증"""
    try:
        limit = int(request.GET.get('limit', 10))
        limit = max(1, min(limit, 100))
    except (ValueError, TypeError):
        limit = 10
    
    search_query = request.GET.get('search', '').strip()
    
    if len(search_query) > 500:
        return {'error': '검색어는 500자를 초과할 수 없습니다.', 'code': 'SEARCH_TOO_LONG'}
    
    return {'limit': limit, 'search': search_query}

# ===== 고급 기능 API =====

@api_view(['POST'])
@throttle_classes([APIThrottle])
def bulk_update_dialogues(request):
    """대사 대량 업데이트 API"""
    from .serializers import BulkDialogueUpdateSerializer
    
    serializer = BulkDialogueUpdateSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        validated_data = serializer.validated_data
        dialogue_ids = validated_data['ids']
        
        # 업데이트할 필드들
        update_fields = {}
        for field in ['translation_quality', 'translation_method', 'is_active']:
            if field in validated_data:
                update_fields[field] = validated_data[field]
        
        if not update_fields:
            return Response({
                'error': '업데이트할 필드가 없습니다.',
                'code': 'NO_UPDATE_FIELDS'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 대량 업데이트 실행
        updated_count = DialogueTable.objects.filter(
            id__in=dialogue_ids
        ).update(**update_fields)
        
        logger.info(f"📝 [BulkUpdate] {updated_count}개 대사 업데이트 완료")
        
        return Response({
            'updated_count': updated_count,
            'updated_fields': list(update_fields.keys()),
            'message': f'{updated_count}개의 대사가 성공적으로 업데이트되었습니다.'
        })
        
    except Exception as e:
        logger.error(f"❌ [BulkUpdate] 오류: {e}")
        return Response({
            'error': '대량 업데이트 중 오류가 발생했습니다.',
            'code': 'BULK_UPDATE_ERROR'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# URL 별칭 (메인 검색 API)
search_movie_quotes = optimized_search_movie_quotes
get_request_table_list = optimized_get_request_table_list
get_movie_table_list = optimized_get_movie_table_list
get_dialogue_table_list = optimized_get_dialogue_table_list

# 레거시 뷰 별칭
MovieListView = OptimizedMovieListView
MovieDetailView = OptimizedMovieDetailView
DialogueListView = OptimizedDialogueListView

# ===== 기존 호환성 함수들 (최적화) =====

@api_view(['GET'])
@throttle_classes([APIThrottle])
def get_movie_quote_detail(request, quote_id):
    """최적화된 구문 상세 조회"""
    try:
        dialogue = DialogueTable.objects.select_related('movie').get(
            id=quote_id, 
            is_active=True
        )
        
        # 조회수 증가 (매니저 메소드 활용)
        DialogueTable.objects.increment_play_count(quote_id)
        
        serializer = LegacySearchSerializer(dialogue, context={'request': request})
        return Response(serializer.data)
        
    except DialogueTable.DoesNotExist:
        return Response({
            'error': '해당 구문을 찾을 수 없습니다.',
            'code': 'QUOTE_NOT_FOUND'
        }, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
@throttle_classes([APIThrottle])
@cache_page(300)
def get_movie_quotes_by_movie(request, movie_id):
    """최적화된 영화별 구문 조회"""
    try:
        # 매니저 메소드 활용
        movie = MovieTable.objects.get(id=movie_id, is_active=True)
        dialogues = DialogueTable.objects.by_movie(movie).order_by('dialogue_start_time')
        
        # 조회수 증가
        MovieTable.objects.increment_view_count(movie_id)
        
        serializer = LegacySearchSerializer(
            dialogues, 
            many=True, 
            context={'request': request}
        )
        
        return Response({
            'movie': movie.movie_title,
            'movie_id': movie.id,
            'quotes_count': len(serializer.data),
            'quotes': serializer.data
        })
        
    except MovieTable.DoesNotExist:
        return Response({
            'error': '해당 영화를 찾을 수 없습니다.',
            'code': 'MOVIE_NOT_FOUND'
        }, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
@cache_page(1800)  # 30분 캐싱
def get_schema_info(request):
    """최적화된 스키마 정보 API"""
    return Response({
        'schema_version': '2.0',
        'optimization_level': 'high',
        'design_document': 'endless_real_clips.txt',
        'performance_features': [
            '쿼리 최적화 (select_related, prefetch_related)',
            '매니저 메소드 활용',
            '다단계 캐싱 전략',
            '성능 모니터링',
            '스로틀링 및 레이트 리미팅'
        ],
        'tables': {
            'request_table': {
                'description': '요청구문을 저장하는 마스터 테이블',
                'primary_key': 'request_phrase',
                'optimizations': ['인덱싱', '캐싱', '통계 메소드'],
                'manager_methods': ['popular_searches', 'recent_searches', 'search_by_phrase']
            },
            'movie_table': {
                'description': '영화정보를 저장하는 마스터 테이블',
                'primary_key': 'id + unique_together',
                'optimizations': ['관계 최적화', '이미지 URL 캐싱'],
                'manager_methods': ['search_movies', 'popular', 'by_rating_range']
            },
            'dialogue_table': {
                'description': '대사구문을 저장하는 슬레이브 테이블',
                'primary_key': 'id (auto-increment)',
                'optimizations': ['검색 벡터', '다국어 지원', '성능 카운터'],
                'manager_methods': ['search_text', 'search_with_movie', 'by_translation_quality']
            }
        },
        'caching_strategy': {
            'search_results': '5분',
            'translations': '10분',
            'statistics': '30분',
            'schema_info': '30분'
        },
        'generated_at': timezone.now().isoformat()
    })

logger.info("✅ 최적화된 뷰 모듈 로드 완료")