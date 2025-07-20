# -*- coding: utf-8 -*-
# dj/phrase/application/translate.py
"""
번역 기능을 제공하는 클래스 및 함수들 - 최적화된 모델 활용
- 새로운 모델과 매니저를 활용한 성능 최적화
- 캐싱 시스템 통합
- 배치 번역 처리 개선
- 번역 품질 관리 강화
"""
import requests
import re
from urllib.parse import quote
import time
import logging
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

# 로깅 설정
logger = logging.getLogger(__name__)

class LibreTranslator:
    def __init__(self):
        # MyMemory API 사용 (더 안정적)
        self.api_url = "https://api.mymemory.translated.net/get"
        self.max_retries = 3
        self.retry_delay = 1
        
        # 캐싱 설정
        self.cache_timeout = 3600  # 1시간
        self.cache_prefix = "translation_"
    
    def is_korean(self, text):
        """한글 포함 여부 확인"""
        korean_pattern = re.compile(r'[가-힣]')
        return bool(korean_pattern.search(text))
    
    def is_english(self, text):
        """영어 포함 여부 확인"""
        english_pattern = re.compile(r'[a-zA-Z]')
        return bool(english_pattern.search(text))
    
    def translate_to_english(self, text):
        """한글 → 영어 번역 (캐싱 적용)"""
        if not self.is_korean(text):
            return text
        
        if len(text.strip()) < 2:
            return text
        
        # 캐시 확인
        cache_key = f"{self.cache_prefix}ko_en_{hash(text)}"
        cached_result = cache.get(cache_key)
        
        if cached_result:
            logger.debug(f"캐시에서 번역 조회: {text[:20]}...")
            return cached_result
        
        # 번역 수행
        translated = self._translate(text, 'ko|en')
        
        # 캐시에 저장
        if translated != text:  # 번역이 성공한 경우만
            cache.set(cache_key, translated, self.cache_timeout)
        
        return translated
    
    def translate_to_korean(self, text):
        """영어 → 한글 번역 (캐싱 적용)"""
        if not self.is_english(text):
            return text
        
        if len(text.strip()) < 2:
            return text
        
        # 캐시 확인
        cache_key = f"{self.cache_prefix}en_ko_{hash(text)}"
        cached_result = cache.get(cache_key)
        
        if cached_result:
            logger.debug(f"캐시에서 번역 조회: {text[:20]}...")
            return cached_result
        
        # 번역 수행
        translated = self._translate(text, 'en|ko')
        
        # 캐시에 저장
        if translated != text:  # 번역이 성공한 경우만
            cache.set(cache_key, translated, self.cache_timeout)
        
        return translated
    
    def _translate(self, text, langpair):
        """공통 번역 로직 (개선된 에러 처리)"""
        for attempt in range(self.max_retries):
            try:
                # URL 파라미터로 전송
                params = {
                    'q': text.strip(),
                    'langpair': langpair
                }
                
                response = requests.get(
                    self.api_url, 
                    params=params, 
                    timeout=10,
                    headers={
                        'User-Agent': 'EndlessRealClips/1.0'
                    }
                )
                
                logger.debug(f"번역 API 응답: {response.status_code} (시도 {attempt + 1}/{self.max_retries})")
                
                if response.status_code == 200:
                    result = response.json()
                    
                    if result.get('responseStatus') == 200:
                        translated_text = result['responseData']['translatedText']
                        
                        # 번역 품질 검증
                        if self._is_valid_translation(text, translated_text, langpair):
                            logger.info(f"번역 성공: '{text[:30]}...' → '{translated_text[:30]}...' ({langpair})")
                            
                            # 번역 품질 기록 (통계용)
                            self._record_translation_quality(text, translated_text, langpair, 'success')
                            
                            return translated_text
                        else:
                            logger.warning(f"번역 품질 낮음: '{text[:30]}...' → '{translated_text[:30]}...'")
                            self._record_translation_quality(text, translated_text, langpair, 'poor_quality')
                            
                    else:
                        logger.warning(f"API 응답 오류: {result.get('responseDetails', 'Unknown error')}")
                        
                elif response.status_code == 429:  # Too Many Requests
                    logger.warning(f"API 요청 한도 초과, {self.retry_delay * (attempt + 1)}초 대기")
                    time.sleep(self.retry_delay * (attempt + 1))
                    continue
                    
                else:
                    logger.error(f"HTTP 오류: {response.status_code}")
                
                # 재시도 대기
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"번역 요청 중 오류 (시도 {attempt + 1}/{self.max_retries}): {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))
                    
            except Exception as e:
                logger.error(f"번역 중 예상치 못한 오류: {e}")
                break
        
        # 모든 시도 실패 시 원본 반환
        logger.error(f"번역 최종 실패: '{text[:30]}...' ({langpair})")
        self._record_translation_quality(text, text, langpair, 'failed')
        return text
    
    def _is_valid_translation(self, original, translated, langpair):
        """번역 품질 검증 (강화)"""
        # 빈 문자열 체크
        if not translated or not translated.strip():
            return False
        
        # 원본과 동일한 경우 (번역되지 않음)
        if original.strip().lower() == translated.strip().lower():
            return False
        
        # 한글 → 영어 번역 검증
        if langpair == 'ko|en':
            # 번역 결과에 영어가 포함되어야 함
            if not self.is_english(translated):
                return False
            # 한글이 남아있으면 번역 실패
            if self.is_korean(translated):
                return False
                
        # 영어 → 한글 번역 검증  
        elif langpair == 'en|ko':
            # 번역 결과에 한글이 포함되어야 함
            if not self.is_korean(translated):
                return False
            # 영어가 많이 남아있으면 번역 실패
            english_ratio = len(re.findall(r'[a-zA-Z]', translated)) / len(translated)
            if english_ratio > 0.3:  # 30% 이상 영어가 남아있으면 실패
                return False
        
        # 길이 검증 (너무 짧거나 긴 번역 결과 제외)
        length_ratio = len(translated) / len(original)
        if length_ratio < 0.3 or length_ratio > 3.0:
            return False
        
        # 의미없는 반복 패턴 체크
        if self._has_meaningless_repetition(translated):
            return False
        
        return True
    
    def _has_meaningless_repetition(self, text):
        """의미없는 반복 패턴 감지"""
        # 같은 단어가 3번 이상 연속으로 반복되는 경우
        words = text.split()
        for i in range(len(words) - 2):
            if words[i] == words[i+1] == words[i+2]:
                return True
        return False
    
    def _record_translation_quality(self, original, translated, langpair, quality):
        """번역 품질 기록 (통계 및 개선용)"""
        try:
            quality_data = {
                'original_length': len(original),
                'translated_length': len(translated),
                'langpair': langpair,
                'quality': quality,
                'timestamp': timezone.now().isoformat()
            }
            
            # 캐시에 통계 저장 (일일 통계)
            today = timezone.now().strftime('%Y-%m-%d')
            stats_key = f"translation_stats_{today}"
            
            daily_stats = cache.get(stats_key, {
                'total': 0,
                'success': 0,
                'poor_quality': 0,
                'failed': 0,
                'ko_en': 0,
                'en_ko': 0
            })
            
            daily_stats['total'] += 1
            daily_stats[quality] += 1
            if langpair == 'ko|en':
                daily_stats['ko_en'] += 1
            else:
                daily_stats['en_ko'] += 1
            
            cache.set(stats_key, daily_stats, 86400)  # 24시간
            
        except Exception as e:
            logger.error(f"번역 품질 기록 실패: {e}")
    
    def get_translation_info(self, text):
        """텍스트 분석 및 번역 정보 반환 (개선)"""
        info = {
            'original': text,
            'language': 'unknown',
            'has_korean': self.is_korean(text),
            'has_english': self.is_english(text),
            'length': len(text),
            'word_count': len(text.split()),
            'translation_needed': False,
            'translated': None,
            'confidence': 0.0
        }
        
        if info['has_korean'] and not info['has_english']:
            info['language'] = 'korean'
            info['translation_needed'] = True
            info['translated'] = self.translate_to_english(text)
            info['translation_direction'] = 'ko→en'
            info['confidence'] = self._calculate_confidence(text, info['translated'], 'ko|en')
            
        elif info['has_english'] and not info['has_korean']:
            info['language'] = 'english'
            info['translation_needed'] = True
            info['translated'] = self.translate_to_korean(text)
            info['translation_direction'] = 'en→ko'
            info['confidence'] = self._calculate_confidence(text, info['translated'], 'en|ko')
            
        elif info['has_korean'] and info['has_english']:
            info['language'] = 'mixed'
            # 혼합 언어의 경우 번역하지 않음
            
        return info
    
    def _calculate_confidence(self, original, translated, langpair):
        """번역 신뢰도 계산"""
        if not translated or original == translated:
            return 0.0
        
        confidence = 0.5  # 기본 신뢰도
        
        # 길이 기반 신뢰도
        length_ratio = len(translated) / len(original)
        if 0.5 <= length_ratio <= 2.0:
            confidence += 0.2
        
        # 언어 검증 기반 신뢰도
        if langpair == 'ko|en' and self.is_english(translated) and not self.is_korean(translated):
            confidence += 0.2
        elif langpair == 'en|ko' and self.is_korean(translated):
            confidence += 0.2
        
        # 특수문자 비율 체크
        special_char_ratio = len(re.findall(r'[^\w\s]', translated)) / len(translated)
        if special_char_ratio < 0.3:  # 특수문자가 너무 많지 않으면
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    def get_translation_statistics(self):
        """번역 통계 조회"""
        today = timezone.now().strftime('%Y-%m-%d')
        stats_key = f"translation_stats_{today}"
        
        return cache.get(stats_key, {
            'total': 0,
            'success': 0,
            'poor_quality': 0,
            'failed': 0,
            'ko_en': 0,
            'en_ko': 0
        })

