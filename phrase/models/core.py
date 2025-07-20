# -*- coding: utf-8 -*-
# phrase/models/core.py
"""
핵심 모델 정의 - MySQL 인덱스 키 길이 문제 해결
RequestTable, MovieTable, DialogueTable
"""
import os
import re
import hashlib
import logging
from django.db import models
from django.core.validators import MinLengthValidator, MaxLengthValidator
from django.core.exceptions import ValidationError

from .base import BaseModel
from .fields import MySQLTextField, MySQLLongTextField, OptimizedCharField, SecureURLField
from .managers import ActiveManager, RequestManager, MovieManager, DialogueManager
from .utils import get_poster_upload_path, get_video_upload_path

logger = logging.getLogger(__name__)

class RequestTable(BaseModel):
    """요청테이블 - MySQL 인덱스 키 길이 문제 해결"""
    # MySQL utf8mb4에서 안전한 최대 길이로 수정 (191자 = 764바이트)
    request_phrase = models.CharField(
        max_length=191,  # 500 -> 191로 수정 (MySQL utf8mb4 safe limit)
        unique=True,
        db_index=True,
        validators=[MinLengthValidator(1), MaxLengthValidator(191)],
        verbose_name="요청구문"
    )
    
    # 긴 요청문을 위한 별도 필드 추가
    request_phrase_full = MySQLTextField(
        blank=True,
        null=True,
        verbose_name="전체 요청구문",
        help_text="191자를 초과하는 긴 요청문"
    )
    
    request_korean = OptimizedCharField(
        max_length=191,  # 500 -> 191로 수정
        blank=True,
        null=True,
        validators=[MaxLengthValidator(191)],
        verbose_name="요청한글"
    )
    
    # 긴 한글 번역을 위한 별도 필드
    request_korean_full = MySQLTextField(
        blank=True,
        null=True,
        verbose_name="전체 요청한글"
    )
    
    # 검색을 위한 해시 필드 추가
    request_hash = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        editable=False,
        verbose_name="요청 해시",
        help_text="중복 체크용 해시값"
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
    user_agent = models.CharField(max_length=191, blank=True, verbose_name="사용자 에이전트")  # 500 -> 191
    
    # 매니저
    objects = RequestManager()
    active = ActiveManager()

    class Meta:
        db_table = 'request_table'
        verbose_name = "검색 요청"
        verbose_name_plural = "검색 요청들"
        constraints = [
            models.CheckConstraint(check=models.Q(search_count__gte=0), name='positive_search_count'),
            models.CheckConstraint(check=models.Q(result_count__gte=0), name='positive_result_count'),
        ]

    def __str__(self):
        phrase = self.get_full_phrase()
        korean_part = f" ({self.get_full_korean()})" if self.get_full_korean() else ""
        return f"{phrase}{korean_part} [{self.search_count}회]"
    
    def get_full_phrase(self):
        """전체 요청 구문 반환"""
        return self.request_phrase_full or self.request_phrase
    
    def get_full_korean(self):
        """전체 한글 구문 반환"""
        return self.request_korean_full or self.request_korean
    
    def generate_request_hash(self):
        """요청의 고유 해시값 생성"""
        full_phrase = self.get_full_phrase()
        return hashlib.sha256(full_phrase.encode('utf-8')).hexdigest()
    
    def clean(self):
        super().clean()
        if self.request_phrase:
            self.request_phrase = self.request_phrase.strip()
        if self.request_korean:
            self.request_korean = self.request_korean.strip()
    
    def save(self, *args, **kwargs):
        """저장 시 추가 처리"""
        # 긴 텍스트 처리
        if len(self.request_phrase or '') > 191:
            self.request_phrase_full = self.request_phrase
            self.request_phrase = self.request_phrase[:191].strip()
        
        if self.request_korean and len(self.request_korean) > 191:
            self.request_korean_full = self.request_korean
            self.request_korean = self.request_korean[:191].strip()
        
        # 해시값 생성
        if not self.request_hash:
            self.request_hash = self.generate_request_hash()
        
        super().save(*args, **kwargs)


