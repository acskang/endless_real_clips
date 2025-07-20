# -*- coding: utf-8 -*-
# phrase/models/user.py
"""
사용자 활동 및 분석 모델
UserSearchQuery, UserSearchResult
"""
from django.db import models
from django.contrib.auth.models import User

from .base import BaseModel
from .fields import OptimizedCharField
from .managers import ActiveManager, UserSearchQueryManager, UserSearchResultManager

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
    user_agent = models.CharField(max_length=500, blank=True, verbose_name="사용자 에이전트")
    
    objects = UserSearchQueryManager()
    active = ActiveManager()
    
    class Meta:
        db_table = 'user_search_query'
        verbose_name = "사용자 검색 쿼리"
        verbose_name_plural = "사용자 검색 쿼리들"


class UserSearchResult(BaseModel):
    """사용자 검색 결과 연결"""
    search_query = models.ForeignKey(UserSearchQuery, related_name='results', on_delete=models.CASCADE)
    # 순환 참조를 피하기 위해 문자열로 참조
    dialogue = models.ForeignKey('phrase.DialogueTable', related_name='search_results', on_delete=models.CASCADE)
    relevance_score = models.FloatField(default=1.0, verbose_name="관련성 점수")
    click_position = models.PositiveIntegerField(verbose_name="클릭 위치")
    
    objects = UserSearchResultManager()
    active = ActiveManager()
    
    class Meta:
        db_table = 'user_search_result'
        verbose_name = "사용자 검색 결과"
        verbose_name_plural = "사용자 검색 결과들"
        unique_together = ['search_query', 'dialogue']