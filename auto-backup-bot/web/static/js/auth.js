// Turnstile success callback
function onTurnstileSuccess(token) {
    const button = document.getElementById('auth-button');
    button.disabled = false;
    button.style.cursor = 'pointer';
}

// Form submission handler
document.getElementById('auth-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const button = document.getElementById('auth-button');
    const originalText = button.innerHTML;
    
    // Show loading state
    button.disabled = true;
    button.innerHTML = '<span class="button-icon">⏳</span> 処理中...';
    
    try {
        const formData = new FormData(e.target);
        const turnstileToken = document.querySelector('[name="cf-turnstile-response"]').value;
        formData.append('cf-turnstile-response', turnstileToken);
        
        const response = await fetch('/verify', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (response.ok && data.redirect) {
            // Redirect to Discord OAuth2
            button.innerHTML = '<span class="button-icon">🚀</span> Discord認証へ...';
            window.location.href = data.redirect;
        } else {
            throw new Error(data.error || '認証に失敗しました');
        }
    } catch (error) {
        console.error('Error:', error);
        button.innerHTML = '<span class="button-icon">❌</span> エラーが発生しました';
        
        // Show error message
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error-message';
        errorDiv.textContent = error.message;
        errorDiv.style.marginTop = '15px';
        errorDiv.style.padding = '10px';
        errorDiv.style.background = 'rgba(237, 66, 69, 0.2)';
        errorDiv.style.borderRadius = '8px';
        errorDiv.style.color = '#ED4245';
        
        const form = document.getElementById('auth-form');
        form.appendChild(errorDiv);
        
        // Reset button after 3 seconds
        setTimeout(() => {
            button.disabled = false;
            button.innerHTML = originalText;
            errorDiv.remove();
            
            // Reset Turnstile
            turnstile.reset();
        }, 3000);
    }
});

// Auto-close success page after 10 seconds
if (window.location.pathname.includes('success')) {
    setTimeout(() => {
        const closeButton = document.querySelector('.btn-secondary');
        if (closeButton) {
            closeButton.textContent = 'このページは自動的に閉じます (5秒)';
            
            setTimeout(() => window.close(), 5000);
        }
    }, 10000);
}

// Add smooth scroll behavior
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({
                behavior: 'smooth'
            });
        }
    });
});
