/* ===================================================================
   TheSysM Website JavaScript - 통합 버전 (커스터마이징 포함)
   Revolutionary AI-Collaborative Development
   =================================================================== */

// === 설정 옵션 ===
const THESYSM_CONFIG = {
    // SVG 애니메이션 설정
    svg: {
        animationInterval: 13000,    // 애니메이션 간격 (ms)
        animationDuration: 8000,     // 애니메이션 지속시간 (ms)
        initialDelay: 3000,          // 첫 애니메이션 딜레이 (ms)
        bouncyChance: 0.5,           // 바운시 애니메이션 확률
        clickCooldown: 1000,         // 클릭 후 쿨다운 (ms)
    },
    
    // 말풍선 설정
    speechBubble: {
        text: 'Click Me!',           // 말풍선 텍스트
        showDelay: 1500,             // 나타나는 딜레이 (ms)
        bounceStartDelay: 2000,      // 바운스 시작 딜레이 (ms)
        pulseStartDelay: 4000,       // 펄스 시작 딜레이 (ms)
        offsetY: 15,                 // SVG 위쪽 여백 (px)
    },
    
    // 네비게이션 설정
    navigation: {
        targetUrl: '/movie/',        // 클릭 시 이동할 URL
        celebrationDelay: 800,       // 축하 메시지 후 이동 딜레이 (ms)
        celebrationMessage: '🎉 Navigating to Movie Search!',
    },
    
    // 반응형 설정
    responsive: {
        mobile: {
            svgSize: 60,             // 모바일 SVG 크기 (px)
            bubbleFontSize: 11,      // 모바일 말풍선 폰트 크기 (px)
        },
        tablet: {
            svgSize: 80,             // 태블릿 SVG 크기 (px)
            bubbleFontSize: 12,      // 태블릿 말풍선 폰트 크기 (px)
        },
        desktop: {
            svgSize: 100,            // 데스크톱 SVG 크기 (px)
            bubbleFontSize: 14,      // 데스크톱 말풍선 폰트 크기 (px)
        }
    }
};

// 다양한 말풍선 메시지
const SPEECH_MESSAGES = [
    'Click Me!',
    'Try Movie Search!',
    'Discover Films!',
    'Let\'s Go!',
    'Adventure Awaits!',
    'Click Here!',
    'Movie Time!',
    'Start Exploring!'
];

// === INITIALIZATION ===
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 TheSysM Website Initialized');
    initializeWebsite();
});

function initializeWebsite() {
    // Remove loading screen
    setTimeout(() => {
        const loading = document.getElementById('loading');
        if (loading) {
            loading.classList.add('hide');
            setTimeout(() => {
                loading.style.display = 'none';
            }, 500);
        }
    }, 1000);

    // Initialize scroll effects
    initializeScrollEffects();
    
    // Initialize navigation
    initializeNavigation();
    
    // Initialize animations
    initializeAnimations();

    // Initialize chat functionality
    initializeChat();

    // Initialize floating SVG animation (향상된 버전)
    initializeFloatingSvgAdvanced();
}

// === NAVIGATION EFFECTS ===
function initializeNavigation() {
    const navbar = document.getElementById('navbar');
    
    // Navbar scroll effect
    window.addEventListener('scroll', function() {
        if (navbar) {
            if (window.scrollY > 100) {
                navbar.classList.add('scrolled');
            } else {
                navbar.classList.remove('scrolled');
            }
        }
    });

    // Smooth scrolling for navigation links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target && navbar) {
                const navHeight = navbar.offsetHeight;
                const targetPosition = target.offsetTop - navHeight;
                window.scrollTo({
                    top: targetPosition,
                    behavior: 'smooth'
                });
            }
        });
    });

    // Mobile menu functionality
    const mobileMenuBtn = document.getElementById('mobileMenuBtn');
    const navLinks = document.querySelector('.nav-links');
    
    if (mobileMenuBtn && navLinks) {
        mobileMenuBtn.addEventListener('click', function() {
            navLinks.style.display = navLinks.style.display === 'flex' ? 'none' : 'flex';
        });
    }
}

// === SCROLL ANIMATIONS ===
function initializeScrollEffects() {
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };

    const observer = new IntersectionObserver(function(entries) {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
            }
        });
    }, observerOptions);

    // Observe all elements with fade-in class
    document.querySelectorAll('.fade-in').forEach(el => {
        observer.observe(el);
    });
}

