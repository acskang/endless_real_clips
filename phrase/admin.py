# -*- coding: utf-8 -*-
# phrase/admin.py
"""
Django Admin 설정
- 모델별 관리자 인터페이스 설정
- 검색, 필터링, 벌크 액션 기능
- 통계 및 분석 기능
"""
from django.contrib import admin
from django.db import models
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.urls import reverse
from django.http import JsonResponse
from django.core.cache import cache
from django.utils import timezone
from django.contrib.admin import SimpleListFilter
from django.contrib.admin.views.main import ChangeList
from django.db.models import Count, Avg, Sum, Q
from django.contrib import messages
from django.shortcuts import render, redirect
from django.template.response import TemplateResponse
import logging

from .models import (
    RequestTable, MovieTable, DialogueTable, 
    UserSearchQuery, UserSearchResult, CacheInvalidation
)

logger = logging.getLogger(__name__)

# ===== 커스텀 필터 클래스 =====

class TranslationQualityFilter(SimpleListFilter):
    """번역 품질 필터"""
    title = '번역 품질'
    parameter_name = 'translation_quality'

    def lookups(self, request, model_admin):
        return [
            ('excellent', '우수'),
            ('good', '양호'),
            ('fair', '보통'),
            ('poor', '미흡'),
            ('unknown', '미확인'),
        ]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(translation_quality=self.value())
        return queryset

class DateRangeFilter(SimpleListFilter):
    """날짜 범위 필터"""
    title = '생성 날짜'
    parameter_name = 'created_range'

    def lookups(self, request, model_admin):
        return [
            ('today', '오늘'),
            ('week', '이번 주'),
            ('month', '이번 달'),
            ('quarter', '이번 분기'),
            ('year', '올해'),
        ]

    def queryset(self, request, queryset):
        now = timezone.now()
        if self.value() == 'today':
            return queryset.filter(created_at__date=now.date())
        elif self.value() == 'week':
            week_ago = now - timezone.timedelta(days=7)
            return queryset.filter(created_at__gte=week_ago)
        elif self.value() == 'month':
            month_ago = now - timezone.timedelta(days=30)
            return queryset.filter(created_at__gte=month_ago)
        elif self.value() == 'quarter':
            quarter_ago = now - timezone.timedelta(days=90)
            return queryset.filter(created_at__gte=quarter_ago)
        elif self.value() == 'year':
            year_ago = now - timezone.timedelta(days=365)
            return queryset.filter(created_at__gte=year_ago)
        return queryset

class HasKoreanTranslationFilter(SimpleListFilter):
    """한글 번역 유무 필터"""
    title = '한글 번역'
    parameter_name = 'has_korean'

    def lookups(self, request, model_admin):
        return [
            ('yes', '번역 있음'),
            ('no', '번역 없음'),
        ]

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.exclude(
                models.Q(dialogue_phrase_ko__isnull=True) | 
                models.Q(dialogue_phrase_ko='')
            )
        elif self.value() == 'no':
            return queryset.filter(
                models.Q(dialogue_phrase_ko__isnull=True) | 
                models.Q(dialogue_phrase_ko='')
            )
        return queryset

# ===== 인라인 어드민 클래스 =====

class DialogueInline(admin.TabularInline):
    """영화 상세 페이지에서 대사 인라인 편집"""
    model = DialogueTable
    extra = 0
    max_num = 10
    fields = ('dialogue_phrase', 'dialogue_phrase_ko', 'dialogue_start_time', 
             'translation_quality', 'play_count', 'is_active')
    readonly_fields = ('play_count', 'created_at')
    can_delete = False
    show_change_link = True

class UserSearchResultInline(admin.TabularInline):
    """검색 쿼리 상세 페이지에서 결과 인라인 편집"""
    model = UserSearchResult
    extra = 0
    max_num = 10
    fields = ('dialogue', 'relevance_score', 'click_position')
    readonly_fields = ('created_at',)
    can_delete = False

