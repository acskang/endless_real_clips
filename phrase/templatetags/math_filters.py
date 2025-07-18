# dj/phrase/templatetags/math_filters.py
# This module defines custom template filters for mathematical operations.
# It includes filters for multiplication, addition of delays, and percentage calculations.
# These filters can be used in Django templates to perform calculations directly within the template context.
from django import template

register = template.Library()

@register.filter
def mul(value, arg):
    """값에 인수를 곱하는 필터"""
    try:
        return int(value) * int(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def add_delay(value):
    """애니메이션 딜레이를 생성하는 필터"""
    try:
        return f"{int(value) * 100}ms"
    except (ValueError, TypeError):
        return "0ms"

@register.filter 
def percentage(value, total):
    """퍼센트 계산 필터"""
    try:
        return round((int(value) / int(total)) * 100, 1)
    except (ValueError, TypeError, ZeroDivisionError):
        return 0