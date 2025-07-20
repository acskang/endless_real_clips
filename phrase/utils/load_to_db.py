# -*- coding: utf-8 -*-
# dj/phrase/utils/load_to_db.py
"""
DB 저장 및 조회 함수 - 4개 모듈 완전 최적화 (수정됨)
- 일본어, 중국어 필드 제거 반영
- 임포트 오류 수정
- 에러 처리 강화
"""
import re
import time
import logging
from django.db import transaction, models
from django.core.files import File
from django.core.files.base import ContentFile
from django.core.cache import cache
from django.utils import timezone
from io import BytesIO
import requests

# 새로운 모델과 매니저 활용
from phrase.models import RequestTable, MovieTable, DialogueTable
from phrase.utils.get_imdb_poster_url import IMDBPosterExtractor, download_poster_image
# 임포트 오류 수정: phrase.application.translate -> phrase.utils.translate
from phrase.utils.translate import LibreTranslator

logger = logging.getLogger(__name__)

# ===== 파일명 및 유틸리티 함수들 =====

def convert_to_pep8_filename(text):
    """파일명을 PEP8 규칙에 맞게 변환 (개선된 버전)"""
    if not text:
        return "unknown_file"
    
    # 기본 정리
    text = text.lower().strip()
    
    # 특수 문자 제거 (단어 구분자는 유지)
    text = re.sub(r"[^\w\s-]", "", text)
    
    # 연속된 공백을 하나로 변환 후 언더스코어로 변경
    text = re.sub(r'\s+', '_', text)
    
    # 연속된 언더스코어 제거
    text = re.sub(r'_+', '_', text)
    
    # 앞뒤 언더스코어 제거
    filename = text.strip('_')
    
    # 길이 제한 (파일시스템 호환성)
    if len(filename) > 100:
        filename = filename[:100]
    
    return filename or "unknown_file"