# ===== 메인 어드민 클래스 =====

@admin.register(RequestTable)
class RequestTableAdmin(admin.ModelAdmin):
    """요청 테이블 관리"""
    list_display = [
        'request_phrase', 'request_korean', 'search_count', 
        'result_count', 'translation_quality', 'last_searched_at',
        'is_active', 'created_at'
    ]
    list_filter = [
        'is_active', TranslationQualityFilter, DateRangeFilter, 
        'search_count', 'result_count'
    ]
    search_fields = ['request_phrase', 'request_korean']
    readonly_fields = ['created_at', 'updated_at', 'last_searched_at', 'ip_address']
    ordering = ['-search_count', '-last_searched_at']
    list_per_page = 25
    list_max_show_all = 100
    
    fieldsets = [
        ('기본 정보', {
            'fields': ['request_phrase', 'request_korean', 'is_active']
        }),
        ('검색 통계', {
            'fields': ['search_count', 'result_count', 'last_searched_at']
        }),
        ('품질 관리', {
            'fields': ['translation_quality']
        }),
        ('시스템 정보', {
            'fields': ['ip_address', 'user_agent', 'metadata', 'created_at', 'updated_at'],
            'classes': ['collapse']
        })
    ]
    
    actions = ['mark_as_excellent', 'mark_as_good', 'mark_as_poor', 'activate_requests', 'deactivate_requests']
    
    def mark_as_excellent(self, request, queryset):
        """우수 품질로 마크"""
        updated = queryset.update(translation_quality='excellent')
        self.message_user(request, f'{updated}개 항목을 우수 품질로 변경했습니다.')
    mark_as_excellent.short_description = '우수 품질로 마크'
    
    def mark_as_good(self, request, queryset):
        """양호 품질로 마크"""
        updated = queryset.update(translation_quality='good')
        self.message_user(request, f'{updated}개 항목을 양호 품질로 변경했습니다.')
    mark_as_good.short_description = '양호 품질로 마크'
    
    def mark_as_poor(self, request, queryset):
        """미흡 품질로 마크"""
        updated = queryset.update(translation_quality='poor')
        self.message_user(request, f'{updated}개 항목을 미흡 품질로 변경했습니다.')
    mark_as_poor.short_description = '미흡 품질로 마크'
    
    def activate_requests(self, request, queryset):
        """요청 활성화"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated}개 항목을 활성화했습니다.')
    activate_requests.short_description = '선택된 요청 활성화'
    
    def deactivate_requests(self, request, queryset):
        """요청 비활성화"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated}개 항목을 비활성화했습니다.')
    deactivate_requests.short_description = '선택된 요청 비활성화'

