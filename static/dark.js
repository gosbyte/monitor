// 暗色模式 — 所有页面通用
(function(){
  var d = localStorage.getItem('dark-mode') === 'true';
  if (d) document.body.classList.add('dark-mode');

  function _applyDarkIcons(isDark) {
    // ID-based icons (header style)
    var sun = document.getElementById('dark-icon-sun');
    var moon = document.getElementById('dark-icon-moon');
    if (sun && moon) {
      sun.classList.toggle('hidden', isDark);
      moon.classList.toggle('hidden', !isDark);
    }
    var label = document.getElementById('dark-label');
    if (label) label.textContent = isDark ? '亮色模式' : '暗色模式';
    // Lucide icon pair inside #dark-toggle
    var sunIcon = document.querySelector('#dark-toggle [data-lucide="sun"]');
    var moonIcon = document.querySelector('#dark-toggle [data-lucide="moon"]');
    if (sunIcon && moonIcon) {
      sunIcon.classList.toggle('hidden', isDark);
      moonIcon.classList.toggle('hidden', !isDark);
    }
    // Mobile menu icons
    var sunM = document.getElementById('dark-icon-sun-m');
    var moonM = document.getElementById('dark-icon-moon-m');
    if (sunM && moonM) {
      sunM.classList.toggle('hidden', isDark);
      moonM.classList.toggle('hidden', !isDark);
    }
    var labelM = document.getElementById('dark-label-m');
    if (labelM) labelM.textContent = isDark ? '亮色模式' : '暗色模式';
  }

  _applyDarkIcons(d);
  window.toggleDarkMode = function() {
    var isDark = !document.body.classList.contains('dark-mode');
    document.body.classList.toggle('dark-mode', isDark);
    document.documentElement.classList.toggle('dark', isDark);
    localStorage.setItem('dark-mode', isDark);
    _applyDarkIcons(isDark);
    if (typeof lucide !== 'undefined') lucide.createIcons();
  };

  // Respect system preference on first visit
  if (localStorage.getItem('dark-mode') === null) {
    var prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    if (prefersDark) {
      document.body.classList.add('dark-mode');
      document.documentElement.classList.add('dark');
      localStorage.setItem('dark-mode', 'true');
      _applyDarkIcons(true);
    }
  }

  // Desktop sidebar toggle
  window.toggleDesktopSidebar = function() {
    var sb = document.getElementById('sidebar');
    var mc = document.getElementById('main-content');
    sb.classList.toggle('collapsed');
    mc.classList.toggle('sidebar-collapsed');
  };

  // Mobile sidebar toggle
  (function() {
    var btn = document.getElementById('mobile-menu-btn');
    var overlay = document.getElementById('sidebar-overlay');
    if (btn && overlay) {
      btn.addEventListener('click', function() {
        var sb = document.getElementById('sidebar');
        sb.classList.toggle('sidebar-open');
        overlay.classList.toggle('sidebar-active');
        document.body.classList.toggle('sidebar-open');
      });
      overlay.addEventListener('click', function() {
        var sb = document.getElementById('sidebar');
        sb.classList.remove('sidebar-open');
        overlay.classList.remove('sidebar-active');
        document.body.classList.remove('sidebar-open');
      });
    }
  })();

  // Listen for system theme changes
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function(e) {
    if (localStorage.getItem('dark-mode') === null) {
      if (e.matches) {
        document.body.classList.add('dark-mode');
      } else {
        document.body.classList.remove('dark-mode');
      }
    }
  });
})();
