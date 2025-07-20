# -*- coding: utf-8 -*-
# phrase/models/fields.py
"""
커스텀 필드 정의
MySQL 호환성 및 보안을 위한 커스텀 Django 필드들
"""
from django.db import models
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

class MySQLTextField(models.TextField):
    """MySQL 호환성을 위한 TextField - 인덱스 키 길이 제한"""
    def __init__(self, *args, **kwargs):
        # MySQL TEXT 필드의 인덱스 키 길이 제한 (InnoDB 기본값: 767바이트, utf8mb4: ~191자)
        self.mysql_key_length = kwargs.pop('mysql_key_length', 191)
        # TEXT 필드는 기본적으로 인덱스를 생성하지 않음
        kwargs['db_index'] = False
        super().__init__(*args, **kwargs)
    
    def db_type(self, connection):
        if connection.vendor == 'mysql':
            # MySQL에서는 TEXT 타입 사용
            return 'TEXT'
        return super().db_type(connection)
    
    def contribute_to_class(self, cls, name, **kwargs):
        super().contribute_to_class(cls, name, **kwargs)
        # TEXT 필드가 unique나 index에 포함되지 않도록 설정
        field = cls._meta.get_field(name)
        field.db_index = False
        field.unique = False

class MySQLLongTextField(models.TextField):
    """긴 텍스트를 위한 MySQL 호환 필드"""
    def __init__(self, *args, **kwargs):
        kwargs['db_index'] = False
        super().__init__(*args, **kwargs)
    
    def db_type(self, connection):
        if connection.vendor == 'mysql':
            return 'LONGTEXT'
        return super().db_type(connection)

class OptimizedCharField(models.CharField):
    """최적화된 CharField (자동 인덱싱 및 검증)"""
    def __init__(self, *args, **kwargs):
        # MySQL의 경우 utf8mb4에서 인덱스 가능한 최대 길이 고려
        if 'db_index' not in kwargs and kwargs.get('max_length', 0) <= 191:
            kwargs['db_index'] = True
        super().__init__(*args, **kwargs)

class SecureURLField(models.URLField):
    """보안이 강화된 URL 필드"""
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('validators', [])
        kwargs['validators'].append(URLValidator(schemes=['http', 'https']))
        # URL 필드는 기본적으로 200자로 제한
        if 'max_length' not in kwargs:
            kwargs['max_length'] = 500
        super().__init__(*args, **kwargs)
    
    def clean(self, value, model_instance):
        value = super().clean(value, model_instance)
        if value:
            dangerous_patterns = ['javascript:', 'data:', 'vbscript:', 'file:']
            if any(pattern in value.lower() for pattern in dangerous_patterns):
                raise ValidationError(_('안전하지 않은 URL입니다.'))
        return value