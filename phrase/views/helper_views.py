# -*- coding: utf-8 -*-
# dj/phrase/views/helper_views.py
"""
헬퍼 뷰 - 디버그, 관리자용 뷰들 (수정된 버전)
"""
import time
import logging
from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.db import transaction, models
from django.contrib.auth.decorators import user_passes_test

from phrase.models import RequestTable, MovieTable, DialogueTable, UserSearchQuery
from phrase.application.translate import LibreTranslator
from ..utils.search_helpers import get_input_type

logger = logging.getLogger(__name__)


def debug_view(request):
    """디버그 뷰"""
    try:
        if request.method == 'POST':
            user_input = request.POST.get('user_text', '').strip()
            
            if user_input:
                # 입력구문 분류
                input_info = get_input_type(user_input)
                
                # 번역 처리
                try:
                    translator = LibreTranslator()
                    if translator.is_korean(user_input):
                        translation_info = {
                            'detected_language': 'korean',
                            'translated_text': translator.translate_to_english(user_input),
                            'method': 'api_translation'
                        }
                    else:
                        translation_info = {
                            'detected_language': 'english',
                            'translated_text': translator.translate_to_korean(user_input),
                            'method': 'api_translation'
                        }
                except Exception as e:
                    translation_info = {'error': str(e)}
                
                # DB 통계 확인
                try:
                    db_stats = {
                        'total_requests': RequestTable.objects.count(),
                        'active_requests': RequestTable.objects.filter(is_active=True).count(),
                        'total_movies': MovieTable.objects.count(),
                        'total_dialogues': DialogueTable.objects.count(),
                        'with_korean': DialogueTable.objects.filter(dialogue_phrase_ko__isnull=False).exclude(dialogue_phrase_ko='').count(),
                    }
                except Exception as e:
                    db_stats = {'error': str(e)}
                
                context = {
                    'user_input': user_input,
                    'input_info': input_info,
                    'translation_info': translation_info,
                    'db_stats': db_stats,
                }
                
                return render(request, 'debug.html', context)
        
        return render(request, 'debug.html')
        
    except Exception as e:
        return HttpResponse(f"디버그 뷰 오류: {str(e)}", status=500)


def korean_translation_status(request):
    """한글 번역 상태 확인 뷰 - 완전히 새로 작성"""
    print("🔍 DEBUG: korean_translation_status 뷰 호출")
    
    try:
        # 기본 통계 계산
        print("📊 DEBUG: 기본 통계 계산 시작")
        
        try:
            total_dialogues = DialogueTable.objects.filter(is_active=True).count()
            print(f"📊 DEBUG: 전체 대사 수: {total_dialogues}")
        except Exception as e:
            print(f"❌ DEBUG: 전체 대사 수 계산 실패: {e}")
            total_dialogues = 0
        
        try:
            with_korean = DialogueTable.objects.filter(
                is_active=True, 
                dialogue_phrase_ko__isnull=False
            ).exclude(dialogue_phrase_ko='').count()
            print(f"📊 DEBUG: 한글 번역 완료: {with_korean}")
        except Exception as e:
            print(f"❌ DEBUG: 한글 번역 완료 수 계산 실패: {e}")
            with_korean = 0
        
        without_korean = total_dialogues - with_korean
        translation_rate = round((with_korean / total_dialogues) * 100, 1) if total_dialogues > 0 else 0
        
        dialogue_stats = {
            'total_dialogues': total_dialogues,
            'with_korean': with_korean,
            'without_korean': without_korean,
            'translation_rate': translation_rate,
        }
        
        print(f"📊 DEBUG: 통계 계산 완료: {dialogue_stats}")
        
        # 최근 번역된 대사들
        print("📋 DEBUG: 최근 번역된 대사 조회")
        try:
            recent_translated = DialogueTable.objects.filter(
                is_active=True,
                dialogue_phrase_ko__isnull=False
            ).exclude(dialogue_phrase_ko='').select_related('movie').order_by('-updated_at')[:10]
            
            recent_translated_list = list(recent_translated)
            print(f"📋 DEBUG: 최근 번역된 대사: {len(recent_translated_list)}개")
        except Exception as e:
            print(f"❌ DEBUG: 최근 번역된 대사 조회 실패: {e}")
            recent_translated_list = []
        
        # 번역이 필요한 대사들
        print("📋 DEBUG: 번역 필요한 대사 조회")
        try:
            needs_translation = DialogueTable.objects.filter(
                is_active=True
            ).filter(
                models.Q(dialogue_phrase_ko__isnull=True) | models.Q(dialogue_phrase_ko='')
            ).select_related('movie')[:10]
            
            needs_translation_list = list(needs_translation)
            print(f"📋 DEBUG: 번역 필요한 대사: {len(needs_translation_list)}개")
        except Exception as e:
            print(f"❌ DEBUG: 번역 필요한 대사 조회 실패: {e}")
            needs_translation_list = []
        
        # 컨텍스트 구성
        context = {
            'stats': dialogue_stats,
            'recent_translated': recent_translated_list,
            'needs_translation': needs_translation_list,
        }
        
        print(f"📋 DEBUG: 최종 컨텍스트 키: {list(context.keys())}")
        print("🎭 DEBUG: korean_translation_status.html 렌더링 시작")
        
        response = render(request, 'korean_translation_status.html', context)
        print("✅ DEBUG: 템플릿 렌더링 성공")
        return response
        
    except Exception as e:
        print(f"❌ DEBUG: korean_translation_status 뷰 전체 오류: {e}")
        print(f"❌ DEBUG: 오류 타입: {type(e).__name__}")
        import traceback
        print(f"❌ DEBUG: 스택 트레이스: {traceback.format_exc()}")
        
        # 오류 시 기본 컨텍스트로 렌더링 시도
        try:
            fallback_context = {
                'stats': {
                    'total_dialogues': 0,
                    'with_korean': 0,
                    'without_korean': 0,
                    'translation_rate': 0,
                },
                'recent_translated': [],
                'needs_translation': [],
                'error': f'번역 상태 조회 중 오류가 발생했습니다: {str(e)}'
            }
            print("🔄 DEBUG: 폴백 컨텍스트로 렌더링 시도")
            return render(request, 'korean_translation_status.html', fallback_context)
        except Exception as render_error:
            print(f"❌ DEBUG: 폴백 렌더링도 실패: {render_error}")
            return HttpResponse(f"번역 상태 뷰 오류: {str(e)}", status=500)