# 번역 유틸리티 함수들 (새 모델 활용)

def translate_dialogue_batch(dialogues, batch_size=20):
    """대화 목록을 배치 번역 (최적화)"""
    translator = LibreTranslator()
    translated_dialogues = []
    
    # 번역이 필요한 대사들만 필터링
    needs_translation = [d for d in dialogues if d.get('text') and not d.get('text_ko')]
    
    logger.info(f"배치 번역 시작: {len(needs_translation)}개 대사")
    
    for i in range(0, len(needs_translation), batch_size):
        batch = needs_translation[i:i + batch_size]
        
        for dialogue in batch:
            try:
                korean_text = translator.translate_to_korean(dialogue['text'])
                if korean_text and korean_text != dialogue['text']:
                    dialogue['text_ko'] = korean_text
                    dialogue['translation_method'] = 'api_auto'
                    dialogue['translation_quality'] = 'fair'
            except Exception as e:
                logger.error(f"배치 번역 실패: {e}")
                dialogue['text_ko'] = dialogue['text']  # 원본 유지
                dialogue['translation_method'] = 'failed'
                dialogue['translation_quality'] = 'poor'
            
            translated_dialogues.append(dialogue)
            
            # API 호출 간격 조절
            time.sleep(0.05)
        
        # 배치 간 대기
        if i + batch_size < len(needs_translation):
            time.sleep(0.5)
    
    # 번역이 필요없던 대사들 추가
    for dialogue in dialogues:
        if dialogue not in needs_translation:
            translated_dialogues.append(dialogue)
    
    logger.info(f"배치 번역 완료: {len(translated_dialogues)}개 처리")
    return translated_dialogues


