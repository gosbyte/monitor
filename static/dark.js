// 暗色模式 — 所有页面通用
(function(){
  var d = localStorage.getItem('dark-mode') === 'true';
  
  function applyTheme(isDark) {
    // Add 'dark' class to <html> for Tailwind dark mode support
    document.documentElement.classList.toggle('dark', isDark);
    // Add 'dark-mode' class to <body> for custom dark.css support
    document.body.classList.toggle('dark-mode', isDark);
  }

  applyTheme(d);

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
    applyTheme(isDark);
    localStorage.setItem('dark-mode', isDark);
    _applyDarkIcons(isDark);
    if (typeof lucide !== 'undefined') lucide.createIcons();
  };

  // Respect system preference on first visit (only if localStorage is empty)
  if (localStorage.getItem('dark-mode') === null) {
    var prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    if (prefersDark) {
      applyTheme(true);
      localStorage.setItem('dark-mode', 'true');
      _applyDarkIcons(true);
    } else {
      localStorage.setItem('dark-mode', 'false');
    }
  }

  // Listen for system theme changes (only when user hasn't manually set a preference)
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function(e) {
    if (localStorage.getItem('dark-mode') === null) {
      applyTheme(e.matches);
    }
  });
})();
