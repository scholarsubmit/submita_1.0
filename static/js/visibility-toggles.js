(function () {
    // ==================== PASSWORD SHOW/HIDE ====================
    document.addEventListener('DOMContentLoaded', function () {
        document.querySelectorAll('[data-password-toggle]').forEach(function (btn) {
            btn.addEventListener('click', function () {
                const targetId = btn.getAttribute('data-password-toggle');
                const input = document.getElementById(targetId);
                if (!input) return;
                const showing = input.type === 'text';
                input.type = showing ? 'password' : 'text';
                btn.textContent = showing ? '👁' : '🙈';
                btn.setAttribute('aria-label', showing ? 'Show password' : 'Hide password');
            });
        });
    });

    // ==================== MATRIC / STAFF ID MASK TOGGLE ====================
    // Persisted globally — hides every ID badge on every page at once,
    // since someone hiding their matric number cares about it being
    // hidden everywhere, not just on the one page they clicked on.
    const ID_MASK_KEY = 'submita-ids-masked';

    function applyIdMask(masked) {
        document.body.classList.toggle('ids-masked', masked);
        document.querySelectorAll('[data-id-toggle]').forEach(function (btn) {
            btn.textContent = masked ? '🙈' : '👁';
            btn.setAttribute('aria-label', masked ? 'Show ID' : 'Hide ID');
        });
    }

    const storedMasked = localStorage.getItem(ID_MASK_KEY) === 'true';
    applyIdMask(storedMasked);

    document.addEventListener('DOMContentLoaded', function () {
        applyIdMask(localStorage.getItem(ID_MASK_KEY) === 'true');
        document.querySelectorAll('[data-id-toggle]').forEach(function (btn) {
            btn.addEventListener('click', function () {
                const nextMasked = !document.body.classList.contains('ids-masked');
                localStorage.setItem(ID_MASK_KEY, nextMasked);
                applyIdMask(nextMasked);
            });
        });
    });
})();
