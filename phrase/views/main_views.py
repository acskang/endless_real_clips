# -*- coding: utf-8 -*-
# dj/phrase/views/main_views.py
"""
메인 뷰 - 핵심 검색 기능 (입력 검증 추가) - 디버그 강화
"""
import time
import logging
from django.shortcuts import render, redirect
from django.core.cache import cache
from django.http import HttpResponse
from django.db import transaction

from phrase.models import RequestTable, DialogueTable
from phrase.application.get_movie_info import get_movie_info
from phrase.application.clean_data import clean_data_v4
from phrase.application.load_to_db import load_to_db
from phrase.application.translate import LibreTranslator

from ..utils.search_helpers import get_client_ip, record_search_query, increment_search_count
from ..utils.data_processing import get_existing_results_from_db
from ..utils.template_helpers import render_search_results, build_error_context
from ..utils.input_validation import InputValidator, get_confirmation_context

logger = logging.getLogger(__name__)


def index(request):
    """메인 페이지 - 디버그 버전"""
    print("🏠 DEBUG: index 뷰 호출")
    print(f"🔍 DEBUG: 요청 메소드: {request.method}")
    print(f"📋 DEBUG: GET 파라미터: {dict(request.GET)}")
    print(f"📋 DEBUG: POST 파라미터: {dict(request.POST)}")
    
    try:
        response = render(request, 'index.html')
        print("✅ DEBUG: index 템플릿 렌더링 성공")
        return response
    except Exception as e:
        print(f"❌ DEBUG: index 템플릿 렌더링 실패: {e}")
        return HttpResponse(f"템플릿 오류: {e}", status=500)


