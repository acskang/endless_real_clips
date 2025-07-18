# -*- coding: utf-8 -*-
# phrase/models.py
"""
최적화된 Django 모델 정의 - Primary Key 충돌 해결
"""
import os
import uuid
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinLengthValidator, MaxLengthValidator, URLValidator
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.core.cache import cache
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
import logging

# 매니저 임포트
from .managers import (
    ActiveManager, RequestManager, MovieManager, DialogueManager,
    UserSearchQueryManager, UserSearchResultManager, CacheInvalidationManager
)

logger = logging.getLogger(__name__)

# ===== 커스텀 필드 및 유틸리티 =====

class OptimizedCharField(models.CharField):
    """최적화된 CharField (자동 인덱싱 및 검증)"""
    def __init__(self, *args, **kwargs):
        if 'db_index' not in kwargs and kwargs.get('max_length', 0) <= 255:
            kwargs['db_index'] = True
        super().__init__(*args, **kwargs)

class SecureURLField(models.URLField):
    """보안이 강화된 URL 필드"""
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('validators', [])
        kwargs['validators'].append(URLValidator(schemes=['http', 'https']))
        super().__init__(*args, **kwargs)
    
    def clean(self, value, model_instance):
        value = super().clean(value, model_instance)
        if value:
            dangerous_patterns = ['javascript:', 'data:', 'vbscript:', 'file:']
            if any(pattern in value.lower() for pattern in dangerous_patterns):
                raise ValidationError(_('안전하지 않은 URL입니다.'))
        return value

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

# ===== 추상 기본 모델 =====

class BaseModel(models.Model):
    """모든 모델의 기본 클래스"""
    id = models.BigAutoField(primary_key=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="생성시간")
    updated_at = models.DateTimeField(auto_now=True, db_index=True, verbose_name="수정시간")
    is_active = models.BooleanField(default=True, db_index=True, verbose_name="활성 상태")
    metadata = models.JSONField(default=dict, blank=True, verbose_name="메타데이터")
    
    class Meta:
        abstract = True
        ordering = ['-created_at']
    
    def soft_delete(self):
        """소프트 삭제"""
        self.is_active = False
        self.save(update_fields=['is_active', 'updated_at'])
    
    def restore(self):
        """삭제된 항목 복원"""
        self.is_active = True
        self.save(update_fields=['is_active', 'updated_at'])

# ===== 메인 모델들 =====

class RequestTable(BaseModel):
    """요청테이블 - 사용자 검색 요청을 저장"""
    # ✅ primary_key=True 제거, unique=True만 유지
    request_phrase = models.CharField(
        max_length=254,
        unique=True,  # ✅ 중복 방지만 유지
        db_index=True,  # ✅ 인덱스는 별도 추가
        validators=[MinLengthValidator(1), MaxLengthValidator(500)],
        verbose_name="요청구문"
    )
    
    request_korean = OptimizedCharField(
        max_length=500,
        blank=True,
        null=True,
        validators=[MaxLengthValidator(500)],
        verbose_name="요청한글"
    )
    
    search_count = models.PositiveIntegerField(default=1, verbose_name="검색 횟수")
    last_searched_at = models.DateTimeField(auto_now=True, verbose_name="마지막 검색 시간")
    result_count = models.PositiveIntegerField(default=0, verbose_name="검색 결과 수")
    
    translation_quality = models.CharField(
        max_length=20,
        choices=[
            ('excellent', '우수'),
            ('good', '양호'),
            ('fair', '보통'),
            ('poor', '미흡'),
            ('unknown', '미확인')
        ],
        default='unknown',
        verbose_name="번역 품질"
    )
    
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name="요청 IP")
    user_agent = models.TextField(blank=True, max_length=1000, verbose_name="사용자 에이전트")
    
    # 매니저
    objects = RequestManager()
    active = ActiveManager()

    class Meta:
        db_table = 'request_table'
        verbose_name = "검색 요청"
        verbose_name_plural = "검색 요청들"
        indexes = [
            models.Index(fields=['request_phrase']),
            models.Index(fields=['request_korean']),
            models.Index(fields=['search_count', '-last_searched_at']),
            models.Index(fields=['-last_searched_at']),
            models.Index(fields=['translation_quality']),
            models.Index(fields=['is_active', '-search_count']),
            models.Index(fields=['created_at', 'is_active']),
        ]
        constraints = [
            models.CheckConstraint(check=models.Q(search_count__gte=0), name='positive_search_count'),
            models.CheckConstraint(check=models.Q(result_count__gte=0), name='positive_result_count'),
        ]

    def __str__(self):
        korean_part = f" ({self.request_korean})" if self.request_korean else ""
        return f"{self.request_phrase}{korean_part} [{self.search_count}회]"
    
    def clean(self):
        super().clean()
        if self.request_phrase:
            self.request_phrase = self.request_phrase.strip()
        if self.request_korean:
            self.request_korean = self.request_korean.strip()