// === INTERACTIVE ANIMATIONS ===
function initializeAnimations() {
    // Service cards hover effects
    document.querySelectorAll('.service-item').forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-15px) scale(1.02)';
        });
        
        card.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0) scale(1)';
        });
    });

    // Button pulse effect on hover
    document.querySelectorAll('.btn').forEach(btn => {
        btn.addEventListener('mouseenter', function() {
            this.style.animation = 'pulse 0.6s ease-in-out';
        });
        
        btn.addEventListener('mouseleave', function() {
            this.style.animation = 'none';
        });
    });
}

// === UTILITY FUNCTIONS ===
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: var(--primary-purple);
        color: white;
        padding: 1rem 1.5rem;
        border-radius: 10px;
        box-shadow: var(--shadow-glow);
        z-index: 10000;
        animation: slideInRight 0.3s ease;
    `;
    toast.textContent = message;
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.style.animation = 'slideOutRight 0.3s ease forwards';
        setTimeout(() => {
            if (document.body.contains(toast)) {
                document.body.removeChild(toast);
            }
        }, 300);
    }, 3000);
}

// === FLOATING SVG ANIMATION (향상된 버전) ===
function initializeFloatingSvgAdvanced() {
    const floatingSvg = document.getElementById('floatingSvg');
    
    if (!floatingSvg) {
        console.warn('Floating SVG element not found');
        return;
    }

    let animationTimeout;
    let isAnimating = false;
    let speechBubble = null;
    let clickCooldown = false;

    // 랜덤 메시지 선택
    function getRandomMessage() {
        return SPEECH_MESSAGES[Math.floor(Math.random() * SPEECH_MESSAGES.length)];
    }

    // 디바이스 타입 감지
    function getDeviceType() {
        const width = window.innerWidth;
        if (width <= 480) return 'mobile';
        if (width <= 1024) return 'tablet';
        return 'desktop';
    }

    // 반응형 크기 적용
    function applyResponsiveSettings() {
        const deviceType = getDeviceType();
        const settings = THESYSM_CONFIG.responsive[deviceType];
        
        floatingSvg.style.width = settings.svgSize + 'px';
        floatingSvg.style.height = settings.svgSize + 'px';
        
        if (speechBubble) {
            speechBubble.style.fontSize = settings.bubbleFontSize + 'px';
        }
    }

    // 향상된 말풍선 생성
    function createAdvancedSpeechBubble() {
        if (speechBubble) {
            return speechBubble;
        }

        speechBubble = document.createElement('div');
        speechBubble.className = 'speech-bubble';
        speechBubble.textContent = getRandomMessage();
        document.body.appendChild(speechBubble);
        
        // 반응형 설정 적용
        applyResponsiveSettings();
        
        return speechBubble;
    }

    // 말풍선 위치 업데이트
    function updateSpeechBubblePosition() {
        if (!speechBubble || !isAnimating) return;

        const svgRect = floatingSvg.getBoundingClientRect();
        const bubbleWidth = speechBubble.offsetWidth;
        const bubbleHeight = speechBubble.offsetHeight;

        speechBubble.style.left = (svgRect.left + svgRect.width / 2 - bubbleWidth / 2) + 'px';
        speechBubble.style.top = (svgRect.top - bubbleHeight - THESYSM_CONFIG.speechBubble.offsetY) + 'px';
    }

    // 말풍선 표시 (향상된 버전)
    function showAdvancedSpeechBubble() {
        const bubble = createAdvancedSpeechBubble();
        updateSpeechBubblePosition();
        
        // 단계별 애니메이션
        setTimeout(() => {
            bubble.classList.add('show');
        }, THESYSM_CONFIG.speechBubble.showDelay);

        setTimeout(() => {
            bubble.classList.add('bounce');
        }, THESYSM_CONFIG.speechBubble.bounceStartDelay);

        setTimeout(() => {
            bubble.classList.remove('bounce');
            bubble.classList.add('pulse');
        }, THESYSM_CONFIG.speechBubble.pulseStartDelay);
    }

    // 말풍선 숨기기
    function hideSpeechBubble() {
        if (speechBubble) {
            speechBubble.classList.remove('show', 'bounce', 'pulse');
            setTimeout(() => {
                if (speechBubble && document.body.contains(speechBubble)) {
                    document.body.removeChild(speechBubble);
                    speechBubble = null;
                }
            }, 300);
        }
    }

    // 랜덤 Y 위치 계산
    function getRandomYPosition() {
        const minY = window.innerHeight * 0.1;
        const maxY = window.innerHeight * 0.9;
        return Math.random() * (maxY - minY) + minY;
    }

    // 향상된 애니메이션 시작
    function startAdvancedFloatingAnimation() {
        if (isAnimating) return;
        
        isAnimating = true;
        
        // 랜덤 Y 위치 설정
        const randomY = getRandomYPosition();
        floatingSvg.style.top = randomY + 'px';
        
        // 애니메이션 타입 선택
        const isBouncy = Math.random() > (1 - THESYSM_CONFIG.svg.bouncyChance);
        floatingSvg.className = `floating-svg active ${isBouncy ? 'bouncy' : ''}`;
        
        // 말풍선 표시
        showAdvancedSpeechBubble();

        // 위치 업데이트 간격
        const positionUpdateInterval = setInterval(() => {
            if (isAnimating) {
                updateSpeechBubblePosition();
            } else {
                clearInterval(positionUpdateInterval);
            }
        }, 50);
        
        // 애니메이션 종료
        animationTimeout = setTimeout(() => {
            isAnimating = false;
            floatingSvg.classList.remove('active', 'bouncy');
            hideSpeechBubble();
            clearInterval(positionUpdateInterval);
            
            // 다음 애니메이션 예약
            setTimeout(() => {
                startAdvancedFloatingAnimation();
            }, THESYSM_CONFIG.svg.animationInterval - THESYSM_CONFIG.svg.animationDuration);
        }, THESYSM_CONFIG.svg.animationDuration);
    }

    // 향상된 클릭 핸들러
    function handleAdvancedClick() {
        if (clickCooldown) return;
        
        clickCooldown = true;
        setTimeout(() => { clickCooldown = false; }, THESYSM_CONFIG.svg.clickCooldown);

        if (isAnimating) {
            // 클릭 효과
            floatingSvg.style.transform += ' scale(1.2)';
            setTimeout(() => {
                floatingSvg.style.transform = floatingSvg.style.transform.replace(' scale(1.2)', '');
            }, 200);
            
            // 축하 메시지
            showToast(THESYSM_CONFIG.navigation.celebrationMessage, 'success');
            
            // 페이지 이동
            setTimeout(() => {
                const currentHost = window.location.origin;
                window.location.href = currentHost + THESYSM_CONFIG.navigation.targetUrl;
            }, THESYSM_CONFIG.navigation.celebrationDelay);
        }
    }

    // 이벤트 리스너 등록
    floatingSvg.addEventListener('click', handleAdvancedClick);
    
    // 말풍선 클릭 이벤트 (이벤트 위임)
    document.addEventListener('click', (e) => {
        if (speechBubble && speechBubble.contains(e.target)) {
            handleAdvancedClick();
        }
    });

    // 반응형 이벤트
    window.addEventListener('resize', () => {
        if (!isAnimating) {
            const randomY = getRandomYPosition();
            floatingSvg.style.top = randomY + 'px';
        } else {
            updateSpeechBubblePosition();
        }
        applyResponsiveSettings();
    });

    // 호버 이벤트
    floatingSvg.addEventListener('mouseenter', () => {
        if (isAnimating) {
            floatingSvg.style.animationPlayState = 'paused';
            if (speechBubble) {
                speechBubble.style.animationPlayState = 'paused';
            }
        }
    });

    floatingSvg.addEventListener('mouseleave', () => {
        if (isAnimating) {
            floatingSvg.style.animationPlayState = 'running';
            if (speechBubble) {
                speechBubble.style.animationPlayState = 'running';
            }
        }
    });

    // 초기 설정 적용
    applyResponsiveSettings();
    
    // 첫 애니메이션 시작
    setTimeout(() => {
        startAdvancedFloatingAnimation();
    }, THESYSM_CONFIG.svg.initialDelay);
}

// === 설정 변경 헬퍼 함수들 ===
function updateSpeechBubbleText(newText) {
    THESYSM_CONFIG.speechBubble.text = newText;
    SPEECH_MESSAGES[0] = newText; // 기본 메시지 업데이트
}

function updateNavigationUrl(newUrl) {
    THESYSM_CONFIG.navigation.targetUrl = newUrl;
}

function updateAnimationInterval(intervalMs) {
    THESYSM_CONFIG.svg.animationInterval = intervalMs;
}

// === RESPONSIVE CHAT FUNCTIONALITY ===
function initializeChat() {
    const chatFloatingBtn = document.getElementById('chatFloatingBtn');
    const chatModal = document.getElementById('chatModal');
    const closeChat = document.getElementById('closeChat');
    const minimizeChat = document.getElementById('minimizeChat');
    const sendMessage = document.getElementById('sendMessage');
    const messageInput = document.getElementById('messageInput');
    const chatMessages = document.getElementById('chatMessages');

    if (!chatFloatingBtn || !chatModal) {
        console.warn('Chat elements not found');
        return;
    }

    let isChatOpen = false;
    let isMinimized = false;

    // Get responsive height based on viewport
    function getResponsiveHeight() {
        const vh = window.innerHeight;
        const isScrolled = window.scrollY > 100;
        const isMobile = window.innerWidth <= 768;
        
        if (isMobile) {
            return isScrolled ? 
                `calc(100vh - 70px)` : 
                `calc(100vh - 80px)`;
        } else {
            return isScrolled ? 
                `min(70vh, 600px)` : 
                `min(80vh, 700px)`;
        }
    }

    // Update modal size based on current state
    function updateModalSize() {
        if (!isMinimized && isChatOpen) {
            chatModal.style.height = getResponsiveHeight();
        }
    }

    // Toggle chat modal
    chatFloatingBtn.addEventListener('click', function() {
        if (!isChatOpen) {
            openChat();
        } else {
            if (closeChat) closeChat.click();
        }
    });

    // Open chat
    function openChat() {
        chatModal.classList.add('show');
        isChatOpen = true;
        isMinimized = false;
        chatFloatingBtn.style.display = 'none';
        updateModalSize();
        if (messageInput) messageInput.focus();
    }

    // Close chat
    if (closeChat) {
        closeChat.addEventListener('click', function() {
            chatModal.classList.remove('show');
            isChatOpen = false;
            isMinimized = false;
            chatFloatingBtn.style.display = 'flex';
        });
    }

    // Minimize chat
    if (minimizeChat) {
        minimizeChat.addEventListener('click', function() {
            if (!isMinimized) {
                chatModal.style.height = '60px';
                if (chatMessages) chatMessages.style.display = 'none';
                const chatInput = document.querySelector('.chat-input');
                if (chatInput) chatInput.style.display = 'none';
                isMinimized = true;
                minimizeChat.innerHTML = '🔳';
            } else {
                if (chatMessages) chatMessages.style.display = 'block';
                const chatInput = document.querySelector('.chat-input');
                if (chatInput) chatInput.style.display = 'flex';
                isMinimized = false;
                minimizeChat.innerHTML = '⧄';
                updateModalSize();
            }
        });
    }

    // Send message functionality
    function sendUserMessage() {
        if (!messageInput || !chatMessages) return;
        
        const messageText = messageInput.value.trim();
        if (messageText) {
            const messageDiv = document.createElement('div');
            messageDiv.classList.add('message', 'sent');
            messageDiv.innerHTML = `
                <div class="message-content">
                    <p>${messageText}</p>
                    <span class="timestamp">${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                </div>
            `;
            chatMessages.appendChild(messageDiv);
            messageInput.value = '';
            messageDiv.scrollIntoView({ behavior: 'smooth' });

            // Auto-reply after a short delay
            setTimeout(() => {
                sendAutoReply(messageText);
            }, 1000 + Math.random() * 2000);
        }
    }

    // Auto-reply system
    function sendAutoReply(userMessage) {
        if (!chatMessages) return;
        
        const replies = [
            "Thanks for your interest! I'll connect you with ganzsKang for detailed information about our AI-collaborative methodology.",
            "Great question! Our 11-stage process can transform your development workflow. Would you like to schedule a consultation?",
            "I'd be happy to help you understand our revolutionary approach. Contact ganzsKang at acskang@gmail.com for personalized guidance.",
            "That's exactly what our methodology addresses! Let me arrange a consultation to show you the 10x productivity gains.",
            "Perfect timing! Our AI-collaborative development approach can solve that challenge. Shall we set up a call?"
        ];

        const reply = replies[Math.floor(Math.random() * replies.length)];
        
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message', 'received');
        messageDiv.innerHTML = `
            <img src="static/img/sandiegoKang.jpg" alt="GK" class="user-avatar">
            <div class="message-content">
                <p>${reply}</p>
                <span class="timestamp">${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
            </div>
        `;
        chatMessages.appendChild(messageDiv);
        messageDiv.scrollIntoView({ behavior: 'smooth' });
    }

    // Send message on button click
    if (sendMessage) {
        sendMessage.addEventListener('click', sendUserMessage);
    }

    // Send message on Enter key
    if (messageInput) {
        messageInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                sendUserMessage();
            }
        });
    }

    // Handle scroll effects for chat
    window.addEventListener('scroll', function() {
        const scrolled = window.scrollY > 100;
        
        if (scrolled) {
            chatFloatingBtn.classList.add('scrolled');
            if (isChatOpen) {
                chatModal.classList.add('scrolled');
                updateModalSize();
            }
        } else {
            chatFloatingBtn.classList.remove('scrolled');
            if (isChatOpen) {
                chatModal.classList.remove('scrolled');
                updateModalSize();
            }
        }
    });

    // Handle resize events for responsive behavior
    window.addEventListener('resize', function() {
        if (isChatOpen) {
            updateModalSize();
        }
    });

    // Add floating animation to chat button
    setInterval(() => {
        if (!isChatOpen && Math.random() > 0.7) {
            chatFloatingBtn.style.animation = 'pulse 0.6s ease-in-out';
            setTimeout(() => {
                chatFloatingBtn.style.animation = 'none';
            }, 600);
        }
    }, 5000);
}

// === CONSOLE BRANDING ===
console.log('%c🚀 TheSysM - Revolutionary AI-Collaborative Development', 'color: #a3a3ff; font-size: 18px; font-weight: bold;');
console.log('%cInterested in our methodology? Contact ganzsKang at acskang@gmail.com', 'color: #8b8bff; font-size: 14px;');

// === ERROR HANDLING ===
window.addEventListener('error', function(e) {
    console.error('Website error:', e.error);
});

// === PERFORMANCE MONITORING ===
window.addEventListener('load', function() {
    // Log performance metrics
    if ('performance' in window && 'timing' in performance) {
        const loadTime = performance.timing.loadEventEnd - performance.timing.navigationStart;
        console.log(`%cWebsite loaded in ${loadTime}ms`, 'color: #a3a3ff; font-weight: bold;');
    }
});

// === 전역 설정 함수들 (브라우저 콘솔에서 사용 가능) ===
window.TheSysMConfig = {
    updateText: updateSpeechBubbleText,
    updateUrl: updateNavigationUrl,
    updateInterval: updateAnimationInterval,
    getConfig: () => THESYSM_CONFIG,
    setConfig: (newConfig) => Object.assign(THESYSM_CONFIG, newConfig)
};

// === FILE DATA FUNCTIONS (Legacy Support) ===
var gk_isXlsx = false;
var gk_xlsxFileLookup = {};
var gk_fileData = {};

function filledCell(cell) {
    return cell !== '' && cell != null;
}

function loadFileData(filename) {
    if (typeof XLSX === 'undefined') {
        console.warn('XLSX library not loaded');
        return gk_fileData[filename] || "";
    }

    if (gk_isXlsx && gk_xlsxFileLookup[filename]) {
        try {
            var workbook = XLSX.read(gk_fileData[filename], { type: 'base64' });
            var firstSheetName = workbook.SheetNames[0];
            var worksheet = workbook.Sheets[firstSheetName];

            var jsonData = XLSX.utils.sheet_to_json(worksheet, { header: 1, blankrows: false, defval: '' });
            var filteredData = jsonData.filter(row => row.some(filledCell));

            var headerRowIndex = filteredData.findIndex((row, index) =>
                row.filter(filledCell).length >= filteredData[index + 1]?.filter(filledCell).length
            );
            
            if (headerRowIndex === -1 || headerRowIndex > 25) {
                headerRowIndex = 0;
            }

            var csv = XLSX.utils.aoa_to_sheet(filteredData.slice(headerRowIndex));
            csv = XLSX.utils.sheet_to_csv(csv, { header: 1 });
            return csv;
        } catch (e) {
            console.error('Error processing XLSX file:', e);
            return "";
        }
    }
    return gk_fileData[filename] || "";
}

// === EXPORT FOR MODULE USAGE ===
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        initializeWebsite,
        initializeNavigation,
        initializeScrollEffects,
        initializeAnimations,
        initializeChat,
        initializeFloatingSvgAdvanced,
        showToast,
        loadFileData,
        THESYSM_CONFIG,
        updateSpeechBubbleText,
        updateNavigationUrl,
        updateAnimationInterval
    };
}