def process_text(request):
    """
    텍스트 검색 처리 뷰 - 입력 검증 추가 (디버그 강화)
    """
    print("🚀 DEBUG: process_text 함수 시작")
    print(f"🔍 DEBUG: 요청 메소드: {request.method}")
    print(f"📍 DEBUG: 요청 URL: {request.get_full_path()}")
    
    # GET 요청 처리
    if request.method != 'POST':
        print("❌ DEBUG: GET 요청이므로 index로 리다이렉트")
        return redirect('phrase:index')

    try:
        # 시작 시간 기록
        start_time = time.time()
        print(f"⏰ DEBUG: 처리 시작 시간: {start_time}")

        # 1단계: 사용자 입력 및 세션 정보 처리
        user_input = request.POST.get('user_text', '').strip()
        skip_confirmation = request.POST.get('skip_confirmation') == 'true'
        session_key = request.session.session_key or request.session.create()
        user_ip = get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        print(f"📝 DEBUG: 사용자 입력: '{user_input}'")
        print(f"🔄 DEBUG: 확인 건너뛰기: {skip_confirmation}")
        print(f"🔑 DEBUG: 세션 키: {session_key}")
        print(f"🌐 DEBUG: 사용자 IP: {user_ip}")
        print(f"🖥️ DEBUG: User Agent: {user_agent[:50]}...")

        # 2단계: 입력 검증 및 확인 필요 여부 판단
        if not skip_confirmation:
            print("🔍 DEBUG: 입력 검증 시작...")
            
            try:
                validator = InputValidator()
                validation_result = validator.validate_input(user_input)
                
                print(f"🔍 DEBUG: 입력 검증 결과: {validation_result}")
                
                # 기본 검증 실패
                if not validation_result['is_valid']:
                    print("❌ DEBUG: 입력 검증 실패")
                    error_context = build_error_context(
                        user_input, 
                        validation_result['warning_message'],
                        validation_result['warning_type']
                    )
                    print(f"❌ DEBUG: 에러 컨텍스트 반환: {error_context}")
                    return render(request, 'index.html', error_context)
                
                # 사용자 확인 필요
                if validation_result['needs_confirmation']:
                    print("⚠️ DEBUG: 사용자 확인 필요 - 확인 모달 표시")
                    
                    try:
                        confirmation_context = get_confirmation_context(validation_result, user_input)
                        print(f"📋 DEBUG: 확인 컨텍스트 생성됨: {confirmation_context}")
                        
                        # 기본 페이지 컨텍스트와 확인 모달 컨텍스트 결합
                        context = {
                            'message': user_input,
                            'movies': [],
                            'total_results': 0,
                            'from_cache': False,
                            'source': 'confirmation_needed'
                        }
                        
                        if confirmation_context:
                            context.update(confirmation_context)
                            print(f"📋 DEBUG: 최종 컨텍스트: {list(context.keys())}")
                            print(f"📋 DEBUG: show_confirmation 값: {context.get('show_confirmation', 'NOT_SET')}")
                        else:
                            print("❌ DEBUG: confirmation_context가 None입니다!")
                        
                        print("🎭 DEBUG: 확인 모달과 함께 index.html 렌더링")
                        return render(request, 'index.html', context)
                        
                    except Exception as e:
                        print(f"❌ DEBUG: 확인 컨텍스트 생성 실패: {e}")
                        print(f"❌ DEBUG: 예외 타입: {type(e).__name__}")
                        import traceback
                        print(f"❌ DEBUG: 스택 트레이스: {traceback.format_exc()}")
                        
                        # 확인 모달 실패 시 기본 에러 처리
                        error_context = build_error_context(
                            user_input, 
                            '입력 검증 중 오류가 발생했습니다.'
                        )
                        return render(request, 'index.html', error_context)
                else:
                    print("✅ DEBUG: 입력 검증 통과 - 확인 불필요")
                    
            except Exception as e:
                print(f"❌ DEBUG: InputValidator 인스턴스 생성 또는 검증 실패: {e}")
                print(f"❌ DEBUG: 예외 타입: {type(e).__name__}")
                import traceback
                print(f"❌ DEBUG: 스택 트레이스: {traceback.format_exc()}")
                
                # 검증 실패 시 기본 검증으로 진행
                print("🔄 DEBUG: 기본 검증으로 대체")
        else:
            print("🔄 DEBUG: 확인 건너뛰기 모드 - 검증 생략")
        
        # 3단계: 기본 입력 검증 (확인 후 또는 확인 불필요한 경우)
        if not user_input:
            print("❌ DEBUG: 빈 입력으로 에러 반환")
            error_context = build_error_context('', '검색할 텍스트를 입력해주세요.')
            return render(request, 'index.html', error_context)

        if len(user_input) > 500:
            print("❌ DEBUG: 입력 길이 초과")
            error_context = build_error_context(
                user_input[:500], 
                '검색어는 500자를 초과할 수 없습니다.'
            )
            return render(request, 'index.html', error_context)

        logger.info(f"🎯 사용자 입력 (검증 완료): '{user_input}' (IP: {user_ip[:10]}...)")

        # 4단계: 번역 처리
        translation_result = _process_translation(user_input)
        
        # 5단계: DB에서 기존 결과 조회
        print("🗄️ DEBUG: DB 검색 시작...")
        
        try:
            existing_results = get_existing_results_from_db(
                translation_result['request_phrase'], 
                translation_result['request_korean']
            )
            print(f"📊 DEBUG: DB 검색 결과: {len(existing_results) if existing_results else 0}개")
        except Exception as e:
            print(f"❌ DEBUG: DB 검색 중 오류: {e}")
            existing_results = None
        
        if existing_results:
            print(f"✅ DEBUG: DB에서 발견: {len(existing_results)}개 영화")
            
            # 검색 횟수 증가
            try:
                increment_search_count(
                    translation_result['request_phrase'],
                    translation_result['request_korean'],
                    len(existing_results),
                    user_ip,
                    user_agent
                )
            except Exception as e:
                print(f"⚠️ DEBUG: 검색횟수 증가 실패: {e}")
            
            # 응답 시간 계산 및 검색 기록 저장
            response_time = int((time.time() - start_time) * 1000)
            try:
                record_search_query(
                    session_key, user_input, translation_result['translated_query'],
                    len(existing_results), True, response_time, user_ip, user_agent
                )
                print("📝 DEBUG: 검색 기록 저장 완료")
            except Exception as e:
                print(f"❌ 검색기록 저장 실패: {e}")
            
            print("🎉 DEBUG: DB 결과로 응답 반환")
            return render_search_results(
                request, user_input, translation_result['translated_query'],
                translation_result['request_phrase'], existing_results, from_cache=True
            )

        # 6단계: 외부 API 호출
        print("🌐 DEBUG: 외부 API 호출 시작 (DB에 결과 없음)")
        
        try:
            # DB 중복 확인 로직 추가
            existing_dialogues = DialogueTable.objects.filter(
                dialogue_phrase__icontains=translation_result['request_phrase']
            ).count()
            
            if existing_dialogues > 0:
                print(f"DB에 기존 데이터 존재, API 호출 건너뜀: {translation_result['request_phrase']}")
                playphrase_movies = []
            else:
                playphrase_movies = get_movie_info(translation_result['request_phrase'])
                print(f"📡 DEBUG: 외부 API 응답: {len(playphrase_movies) if playphrase_movies else 0}개")
        except Exception as e:
            print(f"DB 확인 중 오류: {e}")
            try:
                playphrase_movies = get_movie_info(translation_result['request_phrase'])
                print(f"📡 DEBUG: 외부 API 응답: {len(playphrase_movies) if playphrase_movies else 0}개")
            except Exception as api_error:
                print(f"API에서 데이터를 가져올 수 없음: {translation_result['request_phrase']}")
                playphrase_movies = None

        if not playphrase_movies:
            print("❌ DEBUG: 외부 API 결과 없음")
            
            # 실패 기록 저장
            response_time = int((time.time() - start_time) * 1000)
            try:
                record_search_query(
                    session_key, user_input, translation_result['translated_query'],
                    0, False, response_time, user_ip, user_agent
                )
                print("📝 DEBUG: 실패 기록 저장 완료")
            except Exception as e:
                print(f"❌ 검색기록 저장 실패: {e}")
            
            print("🚫 DEBUG: 에러 응답 반환")
            return render(request, 'index.html', {
                'message': user_input,
                'translated_message': translation_result['translated_query'],
                'error': f'"{user_input}"에 대한 검색 결과를 찾을 수 없습니다.',
                'movies': [],
                'total_results': 0,
                'displayed_results': 0,
                'has_more_results': False,
                'from_cache': False,
                'source': 'api_no_results'
            })

        # 7단계: 데이터 처리 및 저장
        processed_results = _process_and_save_data(
            playphrase_movies, translation_result, user_ip, user_agent
        )
        
        if not processed_results:
            print("❌ DEBUG: 최종 결과 없음")
            return render(request, 'index.html', {
                'message': user_input,
                'translated_message': translation_result['translated_query'],
                'error': '이 대사가 있는 영화를 못 찾았어요. 다른 검색어를 시도해보세요.',
                'movies': [],
                'total_results': 0,
                'displayed_results': 0,
                'has_more_results': False,
                'from_cache': False,
                'source': 'no_processed_results'
            })

        # 8단계: 결과 캐싱 및 최종 응답
        cache_key = f"processed_movies_{hash(translation_result['request_phrase'])}_{len(processed_results)}"
        try:
            cache.set(cache_key, processed_results, 600)  # 10분 캐싱
            print(f"🗄️ DEBUG: 캐시 저장 완료: {cache_key}")
        except Exception as e:
            print(f"⚠️ DEBUG: 캐시 저장 실패: {e}")
        
        response_time = int((time.time() - start_time) * 1000)
        print(f"✅ DEBUG: 처리완료: {len(processed_results)}개 결과, {response_time}ms")
        
        # 검색 기록 저장
        try:
            record_search_query(
                session_key, user_input, translation_result['translated_query'],
                len(processed_results), True, response_time, user_ip, user_agent
            )
            print("📝 DEBUG: 최종 검색 기록 저장 완료")
        except Exception as e:
            print(f"❌ 검색기록 저장 실패: {e}")

        print("🎉 DEBUG: 성공 응답 반환")
        return render_search_results(
            request, user_input, translation_result['translated_query'],
            translation_result['request_phrase'], processed_results, from_cache=False
        )
        
    except Exception as e:
        print(f"❌ DEBUG: 예상치 못한 최상위 오류: {e}")
        print(f"🔍 DEBUG: 오류 타입: {type(e).__name__}")
        import traceback
        print(f"❌ DEBUG: 전체 스택 트레이스: {traceback.format_exc()}")
        
        # 어떤 오류든 반드시 HttpResponse 반환
        try:
            error_context = {
                'error': f'검색 중 시스템 오류가 발생했습니다: {str(e)}',
                'message': user_input if 'user_input' in locals() else '',
                'movies': [],
                'total_results': 0,
                'displayed_results': 0,
                'has_more_results': False,
                'from_cache': False,
                'source': 'system_error'
            }
            return render(request, 'index.html', error_context)
        except:
            # render도 실패하면 최후의 수단
            return HttpResponse(f"시스템 오류: {str(e)}", status=500)


