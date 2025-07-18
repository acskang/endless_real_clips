// index.js - models.py, managers.py, views.py 실제 구조 연동 최적화
// Django 백엔드와 완벽 연동된 프론트엔드 JavaScript

// ===== 전역 설정 및 상태 관리 =====
const APP_CONFIG = {
    // API 설정
    TRANSLATION_API_URL: 'https://libretranslate.de/translate',
    RETRY_ATTEMPTS: 3,
    RETRY_DELAY: 300,
    DEBOUNCE_DELAY: 300,
    
    // UI 설정
    LOADING_STEP_DELAY: 1000,
    MIN_SEARCH_LENGTH: 2,
    MAX_SEARCH_LENGTH: 500, // RequestTable.request_phrase max_length
    
    // 캐시 설정
    CACHE_TIMEOUT: 600000, // 10분
    POPULAR_CACHE_TIME: 300000, // 5분
    STATS_CACHE_TIME: 600000, // 10분
};

// DOM 요소 캐싱
const DOM_ELEMENTS = {
    // 반응형 검색 관련 (새로운 구조)
    searchForm: null,
    unifiedInput: null,
    desktopInput: null,
    mobileInput: null,
    clearDesktop: null,
    clearMobile: null,
    
    // 검색 제안
    searchSuggestions: null,
    suggestionsList: null,
    
    // 로딩 오버레이 (새로 추가)
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

// 앱 상태 관리
const APP_STATE = {
    // 네트워크 상태
    isOnline: navigator.onLine,
    
    // 검색 상태
    currentQuery: '',
    searchHistory: [],
    lastSearchTime: 0,
    
    // 번역 통계 (managers.py 연동)
    translationStats: {
        db: 0,           // DB에서 가져온 번역
        api: 0,          // API로 번역한 것
        failed: 0,       // 번역 실패
        pending: 0       // 번역 중
    },
    
    // UI 상태
    popularSearchesLoaded: false,
    statisticsLoaded: false,
    currentSort: 'relevance',
    
    // 캐시
    cache: new Map(),
    
    // Django 데이터 (전역에서 접근)
    django: null
};

// ===== 초기화 =====
document.addEventListener('DOMContentLoaded', function() {
    console.log('🎬 플레이프레이즈 프론트엔드 초기화 시작...');
    
    // Django 데이터 로드
    loadDjangoData();
    
    // DOM 요소 초기화
    initializeDOM();
    
    // 반응형 검색 폼 초기화 (메인 기능)
    initializeResponsiveSearch();
    
    // 이벤트 리스너 설정 (검색 외 기타 기능들)
    initializeOtherEventListeners();
    
    // 네트워크 모니터링
    initializeNetworkMonitoring();
    
    // 번역 통계 초기화
    initializeTranslationStats();
    
    // 포스터 이미지 초기화
    initializePosterImages();
    
    // 검색 기록 로드
    loadSearchHistory();
    
    console.log('✅ 플레이프레이즈 초기화 완료');
    console.log('📊 번역 통계:', APP_STATE.translationStats);
    console.log('🌐 Django 데이터:', APP_STATE.django);
});

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
    // 반응형 검색 관련
    DOM_ELEMENTS.searchForm = document.getElementById('search-form');
    DOM_ELEMENTS.unifiedInput = document.getElementById('unified-search-input');
    DOM_ELEMENTS.desktopInput = document.getElementById('search-input-desktop');
    DOM_ELEMENTS.mobileInput = document.getElementById('search-input-mobile');
    DOM_ELEMENTS.clearDesktop = document.getElementById('clear-search-desktop');
    DOM_ELEMENTS.clearMobile = document.getElementById('clear-search-mobile');
    
    // 검색 제안
    DOM_ELEMENTS.searchSuggestions = document.getElementById('search-suggestions');
    DOM_ELEMENTS.suggestionsList = document.getElementById('suggestions-list');
    
    // 로딩 오버레이 (새로 추가)
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

// ===== 반응형 검색 폼 초기화 (메인 기능) =====
function initializeResponsiveSearch() {
    console.log('🔍 반응형 검색 초기화 시작...');
    
    // 현재 활성 입력창 가져오기
    function getActiveSearchInput() {
        const isDesktop = window.innerWidth >= 768; // md breakpoint
        return isDesktop ? DOM_ELEMENTS.desktopInput : DOM_ELEMENTS.mobileInput;
    }
    
    // 입력값 동기화 (핵심 기능)
    function syncInputs(sourceValue) {
        console.log('🔄 입력값 동기화:', sourceValue);
        
        // 모든 입력창에 값 설정
        if (DOM_ELEMENTS.unifiedInput) DOM_ELEMENTS.unifiedInput.value = sourceValue;
        if (DOM_ELEMENTS.desktopInput) DOM_ELEMENTS.desktopInput.value = sourceValue;
        if (DOM_ELEMENTS.mobileInput) DOM_ELEMENTS.mobileInput.value = sourceValue;
        
        // 지우기 버튼 표시/숨김
        updateClearButtons(sourceValue);
        
        console.log('✅ 동기화 완료 - 통합필드:', DOM_ELEMENTS.unifiedInput?.value);
    }
    
    // 지우기 버튼 상태 업데이트
    function updateClearButtons(value) {
        const hasValue = value && value.trim().length > 0;
        
        if (DOM_ELEMENTS.clearDesktop) {
            DOM_ELEMENTS.clearDesktop.classList.toggle('d-none', !hasValue);
        }
        if (DOM_ELEMENTS.clearMobile) {
            DOM_ELEMENTS.clearMobile.classList.toggle('d-none', !hasValue);
        }
    }
    
    // 데스크톱 입력 이벤트
    if (DOM_ELEMENTS.desktopInput) {
        DOM_ELEMENTS.desktopInput.addEventListener('input', function() {
            console.log('💻 데스크톱 입력:', this.value);
            syncInputs(this.value);
        });
        
        DOM_ELEMENTS.desktopInput.addEventListener('focus', function() {
            this.parentElement.classList.add('shadow-lg');
        });
        
        DOM_ELEMENTS.desktopInput.addEventListener('blur', function() {
            this.parentElement.classList.remove('shadow-lg');
        });
    }
    
    // 모바일 입력 이벤트
    if (DOM_ELEMENTS.mobileInput) {
        DOM_ELEMENTS.mobileInput.addEventListener('input', function() {
            console.log('📱 모바일 입력:', this.value);
            syncInputs(this.value);
        });
        
        DOM_ELEMENTS.mobileInput.addEventListener('focus', function() {
            this.classList.add('shadow-lg');
        });
        
        DOM_ELEMENTS.mobileInput.addEventListener('blur', function() {
            this.classList.remove('shadow-lg');
        });
    }
    
    // 지우기 버튼 이벤트
    if (DOM_ELEMENTS.clearDesktop) {
        DOM_ELEMENTS.clearDesktop.addEventListener('click', function() {
            console.log('🗑️ 데스크톱 지우기 클릭');
            syncInputs('');
            getActiveSearchInput()?.focus();
        });
    }
    
    if (DOM_ELEMENTS.clearMobile) {
        DOM_ELEMENTS.clearMobile.addEventListener('click', function() {
            console.log('🗑️ 모바일 지우기 클릭');
            syncInputs('');
            getActiveSearchInput()?.focus();
        });
    }
    
    // 폼 제출 시 검증 및 최종 동기화
    if (DOM_ELEMENTS.searchForm) {
        DOM_ELEMENTS.searchForm.addEventListener('submit', function(e) {
            console.log('📝 폼 제출 시작');
            
            const activeInput = getActiveSearchInput();
            const value = activeInput?.value?.trim() || '';
            
            console.log('📋 제출할 값:', value);
            console.log('🔍 활성 입력창:', activeInput?.id);
            console.log('🔗 통합 필드 현재값:', DOM_ELEMENTS.unifiedInput?.value);
            
            if (!value) {
                e.preventDefault();
                activeInput?.focus();
                showToast('검색어를 입력해주세요.', 'warning');
                return false;
            }
            
            // 최종 동기화 (중요!)
            syncInputs(value);
            
            console.log('✅ 최종 제출값:', DOM_ELEMENTS.unifiedInput?.value);
            
            // 🆕 로딩 애니메이션 시작 (새로운 검색어인 경우)
            if (isNewSearchQuery(value)) {
                showSearchLoadingAnimation(value);
            }
            
            // 로딩 상태 표시
            const submitButtons = this.querySelectorAll('button[type="submit"]');
            submitButtons.forEach(btn => {
                btn.disabled = true;
                const originalText = btn.innerHTML;
                btn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>검색 중...';
                
                // 5초 후 복원 (안전장치)
                setTimeout(() => {
                    btn.disabled = false;
                    btn.innerHTML = originalText;
                }, 5000);
            });
        });
    }
    
    // 빠른 검색 버튼
    document.querySelectorAll('.quick-search-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const query = this.dataset.query;
            console.log('⚡ 빠른 검색:', query);
            syncInputs(query);
            
            // 애니메이션 효과
            this.classList.add('animate__pulse');
            setTimeout(() => {
                this.classList.remove('animate__pulse');
                DOM_ELEMENTS.searchForm?.submit();
            }, 200);
        });
    });
    
    // 키보드 단축키
    document.addEventListener('keydown', function(e) {
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            const activeInput = getActiveSearchInput();
            activeInput?.focus();
            activeInput?.select();
        }
        
        if (e.key === 'Escape') {
            const activeInput = getActiveSearchInput();
            if (document.activeElement === activeInput) {
                activeInput.blur();
            }
        }
    });
    
    // 화면 크기 변경 시 처리
    let resizeTimer;
    window.addEventListener('resize', function() {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(() => {
            const currentValue = DOM_ELEMENTS.unifiedInput?.value || 
                                DOM_ELEMENTS.desktopInput?.value || 
                                DOM_ELEMENTS.mobileInput?.value || '';
            syncInputs(currentValue);
        }, 100);
    });
    
    // 초기화: 페이지 로드 시 입력값 동기화
    const initialValue = DOM_ELEMENTS.unifiedInput?.value || '';
    console.log('🚀 초기값 설정:', initialValue);
    
    if (initialValue) {
        syncInputs(initialValue);
    }
    
    // 자동 포커스 (데스크톱에서만)
    if (window.innerWidth >= 768 && DOM_ELEMENTS.desktopInput && !initialValue) {
        setTimeout(() => {
            DOM_ELEMENTS.desktopInput.focus();
        }, 100);
    }
    
    console.log('✅ 반응형 검색 초기화 완료');
}