def update_existing_dialogues_optimized():
    """기존 대사들의 한글 번역 업데이트 (최적화된 매니저 활용)"""
    from phrase.models import DialogueTable
    
    translator = LibreTranslator()
    
    # 매니저를 활용하여 번역이 필요한 대사들 조회
    dialogues_without_korean = DialogueTable.objects.needs_translation('ko')
    
    total_count = dialogues_without_korean.count()
    updated_count = 0
    failed_count = 0
    
    logger.info(f"한글 번역이 필요한 대사 {total_count}개 발견")
    
    if total_count == 0:
        return 0
    
    # 배치 처리 (트랜잭션 최적화)
    batch_size = 50
    
    for i in range(0, total_count, batch_size):
        batch_dialogues = dialogues_without_korean[i:i + batch_size]
        
        with transaction.atomic():
            for dialogue in batch_dialogues:
                try:
                    # 영어 → 한글 번역
                    korean_text = translator.translate_to_korean(dialogue.dialogue_phrase)
                    
                    if korean_text and korean_text != dialogue.dialogue_phrase:
                        # 번역 성공
                        dialogue.dialogue_phrase_ko = korean_text
                        dialogue.translation_method = 'api_auto'
                        dialogue.translation_quality = 'fair'
                    else:
                        # 번역 실패 또는 변화 없음
                        dialogue.translation_method = 'failed'
                        dialogue.translation_quality = 'poor'
                        failed_count += 1
                    
                    dialogue.save(update_fields=[
                        'dialogue_phrase_ko', 
                        'translation_method', 
                        'translation_quality'
                    ])
                    updated_count += 1
                    
                except Exception as e:
                    logger.error(f"대사 번역 실패 (ID: {dialogue.id}): {e}")
                    failed_count += 1
                    continue
                
                # API 호출 간격 조절
                time.sleep(0.1)
        
        # 배치 간 진행 상황 로그
        processed = min(i + batch_size, total_count)
        logger.info(f"진행 상황: {processed}/{total_count} ({updated_count}개 성공, {failed_count}개 실패)")
        
        # 배치 간 대기 (API 제한 방지)
        time.sleep(1)
    
    logger.info(f"일괄 번역 완료: {updated_count}개 번역됨, {failed_count}개 실패")
    
    # 통계 업데이트
    _update_translation_statistics(updated_count, failed_count)
    
    return updated_count


