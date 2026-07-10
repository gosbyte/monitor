// app.js — 公共 JS（sidebar toggle、批量选择、三点菜单、CSRF、Toast、暗色模式）
(function () {
  'use strict';

  // ── Sidebar Toggle (移动端抽屉菜单) ─────────────────────
  window.toggleSidebar = function () {
    var sidebar = document.getElementById('sidebar');
    var overlay = document.getElementById('sidebar-overlay');
    if (!sidebar) return;
    var isOpen = sidebar.classList.contains('sidebar-open');
    if (isOpen) {
      sidebar.classList.remove('sidebar-open');
      if (overlay) { overlay.classList.add('hidden'); overlay.classList.remove('sidebar-active'); }
      document.body.style.overflow = '';
    } else {
      sidebar.classList.add('sidebar-open');
      if (overlay) { overlay.classList.remove('hidden'); overlay.classList.add('sidebar-active'); }
      document.body.style.overflow = 'hidden';
    }
  };

  document.addEventListener('DOMContentLoaded', function () {
    // Initialize Lucide icons
    if (typeof lucide !== 'undefined') {
      lucide.createIcons();
    }
    // Overlay 点击关闭 sidebar
    var overlay = document.getElementById('sidebar-overlay');
    if (overlay) {
      overlay.addEventListener('click', function () {
        var sidebar = document.getElementById('sidebar');
        if (sidebar) sidebar.classList.remove('sidebar-open');
        overlay.classList.add('hidden');
        overlay.classList.remove('sidebar-active');
      });
    }

    // 汉堡菜单按钮
    var btn = document.getElementById('mobile-menu-btn');
    if (btn) {
      btn.addEventListener('click', window.toggleSidebar);
    }

    // 点击导航链接关闭 sidebar（移动端）
    document.querySelectorAll('#sidebar nav a').forEach(function (link) {
      link.addEventListener('click', function () {
        var sidebar = document.getElementById('sidebar');
        var ov = document.getElementById('sidebar-overlay');
        if (sidebar) sidebar.classList.remove('sidebar-open');
        if (ov) { ov.classList.add('hidden'); ov.classList.remove('sidebar-active'); }
      });
    });

    // 根据当前 URL 高亮对应导航项
    (function() {
      var path = window.location.pathname;
      document.querySelectorAll('#sidebar nav a[data-page]').forEach(function(link) {
        if (path === '/' + link.dataset.page || path === '/' + link.dataset.page.replace('_', '-') || path === '/') {
          link.classList.add('bg-blue-50', 'dark:bg-blue-900/30', 'text-blue-600', 'dark:text-blue-400');
        }
      });
    })();

    // Auto-dismiss flash messages after 5s
    var container = document.getElementById('flash-container');
    if (container) {
      setTimeout(function () {
        var msgs = container.querySelectorAll('> div');
        msgs.forEach(function (msg) {
          msg.style.transition = 'opacity 0.3s';
          msg.style.opacity = '0';
          setTimeout(function () { msg.remove(); }, 300);
        });
      }, 5000);
    }
  });

  // ── CSRF Token ──────────────────────────────────────────
  // Read CSRF from meta tag (safer than inline Jinja injection)
  (function() {
    var meta = document.querySelector('meta[name="csrf-token"]');
    if (meta) window._csrfToken = window._csrfToken || meta.getAttribute('content');
    var metaUser = document.querySelector('meta[name="current-user"]');
    if (metaUser) window._currentUser = window._currentUser || metaUser.getAttribute('content');
  })();

  // ── Toast 提示 ──────────────────────────────────────────
  window.showToast = function (msg, type) {
    var container = document.getElementById('toast-container');
    if (!container) return;
    var toast = document.createElement('div');
    var colors = {
      success: 'bg-green-50 border-green-300 text-green-800',
      error: 'bg-red-50 border-red-300 text-red-800',
      info: 'bg-blue-50 border-blue-300 text-blue-800'
    };
    var c = colors[type] || colors.info;
    var iconSvg = '';
    if (type === 'error') {
      iconSvg = '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>';
    } else if (type === 'info') {
      iconSvg = '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>';
    } else {
      iconSvg = '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>';
    }
    var progressColor = type === 'error' ? '#dc2626' : type === 'success' ? '#16a34a' : '#3b82f6';
    toast.className = c + ' px-4 py-3 rounded-lg border shadow-lg text-sm font-medium flex items-center gap-2 toast-enter';
    toast.style.position = 'relative';
    toast.innerHTML = iconSvg + '<span class="flex-1">' + msg + '</span>' +
      '<div class="toast-progress rounded" style="position:absolute;bottom:0;left:0;right:0;height:3px;border-radius:0 0 4px 4px;background:' + progressColor + ';animation:toast-progress 3s linear forwards;"></div>';
    container.appendChild(toast);
    setTimeout(function () {
      toast.classList.remove('toast-enter');
      toast.classList.add('toast-exit');
      setTimeout(function () { if (toast.parentNode) toast.parentNode.removeChild(toast); }, 300);
    }, 3000);
  };

  // 页面加载时检查 URL 参数
  (function () {
    var params = new URLSearchParams(window.location.search);
    var success = params.get('success');
    var error = params.get('error');
    if (success) { showToast(success, 'success'); history.replaceState({}, '', window.location.pathname); }
    if (error) { showToast(error, 'error'); history.replaceState({}, '', window.location.pathname); }
  })();

  // ── 通用确认弹窗 ────────────────────────────────────────
  window.showConfirmModal = function (title, message, okText, okCallback) {
    var titleEl = document.getElementById('confirm-title');
    var msgEl = document.getElementById('confirm-msg');
    var okBtn = document.getElementById('confirm-ok');
    if (titleEl) titleEl.textContent = title;
    if (msgEl) msgEl.textContent = message;
    if (okBtn) okBtn.textContent = okText || '确认';
    if (okBtn) {
      okBtn.onclick = function () {
        closeConfirmModal();
        if (okCallback) okCallback();
      };
    }
    var modal = document.getElementById('confirm-modal');
    if (modal) {
      modal.classList.remove('hidden');
      modal.classList.add('flex');
      document.body.classList.add('modal-open');
    }
  };

  window.closeConfirmModal = function () {
    var modal = document.getElementById('confirm-modal');
    if (modal) {
      modal.classList.add('hidden');
      modal.classList.remove('flex');
      document.body.classList.remove('modal-open');
    }
  };

  // ESC 关闭确认弹窗
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') {
      var cm = document.getElementById('confirm-modal');
      if (cm && !cm.classList.contains('hidden')) closeConfirmModal();
    }
  });

  // ── 模态框管理 ──────────────────────────────────────────
  window.hideModal = function (id) {
    var modal = document.getElementById(id);
    if (modal) {
      modal.classList.add('hidden');
      modal.classList.remove('flex');
      document.body.classList.remove('modal-open');
    }
  };

  window.confirmAction = function (callback) {
    if (callback) callback();
  };

  // ── 批量选择 ────────────────────────────────────────────
  window.getSelectedIds = function () {
    var checkboxes = document.querySelectorAll('.row-checkbox:checked');
    return Array.from(checkboxes).map(function (cb) { return parseInt(cb.value); });
  };

  window.updateBatchUI = function () {
    var ids = window.getSelectedIds();
    var count = ids.length;
    var countEl = document.getElementById('selected-count');
    if (countEl) countEl.textContent = '已选 ' + count + ' 条';
    var btns = ['btn-batch-handle', 'btn-batch-unhandle', 'btn-batch-remind-on', 'btn-batch-remind-off', 'btn-batch-delete'];
    btns.forEach(function (id) {
      var btn = document.getElementById(id);
      if (btn) btn.disabled = count === 0;
    });
    var allCheckboxes = document.querySelectorAll('.row-checkbox');
    var selectAllHeader = document.getElementById('select-all-header');
    var selectAllToolbar = document.getElementById('select-all');
    var allChecked = allCheckboxes.length > 0 && count === allCheckboxes.length;
    if (selectAllHeader) selectAllHeader.checked = allChecked;
    if (selectAllToolbar) selectAllToolbar.checked = allChecked;
  };

  window.toggleSelectAll = function () {
    var checkboxes = document.querySelectorAll('.row-checkbox');
    var selectAllHeader = document.getElementById('select-all-header');
    var selectAllToolbar = document.getElementById('select-all');
    var isChecked = selectAllHeader ? selectAllHeader.checked : (selectAllToolbar ? selectAllToolbar.checked : false);
    if (selectAllHeader) selectAllHeader.checked = isChecked;
    if (selectAllToolbar) selectAllToolbar.checked = isChecked;
    checkboxes.forEach(function (cb) { cb.checked = isChecked; });
    updateBatchUI();
  };

  window.onRowSelect = function (checkbox, certId) {
    var row = document.querySelector('tr[data-id="' + certId + '"]');
    if (row) row.classList.toggle('selected-row', checkbox.checked);
    updateBatchUI();
  };

  // ── 三点菜单 ────────────────────────────────────────────
  window.closeRowMenu = function (certId) {
    var dd = document.getElementById('row-menu-' + certId);
    if (dd) dd.classList.add('hidden');
  };

  window.toggleRowMenu = function (certId, btnEl, evt) {
    var dd = document.getElementById('row-menu-' + certId);
    if (!dd) return;
    var wasHidden = dd.classList.contains('hidden');
    document.querySelectorAll('[id^="row-menu-"]').forEach(function (m) {
      if (m.id !== 'row-menu-' + certId) m.classList.add('hidden');
    });
    if (wasHidden) {
      dd.classList.remove('hidden');
      var rect = btnEl.getBoundingClientRect();
      dd.style.top = (rect.bottom + 4) + 'px';
      dd.style.right = 'auto';
      dd.style.left = rect.left + 'px';
      var ddRect = dd.getBoundingClientRect();
      if (ddRect.bottom > window.innerHeight) {
        dd.style.top = (rect.top - ddRect.height - 4) + 'px';
      }
      if (ddRect.right > window.innerWidth) {
        dd.style.left = '';
        dd.style.right = (window.innerWidth - rect.right) + 'px';
      }
    }
    if (btnEl) {
      btnEl.classList.add('bg-gray-100');
      setTimeout(function () { btnEl.classList.remove('bg-gray-100'); }, 200);
    }
    if (evt) evt.stopPropagation();
  };

  // 点击外部关闭行菜单
  document.addEventListener('click', function (e) {
    document.querySelectorAll('[id^="row-menu-"]').forEach(function (dd) {
      if (dd.classList.contains('hidden')) return;
      if (dd.contains(e.target)) return;
      var confirmModal = document.getElementById('confirm-modal');
      if (confirmModal && !confirmModal.classList.contains('hidden')) return;
      dd.classList.add('hidden');
    });
  });

  // ── 批量下拉菜单 ────────────────────────────────────────
  window.toggleBatchDropdown = function () {
    var dd = document.getElementById('batch-dropdown');
    if (dd) dd.classList.toggle('hidden');
  };
  document.addEventListener('click', function (e) {
    var dd = document.getElementById('batch-dropdown');
    var btn = document.querySelector('[onclick="toggleBatchDropdown()"]');
    if (dd && !dd.contains(e.target) && btn && !btn.contains(e.target)) {
      dd.classList.add('hidden');
    }
  });

  // ── 管理员下拉菜单 ──────────────────────────────────────
  window.toggleAdminMenu = function () {
    var menu = document.getElementById('admin-menu');
    if (menu) menu.classList.toggle('hidden');
  };
  document.addEventListener('click', function (e) {
    var ad = document.getElementById('admin-dropdown');
    if (ad && !ad.contains(e.target)) {
      var menu = document.getElementById('admin-menu');
      if (menu) menu.classList.add('hidden');
    }
  });

  // ── API 请求封装 ────────────────────────────────────────
  window.fetchWithCsrf = function (url, options) {
    options = options || {};
    options.headers = options.headers || {};
    if (options.headers['Content-Type'] && options.headers['Content-Type'].indexOf('application/json') !== -1) {
      options.headers['X-CSRF-Token'] = window._csrfToken;
    } else if (!options.body || typeof options.body === 'string') {
      options.headers['X-CSRF-Token'] = window._csrfToken;
    }
    return fetch(url, options).then(function (r) {
      if (r.url && r.url.includes('/login')) {
        window.location.href = '/login';
        throw new Error('redirect');
      }
      return r.json().then(function (data) {
        if (data.csrf_token) window._csrfToken = data.csrf_token;
        return data;
      });
    }).catch(function (e) {
      console.error('fetchWithCsrf error:', e);
      throw e;
    });
  };

  // ── 键盘快捷键 ──────────────────────────────────────────
  document.addEventListener('keydown', function (e) {
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.tagName === 'SELECT') {
      if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        var form = e.target.closest('form');
        if (form) { form.submit(); e.preventDefault(); }
      }
      return;
    }
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
      var searchInput = document.getElementById('search-input');
      if (searchInput) { searchInput.focus(); e.preventDefault(); }
    }
    if ((e.ctrlKey || e.metaKey) && e.key === 'n') {
      if (typeof openAddModal === 'function') { openAddModal(); e.preventDefault(); }
    }
    if (e.key === 'Escape') {
      var modals = document.querySelectorAll('[id$="-modal"], .modal-overlay:not(.hidden)');
      modals.forEach(function (m) {
        if (!m.classList.contains('hidden')) {
          m.classList.add('hidden');
          m.classList.remove('flex');
        }
      });
      document.body.classList.remove('modal-open');
    }
  });

  // ── 移动端触摸优化 ────────────────────────────────────────
  // 防止双击缩放
  document.addEventListener('dblclick', function (e) {
    e.preventDefault();
  }, { passive: false });

  // 触摸反馈
  document.addEventListener('touchstart', function (e) {
    var target = e.target.closest('button, a, .cursor-pointer');
    if (target) {
      target.style.opacity = '0.7';
      target._touchStart = true;
    }
  }, { passive: true });

  document.addEventListener('touchend', function (e) {
    var target = e.target.closest('button, a, .cursor-pointer');
    if (target && target._touchStart) {
      target.style.opacity = '';
      target._touchStart = false;
    }
  }, { passive: true });

  // 防止移动端输入框缩放 (iOS)
  (function() {
    var inputs = document.querySelectorAll('input[type="text"], input[type="password"], input[type="email"], input[type="number"], input[type="tel"], input[type="url"], input[type="search"], textarea');
    inputs.forEach(function(input) {
      // 设置合适的字体大小防止 iOS 缩放
      if (window.getComputedStyle(input).fontSize !== '16px') {
        input.style.fontSize = '16px';
      }
    });
  })();

})();

// ═══════════════════════════════════════════════════════════
// 通用结果提示（带 lucide 图标）
// ═══════════════════════════════════════════════════════════
window._showResult = function(areaId, ok, message) {
  var area = document.getElementById(areaId);
  if (!area) return;
  area.classList.remove('hidden', 'bg-green-50', 'text-green-700', 'border', 'border-green-200', 'bg-red-50', 'text-red-700', 'border-red-200', 'bg-yellow-50', 'text-yellow-700', 'border-yellow-200');
  if (ok) {
    area.classList.add('bg-green-50', 'text-green-700', 'border', 'border-green-200');
    area.innerHTML = '<span style="font-size:14px"><i data-lucide="check-circle-2" class="w-4 h-4 inline-block text-green-600 mr-1"></i></span> ' + message;
  } else {
    area.classList.add('bg-red-50', 'text-red-700', 'border', 'border-red-200');
    area.innerHTML = '<span style="font-size:14px"><i data-lucide="x-circle" class="w-4 h-4 inline-block text-red-600 mr-1"></i></span> ' + message;
  }
  if (typeof lucide !== 'undefined') lucide.createIcons();
};