// ===== 기타 이벤트 리스너 =====
function initializeOtherEventListeners() {
    // 검색 제안 닫기
    document.getElementById('close-suggestions')?.addEventListener('click', hideSuggestions);

    // 인기 검색어 및 통계 버튼
    document.getElementById('show-popular-on-error')?.addEventListener('click', showPopularSearches);

    // 정렬 및 다운로드
    if (DOM_ELEMENTS.sortSelect) {
        DOM_ELEMENTS.sortSelect.addEventListener('change', handleSortChange);
    }
    if (DOM_ELEMENTS.downloadButton) {
        DOM_ELEMENTS.downloadButton.addEventListener('click', downloadResults);
    }

    // 더보기 버튼
    if (DOM_ELEMENTS.loadMoreButton) {
        DOM_ELEMENTS.loadMoreButton.addEventListener('click', loadMoreResults);
    }

    // 영화 카드 이벤트 (동적 추가된 요소들)
    document.addEventListener('click', handleDynamicClicks);

    // 모달 이벤트
    if (DOM_ELEMENTS.videoModal) {
        DOM_ELEMENTS.videoModal.addEventListener('hidden.bs.modal', handleModalClose);
    }

    // 고급 옵션 토글 애니메이션
    const advancedToggle = document.querySelector('[data-bs-target="#advanced-options"]');
    if (advancedToggle) {
        advancedToggle.addEventListener('click', function() {
            const icon = this.querySelector('.fa-chevron-down');
            if (icon) {
                icon.style.transform = icon.style.transform === 'rotate(180deg)' ? 'rotate(0deg)' : 'rotate(180deg)';
                icon.style.transition = 'transform 0.3s ease';
            }
        });
    }
}

