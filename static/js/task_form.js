document.addEventListener('DOMContentLoaded', function() {
    
    // Character Counter
    const textarea = document.querySelector('.form-textarea');
    const charCount = document.getElementById('charCount');
    
    if (textarea && charCount) {
        const maxChars = 500;
        
        textarea.addEventListener('input', function() {
            const length = this.value.length;
            charCount.textContent = length;
            
            if (length > maxChars) {
                charCount.style.color = 'var(--danger)';
            } else {
                charCount.style.color = 'var(--text-muted)';
            }
        });
        
        charCount.textContent = textarea.value.length;
    }
    
    // Form Validation
    const form = document.getElementById('taskForm');
    
    if (form) {
        form.addEventListener('submit', function(e) {
            const title = form.querySelector('[name="title"]');
            
            console.log("Form submitted! Title value:", title.value);
            
            if (!title.value.trim()) {
                e.preventDefault();
                console.log("Submission blocked: Empty title");
                
                title.focus();
                title.style.borderColor = 'var(--danger)';
                
                let errorMsg = title.parentElement.querySelector('.form-error');
                if (!errorMsg) {
                    errorMsg = document.createElement('div');
                    errorMsg.className = 'form-error';
                    errorMsg.textContent = 'Task title is required';
                    title.parentElement.appendChild(errorMsg);
                }
                
                return false;
            }
            
            console.log("Validation passed. Letting Django handle it...");
            // If we get here, the form submits normally to Django
        });
    }
    
    // Auto-focus Title
    const titleField = document.querySelector('[name="title"]');
    if (titleField) {
        setTimeout(() => titleField.focus(), 100);
    }
    
});