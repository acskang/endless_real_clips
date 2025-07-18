# dj/phrase/application/search_history.py
# This module manages the search history functionality for the phrase application.
# It includes saving search queries, managing search results, and retrieving popular and recent searches.
# It is designed to handle user search queries and results efficiently, providing insights into search patterns.
from phrase.models import UserSearchQuery, UserSearchResult, MovieQuote
from django.db.models import Q, F

class SearchHistoryManager:
    """검색 기록을 관리하는 클래스"""
    
    @staticmethod
    def save_search_query(original_query, translated_query=None, result_count=0):
        """검색어를 저장하거나 업데이트"""
        search_query, created = UserSearchQuery.objects.get_or_create(
            original_query=original_query,
            defaults={
                'translated_query': translated_query,
                'result_count': result_count,
                'has_results': result_count > 0,
            }
        )
        
        if not created:
            # 기존 검색어인 경우 카운트 증가
            search_query.search_count = F('search_count') + 1
            search_query.translated_query = translated_query
            search_query.result_count = result_count
            search_query.has_results = result_count > 0
            search_query.save()
            search_query.refresh_from_db()
        
        return search_query
    
    @staticmethod
    def save_search_results(search_query, movie_quotes):
        """검색 결과를 저장"""
        # 기존 결과 삭제
        UserSearchResult.objects.filter(search_query=search_query).delete()
        
        # 새 결과 저장
        results = []
        for i, quote in enumerate(movie_quotes):
            relevance_score = 1.0 - (i * 0.1)  # 순서에 따른 관련성 점수
            results.append(UserSearchResult(
                search_query=search_query,
                movie_quote=quote,
                relevance_score=max(relevance_score, 0.1)
            ))
        
        UserSearchResult.objects.bulk_create(results)
    
    @staticmethod
    def get_popular_searches(limit=10):
        """인기 검색어 조회"""
        return UserSearchQuery.objects.filter(
            has_results=True
        ).order_by('-search_count', '-last_searched_at')[:limit]
    
    @staticmethod
    def get_recent_searches(limit=10):
        """최근 검색어 조회"""
        return UserSearchQuery.objects.order_by('-last_searched_at')[:limit]
    
    @staticmethod
    def get_korean_searches(limit=10):
        """한글 검색어만 조회"""
        import re
        korean_queries = UserSearchQuery.objects.filter(
            original_query__regex=r'[가-힣]'
        ).order_by('-search_count', '-last_searched_at')[:limit]
        return korean_queries