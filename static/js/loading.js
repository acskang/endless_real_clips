// loading.js - 로딩 애니메이션 시스템

// ===== 로딩 모듈 초기화 =====
function initializeLoading() {
    console.log('🎬 로딩 모듈 초기화 시작...');
    
    // 페이지 로드 완료 시 로딩 애니메이션 숨김
    window.addEventListener('load', function() {
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
            if (typeof showToast === 'function') {
                showToast('검색이 취소되었습니다.', 'info');
            }
        }
    });
    
    console.log('✅ 로딩 모듈 초기화 완료');
}

// ===== 로딩 애니메이션 표시 =====
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

// ===== 로딩 애니메이션 숨김 =====
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

// ===== 로딩 단계 애니메이션 =====
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

// ===== 로딩 단계 초기화 =====
function resetLoadingSteps() {
    const stepIds = ['step-search', 'step-fetch', 'step-process', 'step-save'];
    stepIds.forEach(id => {
        const step = document.getElementById(id);
        if (step) {
            step.classList.remove('active', 'completed');
        }
    });
}

// ===== 프로그레스 바 애니메이션 =====
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
        if (DOM_ELEMENTS.searchProgress) {
            DOM_ELEMENTS.searchProgress.style.width = '100%';
            DOM_ELEMENTS.searchProgress.setAttribute('aria-valuenow', 100);
        }
    }, 10000);
}

// ===== 프로그레스 바 초기화 =====
function resetProgressBar() {
    if (!DOM_ELEMENTS.searchProgress) return;
    
    DOM_ELEMENTS.searchProgress.style.width = '0%';
    DOM_ELEMENTS.searchProgress.setAttribute('aria-valuenow', 0);
}