// ===== 검색 제안 시스템 =====
function hideSuggestions() {
    if (DOM_ELEMENTS.searchSuggestions) {
        DOM_ELEMENTS.searchSuggestions.classList.add('d-none');
    }
}

// ===== 인기 검색어 =====
async function showPopularSearches() {
    if (!DOM_ELEMENTS.popularSection || !DOM_ELEMENTS.popularContainer) return;
    
    DOM_ELEMENTS.popularSection.classList.remove('d-none');
    
    if (!APP_STATE.popularSearchesLoaded) {
        DOM_ELEMENTS.popularContainer.innerHTML = `
            <div class="col-12 text-center text-muted">
                <i class="fas fa-search mb-2" style="font-size: 2rem;"></i>
                <p>인기 검색어 기능은 준비 중입니다.</p>
            </div>
        `;
    }
}

// ===== 네트워크 모니터링 =====
function initializeNetworkMonitoring() {
    function updateNetworkStatus() {
        APP_STATE.isOnline = navigator.onLine;
        if (DOM_ELEMENTS.networkStatus) {
            if (APP_STATE.isOnline) {
                DOM_ELEMENTS.networkStatus.style.display = 'none';
            } else {
                DOM_ELEMENTS.networkStatus.style.display = 'block';
            }
        }
    }

    window.addEventListener('online', updateNetworkStatus);
    window.addEventListener('offline', updateNetworkStatus);
    updateNetworkStatus();
}