class MovieTable(BaseModel):
    """영화테이블 - 필드 길이 최적화"""
    movie_title = OptimizedCharField(
        max_length=191,  # 300 -> 191로 수정
        validators=[MinLengthValidator(1)],
        verbose_name="영화 제목"
    )
    
    original_title = OptimizedCharField(
        max_length=191,  # 300 -> 191로 수정
        blank=True,
        verbose_name="원제목"
    )
    
    # 긴 제목을 위한 별도 필드
    movie_title_full = MySQLTextField(
        blank=True,
        null=True,
        verbose_name="전체 영화 제목"
    )
    
    original_title_full = MySQLTextField(
        blank=True,
        null=True,
        verbose_name="전체 원제목"
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
        max_length=191,  # 300 -> 191로 수정
        default='ahading',
        verbose_name="감독"
    )
    
    # 긴 감독명을 위한 별도 필드
    director_full = MySQLTextField(
        blank=True,
        null=True,
        verbose_name="전체 감독명"
    )
    
    genre = models.CharField(max_length=191, blank=True, verbose_name="장르")  # 200 -> 191
    
    imdb_rating = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        null=True,
        blank=True,
        verbose_name="IMDB 평점"
    )
    
    imdb_url = SecureURLField(
        max_length=191,  # 500 -> 191로 수정 (URL은 보통 짧음)
        blank=True,
        null=True,
        verbose_name="IMDB URL"
    )
    
    poster_url = SecureURLField(
        max_length=191,  # 500 -> 191로 수정
        blank=True,
        null=True,
        verbose_name="포스터 URL"
    )
    
    poster_image = models.ImageField(
        upload_to=get_poster_upload_path,
        blank=True,
        null=True,
        max_length=191,  # 500 -> 191로 수정
        verbose_name="포스터 이미지"
    )
    
    poster_image_path = models.CharField(
        max_length=191,  # 500 -> 191로 수정
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
        constraints = [
            models.CheckConstraint(check=models.Q(view_count__gte=0), name='positive_view_count'),
            models.CheckConstraint(check=models.Q(like_count__gte=0), name='positive_like_count'),
            models.CheckConstraint(check=models.Q(imdb_rating__gte=0) & models.Q(imdb_rating__lte=10), name='valid_imdb_rating'),
        ]
        indexes = [
            models.Index(fields=['movie_title', 'release_year'], name='movie_title_year_idx'),
            models.Index(fields=['director'], name='movie_director_idx'),
            models.Index(fields=['production_country'], name='movie_country_idx'),
            models.Index(fields=['imdb_rating'], name='movie_rating_idx'),
            models.Index(fields=['view_count'], name='movie_view_count_idx'),
        ]

    def __str__(self):
        title = self.get_full_title()
        return f"{title} ({self.release_year})"
    
    def get_full_title(self):
        """전체 제목 반환"""
        return self.movie_title_full or self.movie_title
    
    def get_full_original_title(self):
        """전체 원제목 반환"""
        return self.original_title_full or self.original_title
    
    def get_full_director(self):
        """전체 감독명 반환"""
        return self.director_full or self.director
    
    def clean(self):
        super().clean()
        if self.movie_title:
            self.movie_title = self.movie_title.strip()
        if self.original_title:
            self.original_title = self.original_title.strip()
        if self.director:
            self.director = self.director.strip()
    
    def save(self, *args, **kwargs):
        """저장 시 긴 텍스트 처리"""
        # 긴 제목 처리
        if len(self.movie_title or '') > 191:
            self.movie_title_full = self.movie_title
            self.movie_title = self.movie_title[:191].strip()
        
        if self.original_title and len(self.original_title) > 191:
            self.original_title_full = self.original_title
            self.original_title = self.original_title[:191].strip()
        
        if self.director and len(self.director) > 191:
            self.director_full = self.director
            self.director = self.director[:191].strip()
        
        super().save(*args, **kwargs)
    
    def get_display_title(self):
        """표시용 제목 반환"""
        full_title = self.get_full_title()
        full_original = self.get_full_original_title()
        
        if full_original and full_original != full_title:
            return f"{full_title} ({full_original})"
        return full_title


class DialogueTable(BaseModel):
    """대사테이블 - MySQL 호환성 완전 개선"""
    movie = models.ForeignKey(
        MovieTable,
        related_name='dialogues',
        on_delete=models.CASCADE,
        db_index=True,
        verbose_name="영화"
    )
    
    # MySQL 호환성을 위해 MySQLTextField 사용 - 인덱스 없음
    dialogue_phrase = MySQLTextField(
        blank=True,
        null=True,
        validators=[MinLengthValidator(1)],
        verbose_name="영어 대사"
    )   
    
    dialogue_phrase_ko = MySQLTextField(
        blank=True,
        null=True,
        verbose_name="한글 대사"
    )
    
    # 대사의 해시값을 저장하여 중복 체크용으로 사용
    dialogue_hash = models.CharField(
        max_length=64,
        db_index=True,
        unique=True,
        editable=False,
        null=True,
        verbose_name="대사 해시"
    )
    
    dialogue_start_time = models.CharField(max_length=20, verbose_name="시작 시간")
    dialogue_end_time = models.CharField(max_length=20, blank=True, verbose_name="종료 시간")
    duration_seconds = models.PositiveIntegerField(null=True, blank=True, verbose_name="길이(초)")
    
    video_url = SecureURLField(max_length=191, verbose_name="비디오 URL")  # 500 -> 191
    
    video_file = models.FileField(
        upload_to=get_video_upload_path,
        blank=True,
        null=True,
        max_length=191,  # 500 -> 191
        verbose_name="비디오 파일"
    )
    
    video_file_path = models.CharField(max_length=191, blank=True, verbose_name="비디오 파일 경로")  # 500 -> 191
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
    
    # MySQL 호환성을 위해 검색 벡터는 VARCHAR 사용 (더 짧게)
    search_vector = models.CharField(
        max_length=191,  # 1000 -> 191로 수정
        blank=True,
        db_index=True,
        verbose_name="검색 벡터",
        help_text="전문 검색을 위한 정규화된 텍스트"
    )
    
    # 전체 검색 벡터를 위한 별도 필드
    search_vector_full = MySQLTextField(
        blank=True,
        verbose_name="전체 검색 벡터"
    )
    
    # 매니저
    objects = DialogueManager()
    active = ActiveManager()

    class Meta:
        db_table = 'dialogue_table'
        verbose_name = "영화 대사"
        verbose_name_plural = "영화 대사들"
        constraints = [
            models.CheckConstraint(check=models.Q(play_count__gte=0), name='positive_play_count'),
            models.CheckConstraint(check=models.Q(like_count__gte=0), name='positive_dialogue_like_count'),
            models.CheckConstraint(check=models.Q(duration_seconds__gte=0), name='positive_duration'),
        ]
        indexes = [
            models.Index(fields=['movie', 'dialogue_start_time'], name='dialogue_movie_time_idx'),
            models.Index(fields=['translation_quality'], name='dialogue_quality_idx'),
            models.Index(fields=['translation_method'], name='dialogue_method_idx'),
            models.Index(fields=['play_count'], name='dialogue_play_count_idx'),
            models.Index(fields=['dialogue_hash'], name='dialogue_hash_idx'),
        ]

    def __str__(self):
        phrase = (self.dialogue_phrase or '')[:50]
        return f"{self.movie.movie_title} - {phrase}..."
    
    def clean(self):
        super().clean()
        if self.dialogue_phrase:
            self.dialogue_phrase = self.dialogue_phrase.strip()
        if self.dialogue_phrase_ko:
            self.dialogue_phrase_ko = self.dialogue_phrase_ko.strip()
    
    def generate_dialogue_hash(self):
        """대사의 고유 해시값 생성"""
        hash_string = f"{self.movie_id}:{self.dialogue_phrase}:{self.dialogue_start_time}"
        return hashlib.sha256(hash_string.encode('utf-8')).hexdigest()
    
    def save(self, *args, **kwargs):
        """저장 시 추가 처리"""
        # 해시값 생성
        if not self.dialogue_hash:
            self.dialogue_hash = self.generate_dialogue_hash()
        
        # 검색 벡터 업데이트
        self.update_search_vector()
        
        # 파일 크기 계산
        if self.video_file and not self.file_size_bytes:
            try:
                self.file_size_bytes = self.video_file.size
            except:
                pass
        
        # 자동 번역 처리
        if not kwargs.get('skip_translation', False):
            if self.dialogue_phrase and not self.dialogue_phrase_ko and self.translation_method == 'unknown':
                self.auto_translate_korean()
        
        super().save(*args, **kwargs)
    
    def update_search_vector(self):
        """검색 벡터 업데이트 - MySQL 호환성 고려"""
        texts = []
        
        # 영어 대사 처리
        if self.dialogue_phrase:
            texts.append(self.dialogue_phrase)
        
        # 한글 대사 처리
        if self.dialogue_phrase_ko:
            texts.append(self.dialogue_phrase_ko)
        
        # 텍스트 정규화
        normalized_texts = []
        for text in texts:
            # 특수문자 제거 및 소문자 변환
            normalized = re.sub(r'[^\w\s]', ' ', text.lower())
            normalized = re.sub(r'\s+', ' ', normalized).strip()
            if normalized:
                normalized_texts.append(normalized)
        
        # 전체 검색 텍스트
        full_search_text = ' '.join(normalized_texts)
        self.search_vector_full = full_search_text
        
        # VARCHAR 필드 길이 제한 고려 (191자로 제한)
        self.search_vector = full_search_text[:191]
    
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