class MovieTable(BaseModel):
    """영화테이블 - 영화 정보 저장"""
    movie_title = OptimizedCharField(
        max_length=300,
        validators=[MinLengthValidator(1)],
        verbose_name="영화 제목"
    )
    
    original_title = OptimizedCharField(
        max_length=300,
        blank=True,
        verbose_name="원제목"
    )
    
    release_year = OptimizedCharField(
        max_length=4,
        default='1004',
        validators=[MinLengthValidator(4), MaxLengthValidator(4)],
        verbose_name="개봉연도"
    )
    
    production_country = OptimizedCharField(
        max_length=100,
        default='지구',
        verbose_name="제작국가"
    )
    
    director = OptimizedCharField(
        max_length=300,
        default='ahading',
        verbose_name="감독"
    )
    
    genre = models.CharField(max_length=200, blank=True, verbose_name="장르")
    
    imdb_rating = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        null=True,
        blank=True,
        verbose_name="IMDB 평점"
    )
    
    imdb_url = SecureURLField(
        max_length=600,
        blank=True,
        null=True,
        verbose_name="IMDB URL"
    )
    
    poster_url = SecureURLField(
        max_length=600,
        blank=True,
        null=True,
        verbose_name="포스터 URL"
    )
    
    poster_image = models.ImageField(
        upload_to=get_poster_upload_path,
        blank=True,
        null=True,
        max_length=500,
        verbose_name="포스터 이미지"
    )
    
    poster_image_path = models.CharField(
        max_length=600,
        blank=True,
        verbose_name="포스터 경로"
    )
    
    data_quality = models.CharField(
        max_length=20,
        choices=[
            ('verified', '검증됨'),
            ('pending', '검토중'),
            ('incomplete', '불완전'),
            ('error', '오류')
        ],
        default='pending',
        verbose_name="데이터 품질"
    )
    
    view_count = models.PositiveIntegerField(default=0, verbose_name="조회수")
    like_count = models.PositiveIntegerField(default=0, verbose_name="좋아요 수")
    
    # 매니저
    objects = MovieManager()
    active = ActiveManager()

    class Meta:
        db_table = 'movie_table'
        verbose_name = "영화"
        verbose_name_plural = "영화들"
        unique_together = [('movie_title', 'release_year', 'director')]
        indexes = [
            models.Index(fields=['movie_title']),
            models.Index(fields=['release_year']),
            models.Index(fields=['director']),
            models.Index(fields=['genre']),
            models.Index(fields=['imdb_rating']),
            models.Index(fields=['data_quality']),
            models.Index(fields=['-view_count']),
            models.Index(fields=['movie_title', 'release_year']),
            models.Index(fields=['is_active', 'data_quality']),
            models.Index(fields=['-created_at', 'is_active']),
        ]
        constraints = [
            models.CheckConstraint(check=models.Q(view_count__gte=0), name='positive_view_count'),
            models.CheckConstraint(check=models.Q(like_count__gte=0), name='positive_like_count'),
            models.CheckConstraint(check=models.Q(imdb_rating__gte=0) & models.Q(imdb_rating__lte=10), name='valid_imdb_rating'),
        ]

    def __str__(self):
        return f"{self.movie_title} ({self.release_year})"
    
    def clean(self):
        super().clean()
        if self.movie_title:
            self.movie_title = self.movie_title.strip()
        if self.original_title:
            self.original_title = self.original_title.strip()
        if self.director:
            self.director = self.director.strip()
    
    def get_display_title(self):
        """표시용 제목 반환"""
        if self.original_title and self.original_title != self.movie_title:
            return f"{self.movie_title} ({self.original_title})"
        return self.movie_title