// ===== 번역 통계 초기화 =====
function initializeTranslationStats() {
    // 기존 번역 통계 계산
    const dbTranslated = document.querySelectorAll('.db-translated').length;
    const apiTranslated = document.querySelectorAll('.api-translated').length;
    
    APP_STATE.translationStats.db = dbTranslated;
    APP_STATE.translationStats.api = apiTranslated;
    
    console.log('📊 번역 통계 초기화:', APP_STATE.translationStats);
}

// ===== 포스터 이미지 처리 =====
function initializePosterImages() {
    const movieCards = document.querySelectorAll('.movie-card');
    
    movieCards.forEach((card, index) => {
        const imageContainer = card.querySelector('.movie-card-image');
        const image = imageContainer?.querySelector('img');
        
        if (image && imageContainer) {
            // 로딩 클래스 추가
            imageContainer.classList.add('loading');
            
            console.log(`🖼️ 포스터 ${index + 1} 초기화:`, image.src);
            
            // 이미지 로드 이벤트
            if (image.complete && image.naturalHeight !== 0) {
                handleImageLoad(image, imageContainer, index + 1);
            } else {
                const timeoutId = setTimeout(() => {
                    if (image.style.opacity !== '1') {
                        handleImageError(image, imageContainer, index + 1, '로드 타임아웃');
                    }
                }, 10000);
                
                image.addEventListener('load', () => {
                    clearTimeout(timeoutId);
                    handleImageLoad(image, imageContainer, index + 1);
                });
                
                image.addEventListener('error', () => {
                    clearTimeout(timeoutId);
                    handleImageError(image, imageContainer, index + 1, '로드 실패');
                });
            }
        }
    });
}

function handleImageLoad(image, container, index) {
    image.style.opacity = '1';
    container.classList.remove('loading');
    console.log(`✅ 포스터 ${index} 로드 성공`);
}

function handleImageError(image, container, index, reason) {
    container.classList.remove('loading');
    console.log(`❌ 포스터 ${index} ${reason}:`, image.src);
    
    // 전역 함수 호출 (HTML에서 정의된)
    if (typeof handlePosterError === 'function') {
        handlePosterError(image);
    }
}

// ===== 검색 기록 =====
function loadSearchHistory() {
    try {
        const history = localStorage.getItem('searchHistory');
        if (history) {
            APP_STATE.searchHistory = JSON.parse(history);
        }
    } catch (error) {
        console.warn('검색 기록 로드 실패:', error);
        APP_STATE.searchHistory = [];
    }
}

function addToSearchHistory(query) {
    if (!query || query.trim().length < 2) return;
    
    const cleanQuery = query.trim();
    
    // 중복 제거
    APP_STATE.searchHistory = APP_STATE.searchHistory.filter(item => item !== cleanQuery);
    
    // 맨 앞에 추가
    APP_STATE.searchHistory.unshift(cleanQuery);
    
    // 최대 20개까지만 보관
    if (APP_STATE.searchHistory.length > 20) {
        APP_STATE.searchHistory = APP_STATE.searchHistory.slice(0, 20);
    }
    
    // 로컬 스토리지에 저장
    try {
        localStorage.setItem('searchHistory', JSON.stringify(APP_STATE.searchHistory));
    } catch (error) {
        console.warn('검색 기록 저장 실패:', error);
    }
}

// ===== 동적 이벤트 처리 =====
function handleDynamicClicks(e) {
    // 번역 버튼 클릭
    if (e.target.classList.contains('translate-btn')) {
        e.preventDefault();
        const text = e.target.dataset.text;
        handleTranslateClick(e.target, text);
    }
    
    // 복사 버튼 클릭
    if (e.target.closest('.copy-dialogue')) {
        e.preventDefault();
        const text = e.target.closest('.copy-dialogue').dataset.text;
        copyToClipboard(text);
    }
}