def _process_translation(user_input):
    """번역 처리 헬퍼 함수"""
    print("🔄 DEBUG: 번역기 초기화")
    try:
        translator = LibreTranslator()
        
        if translator.is_korean(user_input):
            print("🇰🇷 DEBUG: 한글구문 감지")
            translated_query = translator.translate_to_english(user_input)
            print(f"🔄 DEBUG: 번역 결과: '{user_input}' → '{translated_query}'")
            return {
                'original_query': user_input,
                'translated_query': translated_query,
                'request_phrase': translated_query,
                'request_korean': user_input
            }
        else:
            print("🇺🇸 DEBUG: 영어구문 감지")
            return {
                'original_query': user_input,
                'translated_query': None,
                'request_phrase': user_input,
                'request_korean': None
            }
            
    except Exception as e:
        print(f"❌ DEBUG: 번역 처리 오류: {e}")
        # 번역 실패해도 계속 진행
        return {
            'original_query': user_input,
            'translated_query': None,
            'request_phrase': user_input,
            'request_korean': None
        }


def _process_and_save_data(playphrase_movies, translation_result, user_ip, user_agent):
    """데이터 처리 및 저장 헬퍼 함수"""
    print("📊 DEBUG: 데이터 처리 및 저장...")
    
    try:
        movies = clean_data_v4(
            playphrase_movies, 
            translation_result['request_phrase'], 
            translation_result['request_korean']
        )
        print(f"🔧 DEBUG: 데이터 정리 완료: {len(movies) if movies else 0}개")
    except Exception as e:
        print(f"❌ DEBUG: 데이터 정리 실패: {e}")
        return None
    
    if not movies:
        print("❌ DEBUG: 데이터 추출 실패")
        return None

    # DB 저장
    print("💾 DEBUG: DB 저장 시작...")
    try:
        with transaction.atomic():
            print("🔄 DEBUG: 트랜잭션 시작")
            
            # 요청 테이블 저장/업데이트
            request_obj, created = RequestTable.objects.get_or_create(
                request_phrase=translation_result['request_phrase'],
                defaults={
                    'request_korean': translation_result['request_korean'],
                    'search_count': 1,
                    'result_count': len(movies),
                    'ip_address': user_ip,
                    'user_agent': user_agent[:1000] if user_agent else '',
                }
            )
            print(f"📋 DEBUG: 요청 테이블 처리: {'생성' if created else '업데이트'}")
            
            if not created:
                request_obj.search_count += 1
                request_obj.save(update_fields=['search_count'])
                print("📊 DEBUG: 검색 횟수 증가")

            # 영화 및 대사 정보 저장
            processed_movies = load_to_db(
                movies, 
                translation_result['request_phrase'], 
                translation_result['request_korean'], 
                batch_size=20
            )
            print(f"🎬 DEBUG: 영화 저장 완료: {len(processed_movies) if processed_movies else 0}개")
            
        return processed_movies
            
    except Exception as e:
        print(f"❌ DEBUG: DB 저장 실패: {e}")
        # DB 저장 실패해도 원본 데이터로 응답
        return movies