// ==================== SUBMITA - MAIN JAVASCRIPT ====================
// Professional, Interactive, Modern

// DOM Content Loaded
document.addEventListener('DOMContentLoaded', function() {
    initDarkMode();
    initToastNotifications();
    initFormValidation();
    initSearchFilters();
    initAnimations();
    initMobileMenu();
});


// Demo video player
function playDemoVideo() {
    const poster = document.getElementById('videoPoster');
    const video = document.getElementById('demoVideo');
    
    poster.classList.add('hidden');
    video.classList.remove('hidden');
    video.play();
}

function seekTo(seconds) {
    const video = document.getElementById('demoVideo');
    const poster = document.getElementById('videoPoster');
    
    // Show video if still on poster
    if (!poster.classList.contains('hidden')) {
        poster.classList.add('hidden');
        video.classList.remove('hidden');
    }
    
    video.currentTime = seconds;
    video.play();
    
    // Smooth scroll to video
    video.scrollIntoView({ behavior: 'smooth', block: 'center' });
}


// ==================== DARK MODE ====================
function initDarkMode() {
    const toggleBtn = document.getElementById('darkModeToggle');
    if (!toggleBtn) return;
    
    // Check saved preference
    const savedTheme = localStorage.getItem('theme');
    const systemPrefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    
    if (savedTheme === 'dark' || (!savedTheme && systemPrefersDark)) {
        document.body.classList.add('dark-mode');
        updateDarkModeIcon(true);
    }
    
    toggleBtn.addEventListener('click', function() {
        const isDark = document.body.classList.toggle('dark-mode');
        localStorage.setItem('theme', isDark ? 'dark' : 'light');
        updateDarkModeIcon(isDark);
        showToast(`Dark mode ${isDark ? 'enabled' : 'disabled'}`, 'info');
    });
    
    // Listen for system theme changes
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
        if (!localStorage.getItem('theme')) {
            document.body.classList.toggle('dark-mode', e.matches);
            updateDarkModeIcon(e.matches);
        }
    });
}

function updateDarkModeIcon(isDark) {
    const toggleBtn = document.getElementById('darkModeToggle');
    if (!toggleBtn) return;
    
    const sunIcon = toggleBtn.querySelector('.fa-sun');
    const moonIcon = toggleBtn.querySelector('.fa-moon');
    
    if (sunIcon && moonIcon) {
        if (isDark) {
            sunIcon.style.display = 'none';
            moonIcon.style.display = 'inline-block';
        } else {
            sunIcon.style.display = 'inline-block';
            moonIcon.style.display = 'none';
        }
    }
}

// ==================== TOAST NOTIFICATIONS ====================
function initToastNotifications() {
    // Check for flash messages from server
    const flashMessages = document.querySelectorAll('.flash-message');
    flashMessages.forEach(msg => {
        const type = msg.dataset.type || 'info';
        const message = msg.textContent;
        showToast(message, type);
        msg.remove();
    });
}

function showToast(message, type = 'info') {
    let container = document.getElementById('toastContainer');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toastContainer';
        container.className = 'toast-container';
        document.body.appendChild(container);
    }
    
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    
    let icon = '';
    switch(type) {
        case 'success': icon = '✅'; break;
        case 'danger': icon = '❌'; break;
        case 'warning': icon = '⚠️'; break;
        default: icon = 'ℹ️';
    }
    
    toast.innerHTML = `
        <div class="toast-icon">${icon}</div>
        <div class="toast-content">${message}</div>
        <button class="toast-close" onclick="this.parentElement.remove()">✕</button>
    `;
    
    toast.addEventListener('click', (e) => {
        if (e.target !== toast.querySelector('.toast-close')) {
            toast.remove();
        }
    });
    
    container.appendChild(toast);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        if (toast.parentElement) {
            toast.style.animation = 'fadeOut 0.3s ease';
            setTimeout(() => toast.remove(), 300);
        }
    }, 5000);
}

// ==================== FORM VALIDATION ====================
function initFormValidation() {
    const forms = document.querySelectorAll('form[data-validate]');
    forms.forEach(form => {
        form.addEventListener('submit', validateForm);
    });
}

function validateForm(e) {
    const form = e.target;
    const inputs = form.querySelectorAll('input[required], textarea[required], select[required]');
    let isValid = true;
    
    inputs.forEach(input => {
        if (!input.value.trim()) {
            isValid = false;
            showInputError(input, 'This field is required');
        } else {
            clearInputError(input);
        }
        
        // Email validation
        if (input.type === 'email' && input.value) {
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (!emailRegex.test(input.value)) {
                isValid = false;
                showInputError(input, 'Please enter a valid email address');
            }
        }
        
        // Password confirmation
        if (input.type === 'password' && input.id === 'confirmPassword') {
            const password = document.getElementById('regPassword')?.value;
            if (password && input.value !== password) {
                isValid = false;
                showInputError(input, 'Passwords do not match');
            }
        }
    });
    
    if (!isValid) {
        e.preventDefault();
        showToast('Please fix the errors in the form', 'danger');
    }
}