// ===== 토스트 알림 =====
function showToast(message, type = 'info') {
    const toastContainer = DOM_ELEMENTS.toastContainer;
    if (!toastContainer) return;
    
    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-white bg-${type} border-0`;
    toast.setAttribute('role', 'alert');
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                <i class="fas fa-${type === 'warning' ? 'exclamation-triangle' : 'info-circle'} me-2"></i>
                ${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
    `;
    
    toastContainer.appendChild(toast);
    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();
    
    // 자동 제거
    setTimeout(() => {
        if (toast.parentNode) {
            toast.parentNode.removeChild(toast);
        }
    }, 5000);
}

// ===== 유틸리티 함수들 =====
function handleSortChange() {
    console.log('정렬 변경:', DOM_ELEMENTS.sortSelect?.value);
}

function downloadResults() {
    console.log('결과 다운로드');
}

function loadMoreResults() {
    console.log('더 많은 결과 로드');
}

function handleTranslateClick(button, text) {
    console.log('번역 요청:', text);
}

function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        showToast('클립보드에 복사되었습니다.', 'success');
    }).catch(() => {
        showToast('복사에 실패했습니다.', 'error');
    });
}

function handleModalClose() {
    console.log('❌ 비디오 모달 닫기');
    
    // 비디오 정지 및 초기화
    const modalVideo = document.getElementById('modal-video');
    if (modalVideo) {
        modalVideo.pause();
        modalVideo.currentTime = 0;
        modalVideo.muted = true; // 다음 재생을 위해 음소거 상태로 리셋
        
        // 비디오 소스 초기화
        const videoSource = document.getElementById('video-source');
        if (videoSource) {
            videoSource.src = '';
        }
        
        modalVideo.load(); // 비디오 리로드하여 완전 초기화
    }
    
    // UI 상태 초기화
    const videoLoading = document.getElementById('video-loading');
    const videoError = document.getElementById('video-error');
    
    if (videoLoading) videoLoading.classList.remove('d-none');
    if (videoError) videoError.classList.add('d-none');
    if (modalVideo) modalVideo.classList.add('d-none');
}

// ===== 디바운스 유틸리티 =====
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// ===== 검색 입력창 플레이스홀더 애니메이션 =====
function animatePlaceholder() {
    const placeholders = [
        '한글 또는 영어 구문을 입력하세요...',
        'hello, thank you, i love you...',
        '안녕하세요, 감사합니다, 사랑해요...',
        '영화 속 명대사를 찾아보세요!'
    ];
    
    let currentIndex = 0;
    
    function updatePlaceholder() {
        const inputs = [DOM_ELEMENTS.desktopInput, DOM_ELEMENTS.mobileInput].filter(Boolean);
        inputs.forEach(input => {
            if (input && !input.value) {
                input.placeholder = placeholders[currentIndex];
            }
        });
        currentIndex = (currentIndex + 1) % placeholders.length;
    }
    
    // 5초마다 플레이스홀더 변경
    setInterval(updatePlaceholder, 5000);
}

// 플레이스홀더 애니메이션 시작
setTimeout(animatePlaceholder, 3000);

// ===== 새로운 검색어 로딩 애니메이션 시스템 =====

// 새로운 검색어인지 확인
function isNewSearchQuery(query) {
    // 검색 기록에 없는 경우 새로운 검색어로 판단
    return !APP_STATE.searchHistory.includes(query.trim().toLowerCase());
}

// 로딩 애니메이션 표시
function showSearchLoadingAnimation(searchQuery) {
    console.log('🎬 로딩 애니메이션 시작:', searchQuery);
    
    if (!DOM_ELEMENTS.searchLoadingOverlay) return;
    
    // 오버레이 표시
    DOM_ELEMENTS.searchLoadingOverlay.classList.remove('d-none');
    document.body.style.overflow = 'hidden'; // 스크롤 방지
    
    // 로딩 메시지 설정
    if (DOM_ELEMENTS.loadingTitle) {
        DOM_ELEMENTS.loadingTitle.textContent = `"${searchQuery}" 검색 중...`;
    }
    
    if (DOM_ELEMENTS.loadingMessage) {
        DOM_ELEMENTS.loadingMessage.textContent = '새로운 영화 대사를 찾기 위해 외부 API에서 데이터를 가져오고 있습니다';
    }
    
    // 진행 단계 애니메이션 시작
    startLoadingSteps();
    
    // 프로그레스 바 애니메이션
    animateProgressBar();
    
    // 자동 숨김 (최대 15초 후)
    setTimeout(() => {
        hideSearchLoadingAnimation();
    }, 15000);
}