@admin.register(MovieTable)
class MovieTableAdmin(admin.ModelAdmin):
    """영화 테이블 관리"""
    list_display = [
        'movie_title', 'release_year', 'director', 'production_country',
        'imdb_rating', 'data_quality', 'view_count', 'dialogue_count',
        'poster_status', 'is_active'
    ]
    list_filter = [
        'is_active', 'data_quality', 'release_year', 'production_country',
        DateRangeFilter
    ]
    search_fields = ['movie_title', 'original_title', 'director', 'genre']
    readonly_fields = ['created_at', 'updated_at', 'view_count', 'like_count']
    ordering = ['-view_count', '-created_at']
    list_per_page = 20
    
    fieldsets = [
        ('영화 정보', {
            'fields': ['movie_title', 'original_title', 'release_year', 'director', 'genre']
        }),
        ('제작 정보', {
            'fields': ['production_country', 'imdb_rating', 'imdb_url']
        }),
        ('이미지 정보', {
            'fields': ['poster_url', 'poster_image', 'poster_image_path']
        }),
        ('통계 정보', {
            'fields': ['view_count', 'like_count', 'data_quality', 'is_active']
        }),
        ('시스템 정보', {
            'fields': ['metadata', 'created_at', 'updated_at'],
            'classes': ['collapse']
        })
    ]
    
    inlines = [DialogueInline]
    actions = ['mark_as_verified', 'mark_as_pending', 'activate_movies', 'deactivate_movies']
    
    def dialogue_count(self, obj):
        """대사 개수 표시"""
        return obj.dialogues.count()
    dialogue_count.short_description = '대사 수'
    
    def poster_status(self, obj):
        """포스터 상태 표시"""
        if obj.poster_image:
            return format_html('<span style="color: green;">✓ 파일</span>')
        elif obj.poster_url:
            return format_html('<span style="color: orange;">URL</span>')
        else:
            return format_html('<span style="color: red;">✗ 없음</span>')
    poster_status.short_description = '포스터'
    
    def mark_as_verified(self, request, queryset):
        """검증됨으로 마크"""
        updated = queryset.update(data_quality='verified')
        self.message_user(request, f'{updated}개 영화를 검증됨으로 변경했습니다.')
    mark_as_verified.short_description = '검증됨으로 마크'
    
    def mark_as_pending(self, request, queryset):
        """검토중으로 마크"""
        updated = queryset.update(data_quality='pending')
        self.message_user(request, f'{updated}개 영화를 검토중으로 변경했습니다.')
    mark_as_pending.short_description = '검토중으로 마크'
    
    def activate_movies(self, request, queryset):
        """영화 활성화"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated}개 영화를 활성화했습니다.')
    activate_movies.short_description = '선택된 영화 활성화'
    
    def deactivate_movies(self, request, queryset):
        """영화 비활성화"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated}개 영화를 비활성화했습니다.')
    deactivate_movies.short_description = '선택된 영화 비활성화'