@user_passes_test(lambda u: u.is_staff)
def bulk_translate_dialogues(request):
    """대사 일괄 번역 뷰 (관리자용) - 수정된 버전"""
    print("🔧 DEBUG: bulk_translate_dialogues 뷰 호출")
    
    try:
        if request.method == 'POST':
            print("📝 DEBUG: POST 요청 - 일괄 번역 시작")
            
            try:
                # 번역이 필요한 대사들 조회
                dialogues_to_translate = DialogueTable.objects.filter(
                    is_active=True
                ).filter(
                    models.Q(dialogue_phrase_ko__isnull=True) | models.Q(dialogue_phrase_ko='')
                )[:100]
                
                dialogues_list = list(dialogues_to_translate)
                print(f"🔍 DEBUG: 번역 대상 대사: {len(dialogues_list)}개")
                
                if not dialogues_list:
                    return JsonResponse({
                        'success': True,
                        'updated_count': 0,
                        'message': '번역이 필요한 대사가 없습니다.'
                    })
                
                translator = LibreTranslator()
                updated_count = 0
                
                # 배치 번역 처리
                print("🔄 DEBUG: 배치 번역 시작")
                with transaction.atomic():
                    for dialogue in dialogues_list:
                        try:
                            korean_text = translator.translate_to_korean(dialogue.dialogue_phrase)
                            if korean_text and korean_text != dialogue.dialogue_phrase:
                                dialogue.dialogue_phrase_ko = korean_text
                                dialogue.translation_method = 'api_auto'
                                dialogue.save(update_fields=['dialogue_phrase_ko', 'translation_method'])
                                updated_count += 1
                                print(f"✅ DEBUG: 번역 완료: {dialogue.dialogue_phrase[:30]}...")
                        except Exception as e:
                            print(f"❌ DEBUG: 개별 번역 실패: {e}")
                            continue
                        
                        # API 호출 간격 조절
                        time.sleep(0.1)
                
                print(f"🎉 DEBUG: 일괄 번역 완료: {updated_count}개")
                return JsonResponse({
                    'success': True,
                    'updated_count': updated_count,
                    'message': f'{updated_count}개 대사가 번역되었습니다.'
                })
                
            except Exception as e:
                print(f"❌ DEBUG: 일괄 번역 처리 중 오류: {e}")
                logger.error(f"일괄 번역 오류: {e}")
                return JsonResponse({
                    'success': False,
                    'error': f'번역 중 오류가 발생했습니다: {str(e)}'
                }, status=500)
        
        # GET 요청 - 일괄 번역 페이지 표시
        print("🔍 DEBUG: GET 요청 - 일괄 번역 페이지")
        try:
            # 간단한 통계
            total_needs_translation = DialogueTable.objects.filter(
                is_active=True
            ).filter(
                models.Q(dialogue_phrase_ko__isnull=True) | models.Q(dialogue_phrase_ko='')
            ).count()
            
            context = {
                'total_needs_translation': total_needs_translation
            }
            
            return render(request, 'bulk_translate.html', context)
        except Exception as e:
            print(f"❌ DEBUG: 일괄 번역 페이지 렌더링 실패: {e}")
            return HttpResponse(f"일괄 번역 페이지 오류: {str(e)}", status=500)
        
    except Exception as e:
        print(f"❌ DEBUG: bulk_translate_dialogues 전체 오류: {e}")
        return HttpResponse(f"일괄 번역 뷰 오류: {str(e)}", status=500)