def download_file_with_retry(url, file_type='image', max_retries=3, timeout=30):
    """파일 다운로드 재시도 로직 (개선된 버전)"""
    if not url:
        logger.warning(f"{file_type} URL이 없습니다")
        return None
    
    for attempt in range(max_retries):
        try:
            logger.info(f"{file_type} 다운로드 시도 {attempt + 1}/{max_retries}: {url}")
            
            response = requests.get(
                url, 
                stream=True, 
                timeout=timeout,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
            )
            response.raise_for_status()
            
            # 파일 크기 체크 (메모리 보호)
            content_length = response.headers.get('content-length')
            if content_length:
                size_mb = int(content_length) / (1024 * 1024)
                max_size = 50 if file_type == 'video' else 10  # MB
                
                if size_mb > max_size:
                    logger.warning(f"{file_type} 파일이 너무 큼: {size_mb:.1f}MB (최대 {max_size}MB)")
                    return None
            
            content = BytesIO(response.content)
            ext = 'jpg' if file_type == 'image' else 'mp4'
            
            logger.info(f"{file_type} 다운로드 성공: {len(response.content)} bytes")
            return content, ext
            
        except requests.RequestException as e:
            logger.warning(f"{file_type} 다운로드 시도 {attempt + 1} 실패: {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # 지수 백오프
            else:
                logger.error(f"{file_type} 다운로드 최종 실패: {url}")
                return None


# ===== 4개 모듈 연동 최적화 함수들 =====

def save_request_table_optimized(request_phrase, request_korean=None, 
                                ip_address=None, user_agent=None):
    """
    요청테이블 최적화 저장 (매니저 활용)
    """
    try:
        # 매니저의 get_or_create와 increment_search_count 활용
        request_obj, created = RequestTable.objects.get_or_create(
            request_phrase=request_phrase,
            defaults={
                'request_korean': request_korean,
                'search_count': 1,
                'result_count': 0,  # 임시값, 나중에 업데이트
                'ip_address': ip_address,
                'user_agent': user_agent[:1000] if user_agent else '',
            }
        )
        
        if not created:
            # 기존 요청인 경우 카운트 증가
            request_obj.search_count += 1
            request_obj.save(update_fields=['search_count'])
            
            # 한글 번역이 없고 새로운 한글이 있으면 업데이트
            if not request_obj.request_korean and request_korean:
                request_obj.request_korean = request_korean
                request_obj.save(update_fields=['request_korean'])
                logger.info(f"🔄 한글 번역 업데이트: {request_korean}")
        
        logger.info(f"✅ 요청구문 처리 완료: {request_phrase} (생성: {created})")
        return request_obj
        
    except Exception as e:
        logger.error(f"❌ 요청구문 저장 실패: {request_phrase} - {e}")
        return None


def save_movie_table_optimized(movie_data):
    """
    영화테이블 최적화 저장 (매니저 및 캐시 활용)
    """
    try:
        # 영화 정보 정규화
        movie_title = movie_data.get('movie_title', movie_data.get('name', ''))
        release_year = movie_data.get('release_year', '1004')
        director = movie_data.get('director', 'ahading')
        production_country = movie_data.get('production_country', '지구')
        
        # 매니저를 활용한 중복 검사 (unique_together 필드들)
        existing_movie = MovieTable.objects.filter(
            movie_title=movie_title,
            release_year=release_year,
            director=director
        ).first()
        
        if existing_movie:
            logger.info(f"⏩ 영화 이미 존재: {movie_title} ({release_year})")
            return existing_movie
        
        # 새 영화 생성
        movie_obj = MovieTable.objects.create(
            movie_title=movie_title,
            original_title=movie_data.get('original_title', ''),
            release_year=release_year,
            production_country=production_country,
            director=director,
            genre=movie_data.get('genre', ''),
            imdb_url=movie_data.get('source_url', movie_data.get('imdb_url', '')),
            data_quality='pending'  # 초기 품질 상태
        )
        
        # IMDB 정보 수집 (조건부)
        if movie_data.get('source_url') and not movie_obj.poster_url:
            poster_info = collect_imdb_info_smart(movie_obj, movie_data['source_url'])
            
            if poster_info:
                movie_obj.poster_url = poster_info.get('poster_url', '')
                movie_obj.data_quality = 'verified'  # IMDB 정보 있으면 검증됨
                movie_obj.save(update_fields=['poster_url', 'data_quality'])
        
        logger.info(f"✅ 새 영화 저장 완료: {movie_title}")
        return movie_obj
        
    except Exception as e:
        logger.error(f"❌ 영화정보 저장 실패: {movie_data.get('name', 'Unknown')} - {e}")
        return None


def collect_imdb_info_smart(movie_obj, imdb_url):
    """
    IMDB 정보 스마트 수집 (캐시 우선)
    """
    # 캐시 확인
    cache_key = f"imdb_info_{movie_obj.movie_title}_{movie_obj.release_year}"
    cached_info = cache.get(cache_key)
    
    if cached_info:
        logger.info(f"IMDB 정보 캐시에서 조회: {movie_obj.movie_title}")
        return cached_info
    
    try:
        extractor = IMDBPosterExtractor()
        poster_url = extractor.extract_poster_url(imdb_url)
        
        imdb_info = {}
        
        if poster_url:
            imdb_info['poster_url'] = poster_url
            
            # 포스터 다운로드 (선택적)
            filename = convert_to_pep8_filename(movie_obj.movie_title)
            poster_content = download_file_with_retry(poster_url, 'image')
            
            if poster_content:
                content, ext = poster_content
                file_name = f"{filename}.{ext}"
                
                # Django File 객체 생성
                poster_file = File(content, name=file_name)
                movie_obj.poster_image = poster_file
                movie_obj.poster_image_path = f'posters/{file_name}'
                movie_obj.save(update_fields=['poster_image', 'poster_image_path'])
                
                logger.info(f"✅ 포스터 다운로드 성공: {movie_obj.movie_title}")
        
        # 캐시에 저장 (24시간)
        if imdb_info:
            cache.set(cache_key, imdb_info, 86400)
        
        return imdb_info
        
    except Exception as e:
        logger.error(f"❌ IMDB 정보 수집 실패: {e}")
        return {}


def save_dialogue_table_optimized(movie_obj, dialogue_data, 
                                 auto_translate=True, download_video=False):
    """
    대사테이블 최적화 저장 (자동 번역 포함) - 일본어/중국어 필드 제거 반영
    """
    try:
        dialogue_phrase = dialogue_data.get('dialogue_phrase', dialogue_data.get('text', ''))
        video_url = dialogue_data.get('video_url', '')
        start_time = dialogue_data.get('dialogue_start_time', dialogue_data.get('start_time', '00:00:00'))
        
        if not dialogue_phrase or not video_url:
            logger.warning(f"필수 대사 정보 누락: {dialogue_phrase[:30]}...")
            return None
        
        # 매니저를 활용한 중복 검사
        existing_dialogue = DialogueTable.objects.filter(
            movie=movie_obj,
            dialogue_phrase=dialogue_phrase
        ).first()
        
        if existing_dialogue:
            logger.info(f"⏩ 대사 이미 존재: {dialogue_phrase[:50]}...")
            return existing_dialogue
        
        # 새 대사 생성
        dialogue_obj = DialogueTable.objects.create(
            movie=movie_obj,
            dialogue_phrase=dialogue_phrase,
            dialogue_start_time=start_time,
            dialogue_end_time=dialogue_data.get('dialogue_end_time', ''),
            video_url=video_url,
            video_quality=dialogue_data.get('video_quality', 'unknown'),
            translation_method='unknown',
            translation_quality='fair'
        )
        
        # 자동 번역 수행 (조건부)
        if auto_translate and dialogue_phrase:
            korean_translation = perform_smart_translation(dialogue_phrase)
            
            if korean_translation:
                dialogue_obj.dialogue_phrase_ko = korean_translation
                dialogue_obj.translation_method = 'api_auto'
                dialogue_obj.save(update_fields=['dialogue_phrase_ko', 'translation_method'])
                logger.info(f"✅ 자동 번역 완료: {dialogue_phrase[:30]}...")
        
        # 비디오 다운로드 (선택적)
        if download_video and video_url:
            video_content = download_file_with_retry(video_url, 'video')
            
            if video_content:
                content, ext = video_content
                filename = convert_to_pep8_filename(dialogue_phrase[:50])
                file_name = f"{filename}.{ext}"
                
                video_file = File(content, name=file_name)
                dialogue_obj.video_file = video_file
                dialogue_obj.video_file_path = f'videos/{file_name}'
                dialogue_obj.file_size_bytes = len(content.getvalue())
                dialogue_obj.save(update_fields=[
                    'video_file', 'video_file_path', 'file_size_bytes'
                ])
                
                logger.info(f"✅ 비디오 다운로드 성공: {dialogue_phrase[:30]}...")
        
        logger.info(f"✅ 새 대사 저장 완료: {dialogue_phrase[:50]}...")
        return dialogue_obj
        
    except Exception as e:
        logger.error(f"❌ 대사정보 저장 실패: {dialogue_data.get('text', 'Unknown')[:50]} - {e}")
        return None


def perform_smart_translation(text):
    """
    스마트 번역 수행 (캐시 및 품질 체크)
    """
    if not text or len(text.strip()) < 2:
        return None
    
    # 번역 캐시 확인
    cache_key = f"translation_{hash(text)}"
    cached_translation = cache.get(cache_key)
    
    if cached_translation:
        logger.debug(f"번역 캐시에서 조회: {text[:20]}...")
        return cached_translation
    
    try:
        translator = LibreTranslator()
        
        # 이미 한글인지 확인
        if translator.is_korean(text):
            logger.debug(f"이미 한글 텍스트: {text[:20]}...")
            return text
        
        # 영어 → 한글 번역
        korean_text = translator.translate_to_korean(text)
        
        if korean_text and korean_text != text:
            # 번역 품질 간단 체크
            if len(korean_text) > len(text) * 3:  # 너무 긴 번역은 의심
                logger.warning(f"번역이 의심스럽게 김: {text[:20]}... → {korean_text[:20]}...")
                return None
            
            # 캐시에 저장 (1시간)
            cache.set(cache_key, korean_text, 3600)
            return korean_text
        
        return None
        
    except Exception as e:
        logger.error(f"번역 실패: {text[:20]}... - {e}")
        return None


# ===== 메인 로드 함수 (4개 모듈 최적화) =====

def load_to_db(movies, request_phrase=None, request_korean=None, 
               batch_size=20, auto_translate=True, download_media=False):
    """
    4개 모듈 최적화 DB 저장 함수 (수정됨)
    """
    if not movies:
        logger.warning("저장할 영화 데이터가 없습니다.")
        return []
    
    logger.info(f"🚀 4개 모듈 최적화 DB 저장 시작: {len(movies)}개 영화")
    
    processed_movies = []
    total_batches = (len(movies) + batch_size - 1) // batch_size
    
    # 1단계: 요청테이블 저장 (매니저 활용)
    request_obj = None
    if request_phrase:
        request_obj = save_request_table_optimized(
            request_phrase, 
            request_korean
        )
    
    # 2단계: 배치별 영화 처리
    for batch_num in range(total_batches):
        start_idx = batch_num * batch_size
        end_idx = min(start_idx + batch_size, len(movies))
        batch = movies[start_idx:end_idx]
        
        logger.info(f"배치 {batch_num + 1}/{total_batches} 처리 중: {len(batch)}개")
        
        try:
            with transaction.atomic():
                batch_results = process_movie_batch_optimized(
                    batch, auto_translate, download_media
                )
                processed_movies.extend(batch_results)
                
                logger.info(f"배치 {batch_num + 1} 완료: {len(batch_results)}개 성공")
                
        except Exception as e:
            logger.error(f"배치 {batch_num + 1} 처리 실패: {e}")
            continue
    
    # 3단계: 요청 결과 수 업데이트
    if request_obj:
        try:
            RequestTable.objects.filter(id=request_obj.id).update(
                result_count=len(processed_movies)
            )
        except Exception as e:
            logger.warning(f"결과 수 업데이트 실패: {e}")
    
    # 4단계: 통계 및 캐시 업데이트
    update_statistics_and_cache(processed_movies)
    
    logger.info(f"✅ 4개 모듈 최적화 저장 완료: {len(processed_movies)}개 성공")
    return processed_movies


def process_movie_batch_optimized(batch, auto_translate=True, download_media=False):
    """
    영화 배치 최적화 처리 (수정됨)
    """
    batch_results = []
    
    for movie_data in batch:
        try:
            # 영화 저장 (매니저 활용)
            movie_obj = save_movie_table_optimized(movie_data)
            if not movie_obj:
                logger.warning(f"영화 저장 실패, 건너뜀: {movie_data.get('name', 'Unknown')}")
                continue
            
            # 대사 저장 (매니저 및 번역 활용)
            dialogue_obj = save_dialogue_table_optimized(
                movie_obj, 
                movie_data, 
                auto_translate, 
                download_media
            )
            if not dialogue_obj:
                logger.warning(f"대사 저장 실패, 건너뜀: {movie_data.get('text', 'Unknown')}")
                continue
            
            # views.py 호환 결과 형식 생성 (일본어/중국어 필드 제거)
            processed_movie_data = build_views_compatible_result(
                movie_obj, dialogue_obj
            )
            
            batch_results.append(processed_movie_data)
            
        except Exception as e:
            logger.error(f"영화 개별 처리 실패: {movie_data.get('name', movie_data.get('movie_title', 'Unknown'))} - {e}")
            continue
            
        # API 호출 간격 조절 (번역 API 부하 방지)
        if auto_translate:
            time.sleep(0.2)
    
    return batch_results


def build_views_compatible_result(movie_obj, dialogue_obj):
    """
    views.py와 호환되는 결과 형식 생성 (일본어/중국어 필드 제거)
    """
    return {
        'title': movie_obj.movie_title,
        'original_title': movie_obj.original_title or movie_obj.movie_title,
        'year': movie_obj.release_year,
        'country': movie_obj.production_country,
        'director': movie_obj.director,
        'genre': movie_obj.genre or '',
        'imdb_rating': float(movie_obj.imdb_rating) if movie_obj.imdb_rating else None,
        'imdb_url': movie_obj.imdb_url or '',
        'poster_url': movie_obj.poster_url or '',
        'poster_image_path': movie_obj.poster_image.url if movie_obj.poster_image else '',
        'data_quality': movie_obj.data_quality,
        'view_count': movie_obj.view_count,
        'like_count': movie_obj.like_count,
        'dialogues': [{
            'id': dialogue_obj.id,
            'text': dialogue_obj.dialogue_phrase,
            'text_ko': dialogue_obj.dialogue_phrase_ko or '',
            # 일본어, 중국어 필드 제거
            'start_time': dialogue_obj.dialogue_start_time,
            'end_time': dialogue_obj.dialogue_end_time or '',
            'duration_seconds': dialogue_obj.duration_seconds,
            'duration_display': getattr(dialogue_obj, 'get_duration_display', lambda: '알 수 없음')(),
            'video_url': dialogue_obj.video_url,
            'video_file_path': dialogue_obj.video_file.url if dialogue_obj.video_file else '',
            'video_quality': dialogue_obj.video_quality,
            'file_size_bytes': dialogue_obj.file_size_bytes,
            'translation_method': dialogue_obj.translation_method,
            'translation_quality': dialogue_obj.translation_quality,
            'play_count': dialogue_obj.play_count,
            'like_count': dialogue_obj.like_count,
            'created_at': dialogue_obj.created_at.isoformat(),
        }],
        'dialogue_count': 1
    }


def update_statistics_and_cache(processed_movies):
    """
    통계 및 캐시 업데이트 (managers.py 연동)
    """
    try:
        # 관련 캐시 무효화
        cache_keys = [
            'movie_statistics',
            'dialogue_statistics',
            'request_statistics'
        ]
        
        for key in cache_keys:
            cache.delete(key)
        
        logger.info(f"통계 캐시 무효화 완료: {len(processed_movies)}개 처리")
        
    except Exception as e:
        logger.error(f"통계 업데이트 실패: {e}")


# ===== DB 조회 함수 (매니저 활용) =====

def get_search_results_from_db(request_phrase, request_korean=None):
    """
    매니저를 활용한 최적화된 DB 조회
    """
    try:
        # 기본 텍스트 검색
        search_results = DialogueTable.objects.filter(
            dialogue_phrase__icontains=request_phrase
        )
        
        # 한글 검색 추가
        if request_korean:
            korean_results = DialogueTable.objects.filter(
                dialogue_phrase_ko__icontains=request_korean
            )
            search_results = search_results.union(korean_results)
        
        # 영화 정보와 함께 조회 (select_related 최적화)
        search_results = search_results.select_related('movie').distinct()
        
        if not search_results.exists():
            logger.info(f"DB 조회 결과 없음: {request_phrase}")
            return []
        
        # views.py 호환 형식으로 변환
        results = []
        for dialogue in search_results:
            result_data = build_views_compatible_result(dialogue.movie, dialogue)
            results.append(result_data)
        
        logger.info(f"✅ DB 조회 완료: {len(results)}개 결과")
        return results
        
    except Exception as e:
        logger.error(f"❌ DB 조회 실패: {e}")
        return []


# ===== 레거시 호환성 함수들 =====

def load_to_db_legacy(movies, request_phrase=None, request_korean=None):
    """기존 load_to_db 호출과의 호환성 유지"""
    return load_to_db(
        movies, 
        request_phrase, 
        request_korean, 
        batch_size=20,
        auto_translate=True,
        download_media=False
    )


# ===== 모듈 메타데이터 =====
__version__ = "4.1.0"
__compatibility__ = ["models.py", "managers.py", "views.py", "get_movie_info.py"]
__features__ = [
    "일본어/중국어 필드 제거 완료",
    "임포트 오류 수정",
    "4개 모듈 완전 연동",
    "배치 처리 최적화",
    "자동 번역 시스템",
    "에러 복구 강화"
]

# 모듈 초기화 로깅
logger.info(f"""
=== load_to_db.py v{__version__} 초기화 완료 (수정됨) ===
🔧 일본어/중국어 필드 제거: ✅ 완료
🔗 임포트 오류 수정: ✅ phrase.utils.translate 사용
📱 models.py 연동: ✅ 새 모델 구조 완전 활용
🌐 views.py 연동: ✅ 캐시 전략 및 형식 호환  
🚀 에러 처리 강화: ✅ 안전한 배치 처리
""")