@admin.register(DialogueTable)
class DialogueTableAdmin(admin.ModelAdmin):
    """대사 테이블 관리"""
    list_display = [
        'dialogue_phrase_short', 'dialogue_phrase_ko_short', 'movie_title',
        'dialogue_start_time', 'translation_quality', 'translation_method',
        'play_count', 'video_status', 'is_active'
    ]
    list_filter = [
        'is_active', TranslationQualityFilter, 'translation_method',
        HasKoreanTranslationFilter, 'video_quality', DateRangeFilter
    ]
    search_fields = ['dialogue_phrase', 'dialogue_phrase_ko', 'movie__movie_title']
    readonly_fields = ['created_at', 'updated_at', 'play_count', 'like_count', 'file_size_bytes']
    ordering = ['-play_count', '-created_at']
    list_per_page = 20
    
    fieldsets = [
        ('대사 정보', {
            'fields': ['movie', 'dialogue_phrase', 'dialogue_phrase_ko']
        }),
        ('다국어 번역', {
            'fields': ['dialogue_phrase_ja', 'dialogue_phrase_zh'],
            'classes': ['collapse']
        }),
        ('시간 정보', {
            'fields': ['dialogue_start_time', 'dialogue_end_time', 'duration_seconds']
        }),
        ('비디오 정보', {
            'fields': ['video_url', 'video_file', 'video_file_path', 'video_quality', 'file_size_bytes']
        }),
        ('번역 관리', {
            'fields': ['translation_method', 'translation_quality']
        }),
        ('통계 정보', {
            'fields': ['play_count', 'like_count', 'is_active']
        }),
        ('검색 정보', {
            'fields': ['search_vector'],
            'classes': ['collapse']
        }),
        ('시스템 정보', {
            'fields': ['metadata', 'created_at', 'updated_at'],
            'classes': ['collapse']
        })
    ]
    
    actions = [
        'mark_translation_excellent', 'mark_translation_good', 'mark_translation_poor',
        'update_search_vectors', 'activate_dialogues', 'deactivate_dialogues'
    ]
    
    def dialogue_phrase_short(self, obj):
        """대사 축약 표시"""
        return obj.dialogue_phrase[:50] + '...' if len(obj.dialogue_phrase) > 50 else obj.dialogue_phrase
    dialogue_phrase_short.short_description = '영어 대사'
    
    def dialogue_phrase_ko_short(self, obj):
        """한글 대사 축약 표시"""
        if obj.dialogue_phrase_ko:
            return obj.dialogue_phrase_ko[:50] + '...' if len(obj.dialogue_phrase_ko) > 50 else obj.dialogue_phrase_ko
        return '(번역 없음)'
    dialogue_phrase_ko_short.short_description = '한글 대사'
    
    def movie_title(self, obj):
        """영화 제목 표시"""
        return obj.movie.movie_title
    movie_title.short_description = '영화'
    
    def video_status(self, obj):
        """비디오 상태 표시"""
        if obj.video_file:
            return format_html('<span style="color: green;">✓ 파일</span>')
        elif obj.video_url:
            return format_html('<span style="color: orange;">URL</span>')
        else:
            return format_html('<span style="color: red;">✗ 없음</span>')
    video_status.short_description = '비디오'
    
    def mark_translation_excellent(self, request, queryset):
        """번역 품질을 우수로 변경"""
        updated = queryset.update(translation_quality='excellent')
        self.message_user(request, f'{updated}개 대사의 번역 품질을 우수로 변경했습니다.')
    mark_translation_excellent.short_description = '번역 품질: 우수'
    
    def mark_translation_good(self, request, queryset):
        """번역 품질을 양호로 변경"""
        updated = queryset.update(translation_quality='good')
        self.message_user(request, f'{updated}개 대사의 번역 품질을 양호로 변경했습니다.')
    mark_translation_good.short_description = '번역 품질: 양호'
    
    def mark_translation_poor(self, request, queryset):
        """번역 품질을 미흡으로 변경"""
        updated = queryset.update(translation_quality='poor')
        self.message_user(request, f'{updated}개 대사의 번역 품질을 미흡으로 변경했습니다.')
    mark_translation_poor.short_description = '번역 품질: 미흡'
    
    def update_search_vectors(self, request, queryset):
        """검색 벡터 업데이트"""
        updated_count = 0
        for dialogue in queryset:
            dialogue.update_search_vector()
            dialogue.save(update_fields=['search_vector'])
            updated_count += 1
        
        self.message_user(request, f'{updated_count}개 대사의 검색 벡터를 업데이트했습니다.')
    update_search_vectors.short_description = '검색 벡터 업데이트'
    
    def activate_dialogues(self, request, queryset):
        """대사 활성화"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated}개 대사를 활성화했습니다.')
    activate_dialogues.short_description = '선택된 대사 활성화'
    
    def deactivate_dialogues(self, request, queryset):
        """대사 비활성화"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated}개 대사를 비활성화했습니다.')
    deactivate_dialogues.short_description = '선택된 대사 비활성화'

@admin.register(UserSearchQuery)
class UserSearchQueryAdmin(admin.ModelAdmin):
    """사용자 검색 쿼리 관리"""
    list_display = [
        'original_query', 'translated_query', 'search_count', 
        'result_count', 'has_results', 'response_time_ms',
        'user', 'created_at'
    ]
    list_filter = [
        'has_results', DateRangeFilter, 'search_count', 'result_count'
    ]
    search_fields = ['original_query', 'translated_query', 'user__username']
    readonly_fields = ['created_at', 'updated_at', 'session_key', 'ip_address']
    ordering = ['-search_count', '-created_at']
    list_per_page = 25
    
    fieldsets = [
        ('검색 정보', {
            'fields': ['original_query', 'translated_query', 'search_count']
        }),
        ('결과 정보', {
            'fields': ['result_count', 'has_results', 'response_time_ms']
        }),
        ('사용자 정보', {
            'fields': ['user', 'session_key', 'ip_address', 'user_agent']
        }),
        ('시스템 정보', {
            'fields': ['metadata', 'created_at', 'updated_at'],
            'classes': ['collapse']
        })
    ]
    
    inlines = [UserSearchResultInline]
    actions = ['mark_as_successful', 'mark_as_failed']
    
    def mark_as_successful(self, request, queryset):
        """성공으로 마크"""
        updated = queryset.update(has_results=True)
        self.message_user(request, f'{updated}개 검색을 성공으로 마크했습니다.')
    mark_as_successful.short_description = '성공으로 마크'
    
    def mark_as_failed(self, request, queryset):
        """실패로 마크"""
        updated = queryset.update(has_results=False)
        self.message_user(request, f'{updated}개 검색을 실패로 마크했습니다.')
    mark_as_failed.short_description = '실패로 마크'

