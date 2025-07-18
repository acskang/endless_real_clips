# -*- coding: utf-8 -*-
# dj/phrase/urls.py
"""
URL 설정 - 모듈화된 뷰 사용
"""
from django.urls import path
from django.views.generic import TemplateView
from .views import (
    index, 
    process_text, 
    popular_searches_api, 
    statistics_api,
    debug_view,
    korean_translation_status,
    bulk_translate_dialogues
)

app_name = 'phrase'

urlpatterns = [
    # 메인 뷰
    path('', TemplateView.as_view(template_name='landing/home_en.html'), name='home'),
    path('movie/', index, name='index'),
    path('search/', process_text, name='process_text'),
    
    # API 뷰
    path('api/popular-searches/', popular_searches_api, name='popular_searches_api'),
    path('api/statistics/', statistics_api, name='statistics_api'),
    
    # 헬퍼 뷰
    path('debug/', debug_view, name='debug_view'),
    path('translation-status/', korean_translation_status, name='korean_translation_status'),
    path('bulk-translate/', bulk_translate_dialogues, name='bulk_translate_dialogues'),
]