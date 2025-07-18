from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

urlpatterns = [
    # === 설계서 기반 핵심 검색 API ===
    path('search/', views.search_movie_quotes, name='search-quotes'),
    
    # === 설계서 기반 테이블별 조회 API ===
    # 요청테이블 조회
    path('requests/', views.get_request_table_list, name='request-table-list'),
    
    # 영화테이블 조회  
    path('movies-table/', views.get_movie_table_list, name='movie-table-list'),
    
    # 대사테이블 조회
    path('dialogues/', views.get_dialogue_table_list, name='dialogue-table-list'),
    
    # === 설계서 정보 API ===
    path('schema/', views.get_schema_info, name='schema-info'),
    
    # === 기존 API 호환성 유지 ===
    # 기본 CRUD API (기존 모델명 사용)
    path('movies/', views.MovieListView.as_view(), name='movie-list'),
    path('movies/<int:pk>/', views.MovieDetailView.as_view(), name='movie-detail'),
    path('quotes/', views.DialogueListView.as_view(), name='quote-list'),
    
    # Flutter 앱용 API (기존 호환성)
    path('quotes/<int:quote_id>/', views.get_movie_quote_detail, name='quote-detail'),
    path('movies/<int:movie_id>/quotes/', views.get_movie_quotes_by_movie, name='movie-quotes'),
]

# API 사용 예시:
"""
=== 설계서 기반 API 사용법 ===

1. 핵심 검색 API (한글/영어 모두 지원)
   GET /api/search/?q=hello&limit=5
   GET /api/search/?q=안녕하세요&limit=10
   
   응답:
   {
     "query": "안녕하세요",
     "translated_query": "hello",
     "search_used": "hello",
     "count": 3,
     "limit": 5,
     "results": [...]
   }

2. 요청테이블 조회
   GET /api/requests/?limit=10&search=hello
   
   응답:
   {
     "count": 5,
     "limit": 10,
     "search": "hello",
     "requests": [
       {
         "request_phrase": "hello",
         "request_korean": "안녕하세요",
         "created_at": "2025-01-01T00:00:00Z",
         "updated_at": "2025-01-01T00:00:00Z"
       }
     ]
   }

3. 영화테이블 조회
   GET /api/movies-table/?limit=10&search=Titanic
   
   응답:
   {
     "count": 1,
     "movies": [
       {
         "movie_title": "Titanic",
         "release_year": "1997",
         "production_country": "미국",
         "director": "James Cameron",
         "imdb_url": "https://imdb.com/title/tt0120338/",
         "poster_url": "https://...",
         "created_at": "2025-01-01T00:00:00Z"
       }
     ]
   }

4. 대사테이블 조회
   GET /api/dialogues/?limit=10&search=hello&movie_id=1
   
   응답:
   {
     "count": 2,
     "dialogues": [
       {
         "id": 1,
         "movie_title": "Titanic",
         "dialogue_phrase": "Hello, nice to meet you",
         "dialogue_start_time": "00:21:30",
         "video_url": "https://...",
         "created_at": "2025-01-01T00:00:00Z"
       }
     ]
   }

5. 스키마 정보 조회
   GET /api/schema/
   
   설계서 기반 DB 구조와 개념 정보 제공

=== 설계서 핵심 개념 ===

입력구문 종류:
- 영음구문: 영어 음성 입력 (STT, 스마트폰 앱)
- 영문구문: 영어 키보드 입력 (웹브라우저) ← 현재 구현
- 한음구문: 한글 음성 입력 (STT, 스마트폰 앱)  
- 한문구문: 한글 키보드 입력 (웹브라우저) ← 현재 구현

처리 흐름:
1. 입력구문 → 번역구문(한글인 경우) → 요청구문(영어) + 요청한글
2. 요청테이블에서 검색 (요청구문 또는 요청한글)
3. 존재하면 DB 조회, 없으면 외부 API 호출
4. playphrase.me → 데이터 추출 → DB 저장 (요청테이블 + 영화테이블 + 대사테이블)
5. 결과 반환

DB 테이블 관계:
- 요청테이블 (Master): 요청구문을 저장
- 영화테이블 (Master): 영화정보 저장, 복합키 사용
- 대사테이블 (Slave): 영화테이블과 1:N 관계, 대사구문 저장

외부 인터페이스:
- playphrase.me: 대사구문 크롤링
- imdb.com: 영화정보 및 포스터 크롤링
"""