@admin.register(UserSearchResult)
class UserSearchResultAdmin(admin.ModelAdmin):
    """사용자 검색 결과 관리"""
    list_display = [
        'search_query_text', 'dialogue_text', 'relevance_score', 
        'click_position', 'created_at'
    ]
    list_filter = [
        'relevance_score', 'click_position', DateRangeFilter
    ]
    search_fields = [
        'search_query__original_query', 'dialogue__dialogue_phrase',
        'dialogue__dialogue_phrase_ko'
    ]
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-relevance_score', '-created_at']
    list_per_page = 25
    
    def search_query_text(self, obj):
        """검색 쿼리 텍스트"""
        return obj.search_query.original_query
    search_query_text.short_description = '검색어'
    
    def dialogue_text(self, obj):
        """대사 텍스트"""
        return obj.dialogue.dialogue_phrase[:50] + '...' if len(obj.dialogue.dialogue_phrase) > 50 else obj.dialogue.dialogue_phrase
    dialogue_text.short_description = '대사'

@admin.register(CacheInvalidation)
class CacheInvalidationAdmin(admin.ModelAdmin):
    """캐시 무효화 관리"""
    list_display = ['cache_key', 'model_name', 'instance_id', 'action', 'created_at']
    list_filter = ['model_name', 'action', DateRangeFilter]
    search_fields = ['cache_key', 'model_name']
    readonly_fields = ['cache_key', 'model_name', 'instance_id', 'action', 'created_at']
    ordering = ['-created_at']
    list_per_page = 30
    
    def has_add_permission(self, request):
        """추가 권한 없음"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """수정 권한 없음"""
        return False
    
    actions = ['cleanup_old_records']
    
    def cleanup_old_records(self, request, queryset):
        """오래된 기록 정리"""
        cutoff = timezone.now() - timezone.timedelta(days=7)
        deleted_count = CacheInvalidation.objects.filter(created_at__lt=cutoff).delete()[0]
        self.message_user(request, f'{deleted_count}개의 오래된 캐시 기록을 정리했습니다.')
    cleanup_old_records.short_description = '오래된 캐시 기록 정리'

# ===== 어드민 사이트 커스터마이징 =====

class CustomAdminSite(admin.AdminSite):
    """커스텀 어드민 사이트"""
    site_header = "영화 대사 검색 시스템 관리"
    site_title = "Movie Phrase Admin"
    index_title = "시스템 관리"
    
    def index(self, request, extra_context=None):
        """어드민 메인 페이지에 통계 추가"""
        extra_context = extra_context or {}
        
        # 통계 정보 수집
        try:
            from .models.managers import get_all_statistics
            stats = get_all_statistics()
            extra_context['custom_stats'] = stats
        except Exception as e:
            logger.error(f"통계 수집 실패: {e}")
            extra_context['custom_stats'] = {}
        
        return super().index(request, extra_context)

# ===== 커스텀 어드민 사이트 사용 =====
# admin_site = CustomAdminSite(name='custom_admin')

# ===== 어드민 사이트 설정 =====
admin.site.site_header = "영화 대사 검색 시스템 관리"
admin.site.site_title = "Movie Phrase Admin"
admin.site.index_title = "시스템 관리"

# ===== 로깅 설정 =====
logger.info("Django Admin 설정 완료")