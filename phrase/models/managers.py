# -*- coding: utf-8 -*-
# phrase/models/managers.py
"""
Django 모델 매니저 정의 (일본어/중국어 제거)
- 커스텀 쿼리셋 및 매니저
- 성능 최적화된 쿼리 메소드
- 재사용 가능한 비즈니스 로직
"""
from django.db import models
from django.core.cache import cache
from django.utils import timezone
from django.apps import apps
import logging

logger = logging.getLogger(__name__)

# ===== 기본 매니저들 =====

class ActiveManager(models.Manager):
    """활성 객체만 반환하는 매니저"""
    def get_queryset(self):
        return super().get_queryset().filter(is_active=True)
    
    def inactive(self):
        """비활성 객체들 반환"""
        return super().get_queryset().filter(is_active=False)
    
    def toggle_active(self, obj_id):
        """활성 상태 토글"""
        try:
            obj = self.get(id=obj_id)
            obj.is_active = not obj.is_active
            obj.save(update_fields=['is_active', 'updated_at'])
            return obj
        except self.model.DoesNotExist:
            return None

# ===== 요청 테이블 매니저 =====

class RequestManager(models.Manager):
    """요청 테이블 전용 매니저"""
    
    def popular_searches(self, limit=10):
        """인기 검색어 조회"""
        return self.filter(is_active=True).order_by('-search_count', '-last_searched_at')[:limit]
    
    def recent_searches(self, limit=10):
        """최근 검색어 조회"""
        return self.filter(is_active=True).order_by('-last_searched_at')[:limit]
    
    def by_translation_quality(self, quality):
        """번역 품질별 조회"""
        return self.filter(translation_quality=quality, is_active=True)
    
    def search_by_phrase(self, phrase):
        """구문으로 검색"""
        return self.filter(
            models.Q(request_phrase__icontains=phrase) |
            models.Q(request_korean__icontains=phrase)
        ).filter(is_active=True)
    
    def increment_search_count(self, phrase):
        """검색 횟수 증가 (안전한 방식)"""
        try:
            obj = self.get(request_phrase=phrase)
            obj.search_count = models.F('search_count') + 1
            obj.last_searched_at = timezone.now()
            obj.save(update_fields=['search_count', 'last_searched_at'])
            obj.refresh_from_db(fields=['search_count'])
            return obj
        except self.model.DoesNotExist:
            return None
    
    def get_statistics(self):
        """요청 통계 조회"""
        cache_key = 'request_statistics'
        stats = cache.get(cache_key)
        
        if stats is None:
            stats = {
                'total_requests': self.count(),
                'active_requests': self.filter(is_active=True).count(),
                'with_korean': self.exclude(request_korean__isnull=True).exclude(request_korean='').count(),
                'avg_search_count': self.aggregate(avg=models.Avg('search_count'))['avg'] or 0,
                'top_quality_distribution': dict(
                    self.values('translation_quality').annotate(count=models.Count('id')).values_list('translation_quality', 'count')
                )
            }
            # 5분간 캐싱
            cache.set(cache_key, stats, 300)
        
        return stats

# ===== 영화 테이블 매니저 =====

