# -*- coding: utf-8 -*-
# dj/phrase/utils/search_helpers.py
"""
검색 관련 헬퍼 함수들
"""
import logging
from phrase.models import RequestTable, UserSearchQuery

logger = logging.getLogger(__name__)


def get_client_ip(request):
    """클라이언트 IP 주소 추출 - 예외 처리 강화"""
    try:
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
            print(f"🌐 DEBUG: X-Forwarded-For IP: {ip}")
        else:
            ip = request.META.get('REMOTE_ADDR')
            print(f"🌐 DEBUG: Remote Addr IP: {ip}")
        
        final_ip = ip or '0.0.0.0'
        print(f"🌐 DEBUG: 최종 IP: {final_ip}")
        return final_ip
    except Exception as e:
        print(f"❌ DEBUG: IP 추출 오류: {e}")
        return '0.0.0.0'


def record_search_query(session_key, original_query, translated_query, 
                       result_count, has_results, response_time, 
                       ip_address, user_agent):
    """검색 쿼리 기록 저장 - 예외 처리 강화"""
    try:
        search_query, created = UserSearchQuery.objects.get_or_create(
            session_key=session_key,
            original_query=original_query,
            defaults={
                'translated_query': translated_query,
                'search_count': 1,
                'result_count': result_count,
                'has_results': has_results,
                'response_time_ms': response_time,
                'ip_address': ip_address,
                'user_agent': user_agent[:1000] if user_agent else '',
            }
        )
        
        if not created:
            # 기존 검색인 경우 카운트 증가
            search_query.search_count += 1
            search_query.save(update_fields=['search_count'])
        
        logger.info(f"📊 검색기록 저장: {original_query} ({result_count}개 결과)")
        
    except Exception as e:
        logger.error(f"❌ 검색기록 저장 실패: {e}")


def increment_search_count(request_phrase, request_korean, result_count, user_ip, user_agent):
    """검색 횟수 증가"""
    try:
        request_obj, created = RequestTable.objects.get_or_create(
            request_phrase=request_phrase,
            defaults={
                'request_korean': request_korean,
                'search_count': 1,
                'result_count': result_count,
                'ip_address': user_ip,
                'user_agent': user_agent[:1000] if user_agent else '',
            }
        )
        if not created:
            request_obj.search_count += 1
            request_obj.save(update_fields=['search_count'])
        print("📊 DEBUG: 검색횟수 증가 완료")
    except Exception as e:
        print(f"⚠️ DEBUG: 검색횟수 증가 실패: {e}")


def get_input_type(user_input):
    """입력구문 분류 함수"""
    try:
        from phrase.application.translate import LibreTranslator
        translator = LibreTranslator()
        
        if translator.is_korean(user_input):
            return {
                'type': '한문구문',
                'language': 'korean',
                'input_method': 'text',
                'description': '한글구문 중 키보드로 입력된 텍스트 (웹브라우저)',
                'needs_translation': True,
                'target_language': 'english'
            }
        else:
            return {
                'type': '영문구문',
                'language': 'english', 
                'input_method': 'text',
                'description': '영어구문 중 키보드로 입력된 텍스트 (웹브라우저)',
                'needs_translation': False,
                'target_language': 'korean'
            }
    except Exception as e:
        return {
            'type': '오류',
            'error': str(e)
        }