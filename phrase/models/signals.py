# -*- coding: utf-8 -*-
# phrase/models/signals.py
"""
Django 신호 처리
모델 변경 시 캐시 무효화 및 파일 정리
"""
import os
import logging
from django.core.cache import cache
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

# 순환 임포트를 피하기 위해 함수 내부에서 임포트
logger = logging.getLogger(__name__)

@receiver(post_save, sender='phrase.RequestTable')
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

@receiver(post_save, sender='phrase.DialogueTable')
def invalidate_dialogue_cache(sender, instance, **kwargs):
    """대사 테이블 변경 시 관련 캐시 무효화"""
    cache_keys = [
        f"movie_dialogues_{instance.movie.id}",
        f"dialogue_translation_{hash(instance.dialogue_phrase)}",
        'dialogue_statistics',
    ]
    
    for key in cache_keys:
        cache.delete(key)

@receiver(post_save, sender='phrase.MovieTable')
def invalidate_movie_cache(sender, instance, **kwargs):
    """영화 테이블 변경 시 관련 캐시 무효화"""
    cache_keys = [
        'movie_statistics',
        f"movie_{instance.id}",
    ]
    
    for key in cache_keys:
        cache.delete(key)

@receiver(post_delete, sender='phrase.MovieTable')
def cleanup_movie_files(sender, instance, **kwargs):
    """영화 삭제 시 관련 파일 정리"""
    if instance.poster_image:
        try:
            if os.path.isfile(instance.poster_image.path):
                os.remove(instance.poster_image.path)
        except Exception as e:
            logger.error(f"포스터 파일 삭제 실패: {e}")

@receiver(post_delete, sender='phrase.DialogueTable')
def cleanup_dialogue_files(sender, instance, **kwargs):
    """대사 삭제 시 관련 파일 정리"""
    if instance.video_file:
        try:
            if os.path.isfile(instance.video_file.path):
                os.remove(instance.video_file.path)
        except Exception as e:
            logger.error(f"비디오 파일 삭제 실패: {e}")

# 최종 설정
logger.info("신호 처리기 등록 완료")