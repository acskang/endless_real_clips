# -*- coding: utf-8 -*-
# dj/phrase/views/api_views.py
"""
API 뷰 - JSON 응답 전담
"""
import logging
from django.http import JsonResponse
from django.views.decorators.cache import cache_page

from phrase.models import RequestTable, MovieTable, DialogueTable, UserSearchQuery

logger = logging.getLogger(__name__)


@cache_page(60 * 5)  # 5분 캐싱
def popular_searches_api(request):
    """인기 검색어 API"""
    try:
        # 매니저 메서드 대신 직접 쿼리 사용
        popular_requests = RequestTable.objects.filter(
            is_active=True,
            search_count__gt=1
        ).order_by('-search_count')[:10]
        
        popular_queries = UserSearchQuery.objects.filter(
            is_active=True,
            search_count__gt=1
        ).order_by('-search_count')[:10]
        
        data = {
            'popular_requests': [
                {
                    'phrase': req.request_phrase,
                    'korean': req.request_korean,
                    'count': req.search_count,
                }
                for req in popular_requests
            ],
            'popular_queries': [
                {
                    'query': query.original_query,
                    'translated': query.translated_query,
                    'count': query.search_count,
                }
                for query in popular_queries
            ]
        }
        
        return JsonResponse(data)
        
    except Exception as e:
        logger.error(f"❌ 인기 검색어 API 오류: {e}")
        return JsonResponse({'error': '데이터를 불러올 수 없습니다.'}, status=500)


@cache_page(60 * 10)  # 10분 캐싱
def statistics_api(request):
    """통계 API"""
    try:
        # get_all_statistics 대신 직접 통계 수집
        stats = {
            'movies': {
                'total_movies': MovieTable.objects.filter(is_active=True).count(),
                'verified_movies': MovieTable.objects.filter(is_active=True, data_quality='verified').count(),
                'recent_movies': MovieTable.objects.filter(is_active=True).order_by('-created_at')[:5].count(),
            },
            'dialogues': {
                'total_dialogues': DialogueTable.objects.filter(is_active=True).count(),
                'with_korean': DialogueTable.objects.filter(is_active=True, dialogue_phrase_ko__isnull=False).exclude(dialogue_phrase_ko='').count(),
                'translation_rate': 0,  # 나중에 계산
            },
            'requests': {
                'total_requests': RequestTable.objects.filter(is_active=True).count(),
                'successful_requests': RequestTable.objects.filter(is_active=True, result_count__gt=0).count(),
                'popular_requests': RequestTable.objects.filter(is_active=True, search_count__gt=1).count(),
            }
        }
        
        # 번역율 계산
        total_dialogues = stats['dialogues']['total_dialogues']
        if total_dialogues > 0:
            stats['dialogues']['translation_rate'] = round(
                (stats['dialogues']['with_korean'] / total_dialogues) * 100, 1
            )
        
        return JsonResponse({
            'statistics': stats,
            'success': True
        })
        
    except Exception as e:
        logger.error(f"❌ 통계 API 오류: {e}")
        return JsonResponse({'error': '통계를 불러올 수 없습니다.'}, status=500)