// 로딩 애니메이션 숨김
function hideSearchLoadingAnimation() {
    console.log('✅ 로딩 애니메이션 종료');
    
    if (!DOM_ELEMENTS.searchLoadingOverlay) return;
    
    // 페이드 아웃 효과
    DOM_ELEMENTS.searchLoadingOverlay.style.opacity = '0';
    
    setTimeout(() => {
        DOM_ELEMENTS.searchLoadingOverlay.classList.add('d-none');
        DOM_ELEMENTS.searchLoadingOverlay.style.opacity = '1';
        document.body.style.overflow = ''; // 스크롤 복원
        
        // 상태 초기화
        resetLoadingSteps();
        resetProgressBar();
    }, 300);
}

// 로딩 단계 애니메이션
function startLoadingSteps() {
    const steps = [
        { id: 'step-search', delay: 0, message: '검색 조건 확인 중...' },
        { id: 'step-fetch', delay: 2000, message: '외부 API에서 데이터 수집 중...' },
        { id: 'step-process', delay: 5000, message: '영화 정보 및 대사 처리 중...' },
        { id: 'step-save', delay: 8000, message: '데이터베이스에 저장 중...' }
    ];
    
    steps.forEach((step, index) => {
        setTimeout(() => {
            // 이전 단계들을 완료 상태로 변경
            for (let i = 0; i < index; i++) {
                const prevStep = document.getElementById(steps[i].id);
                if (prevStep) {
                    prevStep.classList.remove('active');
                    prevStep.classList.add('completed');
                }
            }
            
            // 현재 단계를 활성 상태로 변경
            const currentStep = document.getElementById(step.id);
            if (currentStep) {
                currentStep.classList.add('active');
                
                // 메시지 업데이트
                if (DOM_ELEMENTS.loadingMessage) {
                    DOM_ELEMENTS.loadingMessage.textContent = step.message;
                }
            }
        }, step.delay);
    });
}

// 로딩 단계 초기화
function resetLoadingSteps() {
    const stepIds = ['step-search', 'step-fetch', 'step-process', 'step-save'];
    stepIds.forEach(id => {
        const step = document.getElementById(id);
        if (step) {
            step.classList.remove('active', 'completed');
        }
    });
}

// 프로그레스 바 애니메이션
function animateProgressBar() {
    if (!DOM_ELEMENTS.searchProgress) return;
    
    let progress = 0;
    const interval = setInterval(() => {
        progress += Math.random() * 15 + 5; // 5-20% 증가
        
        if (progress >= 95) {
            progress = 95; // 95%에서 대기
        }
        
        DOM_ELEMENTS.searchProgress.style.width = `${progress}%`;
        DOM_ELEMENTS.searchProgress.setAttribute('aria-valuenow', progress);
        
        if (progress >= 95) {
            clearInterval(interval);
            
            // 완료 시 100%로 설정
            setTimeout(() => {
                DOM_ELEMENTS.searchProgress.style.width = '100%';
                DOM_ELEMENTS.searchProgress.setAttribute('aria-valuenow', 100);
            }, 1000);
        }
    }, 200);
    
    // 안전장치: 10초 후 강제 완료
    setTimeout(() => {
        clearInterval(interval);
        DOM_ELEMENTS.searchProgress.style.width = '100%';
        DOM_ELEMENTS.searchProgress.setAttribute('aria-valuenow', 100);
    }, 10000);
}

// 프로그레스 바 초기화
function resetProgressBar() {
    if (!DOM_ELEMENTS.searchProgress) return;
    
    DOM_ELEMENTS.searchProgress.style.width = '0%';
    DOM_ELEMENTS.searchProgress.setAttribute('aria-valuenow', 0);
}

// 페이지 로드 완료 시 로딩 애니메이션 숨김 (Django에서 결과를 반환한 경우)
window.addEventListener('load', function() {
    // 페이지에 검색 결과가 있거나 오류가 있으면 로딩 숨김
    const hasResults = document.querySelector('.movies-section') || document.querySelector('.alert-danger');
    if (hasResults) {
        setTimeout(() => {
            hideSearchLoadingAnimation();
        }, 500);
    }
});

// Escape 키로 로딩 애니메이션 취소
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape' && DOM_ELEMENTS.searchLoadingOverlay && !DOM_ELEMENTS.searchLoadingOverlay.classList.contains('d-none')) {
        hideSearchLoadingAnimation();
        showToast('검색이 취소되었습니다.', 'info');
    }
});