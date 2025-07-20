# -*- coding: utf-8 -*-
# dj/phrase/utils/get_movie_info.py
"""
playphrase.me API 영화 정보 가져오기 모듈 - 최적화된 모델 활용
- 새로운 모델과 매니저를 활용한 중복 검사
- 캐싱 시스템 통합
- 에러 처리 및 재시도 로직 강화
- 응답 데이터 검증 및 정규화
"""
import requests
import time
import logging
from django.core.cache import cache
from django.conf import settings
from django.utils import timezone
from phrase.models import RequestTable, DialogueTable
from phrase.utils.clean_data import clean_data_from_playphrase

logger = logging.getLogger(__name__)

class PlayPhraseAPIClient:
    """
    playphrase.me API 클라이언트 클래스
    - 캐싱 및 재시도 로직
    - 요청 제한 관리
    - 응답 검증
    """
    
    def __init__(self):
        self.base_url = 'https://www.playphrase.me/api/v1/phrases/search'
        self.timeout = 30
        self.max_retries = 3
        self.retry_delay = 1
        self.cache_timeout = 3600  # 1시간
        
        # API 설정
        self.cookies = {
            'ring-session': '1899c079-0a8e-44da-a1a0-e3a3562dfd53',
        }
        
        self.headers = {
            'accept': 'json',
            'accept-language': 'en-US,en;q=0.8',
            'authorization': 'Token',
            'content-type': 'json',
            'priority': 'u=1, i',
            'referer': 'https://www.playphrase.me/',
            'sec-ch-ua': '"Not)A;Brand";v="8", "Chromium";v="138", "Brave";v="138"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Linux"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'sec-gpc': '1',
            'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
            'x-csrf-token': 'cmf6ALYjeK3Xxi1Wobc1dIitdPqz+IjROylUqKHePZ+HQCkfROzIedaKmgSWlbgJogBBpd5HpkcmvFLF',
        }
    
    def search_phrase(self, text, limit=10, skip=0):
        """
        구문 검색 (캐싱 및 재시도 로직 포함)
        """
        if not text or not text.strip():
            logger.warning("검색 텍스트가 비어있습니다.")
            return None
        
        text = text.strip()
        
        # 캐시 확인
        cache_key = f"playphrase_api_{hash(text)}_{limit}_{skip}"
        cached_result = cache.get(cache_key)
        
        if cached_result:
            logger.info(f"API 응답 캐시에서 조회: {text}")
            return cached_result
        
        # DB에서 기존 데이터 확인 (새 모델 활용)
        if self._has_existing_data(text):
            logger.info(f"DB에 기존 데이터 존재, API 호출 건너뜀: {text}")
            return None  # DB 우선 사용
        
        params = {
            'q': text,
            'limit': str(limit),
            'language': 'en',
            'platform': 'desktop safari',
            'skip': str(skip),
        }
        
        # 재시도 로직
        for attempt in range(self.max_retries):
            try:
                logger.info(f"playphrase.me API 요청 (시도 {attempt + 1}/{self.max_retries}): {text}")
                
                response = requests.get(
                    self.base_url,
                    params=params,
                    cookies=self.cookies,
                    headers=self.headers,
                    timeout=self.timeout
                )
                
                if response.status_code == 200:
                    data = response.text
                    
                    # 응답 검증
                    if self._validate_response(data, text):
                        # 캐시에 저장
                        cache.set(cache_key, data, self.cache_timeout)
                        
                        # API 사용 통계 기록
                        self._record_api_usage(text, True, len(data))
                        
                        logger.info(f"API 응답 수신 성공: {len(data)} 문자")
                        return data
                    else:
                        logger.warning(f"응답 검증 실패: {text}")
                        return None
                
                elif response.status_code == 429:  # Rate limit
                    wait_time = self.retry_delay * (attempt + 1) * 2
                    logger.warning(f"API 요청 제한, {wait_time}초 대기...")
                    time.sleep(wait_time)
                    continue
                
                else:
                    logger.error(f"API 응답 오류 - 상태 코드: {response.status_code}")
                    logger.error(f"응답 내용: {response.text[:200]}...")
                    
                    if attempt < self.max_retries - 1:
                        time.sleep(self.retry_delay * (attempt + 1))
                        continue
                    
            except requests.exceptions.Timeout:
                logger.error(f"API 요청 타임아웃 (시도 {attempt + 1}): {text}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))
                    continue
                    
            except requests.exceptions.ConnectionError:
                logger.error(f"API 연결 실패 (시도 {attempt + 1}): {text}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))
                    continue
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"API 요청 중 오류 (시도 {attempt + 1}): {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))
                    continue
                    
            except Exception as e:
                logger.error(f"예상치 못한 오류: {e}")
                break
        
        # 모든 시도 실패
        self._record_api_usage(text, False, 0)
        logger.error(f"API 요청 최종 실패: {text}")
        return None
    
    def _has_existing_data(self, text):
        """
        DB에 해당 텍스트와 관련된 데이터가 이미 있는지 확인 (매니저 활용)
        """
        try:
            # 요청 테이블에서 확인
            if RequestTable.objects.filter(request_phrase=text).exists():
                return True
            
            # 대사 테이블에서 확인 (매니저 활용)
            if DialogueTable.objects.search_text(text).exists():
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"DB 확인 중 오류: {e}")
            return False
    
    def _validate_response(self, data, text):
        """
        API 응답 검증
        """
        if not data or data.strip() == '':
            logger.warning(f"빈 응답: {text}")
            return False
        
        # 에러 응답인지 확인
        if 'error' in data.lower() or 'not found' in data.lower():
            logger.warning(f"에러 응답: {data[:100]}...")
            return False
        
        # 최소 길이 확인
        if len(data) < 50:  # 너무 짧은 응답
            logger.warning(f"응답이 너무 짧음: {len(data)} 문자")
            return False
        
        # JSON 또는 특수 형식 검증
        if not ('phrases' in data or '°' in data):  # playphrase 특수 형식
            logger.warning(f"올바르지 않은 응답 형식: {data[:100]}...")
            return False
        
        return True
    
    def _record_api_usage(self, text, success, response_size):
        """
        API 사용 통계 기록
        """
        try:
            today = timezone.now().strftime('%Y-%m-%d')
            stats_key = f"api_usage_stats_{today}"
            
            daily_stats = cache.get(stats_key, {
                'total_requests': 0,
                'successful_requests': 0,
                'failed_requests': 0,
                'total_response_size': 0,
                'unique_queries': set(),
            })
            
            daily_stats['total_requests'] += 1
            daily_stats['unique_queries'].add(text[:50])  # 첫 50자만 저장
            
            if success:
                daily_stats['successful_requests'] += 1
                daily_stats['total_response_size'] += response_size
            else:
                daily_stats['failed_requests'] += 1
            
            # set은 JSON 직렬화가 안되므로 길이만 저장
            daily_stats['unique_query_count'] = len(daily_stats['unique_queries'])
            del daily_stats['unique_queries']  # 캐시 저장 전 제거
            
            cache.set(stats_key, daily_stats, 86400)  # 24시간
            
        except Exception as e:
            logger.error(f"API 통계 기록 실패: {e}")

# 전역 클라이언트 인스턴스
api_client = PlayPhraseAPIClient()

def get_movie_info(text):
    """
    playphrase.me API에서 영화 정보를 가져오는 메인 함수 (최적화)
    
    개선사항:
    - 새 모델과 연동한 중복 검사
    - 캐싱 시스템 통합
    - 에러 처리 강화
    - 성능 최적화
    """
    if not text or not text.strip():
        logger.warning("검색 텍스트가 비어있습니다.")
        return None
    
    text = text.strip()
    
    # DB 우선 확인 (새 모델 활용)
    existing_data = check_existing_database_data(text)
    if existing_data:
        logger.info(f"DB에서 기존 데이터 발견, API 호출 생략: {text}")
        return None  # views.py에서 DB 데이터 사용하도록 함
    
    # API 호출
    response_data = api_client.search_phrase(text)
    
    if not response_data:
        logger.warning(f"API에서 데이터를 가져올 수 없음: {text}")
        return None
    
    # 응답 후처리
    try:
        # 응답 데이터 정규화 및 검증
        processed_data = post_process_response(response_data, text)
        
        if processed_data:
            logger.info(f"API 응답 처리 완료: {text}")
            return processed_data
        else:
            logger.warning(f"응답 후처리 실패: {text}")
            return None
            
    except Exception as e:
        logger.error(f"응답 처리 중 오류: {e}")
        return None

def check_existing_database_data(text):
    """
    DB에서 기존 데이터 확인 (매니저 활용)
    """
    try:
        # 1. 요청 테이블에서 확인
        request_exists = RequestTable.objects.filter(
            models.Q(request_phrase__icontains=text) |
            models.Q(request_korean__icontains=text)
        ).exists()
        
        if request_exists:
            logger.info(f"요청 테이블에서 기존 데이터 발견: {text}")
            return True
        
        # 2. 대사 테이블에서 확인 (매니저 활용)
        dialogue_exists = DialogueTable.objects.search_text(text).exists()
        
        if dialogue_exists:
            logger.info(f"대사 테이블에서 기존 데이터 발견: {text}")
            return True
        
        return False
        
    except Exception as e:
        logger.error(f"DB 확인 중 오류: {e}")
        return False

def post_process_response(response_data, original_text):
    """
    API 응답 후처리 및 검증
    """
    try:
        # 기본 검증
        if not response_data or len(response_data) < 10:
            return None
        
        # 응답 데이터 크기 제한 (메모리 보호)
        max_size = 10 * 1024 * 1024  # 10MB
        if len(response_data) > max_size:
            logger.warning(f"응답 데이터가 너무 큼: {len(response_data)} bytes")
            response_data = response_data[:max_size]
        
        # 텍스트 정규화
        processed_data = response_data.strip()
        
        # 메타데이터 추가
        metadata = {
            'original_query': original_text,
            'response_size': len(processed_data),
            'processed_at': timezone.now().isoformat(),
            'api_source': 'playphrase.me',
        }
        
        # 간단한 구조 검증
        if 'phrases' in processed_data or '°' in processed_data:
            logger.info(f"응답 후처리 성공: {len(processed_data)} 문자")
            return processed_data
        else:
            logger.warning(f"응답 구조 검증 실패: {original_text}")
            return None
            
    except Exception as e:
        logger.error(f"응답 후처리 중 오류: {e}")
        return None

def get_movie_info_batch(text_list, batch_size=5):
    """
    여러 텍스트에 대한 배치 처리
    """
    if not text_list:
        return {}
    
    results = {}
    
    # DB에서 기존 데이터 배치 확인
    existing_texts = []
    new_texts = []
    
    for text in text_list:
        if check_existing_database_data(text):
            existing_texts.append(text)
        else:
            new_texts.append(text)
    
    logger.info(f"배치 처리: 기존 {len(existing_texts)}개, 신규 {len(new_texts)}개")
    
    # 신규 텍스트만 API 호출
    for i, text in enumerate(new_texts):
        try:
            result = get_movie_info(text)
            results[text] = result
            
            # 배치 간 대기 (API 제한 방지)
            if (i + 1) % batch_size == 0 and i < len(new_texts) - 1:
                time.sleep(1)
                
        except Exception as e:
            logger.error(f"배치 처리 중 오류 ({text}): {e}")
            results[text] = None
    
    return results

def get_api_statistics():
    """
    API 사용 통계 조회
    """
    today = timezone.now().strftime('%Y-%m-%d')
    stats_key = f"api_usage_stats_{today}"
    
    daily_stats = cache.get(stats_key, {
        'total_requests': 0,
        'successful_requests': 0,
        'failed_requests': 0,
        'total_response_size': 0,
        'unique_query_count': 0,
    })
    
    # 성공률 계산
    total = daily_stats.get('total_requests', 0)
    if total > 0:
        daily_stats['success_rate'] = round(
            (daily_stats.get('successful_requests', 0) / total) * 100, 1
        )
        daily_stats['avg_response_size'] = round(
            daily_stats.get('total_response_size', 0) / daily_stats.get('successful_requests', 1)
        )
    else:
        daily_stats['success_rate'] = 0
        daily_stats['avg_response_size'] = 0
    
    return daily_stats

def clear_api_cache(pattern=None):
    """
    API 캐시 정리
    """
    if pattern:
        # 특정 패턴의 캐시만 정리 (실제 구현은 캐시 백엔드에 따라 다름)
        logger.info(f"API 캐시 정리 (패턴: {pattern})")
    else:
        # 전체 API 캐시 정리
        logger.info("전체 API 캐시 정리")
    
    # Redis 사용 시 패턴 매칭 가능
    # 여기서는 기본적인 로깅만 수행

def validate_api_health():
    """
    API 상태 확인
    """
    test_query = "hello"
    
    try:
        start_time = time.time()
        result = api_client.search_phrase(test_query, limit=1)
        response_time = (time.time() - start_time) * 1000
        
        if result:
            return {
                'status': 'healthy',
                'response_time_ms': round(response_time, 2),
                'message': 'API가 정상 작동 중입니다.'
            }
        else:
            return {
                'status': 'degraded',
                'response_time_ms': round(response_time, 2),
                'message': 'API가 응답하지만 데이터가 없습니다.'
            }
            
    except Exception as e:
        return {
            'status': 'unhealthy',
            'response_time_ms': None,
            'message': f'API 상태 확인 실패: {str(e)}'
        }

# 레거시 호환성을 위한 별칭들
get_movie_info_legacy = get_movie_info

# 모듈 초기화
logger.info("get_movie_info 모듈 초기화 완료 (최적화된 모델 연동)")

# 설정 검증
if hasattr(settings, 'PLAYPHRASE_API_SETTINGS'):
    custom_settings = settings.PLAYPHRASE_API_SETTINGS
    
    if 'timeout' in custom_settings:
        api_client.timeout = custom_settings['timeout']
    if 'max_retries' in custom_settings:
        api_client.max_retries = custom_settings['max_retries']
    if 'cache_timeout' in custom_settings:
        api_client.cache_timeout = custom_settings['cache_timeout']
    
    logger.info("커스텀 API 설정 적용됨")

# Django 모델 임포트 (지연 임포트로 순환 참조 방지)
def _get_models():
    """지연 임포트로 모델 가져오기"""
    try:
        from phrase.models import RequestTable, MovieTable, DialogueTable
        return RequestTable, MovieTable, DialogueTable
    except ImportError:
        logger.warning("모델 임포트 실패 - 마이그레이션이 필요할 수 있습니다.")
        return None, None, None