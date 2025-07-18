# -*- coding: utf-8 -*-
# dj/phrase/utils/template_helpers.py
"""
템플릿 관련 헬퍼 함수들
"""
from django.shortcuts import render
from django.http import HttpResponse


def render_search_results(request, original_query, translated_query, 
                         search_phrase, results, from_cache=False):
    """검색 결과 렌더링 - HttpResponse 반환 보장"""
    print(f"🎨 DEBUG: render_search_results 호출")
    print(f"📊 DEBUG: 결과 개수: {len(results) if results else 0}")
    print(f"🗄️ DEBUG: 캐시에서 로드: {from_cache}")
    
    try:
        total_results = len(results) if results else 0
        displayed_results = min(total_results, 5)
        
        context = {
            'message': original_query,
            'translated_message': translated_query,
            'search_used': search_phrase,
            'movies': results[:5] if results else [],  # 상위 5개만 표시
            'total_results': total_results,
            'displayed_results': displayed_results,
            'has_more_results': total_results > 5,
            'from_cache': from_cache,
            'source': 'cache' if from_cache else 'api',
        }
        
        print(f"📋 DEBUG: 컨텍스트 준비 완료: {list(context.keys())}")
        print(f"🎬 DEBUG: 영화 목록 샘플: {[m.get('title', 'No title') for m in (results[:2] if results else [])]}")
        
        response = render(request, 'index.html', context)
        print("✅ DEBUG: 템플릿 렌더링 성공")
        return response
        
    except Exception as e:
        print(f"❌ DEBUG: render_search_results 오류: {e}")
        # 렌더링 실패 시 최소한의 응답
        try:
            fallback_context = {
                'message': original_query,
                'error': f'결과 표시 중 오류: {str(e)}',
                'movies': [],
                'total_results': 0
            }
            return render(request, 'index.html', fallback_context)
        except:
            return HttpResponse(f"렌더링 오류: {str(e)}", status=500)


def build_error_context(message, error_msg, source='error'):
    """에러 컨텍스트 생성"""
    return {
        'error': error_msg,
        'message': message,
        'movies': [],
        'total_results': 0,
        'displayed_results': 0,
        'has_more_results': False,
        'from_cache': False,
        'source': source
    }


def build_success_context(original_query, translated_query, search_phrase, 
                         results, from_cache=False):
    """성공 컨텍스트 생성"""
    total_results = len(results) if results else 0
    displayed_results = min(total_results, 5)
    
    return {
        'message': original_query,
        'translated_message': translated_query,
        'search_used': search_phrase,
        'movies': results[:5] if results else [],
        'total_results': total_results,
        'displayed_results': displayed_results,
        'has_more_results': total_results > 5,
        'from_cache': from_cache,
        'source': 'cache' if from_cache else 'api',
    }


def build_translation_status_context():
    """번역 상태 컨텍스트 생성"""
    from django.db import models
    from phrase.models import DialogueTable
    
    try:
        total_dialogues = DialogueTable.objects.filter(is_active=True).count()
        with_korean = DialogueTable.objects.filter(
            is_active=True, 
            dialogue_phrase_ko__isnull=False
        ).exclude(dialogue_phrase_ko='').count()
        
        without_korean = total_dialogues - with_korean
        translation_rate = round((with_korean / total_dialogues) * 100, 1) if total_dialogues > 0 else 0
        
        dialogue_stats = {
            'total_dialogues': total_dialogues,
            'with_korean': with_korean,
            'without_korean': without_korean,
            'translation_rate': translation_rate,
        }
        
        # 최근 번역된 대사들
        recent_translated = DialogueTable.objects.filter(
            is_active=True,
            dialogue_phrase_ko__isnull=False
        ).exclude(dialogue_phrase_ko='').order_by('-updated_at')[:10]
        
        # 번역이 필요한 대사들
        needs_translation = DialogueTable.objects.filter(
            is_active=True
        ).filter(
            models.Q(dialogue_phrase_ko__isnull=True) | models.Q(dialogue_phrase_ko='')
        )[:10]
        
        return {
            'stats': dialogue_stats,
            'recent_translated': recent_translated,
            'needs_translation': needs_translation,
        }
        
    except Exception as e:
        return {
            'error': f'번역 상태 조회 오류: {str(e)}',
            'stats': {},
            'recent_translated': [],
            'needs_translation': []
        }