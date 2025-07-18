// ui.js - UI 인터랙션 & 이벤트

// ===== UI 모듈 초기화 =====
function initializeUI() {
    console.log('🎨 UI 모듈 초기화 시작...');
    
    // 이벤트 리스너 설정
    initializeEventListeners();
    
    // 네트워크 모니터링
    initializeNetworkMonitoring();
    
    // 번역 통계 초기화
    initializeTranslationStats();
    
    // 포스터 이미지 초기화
    initializePosterImages();
    
    console.log('✅ UI 모듈 초기화 완료');
}

// ===== 이벤트 리스너 설정 =====
function initializeEventListeners() {
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

// ===== UI 인터랙션 함수들 =====
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