class DialogueTable(BaseModel):
    """대사테이블 - 영화 대사 정보 저장"""
    movie = models.ForeignKey(
        MovieTable,
        related_name='dialogues',
        on_delete=models.CASCADE,
        db_index=True,
        verbose_name="영화"
    )
    
    dialogue_phrase = models.TextField(
        validators=[MinLengthValidator(1)],
        verbose_name="영어 대사"
    )
    
    dialogue_phrase_ko = models.TextField(
        blank=True,
        null=True,
        verbose_name="한글 대사"
    )
    
    dialogue_phrase_ja = models.TextField(
        blank=True,
        null=True,
        verbose_name="일본어 대사"
    )
    
    dialogue_phrase_zh = models.TextField(
        blank=True,
        null=True,
        verbose_name="중국어 대사"
    )
    
    dialogue_start_time = models.CharField(max_length=20, verbose_name="시작 시간")
    dialogue_end_time = models.CharField(max_length=20, blank=True, verbose_name="종료 시간")
    duration_seconds = models.PositiveIntegerField(null=True, blank=True, verbose_name="길이(초)")
    
    video_url = SecureURLField(max_length=600, verbose_name="비디오 URL")
    
    video_file = models.FileField(
        upload_to=get_video_upload_path,
        blank=True,
        null=True,
        max_length=500,
        verbose_name="비디오 파일"
    )
    
    video_file_path = models.CharField(max_length=600, blank=True, verbose_name="비디오 파일 경로")
    file_size_bytes = models.PositiveBigIntegerField(null=True, blank=True, verbose_name="파일 크기(바이트)")
    
    video_quality = models.CharField(
        max_length=20,
        choices=[
            ('720p', '720p HD'),
            ('480p', '480p SD'),
            ('360p', '360p'),
            ('240p', '240p'),
            ('unknown', '알 수 없음')
        ],
        default='unknown',
        verbose_name="비디오 품질"
    )
    
    translation_method = models.CharField(
        max_length=20,
        choices=[
            ('manual', '수동 번역'),
            ('api_auto', 'API 자동번역'),
            ('ai_improved', 'AI 개선번역'),
            ('user_submitted', '사용자 제공'),
            ('unknown', '알 수 없음')
        ],
        default='unknown',
        verbose_name="번역 방식"
    )
    
    translation_quality = models.CharField(
        max_length=20,
        choices=[
            ('excellent', '우수'),
            ('good', '양호'),
            ('fair', '보통'),
            ('poor', '미흡'),
            ('needs_review', '검토 필요')
        ],
        default='fair',
        verbose_name="번역 품질"
    )
    
    play_count = models.PositiveIntegerField(default=0, verbose_name="재생 횟수")
    like_count = models.PositiveIntegerField(default=0, verbose_name="좋아요 수")
    
    search_vector = models.TextField(
        blank=True,
        verbose_name="검색 벡터",
        help_text="전문 검색을 위한 정규화된 텍스트"
    )
    
    # 매니저
    objects = DialogueManager()
    active = ActiveManager()

    class Meta:
        db_table = 'dialogue_table'
        verbose_name = "영화 대사"
        verbose_name_plural = "영화 대사들"
        indexes = [
            models.Index(fields=['dialogue_phrase']),
            models.Index(fields=['dialogue_phrase_ko']),
            models.Index(fields=['video_url']),
            models.Index(fields=['dialogue_start_time']),
            models.Index(fields=['translation_method']),
            models.Index(fields=['translation_quality']),
            models.Index(fields=['-play_count']),
            models.Index(fields=['search_vector']),
            models.Index(fields=['movie', 'dialogue_start_time']),
            models.Index(fields=['movie', '-created_at']),
            models.Index(fields=['is_active', 'translation_quality']),
        ]
        constraints = [
            models.CheckConstraint(check=models.Q(play_count__gte=0), name='positive_play_count'),
            models.CheckConstraint(check=models.Q(like_count__gte=0), name='positive_dialogue_like_count'),
            models.CheckConstraint(check=models.Q(duration_seconds__gte=0), name='positive_duration'),
        ]

    def __str__(self):
        return f"{self.movie.movie_title} - {self.dialogue_phrase[:50]}..."
    
    def clean(self):
        super().clean()
        if self.dialogue_phrase:
            self.dialogue_phrase = self.dialogue_phrase.strip()
        if self.dialogue_phrase_ko:
            self.dialogue_phrase_ko = self.dialogue_phrase_ko.strip()
    
    def save(self, *args, **kwargs):
        """저장 시 추가 처리"""
        self.update_search_vector()
        
        if self.video_file and not self.file_size_bytes:
            try:
                self.file_size_bytes = self.video_file.size
            except:
                pass
        
        if not kwargs.get('skip_translation', False):
            if self.dialogue_phrase and not self.dialogue_phrase_ko and self.translation_method == 'unknown':
                self.auto_translate_korean()
        
        super().save(*args, **kwargs)
    
    def update_search_vector(self):
        """검색 벡터 업데이트"""
        import re
        
        texts = [self.dialogue_phrase]
        if self.dialogue_phrase_ko:
            texts.append(self.dialogue_phrase_ko)
        
        normalized_texts = []
        for text in texts:
            normalized = re.sub(r'[^\w\s]', ' ', text.lower())
            normalized = re.sub(r'\s+', ' ', normalized).strip()
            normalized_texts.append(normalized)
        
        self.search_vector = ' '.join(normalized_texts)
    
    def auto_translate_korean(self):
        """자동 한글 번역"""
        if not self.dialogue_phrase:
            return
        
        try:
            from phrase.application.translate import LibreTranslator
            translator = LibreTranslator()
            
            korean_text = translator.translate_to_korean(self.dialogue_phrase)
            if korean_text and korean_text != self.dialogue_phrase:
                self.dialogue_phrase_ko = korean_text
                self.translation_method = 'api_auto'
                logger.info(f"자동 번역 완료: {self.dialogue_phrase[:30]}...")
        except Exception as e:
            logger.error(f"자동 번역 실패: {e}")
    
    def get_duration_display(self):
        """길이 표시용 문자열"""
        if self.duration_seconds:
            minutes = self.duration_seconds // 60
            seconds = self.duration_seconds % 60
            return f"{minutes:02d}:{seconds:02d}"
        return "알 수 없음"

