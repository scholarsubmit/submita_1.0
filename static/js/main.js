// Dark/Light Mode Toggle - Global with persistence
document.addEventListener('DOMContentLoaded', function() {
    const toggleBtn = document.getElementById('darkModeToggle');
    
    // Function to apply dark mode
    function applyDarkMode(isDark) {
        if (isDark) {
            document.body.classList.add('dark-mode');
        } else {
            document.body.classList.remove('dark-mode');
        }
        localStorage.setItem('theme', isDark ? 'dark' : 'light');
    }
    
    // Check for saved theme or system preference
    const savedTheme = localStorage.getItem('theme');
    const systemPrefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    
    if (savedTheme === 'dark' || (!savedTheme && systemPrefersDark)) {
        applyDarkMode(true);
    } else {
        applyDarkMode(false);
    }
    
    // Toggle theme on button click
    if (toggleBtn) {
        toggleBtn.addEventListener('click', function() {
            const isDark = !document.body.classList.contains('dark-mode');
            applyDarkMode(isDark);
        });
    }
    
    // Listen for system theme changes
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
        if (!localStorage.getItem('theme')) {
            applyDarkMode(e.matches);
        }
    });
});