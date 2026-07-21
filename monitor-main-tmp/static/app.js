// common.js — 公共 JS（模态框、批量选择、三点菜单、CSRF、API、暗色模式、移动端菜单）
(function () {
  'use strict';

  // ── Mobile Menu Toggle ──────────────────────────────────
  window.toggleSidebar = function () {
    var sidebar = document.getElementById('sidebar');
    var overlay = document.getElementById('sidebar-overlay');
    if (!sidebar) return;
    var isOpen = !sidebar.classList.contains('-translate-x-full');
    if (isOpen) {
      sidebar.classList.add('-translate-x-full');
      if (overlay) overlay.classList.add('hidden');
    } else {
      sidebar.classList.remove('-translate-x-full');
      if (overlay) overlay.classList.remove('hidden');
    }
  };

  // Close sidebar when clicking overlay
  document.addEventListener('DOMContentLoaded', function () {
    var overlay = document.getElementById('sidebar-overlay');
    if (overlay) {
      overlay.addEventListener('click', function () {
        var sidebar = document.getElementById('sidebar');
        if (sidebar) sidebar.classList.add('-translate-x-full');
        overlay.classList.add('hidden');
      });
    }

    // Mobile menu button
    var btn = document.getElementById('mobile-menu-btn');
    if (btn) {
      btn.addEventListener('click', window.toggleSidebar);
    }

    // Close sidebar on nav click (mobile)
    document.querySelectorAll('#sidebar nav a').forEach(function (link) {
      link.addEventListener('click', function () {
        var sidebar = document.getElementById('sidebar');
        var ov = document.getElementById('sidebar-overlay');
        if (sidebar) sidebar.classList.add('-translate-x-full');
        if (ov) ov.classList.add('hidden');
      });
    });

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
  window._csrfToken = window._csrfToken || '{{ csrf_token }}';
  window._currentUser = window._currentUser || '{{ current_username }}';

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
    var iconMap = { success: 'check-circle', error: 'x-circle', info: 'info' };
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
    var btns = ['btn-batch-handle', 'btn-batch-unhandle', 'btn-batch-remind-on', 'btn-batch-remind-off', 'btn-batch-delete', 'btn-export-selected'];
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

  // ── 移动端菜单 ──────────────────────────────────────────
  window.toggleMobileMenu = function () {
    var menu = document.getElementById('mobile-menu');
    if (menu) menu.classList.toggle('hidden');
  };
  document.addEventListener('click', function (e) {
    var mobileMenu = document.getElementById('mobile-menu');
    if (mobileMenu && !mobileMenu.classList.contains('hidden')) {
      var hamburger = document.querySelector('button[aria-label="菜单"]');
      if (hamburger && !hamburger.contains(e.target)) {
        mobileMenu.classList.add('hidden');
      }
    }
  });

  // ── API 请求封装 ────────────────────────────────────────
  window.fetchWithCsrf = function (url, options) {
    options = options || {};
    if (!options.method) options.method = 'GET';
    options.headers = options.headers || {};
    
    // 每次请求前从 meta tag 获取最新 CSRF token（防止 token 旋转导致失败）
    var metaEl = document.querySelector('meta[name="csrf-token"]');
    var csrf = metaEl ? metaEl.getAttribute('content') : window._csrfToken;
    options.headers['X-CSRF-Token'] = csrf;
    
    // 对于非 DELETE/GET 请求，确保 body 中包含 _csrf_token
    if (options.method !== 'DELETE' && options.method !== 'GET') {
      // 如果是 JSON 请求（已有 Content-Type: application/json）
      if (options.headers['Content-Type'] && options.headers['Content-Type'].indexOf('application/json') !== -1) {
        if (options.body && typeof options.body === 'string') {
          try {
            var parsed = JSON.parse(options.body);
            parsed._csrf_token = csrf;
            options.body = JSON.stringify(parsed);
          } catch (e) {}
        }
      }
      // 如果是 FormData 请求，_csrf_token 会自动包含
      // 如果是空 body，创建空的 FormData
      else if (!options.body) {
        options.body = new FormData();
        options.body.append('_csrf_token', csrf);
      }
    }
    
    return fetch(url, options).then(function (r) {
      if (r.url && r.url.includes('/login')) {
        window.location.href = '/login';
        throw new Error('redirect');
      }
      return r.json().then(function (data) {
        if (data.csrf_token) {
          window._csrfToken = data.csrf_token;
          var metaEl = document.querySelector('meta[name="csrf-token"]');
          if (metaEl) metaEl.setAttribute('content', data.csrf_token);
        }
        return data;
      });
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
      var mobileMenu = document.getElementById('mobile-menu');
      if (mobileMenu && !mobileMenu.classList.contains('hidden')) mobileMenu.classList.add('hidden');
    }
  });

})();