# ===== 사용자 활동 및 분석 모델 =====

class UserSearchQuery(BaseModel):
    """사용자 검색 쿼리 기록"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, verbose_name="사용자")
    session_key = models.CharField(max_length=40, db_index=True, verbose_name="세션 키")
    original_query = OptimizedCharField(max_length=500, db_index=True, verbose_name="원본 검색어")
    translated_query = OptimizedCharField(max_length=500, blank=True, null=True, verbose_name="번역된 검색어")
    search_count = models.PositiveIntegerField(default=1, verbose_name="검색 횟수")
    result_count = models.PositiveIntegerField(default=0, verbose_name="결과 수")
    has_results = models.BooleanField(default=False, verbose_name="결과 있음")
    response_time_ms = models.PositiveIntegerField(null=True, blank=True, verbose_name="응답 시간(ms)")
    ip_address = models.GenericIPAddressField(verbose_name="IP 주소")
    user_agent = models.TextField(blank=True, verbose_name="사용자 에이전트")
    
    objects = UserSearchQueryManager()
    active = ActiveManager()
    
    class Meta:
        indexes = [
            models.Index(fields=['original_query']),
            models.Index(fields=['session_key', '-created_at']),
            models.Index(fields=['-search_count']),
            models.Index(fields=['has_results', '-created_at']),
        ]

class UserSearchResult(BaseModel):
    """사용자 검색 결과 연결"""
    search_query = models.ForeignKey(UserSearchQuery, related_name='results', on_delete=models.CASCADE)
    dialogue = models.ForeignKey(DialogueTable, related_name='search_results', on_delete=models.CASCADE)
    relevance_score = models.FloatField(default=1.0, verbose_name="관련성 점수")
    click_position = models.PositiveIntegerField(verbose_name="클릭 위치")
    
    objects = UserSearchResultManager()
    active = ActiveManager()
    
    class Meta:
        unique_together = ['search_query', 'dialogue']
        indexes = [
            models.Index(fields=['-relevance_score']),
            models.Index(fields=['click_position']),
        ]

# ===== 캐시 무효화 모델 =====

class CacheInvalidation(models.Model):
    """캐시 무효화 관리"""
    cache_key = models.CharField(max_length=250, unique=True)
    model_name = models.CharField(max_length=100)
    instance_id = models.PositiveIntegerField()
    action = models.CharField(
        max_length=20,
        choices=[('create', '생성'), ('update', '수정'), ('delete', '삭제')]
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    objects = CacheInvalidationManager()
    
    class Meta:
        indexes = [
            models.Index(fields=['model_name', 'instance_id']),
            models.Index(fields=['-created_at']),
        ]

# ===== 신호 처리 =====

@receiver(post_save, sender=RequestTable)
def invalidate_request_cache(sender, instance, **kwargs):
    """요청 테이블 변경 시 관련 캐시 무효화"""
    cache_keys = [
        f"search_result_{hash(instance.request_phrase)}",
        f"search_results_{hash(f'{instance.request_phrase}_{instance.request_korean}')}",
        'request_statistics',
    ]
    
    for key in cache_keys:
        cache.delete(key)
    
    logger.info(f"캐시 무효화: {instance.request_phrase}")

@receiver(post_save, sender=DialogueTable)
def invalidate_dialogue_cache(sender, instance, **kwargs):
    """대사 테이블 변경 시 관련 캐시 무효화"""
    cache_keys = [
        f"movie_dialogues_{instance.movie.id}",
        f"dialogue_translation_{hash(instance.dialogue_phrase)}",
        'dialogue_statistics',
    ]
    
    for key in cache_keys:
        cache.delete(key)

@receiver(post_save, sender=MovieTable)
def invalidate_movie_cache(sender, instance, **kwargs):
    """영화 테이블 변경 시 관련 캐시 무효화"""
    cache_keys = [
        'movie_statistics',
        f"movie_{instance.id}",
    ]
    
    for key in cache_keys:
        cache.delete(key)

@receiver(post_delete, sender=MovieTable)
def cleanup_movie_files(sender, instance, **kwargs):
    """영화 삭제 시 관련 파일 정리"""
    if instance.poster_image:
        try:
            if os.path.isfile(instance.poster_image.path):
                os.remove(instance.poster_image.path)
        except Exception as e:
            logger.error(f"포스터 파일 삭제 실패: {e}")

@receiver(post_delete, sender=DialogueTable)
def cleanup_dialogue_files(sender, instance, **kwargs):
    """대사 삭제 시 관련 파일 정리"""
    if instance.video_file:
        try:
            if os.path.isfile(instance.video_file.path):
                os.remove(instance.video_file.path)
        except Exception as e:
            logger.error(f"비디오 파일 삭제 실패: {e}")

# ===== 기존 호환성을 위한 별칭 =====
Movie = MovieTable
MovieQuote = DialogueTable

# ===== 유틸리티 함수들 =====

def get_model_statistics():
    """모든 모델의 통계를 한 번에 조회"""
    from .managers import get_all_statistics
    return get_all_statistics()

def cleanup_old_data(days=30):
    """오래된 데이터 정리"""
    cutoff_date = timezone.now() - timezone.timedelta(days=days)
    
    old_searches = UserSearchQuery.objects.filter(created_at__lt=cutoff_date, search_count=1)
    deleted_searches = old_searches.delete()[0]
    
    deleted_cache = CacheInvalidation.objects.filter(created_at__lt=cutoff_date).delete()[0]
    
    logger.info(f"오래된 데이터 정리 완료: 검색기록 {deleted_searches}개, 캐시기록 {deleted_cache}개")
    
    return {
        'searches_deleted': deleted_searches,
        'cache_records_deleted': deleted_cache
    }

# ===== 최종 설정 =====

logger.info("최적화된 모델 정의 완료 (Primary Key 충돌 해결)")