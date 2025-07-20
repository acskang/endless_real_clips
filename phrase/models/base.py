# -*- coding: utf-8 -*-
# phrase/models/base.py
"""
기본 추상 모델 정의
모든 모델이 상속받는 기본 클래스
"""
from django.db import models
from django.utils import timezone

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