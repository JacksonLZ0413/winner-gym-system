// 健身房私教预约系统 - 前端脚本

document.addEventListener('DOMContentLoaded', function() {
    // 自动隐藏提示信息
    setTimeout(function() {
        const alerts = document.querySelectorAll('.alert');
        alerts.forEach(function(alert) {
            alert.style.transition = 'opacity 0.5s';
            alert.style.opacity = '0';
            setTimeout(function() {
                alert.remove();
            }, 500);
        });
    }, 5000);

    // 初始化移动端菜单
    initMobileMenu();
});

// 确认删除/取消操作
function confirmAction(message) {
    return confirm(message || '确定要执行此操作吗？');
}

// 显示加载状态
function showLoading(element) {
    if (element) {
        element.disabled = true;
        element.dataset.originalText = element.textContent;
        element.textContent = '加载中...';
    }
}

// 隐藏加载状态
function hideLoading(element) {
    if (element && element.dataset.originalText) {
        element.disabled = false;
        element.textContent = element.dataset.originalText;
    }
}

// 表单验证
function validateForm(form) {
    const required = form.querySelectorAll('[required]');
    let isValid = true;
    
    required.forEach(function(field) {
        if (!field.value.trim()) {
            field.style.borderColor = '#dc3545';
            isValid = false;
        } else {
            field.style.borderColor = '#e8e8e8';
        }
    });
    
    return isValid;
}

// 日期格式化
function formatDate(dateStr) {
    const date = new Date(dateStr);
    const options = { year: 'numeric', month: 'long', day: 'numeric' };
    return date.toLocaleDateString('zh-CN', options);
}

// 时间格式化
function formatTime(timeStr) {
    return timeStr + ':00';
}

// 获取星期几
function getWeekday(dateStr) {
    const date = new Date(dateStr);
    const weekdays = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'];
    return weekdays[date.getDay()];
}

// 相对时间显示
function timeAgo(dateStr) {
    const date = new Date(dateStr);
    const now = new Date();
    const diff = now - date;
    
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);
    
    if (minutes < 1) return '刚刚';
    if (minutes < 60) return minutes + '分钟前';
    if (hours < 24) return hours + '小时前';
    if (days < 7) return days + '天前';
    return formatDate(dateStr);
}

// 评分交互
function initRatingStars() {
    const ratingContainers = document.querySelectorAll('.rating-select');
    
    ratingContainers.forEach(function(container) {
        const stars = container.querySelectorAll('.rating-star');
        const input = container.querySelector('input[type="hidden"]');
        
        stars.forEach(function(star, index) {
            star.addEventListener('click', function() {
                input.value = index + 1;
                updateStars(stars, index + 1);
            });
            
            star.addEventListener('mouseenter', function() {
                updateStars(stars, index + 1);
            });
        });
        
        container.addEventListener('mouseleave', function() {
            updateStars(stars, parseInt(input.value) || 0);
        });
    });
}

function updateStars(stars, rating) {
    stars.forEach(function(star, index) {
        if (index < rating) {
            star.textContent = '★';
            star.style.color = '#ffc107';
        } else {
            star.textContent = '☆';
            star.style.color = '#ddd';
        }
    });
}

// 教练选择时间段的交互
function initTimeSlotSelection() {
    const timeSlots = document.querySelectorAll('.time-slot:not(.disabled)');
    
    timeSlots.forEach(function(slot) {
        slot.addEventListener('click', function() {
            if (this.classList.contains('disabled')) return;
            
            timeSlots.forEach(function(s) {
                s.classList.remove('selected');
            });
            
            this.classList.add('selected');
            
            const hiddenInput = document.querySelector('input[name="time_slot"]');
            if (hiddenInput) {
                hiddenInput.value = this.dataset.time;
            }
        });
    });
}

// 移动端菜单切换
function initMobileMenu() {
    const menuBtn = document.getElementById('mobileToggle');
    const nav = document.getElementById('navLinks');

    if (menuBtn && nav) {
        menuBtn.addEventListener('click', function() {
            nav.classList.toggle('active');
        });
    }
}

// 滚动到顶部
function scrollToTop() {
    window.scrollTo({
        top: 0,
        behavior: 'smooth'
    });
}

// 导出函数供其他脚本使用
window.GymApp = {
    confirmAction: confirmAction,
    showLoading: showLoading,
    hideLoading: hideLoading,
    validateForm: validateForm,
    formatDate: formatDate,
    formatTime: formatTime,
    getWeekday: getWeekday,
    timeAgo: timeAgo,
    scrollToTop: scrollToTop
};
