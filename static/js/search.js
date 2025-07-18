// search.js - 검색 폼 & 입력 처리

// ===== 검색 모듈 초기화 =====
function initializeSearch() {
    console.log('🔍 검색 모듈 초기화 시작...');
    
    // 반응형 검색 폼 초기화
    initializeResponsiveSearch();
    
    // 검색 기록 로드
    loadSearchHistory();
    
    // 플레이스홀더 애니메이션 시작
    setTimeout(animatePlaceholder, 3000);
    
    console.log('✅ 검색 모듈 초기화 완료');
}

// ===== 반응형 검색 폼 =====
function initializeResponsiveSearch() {
    // 현재 활성 입력창 가져오기
    function getActiveSearchInput() {
        const isDesktop = window.innerWidth >= 768;
        return isDesktop ? DOM_ELEMENTS.desktopInput : DOM_ELEMENTS.mobileInput;
    }
    
    // 입력값 동기화
    function syncInputs(sourceValue) {
        console.log('🔄 입력값 동기화:', sourceValue);
        
        if (DOM_ELEMENTS.unifiedInput) DOM_ELEMENTS.unifiedInput.value = sourceValue;
        if (DOM_ELEMENTS.desktopInput) DOM_ELEMENTS.desktopInput.value = sourceValue;
        if (DOM_ELEMENTS.mobileInput) DOM_ELEMENTS.mobileInput.value = sourceValue;
        
        updateClearButtons(sourceValue);
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
    
    // 폼 제출 이벤트
    if (DOM_ELEMENTS.searchForm) {
        DOM_ELEMENTS.searchForm.addEventListener('submit', function(e) {
            console.log('📝 폼 제출 시작');
            
            const activeInput = getActiveSearchInput();
            const value = activeInput?.value?.trim() || '';
            
            if (!value) {
                e.preventDefault();
                activeInput?.focus();
                if (typeof showToast === 'function') {
                    showToast('검색어를 입력해주세요.', 'warning');
                }
                return false;
            }
            
            // 최종 동기화
            syncInputs(value);
            
            // 로딩 애니메이션 시작 (새로운 검색어인 경우)
            if (typeof isNewSearchQuery === 'function' && isNewSearchQuery(value)) {
                if (typeof showSearchLoadingAnimation === 'function') {
                    showSearchLoadingAnimation(value);
                }
            }
            
            // 로딩 상태 표시
            const submitButtons = this.querySelectorAll('button[type="submit"]');
            submitButtons.forEach(btn => {
                btn.disabled = true;
                const originalText = btn.innerHTML;
                btn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>검색 중...';
                
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
    if (initialValue) {
        syncInputs(initialValue);
    }
    
    // 자동 포커스 (데스크톱에서만)
    if (window.innerWidth >= 768 && DOM_ELEMENTS.desktopInput && !initialValue) {
        setTimeout(() => {
            DOM_ELEMENTS.desktopInput.focus();
        }, 100);
    }
}

// ===== 검색 기록 관리 =====
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

// 새로운 검색어인지 확인
function isNewSearchQuery(query) {
    return !APP_STATE.searchHistory.includes(query.trim().toLowerCase());
}

// ===== 플레이스홀더 애니메이션 =====
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

// ===== 검색 제안 시스템 =====
function hideSuggestions() {
    const searchSuggestions = document.getElementById('search-suggestions');
    if (searchSuggestions) {
        searchSuggestions.classList.add('d-none');
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
}// search.js - 검색 폼 & 입력 처리

// ===== 검색 모듈 초기화 =====
function initializeSearch() {
    console.log('🔍 검색 모듈 초기화 시작...');
    
    // 반응형 검색 폼 초기화
    initializeResponsiveSearch();
    
    // 검색 기록 로드
    loadSearchHistory();
    
    // 플레이스홀더 애니메이션 시작
    setTimeout(animatePlaceholder, 3000);
    
    console.log('✅ 검색 모듈 초기화 완료');
}

// ===== 반응형 검색 폼 =====
function initializeResponsiveSearch() {
    // 현재 활성 입력창 가져오기
    function getActiveSearchInput() {
        const isDesktop = window.innerWidth >= 768;
        return isDesktop ? DOM_ELEMENTS.desktopInput : DOM_ELEMENTS.mobileInput;
    }
    
    // 입력값 동기화
    function syncInputs(sourceValue) {
        console.log('🔄 입력값 동기화:', sourceValue);
        
        if (DOM_ELEMENTS.unifiedInput) DOM_ELEMENTS.unifiedInput.value = sourceValue;
        if (DOM_ELEMENTS.desktopInput) DOM_ELEMENTS.desktopInput.value = sourceValue;
        if (DOM_ELEMENTS.mobileInput) DOM_ELEMENTS.mobileInput.value = sourceValue;
        
        updateClearButtons(sourceValue);
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
    
    // 폼 제출 이벤트
    if (DOM_ELEMENTS.searchForm) {
        DOM_ELEMENTS.searchForm.addEventListener('submit', function(e) {
            console.log('📝 폼 제출 시작');
            
            const activeInput = getActiveSearchInput();
            const value = activeInput?.value?.trim() || '';
            
            if (!value) {
                e.preventDefault();
                activeInput?.focus();
                if (typeof showToast === 'function') {
                    showToast('검색어를 입력해주세요.', 'warning');
                }
                return false;
            }
            
            // 최종 동기화
            syncInputs(value);
            
            // 로딩 애니메이션 시작 (새로운 검색어인 경우)
            if (typeof isNewSearchQuery === 'function' && isNewSearchQuery(value)) {
                if (typeof showSearchLoadingAnimation === 'function') {
                    showSearchLoadingAnimation(value);
                }
            }
            
            // 로딩 상태 표시
            const submitButtons = this.querySelectorAll('button[type="submit"]');
            submitButtons.forEach(btn => {
                btn.disabled = true;
                const originalText = btn.innerHTML;
                btn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>검색 중...';
                
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
    if (initialValue) {
        syncInputs(initialValue);
    }
    
    // 자동 포커스 (데스크톱에서만)
    if (window.innerWidth >= 768 && DOM_ELEMENTS.desktopInput && !initialValue) {
        setTimeout(() => {
            DOM_ELEMENTS.desktopInput.focus();
        }, 100);
    }
}

// ===== 검색 기록 관리 =====
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

// 새로운 검색어인지 확인
function isNewSearchQuery(query) {
    return !APP_STATE.searchHistory.includes(query.trim().toLowerCase());
}

// ===== 플레이스홀더 애니메이션 =====
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

// ===== 검색 제안 시스템 =====
function hideSuggestions() {
    const searchSuggestions = document.getElementById('search-suggestions');
    if (searchSuggestions) {
        searchSuggestions.classList.add('d-none');
    }
}

// ===== 인기 검색어 =====
async function showPopularSearches() {
    if (!DOM_ELEMENTS.popularSection || !DOM_ELEMENTS.popularContainer) return;