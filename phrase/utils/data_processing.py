# -*- coding: utf-8 -*-
# dj/phrase/utils/data_processing.py
"""
데이터 처리 관련 헬퍼 함수들
"""
import time
import logging
from django.core.cache import cache
from phrase.models import DialogueTable
from phrase.application.translate import LibreTranslator

logger = logging.getLogger(__name__)


def get_existing_results_from_db(request_phrase, request_korean=None):
    """
    DB에서 기존 검색 결과 조회 (캐시 우선) - 예외 처리 강화
    """
    try:
        # 캐시 확인
        cache_key = f"search_result_{hash(request_phrase)}"
        cached_results = cache.get(cache_key)
        
        if cached_results:
            logger.info(f"✅ 캐시에서 결과 조회: {len(cached_results)}개")
            return cached_results
        
        print("🔍 DEBUG: 캐시에 없음, DB 직접 검색")
        
        # DB에서 검색 (매니저 메서드 대신 직접 쿼리)
        search_results = DialogueTable.objects.filter(
            dialogue_phrase__icontains=request_phrase
        )
        
        # 요청한글이 있으면 추가 검색
        if request_korean:
            korean_results = DialogueTable.objects.filter(
                dialogue_phrase_ko__icontains=request_korean
            )
            # 중복 제거를 위해 union 사용
            search_results = search_results.union(korean_results)
        
        # 영화 정보와 함께 조회
        search_results = search_results.select_related('movie').distinct()
        
        if not search_results.exists():
            print("📭 DEBUG: DB에서 결과 없음")
            return None
        
        print(f"📊 DEBUG: DB에서 {search_results.count()}개 대사 발견")
        
        # 한글 번역 확인 및 보완
        try:
            search_results = ensure_korean_translations_batch(search_results)
        except Exception as e:
            print(f"⚠️ DEBUG: 번역 보완 실패: {e}")
        
        # context 형식으로 변환
        movies_context = build_movies_context_from_db(search_results)
        
        # 캐시에 저장 (10분)
        try:
            cache.set(cache_key, movies_context, 600)
            print(f"🗄️ DEBUG: 결과 캐싱 완료")
        except Exception as e:
            print(f"⚠️ DEBUG: 캐싱 실패: {e}")
        
        return movies_context
        
    except Exception as e:
        print(f"❌ DEBUG: get_existing_results_from_db 오류: {e}")
        return None


