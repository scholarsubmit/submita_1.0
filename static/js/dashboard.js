(function () {
  const STORAGE_KEY = 'submita-sidebar-collapsed';
  const shell = document.getElementById('dashShell');
  const toggleBtn = document.getElementById('sidebarToggle');
  const toggleBtnMobile = document.getElementById('sidebarToggleMobile');

  // Restore collapsed state from last visit (desktop only — mobile always starts closed).
  if (shell && localStorage.getItem(STORAGE_KEY) === 'true') {
    shell.classList.add('sidebar-collapsed');
  }

  if (toggleBtn) {
    toggleBtn.addEventListener('click', function () {
      const collapsed = shell.classList.toggle('sidebar-collapsed');
      localStorage.setItem(STORAGE_KEY, collapsed);
    });
  }

  if (toggleBtnMobile) {
    toggleBtnMobile.addEventListener('click', function () {
      shell.classList.toggle('sidebar-mobile-open');
    });
  }

  // Close mobile sidebar when clicking outside it.
  document.addEventListener('click', function (e) {
    if (!shell || !shell.classList.contains('sidebar-mobile-open')) return;
    const sidebar = document.getElementById('dashSidebar');
    if (!sidebar.contains(e.target) && e.target !== toggleBtnMobile) {
      shell.classList.remove('sidebar-mobile-open');
    }
  });

  // ==================== NOTIFICATION BELL + LIVE POLLING ====================
  const bell = document.getElementById('notifBell');
  const panel = document.getElementById('notifPanel');
  const list = document.getElementById('notifList');
  const dot = document.getElementById('notifDot');
  if (!bell) return;

  let lastSeenId = parseInt(localStorage.getItem('submita-last-seen-feed-id') || '0', 10);
  let latestId = lastSeenId;

  function timeAgo(isoString) {
    const seconds = Math.floor((Date.now() - new Date(isoString).getTime()) / 1000);
    if (seconds < 60) return 'just now';
    if (seconds < 3600) return Math.floor(seconds / 60) + 'm ago';
    if (seconds < 86400) return Math.floor(seconds / 3600) + 'h ago';
    return Math.floor(seconds / 86400) + 'd ago';
  }

  function render(items) {
    if (!items.length) {
      list.innerHTML = '<p class="field-hint" style="padding:16px;">No activity yet.</p>';
      return;
    }
    list.innerHTML = items.map(function (item) {
      const icon = { info: 'ℹ️', success: '✅', warning: '⚠️', submission: '📄', grade: '🎯' }[item.icon] || 'ℹ️';
      return '<div class="dash-notif-item"><span>' + icon + '</span><div>' +
        '<div>' + item.message + '</div>' +
        '<div class="dash-notif-time">' + timeAgo(item.created_at) + '</div>' +
        '</div></div>';
    }).join('');
  }

  function poll() {
    fetch('/api/activity-feed')
      .then(function (r) { return r.json(); })
      .then(function (data) {
        render(data.items);
        if (data.items.length) {
          latestId = Math.max.apply(null, data.items.map(function (i) { return i.id; }));
          dot.hidden = latestId <= lastSeenId;
        }
      })
      .catch(function () { /* silently skip a failed poll cycle */ });
  }

  bell.addEventListener('click', function () {
    panel.hidden = !panel.hidden;
    if (!panel.hidden) {
      lastSeenId = latestId;
      localStorage.setItem('submita-last-seen-feed-id', String(lastSeenId));
      dot.hidden = true;
    }
  });

  document.addEventListener('click', function (e) {
    if (!panel.hidden && !panel.contains(e.target) && e.target !== bell) {
      panel.hidden = true;
    }
  });

  poll();
  setInterval(poll, 30000);
})();