class MovieManager(models.Manager):
    """영화 모델 전용 매니저"""
    
    def with_dialogues(self):
        """대사가 있는 영화들"""
        return self.prefetch_related('dialogues').filter(
            dialogues__isnull=False, 
            is_active=True
        ).distinct()
    
    def by_quality(self, quality='verified'):
        """데이터 품질별 조회"""
        return self.filter(data_quality=quality, is_active=True)
    
    def popular(self, limit=10):
        """인기 영화 (조회수 기준)"""
        return self.filter(is_active=True).order_by('-view_count')[:limit]
    
    def by_year_range(self, start_year, end_year=None):
        """연도 범위별 조회"""
        if end_year is None:
            end_year = timezone.now().year
        
        return self.filter(
            release_year__gte=str(start_year),
            release_year__lte=str(end_year),
            is_active=True
        )
    
    def by_country(self, country):
        """제작국가별 조회"""
        return self.filter(production_country__icontains=country, is_active=True)
    
    def by_director(self, director):
        """감독별 조회"""
        return self.filter(director__icontains=director, is_active=True)
    
    def by_rating_range(self, min_rating, max_rating=10.0):
        """평점 범위별 조회"""
        return self.filter(
            imdb_rating__gte=min_rating,
            imdb_rating__lte=max_rating,
            is_active=True
        ).exclude(imdb_rating__isnull=True)
    
    def with_posters(self):
        """포스터가 있는 영화들"""
        return self.filter(is_active=True).exclude(
            models.Q(poster_image='') & models.Q(poster_url='')
        )
    
    def search_movies(self, query):
        """영화 검색"""
        return self.filter(
            models.Q(movie_title__icontains=query) |
            models.Q(original_title__icontains=query) |
            models.Q(director__icontains=query) |
            models.Q(genre__icontains=query)
        ).filter(is_active=True).distinct()
    
    def increment_view_count(self, movie_id):
        """조회수 증가 (안전한 방식)"""
        try:
            movie = self.get(id=movie_id)
            movie.view_count = models.F('view_count') + 1
            movie.save(update_fields=['view_count'])
            movie.refresh_from_db(fields=['view_count'])
            return movie
        except self.model.DoesNotExist:
            return None
    
    def get_statistics(self):
        """영화 통계 조회"""
        cache_key = 'movie_statistics'
        stats = cache.get(cache_key)
        
        if stats is None:
            stats = {
                'total_movies': self.count(),
                'active_movies': self.filter(is_active=True).count(),
                'with_posters': self.with_posters().count(),
                'with_ratings': self.exclude(imdb_rating__isnull=True).count(),
                'avg_rating': self.aggregate(avg=models.Avg('imdb_rating'))['avg'] or 0,
                'by_decade': self._get_decade_distribution(),
                'by_country': dict(
                    self.values('production_country').annotate(count=models.Count('id')).order_by('-count')[:10].values_list('production_country', 'count')
                )
            }
            # 10분간 캐싱
            cache.set(cache_key, stats, 600)
        
        return stats
    
    def _get_decade_distribution(self):
        """연대별 영화 분포"""
        decades = {}
        for movie in self.values('release_year'):
            try:
                year = int(movie['release_year'])
                decade = (year // 10) * 10
                decades[f"{decade}s"] = decades.get(f"{decade}s", 0) + 1
            except (ValueError, TypeError):
                decades['Unknown'] = decades.get('Unknown', 0) + 1
        
        return dict(sorted(decades.items(), key=lambda x: x[0]))

# ===== 대사 테이블 매니저 =====

class DialogueManager(models.Manager):
    """대사 모델 전용 매니저"""
    
    def with_korean(self):
        """한글 번역이 있는 대사들"""
        return self.exclude(
            dialogue_phrase_ko__isnull=True
        ).exclude(
            dialogue_phrase_ko=''
        ).filter(is_active=True)
    
    def without_korean(self):
        """한글 번역이 없는 대사들"""
        return self.filter(
            models.Q(dialogue_phrase_ko__isnull=True) | 
            models.Q(dialogue_phrase_ko='')
        ).filter(is_active=True)
    
    def by_translation_quality(self, quality='good'):
        """번역 품질별 조회"""
        return self.filter(translation_quality=quality, is_active=True)
    
    def by_translation_method(self, method):
        """번역 방식별 조회"""
        return self.filter(translation_method=method, is_active=True)
    
    def by_movie(self, movie):
        """특정 영화의 대사들"""
        return self.select_related('movie').filter(movie=movie, is_active=True)
    
    def popular_dialogues(self, limit=10):
        """인기 대사 (재생 횟수 기준)"""
        return self.filter(is_active=True).order_by('-play_count')[:limit]
    
    def recent_dialogues(self, limit=10):
        """최근 추가된 대사들"""
        return self.filter(is_active=True).order_by('-created_at')[:limit]
    
    def with_videos(self):
        """비디오 파일이 있는 대사들"""
        return self.filter(is_active=True).exclude(
            models.Q(video_file='') & models.Q(video_url='')
        )
    
    def by_duration_range(self, min_seconds, max_seconds):
        """길이 범위별 조회"""
        return self.filter(
            duration_seconds__gte=min_seconds,
            duration_seconds__lte=max_seconds,
            is_active=True
        ).exclude(duration_seconds__isnull=True)
    
    def search_text(self, query):
        """텍스트 검색 (영어/한국어만 지원)"""
        return self.filter(
            models.Q(dialogue_phrase__icontains=query) |
            models.Q(dialogue_phrase_ko__icontains=query) |
            models.Q(search_vector__icontains=query.lower())
        ).filter(is_active=True).distinct()
    
    def search_with_movie(self, query):
        """영화 정보 포함 검색"""
        return self.select_related('movie').filter(
            models.Q(dialogue_phrase__icontains=query) |
            models.Q(dialogue_phrase_ko__icontains=query) |
            models.Q(movie__movie_title__icontains=query) |
            models.Q(movie__director__icontains=query)
        ).filter(is_active=True).distinct()
    
    def increment_play_count(self, dialogue_id):
        """재생 횟수 증가 (안전한 방식)"""
        try:
            dialogue = self.get(id=dialogue_id)
            dialogue.play_count = models.F('play_count') + 1
            dialogue.save(update_fields=['play_count'])
            dialogue.refresh_from_db(fields=['play_count'])
            
            # 영화 조회수도 함께 증가 (수정된 방식)
            movie = dialogue.movie
            movie.view_count = models.F('view_count') + 1
            movie.save(update_fields=['view_count'])
            
            return dialogue
        except self.model.DoesNotExist:
            return None
    
    def needs_translation(self, language='ko'):
        """번역이 필요한 대사들 (한국어만 지원)"""
        if language == 'ko':
            return self.without_korean()
        else:
            # 한국어 외 다른 언어는 지원하지 않음
            return self.none()
    
    def update_search_vectors_bulk(self):
        """검색 벡터 일괄 업데이트"""
        import re
        
        dialogues = list(self.filter(is_active=True))
        updated_count = 0
        batch_size = 100
        
        for i in range(0, len(dialogues), batch_size):
            batch = dialogues[i:i + batch_size]
            
            for dialogue in batch:
                # 검색 벡터 생성
                texts = [dialogue.dialogue_phrase]
                if dialogue.dialogue_phrase_ko:
                    texts.append(dialogue.dialogue_phrase_ko)
                
                # 텍스트 정규화
                normalized_texts = []
                for text in texts:
                    normalized = re.sub(r'[^\w\s]', ' ', text.lower())
                    normalized = re.sub(r'\s+', ' ', normalized).strip()
                    normalized_texts.append(normalized)
                
                dialogue.search_vector = ' '.join(normalized_texts)[:1000]
                updated_count += 1
            
            # 배치 업데이트
            self.model.objects.bulk_update(batch, ['search_vector'])
            logger.info(f"검색 벡터 업데이트 진행: {updated_count}개 완료")
        
        logger.info(f"검색 벡터 일괄 업데이트 완료: {updated_count}개")
        return updated_count
    
    def get_statistics(self):
        """대사 통계 조회"""
        cache_key = 'dialogue_statistics'
        stats = cache.get(cache_key)
        
        if stats is None:
            total_dialogues = self.count()
            with_korean = self.with_korean().count()
            
            stats = {
                'total_dialogues': total_dialogues,
                'active_dialogues': self.filter(is_active=True).count(),
                'with_korean': with_korean,
                'without_korean': total_dialogues - with_korean,
                'translation_rate': round((with_korean / total_dialogues * 100), 1) if total_dialogues > 0 else 0,
                'with_videos': self.with_videos().count(),
                'avg_play_count': self.aggregate(avg=models.Avg('play_count'))['avg'] or 0,
                'by_translation_method': dict(
                    self.values('translation_method').annotate(count=models.Count('id')).values_list('translation_method', 'count')
                ),
                'by_quality': dict(
                    self.values('translation_quality').annotate(count=models.Count('id')).values_list('translation_quality', 'count')
                )
            }
            # 5분간 캐싱
            cache.set(cache_key, stats, 300)
        
        return stats

# ===== 사용자 검색 매니저 =====

class UserSearchQueryManager(models.Manager):
    """사용자 검색 쿼리 매니저"""
    
    def by_session(self, session_key):
        """세션별 검색 기록"""
        return self.filter(session_key=session_key).order_by('-created_at')
    
    def popular_queries(self, limit=10):
        """인기 검색어"""
        return self.filter(has_results=True).order_by('-search_count')[:limit]
    
    def successful_searches(self):
        """결과가 있는 검색들"""
        return self.filter(has_results=True)
    
    def failed_searches(self):
        """결과가 없는 검색들"""
        return self.filter(has_results=False)
    
    def by_response_time(self, max_ms):
        """응답 시간별 조회"""
        return self.filter(response_time_ms__lte=max_ms).exclude(response_time_ms__isnull=True)

class UserSearchResultManager(models.Manager):
    """사용자 검색 결과 매니저"""
    
    def by_relevance(self):
        """관련성 순 정렬"""
        return self.order_by('-relevance_score', '-created_at')
    
    def high_relevance(self, threshold=0.8):
        """높은 관련성 결과들"""
        return self.filter(relevance_score__gte=threshold)

# ===== 캐시 무효화 매니저 =====

class CacheInvalidationManager(models.Manager):
    """캐시 무효화 관리 매니저"""
    
    def by_model(self, model_name):
        """모델별 캐시 무효화 기록"""
        return self.filter(model_name=model_name).order_by('-created_at')
    
    def recent_invalidations(self, hours=24):
        """최근 무효화 기록"""
        cutoff = timezone.now() - timezone.timedelta(hours=hours)
        return self.filter(created_at__gte=cutoff)
    
    def cleanup_old_records(self, days=7):
        """오래된 기록 정리"""
        cutoff = timezone.now() - timezone.timedelta(days=days)
        deleted_count = self.filter(created_at__lt=cutoff).delete()[0]
        logger.info(f"캐시 무효화 기록 {deleted_count}개 정리 완료")
        return deleted_count

# ===== 매니저 유틸리티 함수 =====

def clear_all_model_caches():
    """모든 모델 관련 캐시 초기화"""
    cache_keys = [
        'request_statistics',
        'movie_statistics', 
        'dialogue_statistics'
    ]
    
    for key in cache_keys:
        cache.delete(key)
    
    logger.info("모든 모델 캐시 초기화 완료")

def get_all_statistics():
    """모든 모델의 통계 조회"""
    if not apps.ready:
        return {}
    
    try:
        # 동적 임포트로 순환 참조 방지
        RequestTable = apps.get_model('phrase', 'RequestTable')
        MovieTable = apps.get_model('phrase', 'MovieTable')
        DialogueTable = apps.get_model('phrase', 'DialogueTable')
        
        return {
            'requests': RequestTable.objects.get_statistics(),
            'movies': MovieTable.objects.get_statistics(),
            'dialogues': DialogueTable.objects.get_statistics(),
            'generated_at': timezone.now().isoformat()
        }
    except Exception as e:
        logger.error(f"통계 조회 실패: {e}")
        return {}