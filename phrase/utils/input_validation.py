# -*- coding: utf-8 -*-
# dj/phrase/utils/input_validation.py
"""
입력 검증 및 품질 확인 서비스
"""
import re
import logging
from phrase.application.translate import LibreTranslator

logger = logging.getLogger(__name__)


class InputValidator:
    """입력 텍스트 검증 및 품질 확인"""
    
    def __init__(self):
        self.translator = LibreTranslator()
    
    def validate_input(self, user_input):
        """
        입력 텍스트 검증 및 확인 필요 여부 판단
        
        Returns:
            {
                'is_valid': bool,
                'needs_confirmation': bool,
                'warning_type': str,
                'warning_message': str,
                'suggestions': list,
                'processed_input': str
            }
        """
        user_input = user_input.strip()
        
        # 기본 검증
        basic_validation = self._basic_validation(user_input)
        if not basic_validation['is_valid']:
            return basic_validation
        
        # 확인이 필요한 경우들 체크
        confirmation_check = self._check_needs_confirmation(user_input)
        
        return {
            'is_valid': True,
            'needs_confirmation': confirmation_check['needs_confirmation'],
            'warning_type': confirmation_check['warning_type'],
            'warning_message': confirmation_check['warning_message'],
            'suggestions': confirmation_check['suggestions'],
            'processed_input': user_input
        }
    
    def _basic_validation(self, user_input):
        """기본 검증 (길이, 문자 등)"""
        
        # 빈 입력
        if not user_input:
            return {
                'is_valid': False,
                'needs_confirmation': False,
                'warning_type': 'empty',
                'warning_message': '검색할 텍스트를 입력해주세요.',
                'suggestions': [],
                'processed_input': ''
            }
        
        # 길이 검증
        if len(user_input) > 500:
            return {
                'is_valid': False,
                'needs_confirmation': False,
                'warning_type': 'too_long',
                'warning_message': '검색어는 500자를 초과할 수 없습니다.',
                'suggestions': [user_input[:500]],
                'processed_input': user_input[:500]
            }
        
        return {'is_valid': True}
    
    def _check_needs_confirmation(self, user_input):
        """확인이 필요한 경우들 체크"""
        
        # 1. 너무 짧은 입력 (1-2글자)
        if len(user_input.strip()) <= 2:
            return {
                'needs_confirmation': True,
                'warning_type': 'too_short',
                'warning_message': f'"{user_input}"은(는) 너무 짧은 검색어입니다. 검색 결과가 너무 많을 수 있습니다.',
                'suggestions': self._suggest_longer_phrases(user_input)
            }
        
        # 2. 단일 문자 또는 특수문자만
        if re.match(r'^[^\w\s]*$', user_input) or len(user_input.strip()) == 1:
            return {
                'needs_confirmation': True,
                'warning_type': 'single_char',
                'warning_message': f'"{user_input}"은(는) 단일 문자입니다. 의미있는 구문을 검색하시겠습니까?',
                'suggestions': self._suggest_common_phrases_with_char(user_input)
            }
        
        # 3. 숫자만 입력
        if user_input.strip().isdigit():
            return {
                'needs_confirmation': True,
                'warning_type': 'only_numbers',
                'warning_message': f'"{user_input}"은(는) 숫자만 포함되어 있습니다. 숫자가 포함된 대사를 찾으시겠습니까?',
                'suggestions': self._suggest_number_phrases(user_input)
            }
        
        # 4. 반복 문자 (aaa, kkk 등)
        if self._is_repeated_chars(user_input):
            return {
                'needs_confirmation': True,
                'warning_type': 'repeated_chars',
                'warning_message': f'"{user_input}"은(는) 반복되는 문자입니다. 오타가 아닌지 확인해주세요.',
                'suggestions': self._suggest_typo_corrections(user_input)
            }
        
        # 5. 일반적이지 않은 문자 조합 (한글+영어 혼용 등)
        mixed_check = self._check_mixed_languages(user_input)
        if mixed_check['needs_confirmation']:
            return mixed_check
        
        # 6. 잠재적 오타 검사 (영어)
        if not self.translator.is_korean(user_input):
            typo_check = self._check_potential_typos(user_input)
            if typo_check['needs_confirmation']:
                return typo_check
        
        # 확인 불필요
        return {
            'needs_confirmation': False,
            'warning_type': 'none',
            'warning_message': '',
            'suggestions': []
        }
    
    def _suggest_longer_phrases(self, char):
        """짧은 문자에 대한 긴 구문 제안"""
        suggestions = {
            'a': ['a little', 'a lot', 'a moment', 'a while'],
            'i': ['I am', 'I love', 'I think', 'I know'],
            'o': ['oh no', 'oh my', 'okay', 'of course'],
            '아': ['아니야', '아무것도', '아마도', '아직'],
            '나': ['나는', '나도', '나중에', '나만'],
            '그': ['그래', '그런데', '그렇다', '그거']
        }
        return suggestions.get(char.lower(), [f'{char}로 시작하는 단어들'])
    
    def _suggest_common_phrases_with_char(self, char):
        """단일 문자가 포함된 일반적인 구문 제안"""
        if char.lower() in 'aeiou':
            return [f'단어에 포함된 "{char}" 검색', f'"{char}"로 시작하는 단어들']
        return [f'"{char}"가 포함된 대사 검색']
    
    def _suggest_number_phrases(self, number):
        """숫자가 포함된 구문 제안"""
        return [
            f'{number} years old',
            f'{number} minutes',
            f'{number} dollars',
            f'number {number}',
            f'{number}살',
            f'{number}개',
            f'{number}번째'
        ]
    
    def _is_repeated_chars(self, text):
        """반복 문자 검사"""
        if len(text) < 2:
            return False
        
        # 같은 문자가 3번 이상 연속
        for i in range(len(text) - 2):
            if text[i] == text[i+1] == text[i+2]:
                return True
        
        # 전체가 같은 문자
        if len(set(text.lower())) == 1 and len(text) > 2:
            return True
            
        return False
    
    def _suggest_typo_corrections(self, text):
        """반복 문자 오타 교정 제안"""
        # 반복 제거
        deduplicated = re.sub(r'(.)\1+', r'\1', text)
        return [deduplicated] if deduplicated != text else []
    
    def _check_mixed_languages(self, text):
        """언어 혼용 검사"""
        has_korean = bool(re.search(r'[가-힣]', text))
        has_english = bool(re.search(r'[a-zA-Z]', text))
        has_numbers = bool(re.search(r'\d', text))
        
        if has_korean and has_english:
            return {
                'needs_confirmation': True,
                'warning_type': 'mixed_languages',
                'warning_message': f'"{text}"에 한글과 영어가 혼용되어 있습니다. 의도한 검색어가 맞나요?',
                'suggestions': [
                    re.sub(r'[a-zA-Z]', '', text).strip(),  # 한글만
                    re.sub(r'[가-힣]', '', text).strip()    # 영어만
                ]
            }
        
        return {'needs_confirmation': False}
    
    def _check_potential_typos(self, text):
        """영어 오타 가능성 검사"""
        
        # 연속된 자음이 많은 경우
        consonant_clusters = re.findall(r'[bcdfghjklmnpqrstvwxyz]{3,}', text.lower())
        if consonant_clusters:
            return {
                'needs_confirmation': True,
                'warning_type': 'consonant_cluster',
                'warning_message': f'"{text}"에 연속된 자음이 있습니다. 오타가 아닌지 확인해주세요.',
                'suggestions': self._suggest_consonant_fixes(text)
            }
        
        # 일반적이지 않은 문자 패턴
        if re.search(r'[qx]{2,}|[z]{2,}', text.lower()):
            return {
                'needs_confirmation': True,
                'warning_type': 'unusual_pattern',
                'warning_message': f'"{text}"에 일반적이지 않은 문자 조합이 있습니다.',
                'suggestions': []
            }
        
        return {'needs_confirmation': False}
    
    def _suggest_consonant_fixes(self, text):
        """자음 연속 오타 수정 제안"""
        # 간단한 수정 제안 (중간에 모음 추가)
        suggestions = []
        consonant_pattern = r'([bcdfghjklmnpqrstvwxyz])([bcdfghjklmnpqrstvwxyz])([bcdfghjklmnpqrstvwxyz])'
        
        def add_vowel(match):
            return f"{match.group(1)}e{match.group(2)}{match.group(3)}"
        
        suggestion = re.sub(consonant_pattern, add_vowel, text.lower())
        if suggestion != text.lower():
            suggestions.append(suggestion)
        
        return suggestions


def get_confirmation_context(validation_result, original_input):
    """확인 모달용 컨텍스트 생성"""
    if not validation_result['needs_confirmation']:
        return None
    
    return {
        'show_confirmation': True,
        'warning_type': validation_result['warning_type'],
        'warning_message': validation_result['warning_message'],
        'original_input': original_input,
        'suggestions': validation_result['suggestions'][:5],  # 최대 5개
        'processed_input': validation_result['processed_input']
    }