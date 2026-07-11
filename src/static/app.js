// app.js — 公共 JS（sidebar toggle、批量选择、三点菜单、CSRF、Toast、暗色模式、DOM缓存、事件委托）
(function () {
  'use strict';

  // ── DOM 缓存对象（同步初始化，确保 index.html inline script 可用） ──
  var $ = {};
  window.$ = $;
  (function initDomCacheSync() {
    var ids = [
      'add-modal','edit-modal','confirm-modal','selfPwdModal',
      'chart-content','chart-chevron','help-content','help-chevron',
      'search-input','search-suggestions','filter-status','filter-type',
      'filter-date-from','filter-date-to','cert-tbody','pagination',
      'page-info','page-buttons','per-page-select','selected-count',
      'select-all','select-all-header','toast-container','flash-container',
      'sidebar','sidebar-overlay','mobile-menu-btn','confirm-title',
      'confirm-msg','confirm-ok','batch-dropdown','batch-toolbar',
      'add-expire-date','edit-expire-date','add-expire-time','edit-expire-time',
      'continue-add','edit-cert-id','edit-customer','edit-cert-type','edit-domain',
      'edit-expire-date','edit-expire-time','edit-note','edit-remind-enabled',
      'edit-handled','edit-responsible-users','last-update-time',
      'skeleton-loading','filter-bar-mobile','type-suggestions',
      'chart-section','chart-body','chart-toggle','help-section','help-body',
      'mobile-menu','admin-menu','admin-menu-btn'
    ];
    ids.forEach(function(id) { $[id] = document.getElementById(id); });
  })();

  // ── Sidebar Toggle (移动端抽屉菜单) ─────────────────────
  window.toggleSidebar = function () {
    var sidebar = $['sidebar'];
    var overlay = $['sidebar-overlay'];
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
    if ($['sidebar-overlay']) {
      $['sidebar-overlay'].addEventListener('click', function () {
        var sidebar = $['sidebar'];
        if (sidebar) sidebar.classList.remove('sidebar-open');
        overlay.classList.add('hidden');
        overlay.classList.remove('sidebar-active');
      });
    }

    // 汉堡菜单按钮
    if ($['mobile-menu-btn']) {
      $['mobile-menu-btn'].addEventListener('click', window.toggleSidebar);
    }

    // 点击导航链接关闭 sidebar（移动端）
    document.querySelectorAll('#sidebar nav a').forEach(function (link) {
      link.addEventListener('click', function () {
        var sidebar = $['sidebar'];
        var ov = $['sidebar-overlay'];
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
    var container = $['flash-container'];
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
  
    // ── 事件委托：统计卡片筛选 ──────────────────────────
    $['stat-cards'].forEach(function(card) {
      card.addEventListener('click', function() {
        var filter = card.getAttribute('data-filter');
        if (filter && typeof window.quickFilter === 'function') window.quickFilter(filter);
      });
    });

    // ── 事件委托：图表/说明折叠 ──────────────────────────
    var chartHeader = document.getElementById('chart-section');
    if (chartHeader) {
      chartHeader.addEventListener('click', function(e) {
        if (e.target.closest('#chart-toggle-area')) {
          if (typeof window.toggleChart === 'function') window.toggleChart();
        }
      });
    }
    var helpSection = document.getElementById('help-section');
    if (helpSection) {
      helpSection.addEventListener('click', function(e) {
        if (e.target.closest('#help-toggle-area')) {
          if (typeof window.toggleHelp === 'function') window.toggleHelp();
        }
      });
    }

    // ── 事件委托：表头排序 ──────────────────────────────
    var thead = document.querySelector('#cert-tbody')?.closest('table')?.querySelector('thead tr');
    if (thead) {
      thead.addEventListener('click', function(e) {
        var th = e.target.closest('th[onclick]');
        if (!th) return;
        var col = th.getAttribute('data-sort-col');
        if (col && typeof window.sortTable === 'function') window.sortTable(col);
      });
    }

    // ── 事件委托：行操作按钮 (编辑/更多) ─────────────────
    var tbody = document.getElementById('cert-tbody');
    if (tbody) {
      tbody.addEventListener('click', function(e) {
        var editBtn = e.target.closest('button[data-action="edit"]');
        if (editBtn) {
          var certId = editBtn.getAttribute('data-cert-id');
          if (typeof window.openEditModal === 'function') window.openEditModal(parseInt(certId));
          return;
        }
        var menuBtn = e.target.closest('button[data-action="menu"]');
        if (menuBtn) {
          var certId = menuBtn.getAttribute('data-cert-id');
          if (typeof window.toggleRowMenu === 'function') window.toggleRowMenu(parseInt(certId), menuBtn, e);
          return;
        }
        var rowMenu = e.target.closest('[id^="row-menu-"] button[data-row-action]');
        if (rowMenu) {
          var action = rowMenu.getAttribute('data-row-action');
          var certId = parseInt(rowMenu.getAttribute('data-cert-id'));
          if (action === 'push') {
            var customer = rowMenu.getAttribute('data-customer');
            if (typeof window.pushCert === 'function') window.pushCert(certId, customer);
          } else if (action === 'toggle-status') {
            if (typeof window.toggleStatus === 'function') window.toggleStatus(certId);
          } else if (action === 'toggle-handled') {
            if (typeof window.toggleHandled === 'function') window.toggleHandled(certId);
          } else if (action === 'duplicate') {
            if (typeof window.duplicateCert === 'function') window.duplicateCert(certId);
          } else if (action === 'delete') {
            var customer = rowMenu.getAttribute('data-customer');
            if (typeof window.confirmDelete === 'function') window.confirmDelete(certId, customer);
          }
          return;
        }
        // 行选择 checkbox
        var checkbox = e.target.closest('.row-checkbox');
        if (checkbox) {
          var certId = parseInt(checkbox.value);
          if (typeof window.onRowSelect === 'function') window.onRowSelect(checkbox, certId);
        }
      });
    }

    // ── 事件委托：搜索/筛选 ─────────────────────────────
    var searchBar = document.getElementById('search-input');
    if (searchBar) {
      searchBar.addEventListener('input', function() {
        if (typeof window.filterTable === 'function') window.filterTable();
        if (typeof window.showSearchSuggestions === 'function') window.showSearchSuggestions(this.value);
      });
      searchBar.addEventListener('keydown', function(e) {
        if (e.key === 'Enter') { e.preventDefault(); if (typeof window.filterTable === 'function') window.filterTable(); }
        if (e.key === 'ArrowDown') { e.preventDefault(); if (typeof window.selectSuggestion === 'function') window.selectSuggestion(1); }
        if (e.key === 'ArrowUp') { e.preventDefault(); if (typeof window.selectSuggestion === 'function') window.selectSuggestion(-1); }
        if (e.key === 'Escape') { if (typeof window.hideSearchSuggestions === 'function') window.hideSearchSuggestions(); }
      });
    }
    $['filter-selects'].forEach(function(sel) {
      sel.addEventListener('change', function() {
        if (typeof window.filterTable === 'function') window.filterTable();
      });
    });

    // ── 事件委托：批量操作 ──────────────────────────────
    var batchToolbar = document.getElementById('batch-toolbar');
    if (batchToolbar) {
      batchToolbar.addEventListener('click', function(e) {
        var selectAll = e.target.closest('#select-all');
        if (selectAll) {
          if (typeof window.toggleSelectAll === 'function') window.toggleSelectAll();
          return;
        }
        var batchBtn = e.target.closest('button[data-batch-action]');
        if (batchBtn) {
          var action = batchBtn.getAttribute('data-batch-action');
          var value = batchBtn.getAttribute('data-batch-value');
          if (action === 'handle') window.batchHandle(value === 'true');
          else if (action === 'remind') window.batchRemind(value === 'true');
          else if (action === 'delete') window.batchDelete();
          return;
        }
        var dropdownBtn = e.target.closest('button[data-batch-dropdown]');
        if (dropdownBtn) {
          if (typeof window.toggleBatchDropdown === 'function') window.toggleBatchDropdown();
        }
      });
    }

    // ── 事件委托：弹窗遮罩关闭 ──────────────────────────
    $['modal-overlays'].forEach(function(overlay) {
      overlay.addEventListener('click', function(e) {
        if (e.target === overlay) {
          var addModal = document.getElementById('add-modal');
          var editModal = document.getElementById('edit-modal');
          if (overlay === addModal) { if (typeof window.closeAddModal === 'function') window.closeAddModal(); }
          if (overlay === editModal) { if (typeof window.closeEditModal === 'function') window.closeEditModal(); }
        }
      });
    });

    // ── 事件委托：快捷日期按钮 ──────────────────────────
    document.querySelectorAll('.expiry-shortcuts button').forEach(function(btn) {
      var days = parseInt(btn.getAttribute('data-days'));
      if (days) {
        btn.addEventListener('click', function() { if (typeof window.setExpiryDays === 'function') window.setExpiryDays(days); });
      }
    });

    // ── 事件委托：添加/编辑弹窗打开按钮 ─────────────────
    document.querySelectorAll('[data-action="open-add-modal"]').forEach(function(btn) {
      btn.addEventListener('click', function() { if (typeof window.openAddModal === 'function') window.openAddModal(); });
    });

    // ── 事件委托：修改密码弹窗 ──────────────────────────
    var selfPwdModal = document.getElementById('selfPwdModal');
    if (selfPwdModal) {
      selfPwdModal.addEventListener('click', function(e) {
        if (e.target === selfPwdModal) { if (typeof window.closeSelfPwdModal === 'function') window.closeSelfPwdModal(); }
      });
    }
    var selfPwdForm = document.getElementById('selfPwdForm');
    if (selfPwdForm) {
      selfPwdForm.addEventListener('submit', function(e) {
        e.preventDefault();
        if (typeof window.checkSelfPwd === 'function') window.checkSelfPwd();
      });
    }

    // ── 事件委托：分页按钮 ──────────────────────────────
    var pagination = document.getElementById('pagination');
    if (pagination) {
      pagination.addEventListener('click', function(e) {
        var pageBtn = e.target.closest('button[data-page]');
        if (pageBtn) {
          var p = parseInt(pageBtn.getAttribute('data-page'));
          if (typeof window.goPage === 'function') window.goPage(p);
        }
        var perPageSel = document.getElementById('per-page-select');
        if (e.target === perPageSel) {
          if (typeof window.changePerPage === 'function') window.changePerPage(perPageSel.value);
        }
      });
    }

    // ── 事件委托：重置筛选按钮 ──────────────────────────
    var resetBtn = document.querySelector('button[data-action="reset-filters"]');
    if (resetBtn) {
      resetBtn.addEventListener('click', function() { if (typeof window.resetFilters === 'function') window.resetFilters(); });
    }

    // ── 点击外部关闭菜单 ────────────────────────────────
    document.addEventListener('click', function(e) {
      // 关闭行菜单
      document.querySelectorAll('[id^="row-menu-"]').forEach(function(dd) {
        if (dd.classList.contains('hidden')) return;
        if (dd.contains(e.target)) return;
        var confirmModal = document.getElementById('confirm-modal');
        if (confirmModal && !confirmModal.classList.contains('hidden')) return;
        dd.classList.add('hidden');
      });
      // 关闭批量下拉
      var batchDd = document.getElementById('batch-dropdown');
      if (batchDd && !batchDd.classList.contains('hidden') && !batchDd.contains(e.target)) {
        var batchBtn = document.querySelector('button[data-batch-dropdown]');
        if (batchBtn && !batchBtn.contains(e.target)) batchDd.classList.add('hidden');
      }
      // 关闭管理员下拉
      var adminDd = document.getElementById('admin-menu');
      if (adminDd && !adminDd.contains(e.target)) {
        var adminBtn = document.getElementById('admin-menu-btn');
        if (adminBtn && !adminBtn.contains(e.target)) adminDd.classList.add('hidden');
      }
      // 关闭移动端菜单
      var mobileMenu = document.getElementById('mobile-menu');
      if (mobileMenu && !mobileMenu.classList.contains('hidden')) {
        var hamburger = document.querySelector('button[aria-label="菜单"]');
        if (hamburger && !hamburger.contains(e.target)) mobileMenu.classList.add('hidden');
      }
    });

    // ── ESC 关闭确认弹窗 ────────────────────────────────
    document.addEventListener('keydown', function(e) {
      if (e.key === 'Escape') {
        var cm = document.getElementById('confirm-modal');
        if (cm && !cm.classList.contains('hidden')) {
          if (typeof window.closeConfirmModal === 'function') window.closeConfirmModal();
        }
      }
    });
  });


  });

  // ── CSRF Token ──────────────────────────────────────────
  // Read CSRF from meta tag (safer than inline Jinja injection)
  (function() {
    var meta = document.querySelector('meta[name="csrf-token"]');
    if (meta) window._csrfToken = window._csrfToken || meta.getAttribute('content');
    var metaUser = document.querySelector('meta[name="current-user"]');
    if (metaUser) window._currentUser = window._currentUser || metaUser.getAttribute('content');
  })();

  // ── Toast 提示 (全局共享，index.html 内联脚本也依赖此函数) ──
  window.showToast = function (msg, type) {
    var container = $['toast-container'];
    if (!container) return;
    var toast = document.createElement('div');
    var colors = {
      success: 'bg-green-50 border-green-300 text-green-800',
      error: 'bg-red-50 border-red-300 text-red-800',
      warning: 'bg-yellow-50 border-yellow-300 text-yellow-800',
      info: 'bg-blue-50 border-blue-300 text-blue-800'
    };
    var c = colors[type] || colors.info;
    toast.className = c + ' px-4 py-3 rounded-lg border shadow-lg text-sm font-medium flex items-center gap-2 toast-enter';
    toast.style.position = 'relative';
    var iconMap = {
      success: '<i data-lucide="check-circle" class="w-4 h-4 flex-shrink-0"></i>',
      error: '<i data-lucide="x-circle" class="w-4 h-4 flex-shrink-0"></i>',
      warning: '<i data-lucide="alert-triangle" class="w-4 h-4 flex-shrink-0"></i>',
      info: '<i data-lucide="info" class="w-4 h-4 flex-shrink-0"></i>'
    };
    toast.innerHTML = (iconMap[type] || iconMap.info) + '<span class="flex-1">' + msg + '</span>' +
      '<div class="toast-progress" style="position:absolute;bottom:0;left:0;right:0;height:3px;border-radius:0 0 4px 4px;background:' + (type==='error'?'#dc2626':type==='success'?'#16a34a':'#3b82f6') + ';animation:toast-progress 3s linear forwards;"></div>';
    container.appendChild(toast);
    // Re-render lucide icons in toast
    if (window.lucide) lucide.createIcons();
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
      // console.error('fetchWithCsrf error:', e);  // removed: errors are thrown to caller
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
