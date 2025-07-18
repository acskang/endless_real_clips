// app.js - 앱 초기화 & 전역 설정

// ===== 전역 설정 =====
window.APP_CONFIG = {
    // API 설정
    TRANSLATION_API_URL: 'https://libretranslate.de/translate',
    RETRY_ATTEMPTS: 3,
    RETRY_DELAY: 300,
    DEBOUNCE_DELAY: 300,
    
    // UI 설정
    LOADING_STEP_DELAY: 1000,
    MIN_SEARCH_LENGTH: 2,
    MAX_SEARCH_LENGTH: 500,
    
    // 캐시 설정
    CACHE_TIMEOUT: 600000, // 10분
    POPULAR_CACHE_TIME: 300000, // 5분
    STATS_CACHE_TIME: 600000, // 10분
};

// ===== 앱 상태 관리 =====
window.APP_STATE = {
    // 네트워크 상태
    isOnline: navigator.onLine,
    
    // 검색 상태
    currentQuery: '',
    searchHistory: [],
    lastSearchTime: 0,
    
    // 번역 통계
    translationStats: {
        db: 0,
        api: 0,
        failed: 0,
        pending: 0
    },
    
    // UI 상태
    popularSearchesLoaded: false,
    statisticsLoaded: false,
    currentSort: 'relevance',
    
    // 캐시
    cache: new Map(),
    
    // Django 데이터
    django: null
};

// ===== DOM 요소 캐싱 =====
window.DOM_ELEMENTS = {
    // 검색 관련
    searchForm: null,
    unifiedInput: null,
    desktopInput: null,
    mobileInput: null,
    clearDesktop: null,
    clearMobile: null,
    
    // 로딩 오버레이
    searchLoadingOverlay: null,
    loadingTitle: null,
    loadingMessage: null,
    searchProgress: null,
    
    // 모달 관련
    videoModal: null,
    modalVideo: null,
    modalTitle: null,
    modalTextEn: null,
    modalTextKo: null,
    videoLoading: null,
    videoError: null,
    
    // 섹션 관련
    popularSection: null,
    popularContainer: null,
    statisticsSection: null,
    statisticsContainer: null,
    moviesContainer: null,
    
    // 기타
    networkStatus: null,
    loadMoreButton: null,
    sortSelect: null,
    downloadButton: null,
    toastContainer: null
};

// ===== 앱 초기화 =====
function initializeApp() {
    console.log('🎬 플레이프레이즈 프론트엔드 초기화 시작...');
    
    // Django 데이터 로드
    loadDjangoData();
    
    // DOM 요소 초기화
    initializeDOM();
    
    // 각 모듈 초기화
    if (typeof initializeSearch === 'function') {
        initializeSearch();
    }
    
    if (typeof initializeLoading === 'function') {
        initializeLoading();
    }
    
    if (typeof initializeUI === 'function') {
        initializeUI();
    }
    
    if (typeof initializeUtils === 'function') {
        initializeUtils();
    }
    
    console.log('✅ 플레이프레이즈 초기화 완료');
    console.log('📊 번역 통계:', APP_STATE.translationStats);
    console.log('🌐 Django 데이터:', APP_STATE.django);
}

// ===== Django 데이터 로드 =====
function loadDjangoData() {
    if (typeof window.djangoData !== 'undefined') {
        APP_STATE.django = window.djangoData;
        APP_CONFIG.MAX_SEARCH_LENGTH = APP_STATE.django.settings?.maxSearchLength || 500;
        APP_CONFIG.MIN_SEARCH_LENGTH = APP_STATE.django.settings?.minSearchLength || 2;
        
        // 현재 검색어가 있으면 상태에 저장
        if (APP_STATE.django.search?.query) {
            APP_STATE.currentQuery = APP_STATE.django.search.query;
        }
        
        console.log('📋 Django 설정 로드:', {
            maxLength: APP_CONFIG.MAX_SEARCH_LENGTH,
            minLength: APP_CONFIG.MIN_SEARCH_LENGTH,
            currentQuery: APP_STATE.currentQuery
        });
    } else {
        console.warn('⚠️ Django 데이터를 찾을 수 없습니다.');
        APP_STATE.django = { urls: {}, search: {}, settings: {} };
    }
}

// ===== DOM 초기화 =====
function initializeDOM() {
    // 검색 관련
    DOM_ELEMENTS.searchForm = document.getElementById('search-form');
    DOM_ELEMENTS.unifiedInput = document.getElementById('unified-search-input');
    DOM_ELEMENTS.desktopInput = document.getElementById('search-input-desktop');
    DOM_ELEMENTS.mobileInput = document.getElementById('search-input-mobile');
    DOM_ELEMENTS.clearDesktop = document.getElementById('clear-search-desktop');
    DOM_ELEMENTS.clearMobile = document.getElementById('clear-search-mobile');
    
    // 로딩 오버레이
    DOM_ELEMENTS.searchLoadingOverlay = document.getElementById('search-loading-overlay');
    DOM_ELEMENTS.loadingTitle = document.getElementById('loading-title');
    DOM_ELEMENTS.loadingMessage = document.getElementById('loading-message');
    DOM_ELEMENTS.searchProgress = document.getElementById('search-progress');
    
    // 모달 관련
    DOM_ELEMENTS.videoModal = document.getElementById('video-modal');
    DOM_ELEMENTS.modalVideo = document.getElementById('modal-video');
    DOM_ELEMENTS.modalTitle = document.getElementById('modal-title');
    DOM_ELEMENTS.modalTextEn = document.getElementById('modal-text-en');
    DOM_ELEMENTS.modalTextKo = document.getElementById('modal-text-ko');
    DOM_ELEMENTS.videoLoading = document.getElementById('video-loading');
    DOM_ELEMENTS.videoError = document.getElementById('video-error');
    
    // 섹션 관련
    DOM_ELEMENTS.popularSection = document.getElementById('popular-section');
    DOM_ELEMENTS.popularContainer = document.getElementById('popular-searches-container');
    DOM_ELEMENTS.statisticsSection = document.getElementById('statistics-section');
    DOM_ELEMENTS.statisticsContainer = document.getElementById('statistics-container');
    DOM_ELEMENTS.moviesContainer = document.getElementById('movies-container');
    
    // 기타
    DOM_ELEMENTS.networkStatus = document.getElementById('network-status');
    DOM_ELEMENTS.loadMoreButton = document.getElementById('load-more');
    DOM_ELEMENTS.sortSelect = document.getElementById('sort-select');
    DOM_ELEMENTS.downloadButton = document.getElementById('download-results');
    DOM_ELEMENTS.toastContainer = document.getElementById('toast-container');
    
    // DOM 요소 확인 로그
    console.log('🔍 DOM 요소 확인:');
    Object.keys(DOM_ELEMENTS).forEach(key => {
        console.log(`  - ${key}:`, DOM_ELEMENTS[key] ? '✅' : '❌');
    });
}

// ===== 전역 함수들 (HTML에서 호출) =====
window.handlePosterError = function(img) {
    const container = img.parentElement;
    container.innerHTML = `
        <div class="poster-placeholder d-flex flex-column align-items-center justify-content-center h-100 bg-secondary bg-opacity-50">
            <i class="fas fa-film text-muted" style="font-size: 3rem;"></i>
            <span class="text-muted mt-2">포스터 없음</span>
        </div>
    `;
};

// 🔧 비디오 모달 함수는 scripts.html에서만 정의 (app.js에서는 정의하지 않음)

// ===== 앱 시작 =====
document.addEventListener('DOMContentLoaded', initializeApp);