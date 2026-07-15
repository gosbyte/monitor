// index.js — 首页专用 JS（搜索/筛选、分页、批量操作、行操作、拖拽排序）
(function () {
  'use strict';

  // ── Toast 通知 ──────────────────────────────────────────
  window.showToast = function (message, type) {
    var container = document.getElementById('toast-container');
    if (!container) return;
    var colors = {
      success: 'border-green-400 bg-green-50 text-green-800',
      error: 'border-red-400 bg-red-50 text-red-800',
      warning: 'border-yellow-400 bg-yellow-50 text-yellow-800',
      info: 'border-blue-400 bg-blue-50 text-blue-800'
    };
    var icons = {
      success: '<i data-lucide="check-circle" class="w-4 h-4 flex-shrink-0"></i>',
      error: '<i data-lucide="alert-circle" class="w-4 h-4 flex-shrink-0"></i>',
      warning: '<i data-lucide="alert-triangle" class="w-4 h-4 flex-shrink-0"></i>',
      info: '<i data-lucide="info" class="w-4 h-4 flex-shrink-0"></i>'
    };
    var cls = colors[type] || colors.info;
    var icon = icons[type] || icons.info;
    var toast = document.createElement('div');
    toast.className = 'bg-white border rounded-lg shadow-sm p-3 flex items-start gap-2 toast-enter max-w-xs';
    toast.style.borderColor = type === 'success' ? '#86efac' : type === 'error' ? '#fca5a5' : type === 'warning' ? '#fde047' : '#93c5fd';
    toast.innerHTML = icon + '<span class="text-sm flex-1">' + message + '</span><button class="flex-shrink-0 text-gray-400 hover:text-gray-600" onclick="this.parentElement.classList.replace(\'toast-enter\',\'toast-exit\');setTimeout(function(){this.parentElement.remove()}.bind(this),300)">×';
    container.appendChild(toast);
    if (typeof lucide !== 'undefined') lucide.createIcons();
    setTimeout(function () {
      if (toast.parentElement) {
        toast.classList.replace('toast-enter', 'toast-exit');
        setTimeout(function () { if (toast.parentElement) toast.remove(); }, 300);
      }
    }, 3000);
  };

  // ── 快捷日期设置 ────────────────────────────────────────
  window.setExpiryDays = function (days) {
    var dateInput = document.getElementById('add-expire-date') || document.getElementById('edit-expire-date');
    var timeInput = document.getElementById('add-expire-time') || document.getElementById('edit-expire-time');
    if (!dateInput || !timeInput) return;
    var today = new Date();
    today.setDate(today.getDate() + days);
    var y = today.getFullYear();
    var m = String(today.getMonth() + 1).padStart(2, '0');
    var d = String(today.getDate()).padStart(2, '0');
    dateInput.value = y + '-' + m + '-' + d;
    timeInput.value = today.toTimeString().slice(0, 5);
  };

  // ── 添加弹窗 ────────────────────────────────────────────
  window.openAddModal = function () {
    var modal = document.getElementById('add-modal');
    if (!modal) return;
    modal.classList.remove('hidden');
    modal.classList.add('flex');
    var cont = document.getElementById('continue-add');
    if (cont) cont.checked = false;
    document.body.classList.add('modal-open');
  };

  window.closeAddModal = function () {
    var modal = document.getElementById('add-modal');
    if (!modal) return;
    modal.classList.add('hidden');
    modal.classList.remove('flex');
    document.body.classList.remove('modal-open');
  };

  // 添加表单 AJAX 提交
  document.addEventListener('DOMContentLoaded', function () {
    var addModal = document.getElementById('add-modal');
    if (addModal) {
      var form = addModal.querySelector('form');
      if (form) {
        form.addEventListener('submit', function (e) {
          e.preventDefault();
          var btn = form.querySelector('button[type="submit"]');
          var continueAdd = document.getElementById('continue-add') ? document.getElementById('continue-add').checked : false;
          btn.disabled = true;
          btn.textContent = '添加中…';

          var dateVal = document.getElementById('add-expire-date').value;
          var timeVal = document.getElementById('add-expire-time').value;
          var combined = '';
          if (dateVal && timeVal) combined = dateVal + ' ' + timeVal;
          else if (dateVal) combined = dateVal;

          var hiddenField = document.createElement('input');
          hiddenField.type = 'hidden';
          hiddenField.name = 'expire_date_combined';
          hiddenField.value = combined;
          form.appendChild(hiddenField);

          fetch(form.action, {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded', 'X-Requested-With': 'XMLHttpRequest', 'X-CSRF-Token': window._csrfToken },
            body: new URLSearchParams(new FormData(form))
          }).then(function (r) {
            if (r.url && r.url.includes('/login')) { window.location.href = '/login'; throw new Error('redirect'); }
            if (!r.ok) {
              return r.text().then(function (text) { throw new Error('HTTP ' + r.status + ': ' + text.substring(0, 200)); });
            }
            return r.json();
          }).then(function (data) {
            console.log('Add response:', data);
            if (data.csrf_token) window._csrfToken = data.csrf_token;
            form.querySelectorAll('input[name="_csrf_token"]').forEach(function (inp) { inp.value = data.csrf_token || window._csrfToken; });
            if (!data.ok) {
              showToast('添加失败: ' + (data.message || '未知错误'), 'error');
              return;
            }
            if (continueAdd) {
              form.querySelector('input[name="customer"]').value = '';
              form.querySelector('input[name="cert_type"]').value = '';
              form.querySelector('input[name="expire_date"]').value = '';
              form.querySelector('input[name="expire_time"]').value = '';
              form.querySelector('textarea[name="note"]').value = '';
              form.querySelectorAll('input[name="responsible_users"]').forEach(function (cb) { cb.checked = false; });
              form.querySelector('input[name="customer"]').focus();
              showToast('添加成功！继续添加下一条…', 'success');
            } else {
              closeAddModal();
              showToast('添加成功！', 'success');
              setTimeout(function () { location.reload(); }, 800);
            }
          }).catch(function (e) {
            if (e.message !== 'redirect') showToast('添加失败，请重试', 'error');
          }).finally(function () {
            btn.disabled = false;
            btn.textContent = '添加';
          });
        });
      }
    }
  });

  // ── 复制记录 ────────────────────────────────────────────
  window.duplicateCert = function (certId) {
    var addModal = document.getElementById('add-modal');
    if (!addModal) return;
    var form = addModal.querySelector('form');
    form.reset();
    form.querySelectorAll('input[name="responsible_users"]').forEach(function (cb) { cb.checked = false; });
    fetchWithCsrf('/api/cert_status/' + certId).then(function (data) {
      if (!data.ok) { showToast('获取数据失败', 'error'); return; }
      form.querySelector('input[name="customer"]').value = data.customer || '';
      form.querySelector('input[name="cert_type"]').value = data.cert_type || '';
      if (data.expire_date) {
        var dt = data.expire_date.replace('T', ' ').trim();
        var parts = dt.split(' ');
        var baseDate = parts[0] || '';
        var baseTime = parts[1] || '00:00';
        var d = new Date(baseDate.replace('-', '/', 'g').replace('/', '-', 1) + 'T' + baseTime);
        if (isNaN(d.getTime())) d = new Date(dt.replace(' ', 'T'));
        d.setDate(d.getDate() + 30);
        var y = d.getFullYear();
        var m = String(d.getMonth() + 1).padStart(2, '0');
        var day = String(d.getDate()).padStart(2, '0');
        var hh = String(d.getHours()).padStart(2, '0');
        var mm = String(d.getMinutes()).padStart(2, '0');
        form.querySelector('input[name="expire_date"]').value = y + '-' + m + '-' + day;
        form.querySelector('input[name="expire_time"]').value = hh + ':' + mm;
      }
      form.querySelector('textarea[name="note"]').value = data.note || '';
      form.querySelector('input[name="remind_enabled"]').checked = data.remind_enabled !== false;
      openAddModal();
      showToast('已复制到表单，修改到期时间后提交', 'info');
    }).catch(function (e) { showToast('加载失败', 'error'); });
  };

  // ── 编辑弹窗 ────────────────────────────────────────────
  window.openEditModal = function (certId) {
    var modal = document.getElementById('edit-modal');
    if (!modal) return;
    document.getElementById('edit-cert-id').value = certId;
    document.body.classList.add('modal-open');
    fetchWithCsrf('/api/cert_status/' + certId).then(function (data) {
      if (!data.ok) { showToast('获取数据失败', 'error'); return; }
      document.getElementById('edit-customer').value = data.customer || '';
      document.getElementById('edit-cert-type').value = data.cert_type || '';
      document.getElementById('edit-domain').value = data.domain || '';
      var dt = (data.expire_date || '').replace('T', ' ').trim();
      var parts = dt.split(' ');
      document.getElementById('edit-expire-date').value = parts[0] || '';
      document.getElementById('edit-expire-time').value = parts[1] || '00:00';
      document.getElementById('edit-note').value = data.note || '';
      document.getElementById('edit-remind-enabled').checked = data.remind_enabled !== false;
      document.getElementById('edit-handled').checked = data.handled === true;
      var responsibleUsers = data.responsible_users || [];
      if (typeof responsibleUsers === 'string') { try { responsibleUsers = JSON.parse(responsibleUsers); } catch (e) {} }
      var checkboxes = document.querySelectorAll('#edit-responsible-users input[name="responsible_users"]');
      checkboxes.forEach(function (cb) {
        cb.checked = responsibleUsers.indexOf(cb.value) >= 0;
        toggleEditRespLabel(cb.value, cb.checked);
      });
      modal.classList.remove('hidden');
      modal.classList.add('flex');
      if (typeof lucide !== 'undefined') lucide.createIcons();
    }).catch(function (e) { showToast('加载失败：' + e.message, 'error'); });
  };

  window.closeEditModal = function () {
    var modal = document.getElementById('edit-modal');
    if (!modal) return;
    modal.classList.add('hidden');
    modal.classList.remove('flex');
    document.body.classList.remove('modal-open');
  };

  window.toggleEditRespLabel = function (username, checked) {
    var label = document.getElementById('edit-resp-label-' + username);
    if (!label) return;
    if (checked) label.classList.add('border-blue-400', 'bg-blue-50');
    else label.classList.remove('border-blue-400', 'bg-blue-50');
  };

  // 编辑表单 AJAX 提交
  document.addEventListener('DOMContentLoaded', function () {
    var editForm = document.getElementById('edit-cert-form');
    if (editForm) {
      editForm.addEventListener('submit', function (e) {
        e.preventDefault();
        // 表单验证
        var customer = document.getElementById('edit-customer');
        if (customer && !customer.value.trim()) {
          showToast('客户名称不能为空', 'error');
          customer.focus();
          return;
        }
        var certId = document.getElementById('edit-cert-id').value;
        var payload = {};
        payload['remind_enabled'] = document.getElementById('edit-remind-enabled').checked;
        payload['handled'] = document.getElementById('edit-handled').checked;
        var dateVal = document.getElementById('edit-expire-date').value;
        var timeVal = document.getElementById('edit-expire-time').value;
        if (dateVal && timeVal) payload['expire_date'] = dateVal + ' ' + timeVal;
        else if (dateVal) payload['expire_date'] = dateVal;
        var respUsers = [];
        document.querySelectorAll('#edit-responsible-users input[name="responsible_users"]:checked').forEach(function (cb) {
          respUsers.push(cb.value);
        });
        payload['responsible_users'] = respUsers;

        var submitBtn = this.querySelector('button[type=submit]');
        var origLabel = submitBtn.innerHTML;
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i data-lucide="loader" class="w-4 h-4 animate-spin inline-block"></i> 保存中…';

        fetchWithCsrf('/edit/' + certId, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        }).then(function (data) {
          if (data.success || data.ok) {
            closeEditModal();
            showToast('保存成功', 'success');
            fetchWithCsrf('/api/cert_status/' + certId).then(function (sdata) {
              if (sdata.ok && sdata.badge_html !== undefined) {
                var row = document.querySelector('tr[data-id="' + certId + '"]');
                if (row) {
                  row.dataset.customer = document.getElementById('edit-customer').value;
                  row.dataset.type = document.getElementById('edit-cert-type').value;
                  row.dataset.expire = document.getElementById('edit-expire-date').value;
                  row.dataset.note = document.getElementById('edit-note').value;
                  row.dataset.handled = document.getElementById('edit-handled').checked;
                  var cells = row.querySelectorAll('td');
                  if (cells[1]) { var ns = cells[1].querySelector('span'); if (ns) ns.textContent = document.getElementById('edit-customer').value; }
                  if (cells[2]) { var ts = cells[2].querySelector('span'); if (ts) ts.textContent = document.getElementById('edit-cert-type').value; }
                  if (cells[3]) { var ds = cells[3].querySelector('span'); if (ds) ds.textContent = (document.getElementById('edit-expire-date').value || '').replace('T', ' '); }
                  if (cells.length > 5 && cells[5] && !cells[5].classList.contains('hidden')) { var domS = cells[5].querySelector('span'); if (domS) domS.textContent = document.getElementById('edit-domain').value || '-'; }
                  if (cells[4]) cells[4].innerHTML = sdata.badge_html;
                  if (typeof lucide !== 'undefined') lucide.createIcons();
                }
              } else { location.reload(); }
            });
          } else { showToast(data.message || '保存失败', 'error'); }
        }).catch(function (e) {
          if (e.message !== 'redirect') showToast('网络错误：' + e.message, 'error');
        }).finally(function () {
          submitBtn.disabled = false;
          submitBtn.innerHTML = origLabel;
        });
      });
    }
  });

  // ── 删除操作 ────────────────────────────────────────────
  window.confirmDelete = function (certId, customerName) {
    showConfirmModal('确认删除', '确定删除「' + customerName + '」的记录？此操作不可恢复。', '确认删除', function () {
      fetchWithCsrf('/api/cert/' + certId, { method: 'DELETE' }).then(function (data) {
        if (data.ok) {
          var row = document.querySelector('tr[data-id="' + certId + '"]');
          if (row) row.remove();
          showToast('删除成功', 'success');
        } else { showToast(data.message || '删除失败', 'error'); }
      }).catch(function (e) { showToast('网络错误：' + e.message, 'error'); });
    });
  };

  window.batchDelete = function () {
    var ids = getSelectedIds();
    if (ids.length === 0) return;
    var names = Array.from(document.querySelectorAll('.row-checkbox:checked'))
      .map(function (cb) { return cb.closest('tr').querySelector('td:nth-child(2) span').textContent.trim(); })
      .slice(0, 5);
    var msg = ids.length + ' 条记录';
    if (names.length > 0) msg += '：' + names.join('、') + (ids.length > 5 ? '…' : '');
    showConfirmModal('确认删除', msg + '？此操作不可恢复。', '确认删除', function () {
      fetchWithCsrf('/api/batch_delete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ids: ids })
      }).then(function (data) {
        if (data.ok) {
          var delIds = data.deleted_ids || [];
          delIds.forEach(function (id) {
            var row = document.querySelector('tr[data-id="' + id + '"]');
            if (row) row.remove();
          });
          showToast('删除成功', 'success');
        } else { showToast(data.message || '删除失败', 'error'); }
      }).catch(function (e) { showToast('网络错误：' + e.message, 'error'); });
    });
  };

  // ── 批量操作 ────────────────────────────────────────────
  window.batchHandle = function (handled) {
    var ids = getSelectedIds();
    if (ids.length === 0) return;
    var btnId = handled ? 'btn-batch-handle' : 'btn-batch-unhandle';
    var btn = document.getElementById(btnId);
    var origLabel = handled ? '标记已处理' : '取消已处理';
    btn.disabled = true;
    btn.innerHTML = '<i data-lucide="loader" class="w-3.5 h-3.5 animate-spin inline-block"></i> 处理中…';
    fetchWithCsrf('/api/batch_handle', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ids: ids, handled: handled })
    }).then(function (data) {
      if (data.ok) { location.reload(); }
      else { showToast(data.message || '操作失败', 'error'); btn.disabled = false; btn.innerHTML = origLabel; }
    }).catch(function (e) { showToast('网络错误：' + e.message, 'error'); btn.disabled = false; btn.innerHTML = origLabel; });
  };

  window.batchRemind = function (remind_enabled) {
    var ids = getSelectedIds();
    if (ids.length === 0) return;
    var btnId = remind_enabled ? 'btn-batch-remind-on' : 'btn-batch-remind-off';
    var btn = document.getElementById(btnId);
    var origLabel = remind_enabled ? '启用提醒' : '禁用提醒';
    btn.disabled = true;
    btn.innerHTML = '<i data-lucide="loader" class="w-3.5 h-3.5 animate-spin inline-block"></i> 处理中…';
    fetchWithCsrf('/api/batch_remind', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ids: ids, remind_enabled: remind_enabled })
    }).then(function (data) {
      if (data.ok) { location.reload(); }
      else { showToast(data.message || '操作失败', 'error'); btn.disabled = false; btn.innerHTML = origLabel; }
    }).catch(function (e) { showToast('网络错误：' + e.message, 'error'); btn.disabled = false; btn.innerHTML = origLabel; });
  };

  // ── 状态切换 ────────────────────────────────────────────
  window.toggleStatus = function (certId) {
    var btn = document.getElementById('btn-status-' + certId);
    if (btn) { btn.disabled = true; btn.style.opacity = '0.5'; }
    fetchWithCsrf('/api/status/' + certId, { method: 'POST' }).then(function (data) {
      if (!data.ok) { showToast('操作失败', 'error'); return; }
      var row = document.querySelector('tr[data-id="' + certId + '"]');
      if (row && data.badge_html !== undefined) {
        var nth = document.querySelector('.row-checkbox') ? 5 : 4;
        var statusCell = row.querySelector('td:nth-child(' + nth + ')');
        if (statusCell) { statusCell.innerHTML = data.badge_html; if (typeof lucide !== 'undefined') lucide.createIcons(); }
      } else { location.reload(); }
    }).catch(function () { showToast('操作失败，请重试', 'error'); })
      .finally(function () { if (btn) { btn.disabled = false; btn.style.opacity = '1'; } });
  };

  window.toggleHandled = function (certId) {
    var btn = document.getElementById('btn-handled-' + certId);
    if (btn) { btn.disabled = true; btn.style.opacity = '0.5'; }
    fetchWithCsrf('/api/handle/' + certId, { method: 'POST' }).then(function (data) {
      if (!data.ok) { showToast('操作失败', 'error'); return; }
      location.reload();
    }).catch(function () { showToast('操作失败，请重试', 'error'); })
      .finally(function () { if (btn) { btn.disabled = false; btn.style.opacity = '1'; } });
  };

  // ── 手动推送 ────────────────────────────────────────────
  window.pushCert = function (certId, customerName) {
    showConfirmModal('确认推送', '确定向钉钉推送「' + customerName + '」的到期提醒？', '确认推送', function () {
      fetchWithCsrf('/api/push/' + certId, { method: 'POST' }).then(function (data) {
        if (data.ok) { showToast('推送成功！', 'success'); }
        else { showToast('推送失败：' + (data.message || '未知错误'), 'error'); }
      }).catch(function (e) { if (e.message !== 'redirect') showToast('网络错误：' + e.message, 'error'); });
    });
  };

  // ── 排序 ────────────────────────────────────────────────
  var sortKey = 'days_left';
  var sortDesc = true;

  window.sortTable = function (key) {
    if (sortKey === key) sortDesc = !sortDesc;
    else { sortKey = key; sortDesc = true; }
    filterTable();
  };

  // ── 分页 ────────────────────────────────────────────────
  var currentPage = 1;
  var perPage = 20;

  window.goPage = function (p) { currentPage = p; filterTable(); };

  // ── 筛选 ────────────────────────────────────────────────
  window.filterTable = function () {
    var search = document.getElementById('search-input') ? document.getElementById('search-input').value.trim().toLowerCase() : '';
    var statusFilter = document.getElementById('filter-status') ? document.getElementById('filter-status').value : '';
    var typeFilter = document.getElementById('filter-type') ? document.getElementById('filter-type').value : '';
    var dateFrom = document.getElementById('filter-date-from') ? document.getElementById('filter-date-from').value : '';
    var dateTo = document.getElementById('filter-date-to') ? document.getElementById('filter-date-to').value : '';
    var rows = document.querySelectorAll('#cert-tbody tr');
    var visible = 0;
    var today = new Date(); today.setHours(0, 0, 0, 0);

    rows.forEach(function (row) {
      var customer = (row.dataset.customer || '').toLowerCase();
      var status = row.dataset.status || '';
      var certType = row.dataset.type || '';
      var days = parseInt(row.dataset.days) || 0;
      var handled = row.dataset.handled === 'true';
      var certTypeL = certType.toLowerCase();
      var note = (row.dataset.note || '').toLowerCase();
      var matchSearch = !search || customer.includes(search) || certTypeL.includes(search) || note.includes(search);
      var matchStatus = true;
      if (statusFilter) {
        if (statusFilter === 'handled') matchStatus = handled;
        else if (statusFilter === 'unhandled') matchStatus = !handled;
        else if (statusFilter === 'mine') matchStatus = row.dataset.createdby === window._currentUser;
        else matchStatus = status === statusFilter;
      }
      var matchType = !typeFilter || certType === typeFilter;
      var matchDate = true;
      if (dateFrom || dateTo) {
        var expireDate = new Date(today); expireDate.setDate(expireDate.getDate() + days);
        if (dateFrom) { var f = new Date(dateFrom); if (expireDate < f) matchDate = false; }
        if (dateTo) { var t = new Date(dateTo); t.setDate(t.getDate() + 1); if (expireDate >= t) matchDate = false; }
      }
      row.style.display = (matchSearch && matchStatus && matchType && matchDate) ? '' : 'none';
      if (row.style.display !== 'none') visible++;
    });

    var tbody = document.getElementById('cert-tbody');
    var visibleRows = Array.from(tbody.querySelectorAll('tr')).filter(function (r) { return r.style.display !== 'none'; });
    visibleRows.sort(function (a, b) {
      var va, vb;
      switch (sortKey) {
        case 'days_left': va = parseInt(a.dataset.days) || -999; vb = parseInt(b.dataset.days) || -999; break;
        case 'customer': va = a.dataset.customer; vb = b.dataset.customer; break;
        case 'cert_type': va = a.dataset.type; vb = b.dataset.type; break;
        case 'expire_date': va = a.dataset.expire || ''; vb = b.dataset.expire || ''; break;
        default: va = -999; vb = -999;
      }
      if (sortKey === 'days_left' || sortKey === 'expire_date')
        return sortDesc ? (va > vb ? -1 : 1) : (va < vb ? -1 : 1);
      return sortDesc ? va.localeCompare(vb, 'zh') : vb.localeCompare(va, 'zh');
    });
    visibleRows.forEach(function (row) { tbody.appendChild(row); });

    var totalPages = Math.max(1, Math.ceil(visible / perPage));
    if (currentPage > totalPages) currentPage = totalPages;
    var start = (currentPage - 1) * perPage;
    visibleRows.forEach(function (row, i) {
      row.style.display = (i >= start && i < start + perPage) ? '' : 'none';
    });

    var pageInfo = document.getElementById('page-info');
    var pageButtons = document.getElementById('page-buttons');
    if (pageInfo) pageInfo.textContent = '第 ' + currentPage + '/' + totalPages + ' 页，共 ' + visible + ' 条';
    if (pageButtons) {
      var html = '';
      if (currentPage > 1) html += '<button onclick="goPage(' + (currentPage - 1) + ')" class="px-3 py-1 border border-gray-200 rounded hover:bg-gray-100">上一页</button>';
      var maxBtns = 5;
      var startP = Math.max(1, currentPage - 2);
      var endP = Math.min(totalPages, startP + maxBtns - 1);
      if (endP - startP < maxBtns - 1) startP = Math.max(1, endP - maxBtns + 1);
      for (var p = startP; p <= endP; p++) {
        var active = p === currentPage ? 'bg-blue-600 text-white border-blue-600' : 'border-gray-200 hover:bg-gray-100';
        html += '<button onclick="goPage(' + p + ')" class="px-3 py-1 border rounded ' + active + '">' + p + '</button>';
      }
      if (currentPage < totalPages) html += '<button onclick="goPage(' + (currentPage + 1) + ')" class="px-3 py-1 border border-gray-200 rounded hover:bg-gray-100">下一页</button>';
      pageButtons.innerHTML = html;
    }

    document.querySelectorAll('.sort-icon').forEach(function (el) { el.textContent = ''; });
    var activeIcon = document.querySelector('.sort-icon[data-col="' + sortKey + '"]');
    if (activeIcon) activeIcon.textContent = sortDesc ? ' ▼' : ' ▲';

    updateLastTime();
  };

  // ── 搜索建议 ────────────────────────────────────────────
  var _searchCache = [];
  var _searchCacheDirty = true;

  // ── 搜索防抖 ────────────────────────────────────────────
  var _searchDebounceTimer = null;
  var _lastSearchQuery = '';

  window.debounceFilter = function (query) {
    if (_lastSearchQuery === query) return;
    _lastSearchQuery = query;
    clearTimeout(_searchDebounceTimer);
    _searchDebounceTimer = setTimeout(function () {
      filterTable();
      showSearchSuggestions(query);
    }, 300);
  };

  window.clearSearch = function () {
    var input = document.getElementById('search-input');
    if (input) input.value = '';
    var clearBtn = document.getElementById('clear-search-btn');
    if (clearBtn) clearBtn.classList.add('hidden');
    _lastSearchQuery = '';
    filterTable();
  };

  function updateClearSearchBtn() {
    var btn = document.getElementById('clear-search-btn');
    var input = document.getElementById('search-input');
    if (btn && input) {
      btn.classList.toggle('hidden', !input.value.trim());
    }
  }

  // ── 搜索历史 ────────────────────────────────────────────
  var _searchHistory = JSON.parse(localStorage.getItem('cert_search_history') || '[]');

  function addToSearchHistory(term) {
    if (!term || term.length < 1) return;
    _searchHistory = _searchHistory.filter(function (h) { return h !== term; });
    _searchHistory.unshift(term);
    if (_searchHistory.length > 5) _searchHistory = _searchHistory.slice(0, 5);
    localStorage.setItem('cert_search_history', JSON.stringify(_searchHistory));
  }

  function _buildSearchCache() {
    if (!_searchCacheDirty) return;
    _searchCache = [];
    var rows = document.querySelectorAll('#cert-tbody tr');
    rows.forEach(function (row) {
      var customer = row.dataset.customer;
      var certType = row.dataset.type;
      if (customer && _searchCache.indexOf(customer) === -1) _searchCache.push(customer);
      if (certType && _searchCache.indexOf(certType) === -1) _searchCache.push(certType);
    });
    _searchCache.sort();
    _searchCacheDirty = false;
  }

  window.showSearchSuggestions = function (query) {
    if (!query || query.length < 1) { hideSearchSuggestions(); return; }
    _buildSearchCache();
    var container = document.getElementById('search-suggestions');
    if (!container) return;
    var lower = query.toLowerCase();
    var matches = _searchCache.filter(function (item) { return item.toLowerCase().includes(lower); }).slice(0, 8);
    if (matches.length === 0) { hideSearchSuggestions(); return; }
    var html = '';
    matches.forEach(function (m, i) {
      html += '<div class="px-3 py-2 text-sm text-gray-700 hover:bg-blue-50 cursor-pointer' + (i === 0 ? ' bg-blue-50' : '') + '" data-index="' + i + '" onclick="selectSuggestion(' + i + ')">' + m + '</div>';
    });
    container.innerHTML = html;
    container.classList.remove('hidden');
  };

  window.hideSearchSuggestions = function () {
    var container = document.getElementById('search-suggestions');
    if (container) container.classList.add('hidden');
  };

  window.selectSuggestion = function (index) {
    var container = document.getElementById('search-suggestions');
    if (!container || container.classList.contains('hidden')) return;
    var items = container.querySelectorAll('div');
    if (items[index]) {
      document.getElementById('search-input').value = items[index].textContent;
      hideSearchSuggestions();
      filterTable();
    }
  };

  // ── 重置筛选 ────────────────────────────────────────────
  window.resetFilters = function () {
    var si = document.getElementById('search-input'); if (si) si.value = '';
    var fs = document.getElementById('filter-status'); if (fs) fs.value = '';
    var ft = document.getElementById('filter-type'); if (ft) ft.value = '';
    var fd = document.getElementById('filter-date-from'); if (fd) fd.value = '';
    var ft2 = document.getElementById('filter-date-to'); if (ft2) ft2.value = '';
    _searchCacheDirty = true;
    filterTable();
  };

  // ── 最后更新时间 ────────────────────────────────────────
  window.updateLastTime = function () {
    var el = document.getElementById('last-update-time');
    if (el) {
      var now = new Date();
      var h = String(now.getHours()).padStart(2, '0');
      var m = String(now.getMinutes()).padStart(2, '0');
      var s = String(now.getSeconds()).padStart(2, '0');
      el.textContent = '更新于 ' + h + ':' + m + ':' + s;
    }
  };

  // ── 图表折叠 ────────────────────────────────────────────
  window.toggleChart = function () {
    var content = document.getElementById('chart-content');
    var chevron = document.getElementById('chart-chevron');
    if (content) {
      if (content.classList.contains('hidden')) {
        content.classList.remove('hidden');
        if (chevron) chevron.classList.remove('rotate-180');
      } else {
        content.classList.add('hidden');
        if (chevron) chevron.classList.add('rotate-180');
      }
    }
  };

  // ── 使用说明折叠 ────────────────────────────────────────
  window.toggleHelp = function () {
    var content = document.getElementById('help-content');
    var chevron = document.getElementById('help-chevron');
    if (content) {
      if (content.classList.contains('hidden')) {
        content.classList.remove('hidden');
        if (chevron) chevron.setAttribute('data-lucide', 'chevron-up');
        localStorage.setItem('help-expanded', 'true');
      } else {
        content.classList.add('hidden');
        if (chevron) chevron.setAttribute('data-lucide', 'chevron-down');
        localStorage.setItem('help-expanded', 'false');
      }
    }
    if (typeof lucide !== 'undefined') lucide.createIcons();
  };
  (function () {
    if (!localStorage.getItem('help-expanded')) {
      setTimeout(function () {
        var content = document.getElementById('help-content');
        var chevron = document.getElementById('help-chevron');
        if (content) content.classList.remove('hidden');
        if (chevron) chevron.setAttribute('data-lucide', 'chevron-up');
        if (typeof lucide !== 'undefined') lucide.createIcons();
      }, 500);
    }
  })();

  // ── 计数动画 ────────────────────────────────────────────
  function animateCounters() {
    var counters = document.querySelectorAll('[data-count]');
    counters.forEach(function (el) {
      var target = parseInt(el.getAttribute('data-count'));
      if (isNaN(target) || target <= 0) { el.textContent = target || 0; return; }
      var duration = 800;
      var startTime = null;
      function step(timestamp) {
        if (!startTime) startTime = timestamp;
        var progress = Math.min((timestamp - startTime) / duration, 1);
        el.textContent = Math.floor(progress * target);
        if (progress < 1) requestAnimationFrame(step);
      }
      requestAnimationFrame(step);
    });
  }
  document.addEventListener('DOMContentLoaded', animateCounters);

  // ── 快速筛选 ────────────────────────────────────────────
  window.quickFilter = function (status) {
    var statusSelect = document.getElementById('filter-status');
    var searchInput = document.getElementById('search-input');
    if (status === 'all') {
      if (statusSelect) statusSelect.value = '';
      if (searchInput) searchInput.value = '';
    } else {
      if (statusSelect) statusSelect.value = status;
    }
    currentPage = 1;
    filterTable();
    document.querySelectorAll('[onclick^="quickFilter"]').forEach(function (card) {
      card.classList.remove('ring-2', 'ring-offset-2', 'ring-blue-500');
    });
    if (status !== 'all') {
      var map = { normal: 'green', expiring: 'orange', expired: 'red' };
      var color = map[status];
      var activeCard = document.querySelector('[data-filter-status="' + status + '"]');
      var activeCard = document.querySelector(selector);
      if (activeCard) activeCard.classList.add('ring-2', 'ring-offset-2', 'ring-' + color + '-500');
    }
    var tbody = document.getElementById('cert-tbody');
    if (tbody) tbody.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  // ── 导出筛选数据为 CSV ────────────────────────────────
  window.exportFiltered = function () {
    var rows = document.querySelectorAll('#cert-tbody tr:not([style*="display: none"])');
    var csv = '\uFEFF客户名称,提醒类型,到期时间,剩余天数,状态,备注,是否已处理,负责人\n';
    rows.forEach(function (row) {
      var cells = row.querySelectorAll('td');
      var customer = cells[1] ? cells[1].textContent.trim() : '';
      var certType = cells[2] ? cells[2].textContent.trim() : '';
      var expireDate = cells[3] ? cells[3].textContent.trim() : '';
      var daysLeft = row.dataset.days || '';
      var status = cells[4] ? cells[4].textContent.trim() : '';
      var note = cells[5] ? cells[5].textContent.trim() : '';
      var handled = row.dataset.handled === 'true' ? '是' : '否';
      var creator = row.dataset.createdby || '';
      csv += '"' + customer + '","' + certType + '","' + expireDate + '",' + daysLeft + ',"' + status + '","' + note + '","' + handled + '","' + creator + '"\n';
    });
    var blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    var link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = '证书到期提醒_' + new Date().toLocaleDateString('zh-CN').replace(/\//g, '-') + '.csv';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(link.href);
    showToast('导出成功：' + rows.length + ' 条记录', 'success');
  };

  // ── 自动刷新 ──────────────────────────────────────────
  var _autoRefreshEnabled = localStorage.getItem('cert-auto-refresh') === 'true';
  var _autoRefreshInterval = null;

  window.toggleAutoRefresh = function () {
    _autoRefreshEnabled = !_autoRefreshEnabled;
    localStorage.setItem('cert-auto-refresh', _autoRefreshEnabled ? 'true' : 'false');
    if (_autoRefreshEnabled) {
      _autoRefreshInterval = setInterval(function () { location.reload(); }, 60000);
      showToast('已开启自动刷新（每60秒）', 'success');
    } else {
      clearInterval(_autoRefreshInterval);
      _autoRefreshInterval = null;
      showToast('已关闭自动刷新', 'info');
    }
  };

  if (_autoRefreshEnabled) {
    _autoRefreshInterval = setInterval(function () { location.reload(); }, 60000);
  }

  // ── 网络状态指示器 ────────────────────────────────────
  (function () {
    var dot = document.createElement('div');
    dot.id = 'network-status-dot';
    dot.style.cssText = 'position:fixed;bottom:16px;left:16px;width:10px;height:10px;border-radius:50%;z-index:9999;transition:background .3s;';
    dot.style.background = navigator.onLine ? '#22c55e' : '#ef4444';
    document.body.appendChild(dot);
    window.addEventListener('offline', function () {
      dot.style.background = '#ef4444';
      showToast('网络已断开', 'error');
    });
    window.addEventListener('online', function () {
      dot.style.background = '#22c55e';
      showToast('网络已恢复', 'success');
    });
  })();

  // ── 滚动到顶部按钮 ────────────────────────────────────
  (function () {
    var btn = document.createElement('button');
    btn.id = 'scroll-top-btn';
    btn.style.cssText = 'position:fixed;bottom:16px;right:16px;width:40px;height:40px;border-radius:50%;background:#3b82f6;color:white;display:flex;align-items:center;justify-content:center;z-index:9999;opacity:0;visibility:hidden;transition:all .3s;box-shadow:0 2px 8px rgba(0,0,0,.15);';
    btn.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="18 15 12 9 6 15"></polyline></svg>';
    btn.onclick = function () { window.scrollTo({ top: 0, behavior: 'smooth' }); };
    document.body.appendChild(btn);
    window.addEventListener('scroll', function () {
      btn.style.opacity = window.scrollY > 300 ? '1' : '0';
      btn.style.visibility = window.scrollY > 300 ? 'visible' : 'hidden';
    });
  })();

  // ── 活动日志 ──────────────────────────────────────────
  var _activityLog = JSON.parse(localStorage.getItem('cert_activity_log') || '[]');

  window.addActivity = function (type, message, icon) {
    _activityLog.unshift({ type: type, message: message, icon: icon || 'info', time: new Date().toISOString() });
    if (_activityLog.length > 20) _activityLog = _activityLog.slice(0, 20);
    localStorage.setItem('cert_activity_log', JSON.stringify(_activityLog));
  };

  window.renderActivity = function () {
    var list = document.getElementById('activity-list');
    var count = document.getElementById('activity-count');
    if (!list) return;
    list.innerHTML = '';
    var recent = _activityLog.slice(0, 5);
    recent.forEach(function (entry) {
      var div = document.createElement('div');
      div.className = 'flex items-start gap-2 py-1 text-xs';
      var time = new Date(entry.time).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
      div.innerHTML = '<span class="text-gray-400 w-12 flex-shrink-0">' + time + '</span><span class="text-gray-600">' + entry.message + '</span>';
      list.appendChild(div);
    });
    if (count) count.textContent = _activityLog.length;
  };

  window.clearActivity = function (event) {
    event.stopPropagation();
    _activityLog = [];
    localStorage.removeItem('cert_activity_log');
    renderActivity();
    showToast('活动日志已清空', 'success');
  };

  // ── 键盘快捷键 ────────────────────────────────────────
  document.addEventListener('keydown', function (e) {
    // Skip if typing in input/textarea
    var tag = e.target.tagName;
    if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') {
      if (e.key === 'Escape') { e.target.blur(); }
      return;
    }
    if (e.ctrlKey && e.key === 'n') { e.preventDefault(); window.openAddModal(); }
    if (e.ctrlKey && (e.key === 'k' || e.key === 'f')) { e.preventDefault(); var si = document.getElementById('search-input'); if (si) si.focus(); }
    if (e.key === 'Escape') { window.closeAddModal(); window.closeEditModal(); }
    if (e.key === 'j' || e.key === 'ArrowDown') {
      var rows = document.querySelectorAll('#cert-tbody tr:not([style*="display: none"])');
      if (rows.length > 0) {
        rows[rows.length - 1].scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      }
    }
    if (e.key === 'k' || e.key === 'ArrowUp') {
      var rows2 = document.querySelectorAll('#cert-tbody tr:not([style*="display: none"])');
      if (rows2.length > 0) {
        rows2[0].scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      }
    }
  });

  // ── 表单验证 ──────────────────────────────────────────
  window.validateAddForm = function () {
    var customer = document.querySelector('input[name="customer"]');
    if (customer && !customer.value.trim()) {
      showToast('请输入客户名称', 'error');
      customer.focus();
      return false;
    }
    return true;
  };

  window.validateEditForm = function () {
    var customer = document.getElementById('edit-customer');
    if (customer && !customer.value.trim()) {
      showToast('客户名称不能为空', 'error');
      customer.focus();
      return false;
    }
    return true;
  };

  // ── 快捷键帮助对话框 ──────────────────────────────────
  window.showShortcutsHelp = function () {
    var html = '<div class="space-y-2 text-sm">';
    html += '<div class="flex items-center justify-between py-2 border-b"><span>添加记录</span><kbd class="px-2 py-0.5 bg-gray-100 rounded text-xs">Ctrl+N</kbd></div>';
    html += '<div class="flex items-center justify-between py-2 border-b"><span>聚焦搜索</span><kbd class="px-2 py-0.5 bg-gray-100 rounded text-xs">Ctrl+K</kbd></div>';
    html += '<div class="flex items-center justify-between py-2 border-b"><span>关闭弹窗</span><kbd class="px-2 py-0.5 bg-gray-100 rounded text-xs">Esc</kbd></div>';
    html += '<div class="flex items-center justify-between py-2 border-b"><span>向下滚动</span><kbd class="px-2 py-0.5 bg-gray-100 rounded text-xs">J</kbd></div>';
    html += '<div class="flex items-center justify-between py-2 border-b"><span>向上滚动</span><kbd class="px-2 py-0.5 bg-gray-100 rounded text-xs">K</kbd></div>';
    html += '</div>';
    showConfirmModal('⌨️ 快捷键', html, '知道了', function () {});
  };

  // ── 刷新数据 ──────────────────────────────────────────
  window.refreshData = function () {
    location.reload();
  };

})();