function showInputError(input, message) {
    input.classList.add('error');
    let errorDiv = input.parentElement.querySelector('.error-message');
    if (!errorDiv) {
        errorDiv = document.createElement('div');
        errorDiv.className = 'error-message text-danger text-sm mt-1';
        input.parentElement.appendChild(errorDiv);
    }
    errorDiv.textContent = message;
}

function clearInputError(input) {
    input.classList.remove('error');
    const errorDiv = input.parentElement.querySelector('.error-message');
    if (errorDiv) errorDiv.remove();
}

// ==================== PASSWORD STRENGTH ====================
function checkPasswordStrength(password) {
    let strength = 0;
    let feedback = [];
    
    if (password.length >= 8) {
        strength++;
    } else {
        feedback.push('At least 8 characters');
    }
    
    if (/[A-Z]/.test(password)) {
        strength++;
    } else {
        feedback.push('Include uppercase letters');
    }
    
    if (/[0-9]/.test(password)) {
        strength++;
    } else {
        feedback.push('Include numbers');
    }
    
    if (/[^A-Za-z0-9]/.test(password)) {
        strength++;
    } else {
        feedback.push('Include special characters');
    }
    
    let level = 'Weak';
    let color = '#EF4444';
    let width = '25%';
    
    if (strength >= 3) {
        level = 'Strong';
        color = '#10B981';
        width = '100%';
    } else if (strength === 2) {
        level = 'Medium';
        color = '#F59E0B';
        width = '66%';
    }
    
    return { level, color, width, feedback };
}

// ==================== SEARCH & FILTERS ====================
function initSearchFilters() {
    const searchInput = document.getElementById('searchInput');
    if (!searchInput) return;
    
    searchInput.addEventListener('input', function() {
        const searchTerm = this.value.toLowerCase();
        const items = document.querySelectorAll('.searchable-item');
        
        items.forEach(item => {
            const text = item.textContent.toLowerCase();
            if (text.includes(searchTerm)) {
                item.style.display = '';
            } else {
                item.style.display = 'none';
            }
        });
    });
}

function filterTable() {
    const filterValue = document.querySelector('.filter-chip.active')?.dataset.filter || 'all';
    const searchTerm = document.getElementById('searchInput')?.value.toLowerCase() || '';
    const rows = document.querySelectorAll('.table-row');
    
    rows.forEach(row => {
        const status = row.dataset.status;
        const text = row.textContent.toLowerCase();
        
        let statusMatch = filterValue === 'all' || status === filterValue;
        let searchMatch = searchTerm === '' || text.includes(searchTerm);
        
        row.style.display = (statusMatch && searchMatch) ? '' : 'none';
    });
}

// ==================== ANIMATIONS ====================
function initAnimations() {
    // Add fade-in class to elements
    const elements = document.querySelectorAll('.animate-on-scroll');
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('fade-in');
                observer.unobserve(entry.target);
            }
        });
    }, { threshold: 0.1 });
    
    elements.forEach(el => observer.observe(el));
}

// ==================== MOBILE MENU ====================
function initMobileMenu() {
    const menuBtn = document.getElementById('mobileMenuBtn');
    const sidebar = document.getElementById('sidebar');
    
    if (menuBtn && sidebar) {
        menuBtn.addEventListener('click', () => {
            sidebar.classList.toggle('open');
        });
    }
}

// ==================== FILE UPLOAD PREVIEW ====================
function previewFile(input) {
    const preview = document.getElementById('filePreview');
    if (!preview) return;
    
    if (input.files && input.files[0]) {
        const file = input.files[0];
        const reader = new FileReader();
        
        reader.onload = function(e) {
            if (file.type.startsWith('image/')) {
                preview.innerHTML = `<img src="${e.target.result}" class="preview-image">`;
            } else {
                preview.innerHTML = `<div class="file-info">${file.name} (${(file.size / 1024).toFixed(2)} KB)</div>`;
            }
        };
        
        reader.readAsDataURL(file);
    }
}

// ==================== COPY TO CLIPBOARD ====================
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        showToast('Copied to clipboard!', 'success');
    }).catch(() => {
        showToast('Failed to copy', 'danger');
    });
}

// ==================== CONFIRM DIALOG ====================
function confirmAction(message, callback) {
    if (confirm(message)) {
        callback();
    }
}

// ==================== LOADING STATE ====================
function showLoading(button) {
    const originalText = button.innerHTML;
    button.disabled = true;
    button.innerHTML = '<span class="spinner-sm"></span> Loading...';
    return () => {
        button.disabled = false;
        button.innerHTML = originalText;
    };
}

// ==================== EXPORT FUNCTIONS ====================
window.showToast = showToast;
window.copyToClipboard = copyToClipboard;
window.confirmAction = confirmAction;
window.previewFile = previewFile;
window.filterTable = filterTable;
window.checkPasswordStrength = checkPasswordStrength;