# -*- coding: utf-8 -*-
# phrase/models/cache.py
"""
캐시 무효화 모델
캐시 관리를 위한 모델 정의
"""
from django.db import models
from .managers import CacheInvalidationManager

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
        db_table = 'cache_invalidation'
        verbose_name = "캐시 무효화"
        verbose_name_plural = "캐시 무효화들"
        indexes = [
            models.Index(fields=['model_name', 'instance_id']),
            models.Index(fields=['-created_at']),
        ]