def translate_missing_korean_dialogues():
    """누락된 한글 번역 보완 (Django 관리 명령어용)"""
    return update_existing_dialogues_optimized()


def bulk_translate_by_movie(movie_id, force_retranslate=False):
    """특정 영화의 대사들을 일괄 번역"""
    from phrase.models import MovieTable, DialogueTable
    
    try:
        movie = MovieTable.objects.get(id=movie_id)
        
        if force_retranslate:
            # 모든 대사 재번역
            dialogues = DialogueTable.objects.by_movie(movie)
        else:
            # 번역이 없는 대사만
            dialogues = DialogueTable.objects.by_movie(movie).filter(
                dialogue_phrase_ko__isnull=True
            )
        
        translator = LibreTranslator()
        updated_count = 0
        
        logger.info(f"영화 '{movie.movie_title}' 대사 번역 시작: {dialogues.count()}개")
        
        with transaction.atomic():
            for dialogue in dialogues:
                try:
                    korean_text = translator.translate_to_korean(dialogue.dialogue_phrase)
                    
                    if korean_text and korean_text != dialogue.dialogue_phrase:
                        dialogue.dialogue_phrase_ko = korean_text
                        dialogue.translation_method = 'api_auto'
                        dialogue.translation_quality = 'fair'
                        dialogue.save(update_fields=[
                            'dialogue_phrase_ko', 
                            'translation_method', 
                            'translation_quality'
                        ])
                        updated_count += 1
                        
                except Exception as e:
                    logger.error(f"대사 번역 실패: {e}")
                    continue
                
                time.sleep(0.1)
        
        logger.info(f"영화 '{movie.movie_title}' 번역 완료: {updated_count}개")
        return updated_count
        
    except MovieTable.DoesNotExist:
        logger.error(f"영화를 찾을 수 없음: {movie_id}")
        return 0