def build_movies_context_from_db(search_results):
    """
    DB 검색 결과를 index.html용 context 형식으로 변환 - 템플릿 호환성 보장
    """
    try:
        movies_dict = {}
        
        for dialogue in search_results:
            try:
                movie = dialogue.movie
                movie_key = f"{movie.movie_title}_{movie.release_year}_{movie.director}"
                
                if movie_key not in movies_dict:
                    # 새로운 영화 항목 생성 (템플릿 호환을 위해 두 가지 필드명 모두 제공)
                    movies_dict[movie_key] = {
                        # 기존 필드명 (템플릿에서 사용)
                        'title': movie.movie_title,
                        'movie_title': movie.movie_title,  # 템플릿 호환성
                        'year': movie.release_year,
                        'release_year': movie.release_year,  # 템플릿 호환성
                        'director': movie.director,
                        'country': movie.production_country,
                        'production_country': movie.production_country,  # 템플릿 호환성
                        
                        # 추가 영화 정보
                        'original_title': movie.original_title or movie.movie_title,
                        'genre': movie.genre or '',
                        'imdb_rating': float(movie.imdb_rating) if movie.imdb_rating else None,
                        'imdb_url': movie.imdb_url or '',
                        'poster_url': movie.poster_url or '',
                        'poster_image_path': movie.poster_image.url if movie.poster_image else '',
                        'data_quality': movie.data_quality,
                        'view_count': movie.view_count,
                        'like_count': movie.like_count,
                        'dialogues': []
                    }
                
                # 대사 정보 추가 (템플릿 호환을 위해 두 가지 필드명 모두 제공)
                dialogue_info = {
                    'id': dialogue.id,
                    
                    # 영어 대사 (두 가지 필드명)
                    'text': dialogue.dialogue_phrase,
                    'dialogue_phrase': dialogue.dialogue_phrase,  # 템플릿 호환성
                    
                    # 한글 번역 (두 가지 필드명)
                    'text_ko': dialogue.dialogue_phrase_ko or '',
                    'dialogue_phrase_ko': dialogue.dialogue_phrase_ko or '',  # 템플릿 호환성
                    
                    # 기타 언어
                    'text_ja': dialogue.dialogue_phrase_ja or '',
                    'text_zh': dialogue.dialogue_phrase_zh or '',
                    
                    # 시간 정보 (두 가지 필드명)
                    'start_time': dialogue.dialogue_start_time,
                    'dialogue_start_time': dialogue.dialogue_start_time,  # 템플릿 호환성
                    'end_time': dialogue.dialogue_end_time or '',
                    'duration_seconds': dialogue.duration_seconds,
                    'duration_display': getattr(dialogue, 'get_duration_display', lambda: '알 수 없음')(),
                    
                    # 비디오 정보
                    'video_url': dialogue.video_url,
                    'video_file_path': dialogue.video_file.url if dialogue.video_file else '',
                    'video_quality': dialogue.video_quality,
                    'file_size_bytes': dialogue.file_size_bytes,
                    
                    # 번역 메타데이터
                    'translation_method': dialogue.translation_method,
                    'translation_quality': dialogue.translation_quality,
                    
                    # 통계
                    'play_count': dialogue.play_count,
                    'like_count': dialogue.like_count,
                    'created_at': dialogue.created_at.isoformat() if dialogue.created_at else '',
                }
                
                movies_dict[movie_key]['dialogues'].append(dialogue_info)
                
            except Exception as e:
                print(f"⚠️ DEBUG: 대사 처리 중 오류: {e}")
                continue
        
        # 딕셔너리를 리스트로 변환 (조회수 기준 정렬)
        movies_list = list(movies_dict.values())
        movies_list.sort(key=lambda x: x.get('view_count', 0), reverse=True)
        
        # 각 영화의 대사들을 재생수 기준으로 정렬
        for movie in movies_list:
            movie['dialogues'].sort(key=lambda x: x.get('play_count', 0), reverse=True)
            # 대사 개수 추가
            movie['dialogue_count'] = len(movie['dialogues'])
        
        print(f"📋 DEBUG: DB 결과 변환 완료: {len(movies_list)}개 영화")
        logger.info(f"📋 DB 결과 변환 완료: {len(movies_list)}개 영화, 총 {len(search_results)}개 대사")
        
        return movies_list
        
    except Exception as e:
        print(f"❌ DEBUG: build_movies_context_from_db 오류: {e}")
        return []


def ensure_korean_translations_batch(dialogues):
    """대사들의 한글 번역 배치 확인 및 보완 - 예외 처리 강화"""
    try:
        translator = LibreTranslator()
        updated_dialogues = []
        
        # 한글 번역이 없는 대사들 찾기
        needs_translation = []
        
        for dialogue in dialogues:
            if not dialogue.dialogue_phrase_ko:
                needs_translation.append(dialogue)
            updated_dialogues.append(dialogue)
        
        # 배치 번역 처리 (최대 10개씩)
        if needs_translation:
            logger.info(f"🔄 배치 번역 시작: {len(needs_translation)}개")
            
            batch_size = 10
            for i in range(0, len(needs_translation), batch_size):
                batch = needs_translation[i:i + batch_size]
                
                for dialogue in batch:
                    try:
                        korean_text = translator.translate_to_korean(dialogue.dialogue_phrase)
                        if korean_text and korean_text != dialogue.dialogue_phrase:
                            dialogue.dialogue_phrase_ko = korean_text
                            dialogue.translation_method = 'api_auto'
                            dialogue.save(update_fields=['dialogue_phrase_ko', 'translation_method'])
                            logger.info(f"✅ 번역완료: {dialogue.dialogue_phrase[:30]}...")
                    except Exception as e:
                        logger.error(f"❌ 번역실패: {e}")
                    
                    # API 호출 간격 조절
                    time.sleep(0.1)
        
        return updated_dialogues
        
    except Exception as e:
        print(f"❌ DEBUG: ensure_korean_translations_batch 오류: {e}")
        return dialogues