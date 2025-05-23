/**
 * BLACK COMBAT LAND
 * 클라이언트 측 스크립트
 */

// 문서가 준비되면 실행
document.addEventListener('DOMContentLoaded', function() {
    // 경고창 자동 닫기 (5초 후)
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(function(alert) {
        setTimeout(function() {
            // Bootstrap 경고창 닫기
            const closeButton = alert.querySelector('.btn-close');
            if (closeButton) {
                closeButton.click();
            }
        }, 5000);
    });

    // 이미지 미리보기 기능 (게시글 작성/수정 페이지)
    const imageInput = document.getElementById('image');
    const imagePreview = document.getElementById('imagePreview');
    
    if (imageInput && imagePreview) {
        imageInput.addEventListener('change', function() {
            if (this.files && this.files[0]) {
                const reader = new FileReader();
                
                reader.onload = function(e) {
                    imagePreview.innerHTML = `<img src="${e.target.result}" class="img-fluid mt-2" style="max-height: 200px;">`;
                }
                
                reader.readAsDataURL(this.files[0]);
            } else {
                imagePreview.innerHTML = '';
            }
        });
    }

    // 게시글 삭제 확인
    const deleteForm = document.getElementById('deleteForm');
    if (deleteForm) {
        deleteForm.addEventListener('submit', function(e) {
            if (!confirm('정말 삭제하시겠습니까?')) {
                e.preventDefault();
            }
        });
    }

    // 페이지네이션 활성화
    const currentPage = new URLSearchParams(window.location.search).get('page') || 1;
    const pageLinks = document.querySelectorAll('.pagination .page-link');
    
    pageLinks.forEach(function(link) {
        const linkPage = new URLSearchParams(link.getAttribute('href').split('?')[1]).get('page');
        if (linkPage == currentPage) {
            link.parentElement.classList.add('active');
        }
    });

    // VIP 게시글 강조 표시
    const vipPosts = document.querySelectorAll('.post-item.vip');
    vipPosts.forEach(function(post) {
        post.classList.add('vip-highlight');
    });

    // 새 게시글 표시 (1시간 이내 작성)
    const postTimes = document.querySelectorAll('.post-time');
    const now = new Date();
    
    postTimes.forEach(function(timeEl) {
        const postTime = new Date(timeEl.getAttribute('data-time'));
        const timeDiff = now - postTime;
        
        // 1시간 이내 작성된 글
        if (timeDiff < 3600000) {
            const titleEl = timeEl.closest('.post-item').querySelector('.post-title');
            if (titleEl) {
                titleEl.innerHTML += ' <span class="badge bg-danger">NEW</span>';
            }
        }
    });

    // 댓글 입력 글자 수 제한 및 표시
    const commentContent = document.getElementById('commentContent');
    const charCount = document.getElementById('charCount');
    
    if (commentContent && charCount) {
        const maxLength = 500;
        
        commentContent.addEventListener('input', function() {
            const remaining = maxLength - this.value.length;
            charCount.textContent = `${this.value.length}/${maxLength}`;
            
            if (remaining < 0) {
                this.value = this.value.substring(0, maxLength);
                charCount.textContent = `${maxLength}/${maxLength}`;
            }
        });
    }
});

// VIP 배지 표시 함수
function showVipBadge(element) {
    const badge = document.createElement('span');
    badge.className = 'vip-badge';
    badge.textContent = 'VIP';
    element.appendChild(badge);
}

// 문자열 길이 제한 함수
function truncateText(text, maxLength) {
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
}

// CSRF 토큰 설정
$(document).ready(function() {
    var csrftoken = $('meta[name=csrf-token]').attr('content');
    
    $.ajaxSetup({
        beforeSend: function(xhr, settings) {
            if (!/^(GET|HEAD|OPTIONS|TRACE)$/i.test(settings.type)) {
                xhr.setRequestHeader("X-CSRFToken", csrftoken);
            }
        }
    });
    
    // 기존 코드는 그대로 유지
}); 