def get_translation_quality_report():
    """번역 품질 리포트 생성 (매니저 활용)"""
    from phrase.models import DialogueTable
    
    # 매니저를 활용한 통계 수집
    stats = DialogueTable.objects.get_statistics()
    
    # 번역 방식별 품질 분석
    quality_by_method = {}
    translation_methods = ['api_auto', 'manual', 'ai_improved', 'user_submitted']
    
    for method in translation_methods:
        method_dialogues = DialogueTable.objects.by_translation_method(method)
        if method_dialogues.exists():
            quality_dist = method_dialogues.values('translation_quality').annotate(
                count=models.Count('id')
            )
            quality_by_method[method] = {
                'total': method_dialogues.count(),
                'quality_distribution': dict(quality_dist.values_list('translation_quality', 'count'))
            }
    
    # 일일 번역 통계
    translator = LibreTranslator()
    daily_stats = translator.get_translation_statistics()
    
    report = {
        'overall_stats': stats,
        'quality_by_method': quality_by_method,
        'daily_translation_stats': daily_stats,
        'recommendations': _generate_translation_recommendations(stats, quality_by_method)
    }
    
    return report


def _generate_translation_recommendations(overall_stats, quality_by_method):
    """번역 개선 권장사항 생성"""
    recommendations = []
    
    # 번역률 체크
    if overall_stats.get('translation_rate', 0) < 80:
        recommendations.append({
            'type': 'coverage',
            'message': f"번역률이 {overall_stats.get('translation_rate', 0):.1f}%입니다. 일괄 번역을 실행하세요.",
            'action': 'bulk_translate'
        })
    
    # 품질 체크
    poor_quality_ratio = 0
    if 'api_auto' in quality_by_method:
        auto_stats = quality_by_method['api_auto']
        total = auto_stats['total']
        poor_count = auto_stats['quality_distribution'].get('poor', 0)
        poor_quality_ratio = (poor_count / total) * 100 if total > 0 else 0
        
        if poor_quality_ratio > 20:
            recommendations.append({
                'type': 'quality',
                'message': f"자동 번역 품질이 낮습니다 ({poor_quality_ratio:.1f}% 미흡). 수동 검토가 필요합니다.",
                'action': 'manual_review'
            })
    
    return recommendations


def _update_translation_statistics(success_count, failed_count):
    """번역 통계 업데이트"""
    try:
        today = timezone.now().strftime('%Y-%m-%d')
        stats_key = f"bulk_translation_stats_{today}"
        
        daily_bulk_stats = cache.get(stats_key, {
            'total_processed': 0,
            'successful': 0,
            'failed': 0,
            'last_run': None
        })
        
        daily_bulk_stats['total_processed'] += success_count + failed_count
        daily_bulk_stats['successful'] += success_count
        daily_bulk_stats['failed'] += failed_count
        daily_bulk_stats['last_run'] = timezone.now().isoformat()
        
        cache.set(stats_key, daily_bulk_stats, 86400)  # 24시간
        
    except Exception as e:
        logger.error(f"번역 통계 업데이트 실패: {e}")


# Celery 태스크용 함수들 (비동기 처리)
def translate_dialogue_async(dialogue_id):
    """개별 대사 비동기 번역"""
    from phrase.models import DialogueTable
    
    try:
        dialogue = DialogueTable.objects.get(id=dialogue_id)
        
        if dialogue.dialogue_phrase_ko:
            return "이미 번역됨"
        
        translator = LibreTranslator()
        korean_text = translator.translate_to_korean(dialogue.dialogue_phrase)
        
        if korean_text and korean_text != dialogue.dialogue_phrase:
            dialogue.dialogue_phrase_ko = korean_text
            dialogue.translation_method = 'api_auto'
            dialogue.translation_quality = 'fair'
            dialogue.save(update_fields=[
                'dialogue_phrase_ko', 
                'translation_method', 
                'translation_quality'
            ])
            return "번역 완료"
        else:
            return "번역 실패"
            
    except DialogueTable.DoesNotExist:
        return "대사를 찾을 수 없음"
    except Exception as e:
        logger.error(f"비동기 번역 실패: {e}")
        return f"오류: {str(e)}"