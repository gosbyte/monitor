// Index page JavaScript — extracted from index.html inline script
// This file is loaded by index.html via <script src="{{ url_for('static', filename='index.js') }}" nonce="{{ csp_nonce }}"></script>


// ── DOM 缓存（app.js 已初始化 window.$，此处做页面特定补充）──────────────
(function() {
  if (!window.$) window.$ = {};
  // 页面特有的缓存（app.js 已缓存常用ID）
  var ids = ['chart-body','chart-toggle','help-body','mobile-menu','admin-menu-btn','admin-menu'];
  ids.forEach(function(id) { if (!window.$[id]) window.$[id] = document.getElementById(id); });
})();

// ── 弹窗控制 ──────────────────────────────────────────
function setExpiryDays(days) {
  var dateInput = $['add-expire-date'] || $['edit-expire-date'];
  var timeInput = $['add-expire-time'] || $['edit-expire-time'];
  if (!dateInput || !timeInput) return;
  var today = new Date();
  today.setDate(today.getDate() + days);
  var y = today.getFullYear();
  var m = String(today.getMonth() + 1).padStart(2, '0');
  var d = String(today.getDate()).padStart(2, '0');
  dateInput.value = y + '-' + m + '-' + d;
  timeInput.value = today.toTimeString().slice(0, 5);
}

function openAddModal() {
  $['add-modal'].classList.remove('hidden');
  $['add-modal'].classList.add('flex');
  $['continue-add'].checked = false;
  document.body.classList.add('modal-open');
}

function duplicateCert(certId) {
  var row = document.querySelector('tr[data-id="' + certId + '"]');
  var customer = row ? (row.dataset.customer || '') : '';
  showConfirmModal('确认复制', '确定复制「' + customer + '」的记录吗？', '确认复制', function() {
  var form = $['add-modal'].querySelector('form');
  form.reset();
  // 重置负责人勾选
  form.querySelectorAll('input[name="responsible_users"]').forEach(function(cb) { cb.checked = false; });
  fetch('/api/cert_status/' + certId)
    .then(function(r) { return r.json(); })
    .then(function(data) {
      if (!data.ok) { showToast('获取数据失败', 'error'); return; }
      form.querySelector('input[name="customer"]').value = data.customer || '';
      form.querySelector('input[name="cert_type"]').value = data.cert_type || '';
      // 到期时间加30天作为建议
      if (data.expire_date) {
        // 统一格式：支持 T 和空格分隔
        var dt = data.expire_date.replace('T', ' ').trim();
        var parts = dt.split(' ');
        var baseDate = parts[0] || '';
        var baseTime = parts[1] || '00:00';
        var d = new Date(baseDate.replace('-', '/', 'g').replace('/', '-', 1) + 'T' + baseTime);
        if (isNaN(d.getTime())) {
          // 尝试直接解析
          d = new Date(dt.replace(' ', 'T'));
        }
        d.setDate(d.getDate() + 30);
        var y = d.getFullYear();
        var m = String(d.getMonth() + 1).padStart(2, '0');
        var day = String(d.getDate()).padStart(2, '0');
        var hh = String(d.getHours()).padStart(2, '0');
        var mm = String(d.getMinutes()).padStart(2, '0');
        // 拆分到 date 和 time 两个 input
        form.querySelector('input[name="expire_date"]').value = y + '-' + m + '-' + day;
        form.querySelector('input[name="expire_time"]').value = hh + ':' + mm;
      }
      form.querySelector('textarea[name="note"]').value = data.note || '';
      form.querySelector('input[name="remind_enabled"]').checked = data.remind_enabled !== false;
      $['add-modal'].classList.remove('hidden');
      $['add-modal'].classList.add('flex');
      showToast('已复制到表单，修改到期时间后提交', 'info');
    })
    .catch(function(e) { showToast('加载失败', 'error'); });
  });
}

function closeAddModal() {
  $['add-modal'].classList.add('hidden');
  $['add-modal'].classList.remove('flex');
  document.body.classList.remove('modal-open');
}

// ── 编辑弹窗 ──────────────────────────
function openEditModal(certId) {
  var modal = $['edit-modal'];
  $['edit-cert-id'].value = certId;
  document.body.classList.add('modal-open');
  fetch('/api/cert_status/' + certId)
    .then(function(r) { return r.json(); })
    .then(function(data) {
      if (!data.ok) { showToast('获取数据失败', 'error'); return; }
      // 使用API返回的完整数据填充表单
      $['edit-customer'].value = data.customer || '';
      $['edit-cert-type'].value = data.cert_type || '';
      $['edit-domain'].value = data.domain || '';
      // 统一日期格式：支持 "2026-07-15T10:00" 和 "2026-07-15 10:00"
      var dt = data.expire_date || '';
      dt = dt.replace('T', ' ').trim();
      var parts = dt.split(' ');
      $['edit-expire-date'].value = parts[0] || '';
      $['edit-expire-time'].value = parts[1] || '00:00';
      $['edit-note'].value = data.note || '';
      $['edit-remind-enabled'].checked = data.remind_enabled !== false;
      $['edit-handled'].checked = data.handled === true;
      // 负责人复选框
      var responsibleUsers = data.responsible_users || [];
      if (typeof responsibleUsers === 'string') {
        try { responsibleUsers = JSON.parse(responsibleUsers); } catch(e) {}
      }
      var checkboxes = document.querySelectorAll('#edit-responsible-users input[name="responsible_users"]');
      checkboxes.forEach(function(cb) {
        cb.checked = responsibleUsers.indexOf(cb.value) >= 0;
        toggleEditRespLabel(cb.value, cb.checked);
      });
      modal.classList.remove('hidden');
      modal.classList.add('flex');
      lucide.createIcons();
    })
    .catch(function(e) { showToast('加载失败：' + e.message, 'error'); });
}

function closeEditModal() {
  $['edit-modal'].classList.add('hidden');
  $['edit-modal'].classList.remove('flex');
  document.body.classList.remove('modal-open');
}

function toggleEditRespLabel(username, checked) {
  var label = document.getElementById('edit-resp-label-' + username);
  if (!label) return;
  if (checked) {
    label.classList.add('border-blue-400', 'bg-blue-50');
  } else {
    label.classList.remove('border-blue-400', 'bg-blue-50');
  }
}

// 表单AJAX提交
$['edit-cert-form'].addEventListener('submit', function(e) {
  e.preventDefault();
  var certId = $['edit-cert-id'].value;
  var formData = new FormData(this);
  var payload = {};
  formData.forEach(function(v, k) {
    if (k === 'remind_enabled' || k === 'handled') {
      payload[k] = true;  // checkbox checked
    } else {
      payload[k] = v;
    }
  });
  // Handle checkboxes properly
  payload['remind_enabled'] = $['edit-remind-enabled'].checked;
  payload['handled'] = $['edit-handled'].checked;
  // 合并日期和时间（格式: YYYY-MM-DD HH:mm）
  var dateVal = $['edit-expire-date'].value;
  var timeVal = $['edit-expire-time'].value;
  if (dateVal && timeVal) {
    payload['expire_date'] = dateVal + ' ' + timeVal;
  } else if (dateVal) {
    payload['expire_date'] = dateVal;
  }
  var respUsers = [];
  document.querySelectorAll('#edit-responsible-users input[name="responsible_users"]:checked').forEach(function(cb) {
    respUsers.push(cb.value);
  });
  payload['responsible_users'] = respUsers;

  var submitBtn = this.querySelector('button[type=submit]');
  var origLabel = submitBtn.innerHTML;
  submitBtn.disabled = true;
  submitBtn.innerHTML = '<svg class="animate-spin w-4 h-4 inline-block mr-1" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="3" fill="none" opacity=".25"/><path d="M4 12a8 8 0 018-8" stroke="currentColor" stroke-width="3" fill="none"/></svg> 保存中…';

  fetch('/edit/' + certId, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': _csrfToken },
    body: JSON.stringify(payload)
  })
  .then(function(r) {
    if (r.url && r.url.includes('/login')) { window.location.href = '/login'; throw new Error('redirect'); }
    return r.json ? r.json() : {}; })
  .then(function(data) {
    if (data.csrf_token) _csrfToken = data.csrf_token;
    if (data.success || data.ok) {
      closeEditModal();
      showToast('保存成功', 'success');
      // AJAX局部更新该行
      fetch('/api/cert_status/' + certId)
        .then(function(r2) { return r2.json(); })
        .then(function(sdata) {
          if (sdata.ok && sdata.badge_html !== undefined) {
            var row = document.querySelector('tr[data-id="' + certId + '"]');
            if (row) {
              // 更新data属性
              row.dataset.customer = document.getElementById('edit-customer').value;
              row.dataset.type = document.getElementById('edit-cert-type').value;
              row.dataset.expire = document.getElementById('edit-expire-date').value;
              row.dataset.note = document.getElementById('edit-note').value;
              row.dataset.handled = document.getElementById('edit-handled').checked;
              // 更新各列
              var cells = row.querySelectorAll('td');
              // 客户名称列
              if (cells[1]) {
                var nameSpan = cells[1].querySelector('span');
                if (nameSpan) nameSpan.textContent = document.getElementById('edit-customer').value;
              }
              // 类型列
              if (cells[2]) {
                var typeSpan = cells[2].querySelector('span');
                if (typeSpan) typeSpan.textContent = document.getElementById('edit-cert-type').value;
              }
              // 到期日期列
              if (cells[3]) {
                var dateSpan = cells[3].querySelector('span');
                if (dateSpan) dateSpan.textContent = (document.getElementById('edit-expire-date').value || '').replace('T', ' ');
              }
              // domain 列（如果有）
              if (cells.length > 5 && cells[5] && !cells[5].classList.contains('hidden')) {
                var domainSpan = cells[5].querySelector('span');
                if (domainSpan) domainSpan.textContent = document.getElementById('edit-domain').value || '-';
              }
              // 状态列
              if (cells[4]) {
                cells[4].innerHTML = sdata.badge_html;
              }
              lucide.createIcons();
            }
          } else { location.reload(); }
        })
        .catch(function(e) { console.error('cert_status refresh error:', e); });
    } else { showToast(data.message || '保存失败', 'error'); }
  })
  .catch(function(e) { 
    if (e.message !== 'redirect') showToast('网络错误：' + e.message, 'error'); 
  })
  .finally(function() { submitBtn.disabled = false; submitBtn.innerHTML = origLabel; });
});


// ── 添加表单 AJAX 提交（支持继续添加）──────────────────
$['add-modal'].querySelector('form').addEventListener('submit', function(e) {
  e.preventDefault();
  var form = e.target;
  var btn = form.querySelector('button[type="submit"]');
  var continueAdd = $['continue-add'].checked;
  btn.disabled = true;
  btn.textContent = '添加中…';

  // 合并日期和时间（格式: YYYY-MM-DD HH:mm）
  // 注意：不要修改DOM中的expire_date输入框，否则后端再次拼接会导致"2027-07-02 10:30 10:30"
  var dateVal = $['add-expire-date'].value;
  var timeVal = $['add-expire-time'].value;
  var combined = '';
  if (dateVal && timeVal) {
    combined = dateVal + ' ' + timeVal;
  } else if (dateVal) {
    combined = dateVal;
  }
  // 通过隐藏字段传递合并后的值（不修改DOM）
  var hiddenField = document.createElement('input');
  hiddenField.type = 'hidden';
  hiddenField.name = 'expire_date_combined';
  hiddenField.value = combined;
  form.appendChild(hiddenField);

  fetch(form.action, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded', 'X-Requested-With': 'XMLHttpRequest', 'X-CSRF-Token': _csrfToken },
    body: new URLSearchParams(new FormData(form))
  }).then(function(r) {
    if (r.url && r.url.includes('/login')) {
      window.location.href = '/login';
      throw new Error('redirect');
    }
    if (!r.ok) {
      return r.text().then(function(text) {
        throw new Error('HTTP ' + r.status + ': ' + text.substring(0, 200));
      });
    }
    return r.json();
  }).then(function(data) {
    // console.log('Add response:', data);
    if (data.csrf_token) _csrfToken = data.csrf_token;
    form.querySelectorAll('input[name="_csrf_token"]').forEach(function(inp) { inp.value = data.csrf_token || _csrfToken; });
    if (!data.ok) {
      showToast('添加失败: ' + (data.message || '未知错误'), 'error');
      return;
    }
    if (continueAdd) {
      // 重置表单（保留负责人和提醒开关）
      form.querySelector('input[name="customer"]').value = '';
      form.querySelector('input[name="cert_type"]').value = '';
      form.querySelector('input[name="expire_date"]').value = '';
      form.querySelector('input[name="expire_time"]').value = '';
      form.querySelector('textarea[name="note"]').value = '';
      form.querySelectorAll('input[name="responsible_users"]').forEach(function(cb) { cb.checked = false; });
      form.querySelector('input[name="customer"]').focus();
      showToast('添加成功！继续添加下一条…', 'success');
    } else {
      closeAddModal();
      showToast('添加成功！', 'success');
      setTimeout(function() { location.reload(); }, 800);
    }
  }).catch(function(e) {
    if (e.message !== 'redirect') {
      showToast('添加失败，请重试', 'error');
    }
  }).finally(function() {
    btn.disabled = false;
    btn.textContent = '添加';
  });
});

// ── 点击外部关闭下拉菜单 ──────────────────────────────
document.addEventListener('click', function(e) {
  var ad = document.getElementById('admin-dropdown');
  if (ad && !ad.contains(e.target)) {
    document.getElementById('admin-menu').classList.add('hidden');
  }
});


// ── 图表切换 ────────────────────────────────────────────
function toggleChart() {
  var chartBody = $['chart-body'];
  var chartToggle = $['chart-toggle'];
  if (chartBody.classList.contains('hidden')) {
    chartBody.classList.remove('hidden');
    chartToggle.innerHTML = '<i data-lucide="chevron-down" class="w-4 h-4 inline-block"></i> 收起图表';
  } else {
    chartBody.classList.add('hidden');
    chartToggle.innerHTML = '<i data-lucide="chevron-up" class="w-4 h-4 inline-block"></i> 展开图表';
  }
  if (typeof lucide !== 'undefined') lucide.createIcons();
}

// ── 移动端菜单 ────────────────────────────────────────
function toggleMobileMenu() {
  var menu = document.getElementById('mobile-menu');
  if (menu) menu.classList.toggle('hidden');
}
// 点击外部关闭移动端菜单和管理员下拉菜单
document.addEventListener('click', function(e) {
  var mobileMenu = document.getElementById('mobile-menu');
  if (mobileMenu && !mobileMenu.classList.contains('hidden')) {
    var hamburger = document.querySelector('button[aria-label="菜单"]');
    if (hamburger && !hamburger.contains(e.target)) {
      mobileMenu.classList.add('hidden');
    }
  }
});
function toggleAdminMenu() {
  document.getElementById('admin-menu').classList.toggle('hidden');
}

// ── 批量操作 ──────────────────────────────────────────
function getSelectedIds() {
  var checkboxes = document.querySelectorAll('.row-checkbox:checked');
  return Array.from(checkboxes).map(cb => parseInt(cb.value));
}

function updateBatchUI() {
  var ids = getSelectedIds();
  var count = ids.length;
  var countEl = $['selected-count'];
  if (countEl) countEl.textContent = '已选 ' + count + ' 条';

  var btns = ['btn-batch-handle', 'btn-batch-unhandle', 'btn-batch-remind-on', 'btn-batch-remind-off', 'btn-batch-delete'];
  btns.forEach(function(id) {
    var btn = document.getElementById(id);
    if (btn) btn.disabled = count === 0;
  });

  // Update select-all checkbox state
  var allCheckboxes = document.querySelectorAll('.row-checkbox');
  var selectAllHeader = $['select-all-header'];
  var selectAllToolbar = $['select-all'];
  var allChecked = allCheckboxes.length > 0 && count === allCheckboxes.length;
  if (selectAllHeader) selectAllHeader.checked = allChecked;
  if (selectAllToolbar) selectAllToolbar.checked = allChecked;
}

function toggleSelectAll() {
  var checkboxes = document.querySelectorAll('.row-checkbox');
  var selectAllHeader = $['select-all-header'];
  var selectAllToolbar = $['select-all'];
  var isChecked = selectAllHeader ? selectAllHeader.checked : (selectAllToolbar ? selectAllToolbar.checked : false);
  // Sync both select-all checkboxes
  if (selectAllHeader) selectAllHeader.checked = isChecked;
  if (selectAllToolbar) selectAllToolbar.checked = isChecked;
  checkboxes.forEach(function(cb) { cb.checked = isChecked; });
  updateBatchUI();
}

// ── 通用确认弹窗 ────────────────────────────────────────
function showConfirmModal(title, message, okText, okCallback) {
  $['confirm-title'].textContent = title;
  $['confirm-msg'].textContent = message;
  $['confirm-ok'].textContent = okText || '确认';
  $['confirm-ok'].onclick = function() {
    closeConfirmModal();
    if (okCallback) okCallback();
  };
  $['confirm-modal'].classList.remove('hidden');
  $['confirm-modal'].classList.add('flex');
  document.body.classList.add('modal-open');
}
function closeConfirmModal() {
  $['confirm-modal'].classList.add('hidden');
  $['confirm-modal'].classList.remove('flex');
  document.body.classList.remove('modal-open');
}

// ESC 键关闭确认弹窗
document.addEventListener('keydown', function(e) {
  if (e.key === 'Escape') {
    var confirmModal = $['confirm-modal'];
    if (confirmModal && !confirmModal.classList.contains('hidden')) {
      closeConfirmModal();
    }
  }
});

// ── 行操作下拉菜单 ────────────────────────────────────────
function closeRowMenu(certId) {
  var dd = $['row-menu-' + certId];
  if (dd) dd.classList.add('hidden');
}

function toggleRowMenu(certId, btnEl, evt) {
  var dd = $['row-menu-' + certId];
  if (!dd) return;
  var wasHidden = dd.classList.contains('hidden');
  // 先关闭所有其他菜单并重置 aria-expanded
  document.querySelectorAll('[id^="row-menu-"]').forEach(function(m) {
    if (m.id !== 'row-menu-' + certId) m.classList.add('hidden');
  });
  document.querySelectorAll('[data-row-menu-btn]').forEach(function(btn) {
    btn.setAttribute('aria-expanded', 'false');
  });
  btnEl.setAttribute('aria-expanded', String(!wasHidden));
  if (wasHidden) {
    dd.classList.remove('hidden');
    // 计算按钮位置，用 fixed 定位菜单
    var rect = btnEl.getBoundingClientRect();
    dd.style.top = (rect.bottom + 4) + 'px';
    dd.style.right = 'auto';
    dd.style.left = rect.left + 'px';
    // 边界检测：如果菜单超出视口底部，往上弹
    var ddRect = dd.getBoundingClientRect();
    if (ddRect.bottom > window.innerHeight) {
      dd.style.top = (rect.top - ddRect.height - 4) + 'px';
    }
    // 如果菜单超出视口右侧，靠右对齐
    if (ddRect.right > window.innerWidth) {
      dd.style.left = '';
      dd.style.right = (window.innerWidth - rect.right) + 'px';
    }
  }
  // 按钮点击反馈
  if (btnEl) {
    btnEl.classList.add('bg-gray-100');
    setTimeout(function() { btnEl.classList.remove('bg-gray-100'); }, 200);
  }
  if (evt) evt.stopPropagation();
}

// 关闭行操作菜单（点击外部时）
document.addEventListener('click', function(e) {
  document.querySelectorAll('[id^="row-menu-"]').forEach(function(dd) {
    if (dd.classList.contains('hidden')) return;
    // 点击菜单内部不关闭
    if (dd.contains(e.target)) return;
    var confirmModal = document.getElementById('confirm-modal');
    if (confirmModal && !confirmModal.classList.contains('hidden')) return;
    dd.classList.add('hidden');
  });
});

// ── 批量下拉菜单 ────────────────────────────────────────
function toggleBatchDropdown() {
  var dd = $['batch-dropdown'];
  dd.classList.toggle('hidden');
}
document.addEventListener('click', function(e) {
  var dd = document.getElementById('batch-dropdown');
  var btn = document.querySelector('[data-batch-dropdown=""]');
  if (dd && !dd.contains(e.target) && btn && !btn.contains(e.target)) {
    dd.classList.add('hidden');
  }
});
function confirmDelete(certId, customerName) {
  showConfirmModal('确认删除', '确定删除「' + customerName + '」的记录？此操作不可恢复。', '确认删除', function() {
    var row = document.querySelector('tr[data-id="' + certId + '"]');
    var btn = row ? row.querySelector('button[onclick*="confirmDelete"]') : null;
    if (btn) { btn.disabled = true; btn.style.opacity = '0.5'; }
    fetch('/api/cert/' + certId, {
      method: 'DELETE',
      headers: { 'X-CSRF-Token': _csrfToken }
    })
    .then(function(r) { return r.json(); })
    .then(function(data) {
      if (data.csrf_token) _csrfToken = data.csrf_token;
      if (data.ok) {
        var row = document.querySelector('tr[data-id="' + certId + '"]');
        if (row) row.remove();
        showToast('删除成功', 'success');
      } else { showToast(data.message || '删除失败', 'error'); }
    })
    .catch(function(e) { showToast('网络错误：' + e.message, 'error'); })
    .finally(function() {
      if (btn) { btn.disabled = false; btn.style.opacity = '1'; }
    });
  });
}

function batchDelete() {
  var ids = getSelectedIds();
  if (ids.length === 0) return;
  var names = Array.from(document.querySelectorAll('.row-checkbox:checked'))
    .map(function(cb) { return cb.closest('tr').querySelector('td:nth-child(2) span').textContent.trim(); })
    .slice(0, 5);
  var msg = ids.length + ' 条记录';
  if (names.length > 0) msg += '：' + names.join('、') + (ids.length > 5 ? '…' : '');
  showConfirmModal('确认删除', msg + '？此操作不可恢复。', '确认删除', function() {
    fetch('/api/batch_delete', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': _csrfToken },
      body: JSON.stringify({ ids: ids })
    })
    .then(function(r) {
      var ct = r.headers.get('content-type') || '';
      if (!ct.includes('application/json')) {
        return r.text().then(function(txt) { throw new Error('服务端返回非JSON: ' + txt.substring(0, 150)); });
      }
      return r.json();
    })
    .then(function(data) {
      if (data.csrf_token) _csrfToken = data.csrf_token;
      if (data.ok) {
        var ids = data.deleted_ids || [];
        ids.forEach(function(id) {
          var row = document.querySelector('tr[data-id="' + id + '"]');
          if (row) row.remove();
        });
        showToast('删除成功', 'success');
      }
      else { showToast(data.message || '删除失败', 'error'); }
    })
    .catch(function(e) { 
        console.error('Batch delete error:', e);
        showToast('网络错误：' + e.message, 'error'); 
      });
  });
}

function batchHandle(handled) {
  var ids = getSelectedIds();
  if (ids.length === 0) return;
  var btnId = handled ? 'btn-batch-handle' : 'btn-batch-unhandle';
  var btn = document.getElementById(btnId);
  var origLabel = handled ? '标记已处理' : '取消已处理';
  btn.disabled = true; btn.innerHTML = '<svg class="animate-spin w-3.5 h-3.5 inline-block mr-1" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="3" fill="none" opacity=".25"/><path d="M4 12a8 8 0 018-8" stroke="currentColor" stroke-width="3" fill="none"/></svg> 处理中…';
  fetch('/api/batch_handle', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': _csrfToken },
    body: JSON.stringify({ ids: ids, handled: handled })
  })
  .then(function(r) {
    var ct = r.headers.get('content-type') || '';
    if (!ct.includes('application/json')) {
      return r.text().then(function(txt) { throw new Error('服务端返回非JSON: ' + txt.substring(0, 150)); });
    }
    return r.json();
  })
  .then(function(data) {
    if (data.csrf_token) _csrfToken = data.csrf_token;
    if (data.ok) { _searchCacheDirty = true; filterTable(); }
    else { showToast(data.message || '操作失败', 'error'); btn.disabled = false; btn.innerHTML = origLabel; }
  })
  .catch(function(e) { showToast('网络错误：' + e.message, 'error'); btn.disabled = false; btn.innerHTML = origLabel; });
}

function batchRemind(remind_enabled) {
  var ids = getSelectedIds();
  if (ids.length === 0) return;
  var btnId = remind_enabled ? 'btn-batch-remind-on' : 'btn-batch-remind-off';
  var btn = document.getElementById(btnId);
  var origLabel = remind_enabled ? '启用提醒' : '禁用提醒';
  btn.disabled = true; btn.innerHTML = '<svg class="animate-spin w-3.5 h-3.5 inline-block mr-1" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="3" fill="none" opacity=".25"/><path d="M4 12a8 8 0 018-8" stroke="currentColor" stroke-width="3" fill="none"/></svg> 处理中…';
  fetch('/api/batch_remind', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': _csrfToken },
    body: JSON.stringify({ ids: ids, remind_enabled: remind_enabled })
  })
  .then(function(r) {
    var ct = r.headers.get('content-type') || '';
    if (!ct.includes('application/json')) {
      return r.text().then(function(txt) { throw new Error('服务端返回非JSON: ' + txt.substring(0, 150)); });
    }
    return r.json();
  })
  .then(function(data) {
    if (data.csrf_token) _csrfToken = data.csrf_token;
    if (data.ok) { _searchCacheDirty = true; filterTable(); }
    else { showToast(data.message || '操作失败', 'error'); btn.disabled = false; btn.innerHTML = origLabel; }
  })
  .catch(function(e) { showToast('网络错误：' + e.message, 'error'); btn.disabled = false; btn.innerHTML = origLabel; });
}

// ── 排序 ────────────────────────────────────────────────
let sortKey = 'days_left';
let sortDesc = true;

function sortTable(key) {
  if (sortKey === key) sortDesc = !sortDesc;
  else { sortKey = key; sortDesc = true; }
  filterTable();
}

// ── 分页 ──────────────────────────────────────────
let currentPage = 1;
let perPage = parseInt(localStorage.getItem('perPage') || '20');

// ── 行选择高亮 ────────────────────────────────────────────────
function onRowSelect(checkbox, certId) {
  var row = document.querySelector('tr[data-id="' + certId + '"]');
  if (row) {
    row.classList.toggle('selected-row', checkbox.checked);
  }
  updateBatchUI();
}

// ── 筛选 ────────────────────────────────────────────────
function filterTable() {
  const search = ($['search-input'] || document.getElementById('search-input')).value.trim().toLowerCase();
  const statusFilter = ($['filter-status'] || document.getElementById('filter-status')).value;
  const typeFilter = ($['filter-type'] || document.getElementById('filter-type')).value;
  const dateFrom = ($['filter-date-from'] || document.getElementById('filter-date-from')).value;
  const dateTo = ($['filter-date-to'] || document.getElementById('filter-date-to')).value;
  const rows = document.querySelectorAll('#cert-tbody tr');
  let visible = 0;
  const today = new Date(); today.setHours(0,0,0,0);

  rows.forEach(row => {
    const customer = row.dataset.customer.toLowerCase();
    const status = row.dataset.status;
    const certType = row.dataset.type;
    const days = parseInt(row.dataset.days) || 0;
    const handled = row.dataset.handled === 'true';

    const certTypeL = certType.toLowerCase(); const note = (row.dataset.note || '').toLowerCase();
    const matchSearch = !search || customer.includes(search) || certTypeL.includes(search) || note.includes(search);
    let matchStatus = true;
    if (statusFilter) {
      if (statusFilter === 'handled') matchStatus = handled;
      else if (statusFilter === 'unhandled') matchStatus = !handled;
      else if (statusFilter === 'mine') matchStatus = row.dataset.createdby === currentUser;
      else matchStatus = status === statusFilter;
    }
    const matchType = !typeFilter || certType === typeFilter;

    let matchDate = true;
    if (dateFrom || dateTo) {
      const expireDate = new Date(today); expireDate.setDate(expireDate.getDate() + days);
      if (dateFrom) { const f = new Date(dateFrom); if (expireDate < f) matchDate = false; }
      if (dateTo) { const t = new Date(dateTo); t.setDate(t.getDate()+1); if (expireDate >= t) matchDate = false; }
    }

    row.style.display = (matchSearch && matchStatus && matchType && matchDate) ? '' : 'none';
    if (row.style.display !== 'none') visible++;
  });

  // 排序可见行（使用 DocumentFragment 减少重排）
  const tbody = $['cert-tbody'] || document.getElementById('cert-tbody');
  const visibleRows = Array.from(tbody.querySelectorAll('tr')).filter(r => r.style.display !== 'none');
  visibleRows.sort((a, b) => {
    let va, vb;
    switch (sortKey) {
      case 'days_left': va = parseInt(a.dataset.days)||-999; vb = parseInt(b.dataset.days)||-999; break;
      case 'customer': va = a.dataset.customer; vb = b.dataset.customer; break;
      case 'cert_type': va = a.dataset.type; vb = b.dataset.type; break;
      case 'expire_date':
        va = a.dataset.expire || '';
        vb = b.dataset.expire || ''; break;
      default: va = -999; vb = -999;
    }
    if (sortKey === 'days_left' || sortKey === 'expire_date')
      return sortDesc ? (va > vb ? -1 : 1) : (va < vb ? -1 : 1);
    return sortDesc ? va.localeCompare(vb, 'zh') : vb.localeCompare(va, 'zh');
  });
  // 使用 DocumentFragment 一次性移动 DOM 节点
  const frag = document.createDocumentFragment();
  visibleRows.forEach(row => {
    row.classList.add('row-animate');
    frag.appendChild(row);
  });
  tbody.appendChild(frag);

  // 分页
  const totalPages = Math.max(1, Math.ceil(visible / perPage));
  if (currentPage > totalPages) currentPage = totalPages;
  const start = (currentPage - 1) * perPage;
  visibleRows.forEach((row, i) => {
    row.style.display = (i >= start && i < start + perPage) ? '' : 'none';
  });

  // 渲染分页
  const pageInfo = $['page-info'];
  const pageButtons = $['page-buttons'];
  if (pageInfo) pageInfo.textContent = '第 ' + currentPage + '/' + totalPages + ' 页，共 ' + visible + ' 条';
  if (pageButtons) {
    let html = '';
    if (currentPage > 1) html += '<button onclick="goPage('+(currentPage-1)+')" class="px-3 py-1 border border-gray-200 rounded hover:bg-gray-100" aria-label="上一页">上一页</button>';
    const maxBtns = 5; let startP = Math.max(1, currentPage-2); let endP = Math.min(totalPages, startP+maxBtns-1);
    if (endP-startP < maxBtns-1) startP = Math.max(1, endP-maxBtns+1);
    for (let p=startP; p<=endP; p++) {
      const active = p===currentPage ? 'bg-blue-600 text-white border-blue-600':'border-gray-200 hover:bg-gray-100';
      html += '<button onclick="goPage('+p+')" class="px-3 py-1 border rounded '+active+'" aria-label="第'+p+'页">'+p+'</button>';
    }
    if (currentPage < totalPages) html += '<button onclick="goPage('+(currentPage+1)+')" class="px-3 py-1 border border-gray-200 rounded hover:bg-gray-100" aria-label="下一页">下一页</button>';
    pageButtons.innerHTML = html;
  }

  // 更新排序图标
  document.querySelectorAll('.sort-icon').forEach(el => { el.textContent = ''; });
  const activeIcon = document.querySelector(`.sort-icon[data-col="${sortKey}"]`);
  if (activeIcon) activeIcon.textContent = sortDesc ? ' ▼' : ' ▲';

  // 更新最后时间
  updateLastTime();
  
  // 隐藏骨架屏
  var sk = $['skeleton-loading'];
  if (sk) sk.classList.add('hidden');
}

// ── 每页展示数量 ────────────────────────────────────────────
function changePerPage(val) {
  perPage = parseInt(val) || 20;
  localStorage.setItem('perPage', String(perPage));
  currentPage = 1;
  filterTable();
}

// ── 搜索建议 ────────────────────────────────────────────
var _searchCache = [];
var _searchCacheDirty = true;

function _buildSearchCache() {
  if (!_searchCacheDirty) return;
  _searchCache = [];
  var rows = document.querySelectorAll('#cert-tbody tr');
  rows.forEach(function(row) {
    var customer = row.dataset.customer;
    var certType = row.dataset.type;
    if (customer && _searchCache.indexOf(customer) === -1) _searchCache.push(customer);
    if (certType && _searchCache.indexOf(certType) === -1) _searchCache.push(certType);
  });
  _searchCache.sort();
  _searchCacheDirty = false;
}

function showSearchSuggestions(query) {
  if (!query || query.length < 1) { hideSearchSuggestions(); return; }
  _buildSearchCache();
  var container = $['search-suggestions'];
  var lower = query.toLowerCase();
  var matches = _searchCache.filter(function(item) { return item.toLowerCase().includes(lower); }).slice(0, 8);
  if (matches.length === 0) { hideSearchSuggestions(); return; }
  var html = '';
  matches.forEach(function(m, i) {
    var escaped = m.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
    html += '<div class="px-3 py-2 text-sm text-gray-700 hover:bg-blue-50 cursor-pointer' + (i === 0 ? ' bg-blue-50' : '') + '" data-index="' + i + '" onclick="selectSuggestion(' + i + ')">' + escaped + '</div>';
  });
  container.innerHTML = html;
  container.classList.remove('hidden');
}

function hideSearchSuggestions() {
  var container = $['search-suggestions'];
  if (container) container.classList.add('hidden');
}

function selectSuggestion(index) {
  var container = $['search-suggestions'];
  if (!container || container.classList.contains('hidden')) return;
  var items = container.querySelectorAll('div');
  if (items[index]) {
    ($['search-input'] || document.getElementById('search-input')).value = items[index].textContent;
    hideSearchSuggestions();
    filterTable();
  }
}

// ── 重置筛选 ────────────────────────────────────────────
function resetFilters() {
  ($['search-input'] || document.getElementById('search-input')).value = '';
  ($['filter-status'] || document.getElementById('filter-status')).value = '';
  ($['filter-type'] || document.getElementById('filter-type')).value = '';
  ($['filter-date-from'] || document.getElementById('filter-date-from')).value = '';
  ($['filter-date-to'] || document.getElementById('filter-date-to')).value = '';
  _searchCacheDirty = true;
  filterTable();
}

// ── 最后更新时间 ────────────────────────────────────────────
function updateLastTime() {
  var el = $['last-update-time'];
  if (el) {
    var now = new Date();
    var h = String(now.getHours()).padStart(2, '0');
    var m = String(now.getMinutes()).padStart(2, '0');
    var s = String(now.getSeconds()).padStart(2, '0');
    el.textContent = '更新于 ' + h + ':' + m + ':' + s;
  }
}

// ── 键盘快捷键 ────────────────────────────────────────────
document.addEventListener('keydown', function(e) {
  // Ctrl+K 聚焦搜索
  if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
    e.preventDefault();
    ($['search-input'] || document.getElementById('search-input')).focus();
  }
  // Ctrl+N 新建记录
  if ((e.ctrlKey || e.metaKey) && e.key === 'n') {
    e.preventDefault();
    openAddModal();
  }
  // Escape 关闭弹窗
  if (e.key === 'Escape') {
    hideSearchSuggestions();
    if (!$['add-modal']?.classList.contains('hidden')) { closeAddModal(); return; }
    if (!$['edit-modal']?.classList.contains('hidden')) { closeEditModal(); return; }
    if (!$['confirm-modal']?.classList.contains('hidden')) { closeConfirmModal(); return; }
  }
});

function goPage(p) { currentPage = p; filterTable(); }

// ── CSRF Token ──────────────────────────────────────────
window._csrfToken = "{{ csrf_token }}";
let currentUser = "{{ current_username }}";

// ── API 操作 ────────────────────────────────────────────
function toggleStatus(certId) {
  var row = document.querySelector('tr[data-id="' + certId + '"]');
  var btn = row ? row.querySelector('button[onclick*="toggleStatus"]') : null;
  if (btn) { btn.disabled = true; btn.style.opacity = '0.5'; }
  fetch('/api/status/' + certId, { method: 'POST', headers: { 'X-CSRF-Token': _csrfToken } })
    .then(function(r) { return r.json(); })
    .then(function(data) {
      if (data.csrf_token) _csrfToken = data.csrf_token;
      if (!data.ok) { showToast('操作失败', 'error'); return; }
      var row = document.querySelector('tr[data-id="' + certId + '"]');
      if (row && data.badge_html !== undefined) {
        var nth = document.querySelector('.row-checkbox') ? 5 : 4;
        var statusCell = row.querySelector('td:nth-child(' + nth + ')');
        if (statusCell) { statusCell.innerHTML = data.badge_html; lucide.createIcons(); }
      } else { location.reload(); }
    })
    .catch(function() { showToast('操作失败，请重试', 'error'); })
    .finally(function() { if (btn) { btn.disabled = false; btn.style.opacity = '1'; } });
}

function toggleHandled(certId) {
  var row = document.querySelector('tr[data-id="' + certId + '"]');
  var btn = row ? row.querySelector('button[onclick*="toggleHandled"]') : null;
  var customer = row ? (row.dataset.customer || '') : '';
  var isHandled = row ? (row.dataset.handled === 'true' || row.dataset.handled === 'True') : false;
  var actionText = isHandled ? '取消已处理' : '标记已处理';
  
  showConfirmModal('确认操作', '确定' + actionText + '「' + customer + '」吗？', '确认', function() {
    if (btn) { btn.disabled = true; btn.style.opacity = '0.5'; }
    fetch('/api/handle/' + certId, { method: 'POST', headers: { 'X-CSRF-Token': _csrfToken } })
      .then(function(r) { return r.json(); })
      .then(function(data) {
        if (data.csrf_token) _csrfToken = data.csrf_token;
        if (!data.ok) { showToast('操作失败', 'error'); return; }
        location.reload();
      })
      .catch(function() { showToast('操作失败，请重试', 'error'); })
      .finally(function() { if (btn) { btn.disabled = false; btn.style.opacity = '1'; } });
  });
}

// ── 手动推送 ────────────────────────────────────────────
function pushCert(certId, customerName) {
  showConfirmModal('确认推送', '确定向钉钉推送「' + customerName + '」的到期提醒？', '确认推送', function() {
    var row = document.querySelector('tr[data-id="' + certId + '"]');
    var btn = row ? row.querySelector('button[onclick*="pushCert"]') : null;
    if (btn) { btn.disabled = true; }
    fetch('/api/push/' + certId, { method: 'POST', headers: { 'X-CSRF-Token': _csrfToken } })
      .then(function(r) {
        if (r.url && r.url.includes('/login')) {
          window.location.href = '/login';
          throw new Error('redirect');
        }
        return r.json();
      })
      .then(function(data) {
        if (data.csrf_token) _csrfToken = data.csrf_token;
        if (data.ok) { showToast('推送成功！', 'success'); }
        else { showToast('推送失败：' + (data.message || '未知错误'), 'error'); }
      })
      .catch(function(e) {
        if (e.message !== 'redirect') { showToast('网络错误：' + e.message, 'error'); }
      })
      .finally(function() { if (btn) btn.disabled = false; });
  });
}


// ── 使用说明折叠（首次访问自动展开）──────────────────────
function toggleHelp() {
  var content = $['help-content'];
  var chevron = $['help-chevron'];
  if (content.classList.contains('hidden')) {
    content.classList.remove('hidden');
    chevron.setAttribute('data-lucide', 'chevron-up');
    localStorage.setItem('help-expanded', 'true');
  } else {
    content.classList.add('hidden');
    chevron.setAttribute('data-lucide', 'chevron-down');
    localStorage.setItem('help-expanded', 'false');
  }
  if (typeof lucide !== 'undefined') lucide.createIcons();
}
(function() {
  if (!localStorage.getItem('help-expanded')) {
    // 首次访问，自动展开一次
    setTimeout(function() {
      var content = document.getElementById('help-content');
      var chevron = document.getElementById('help-chevron');
      if (content) content.classList.remove('hidden');
      if (chevron) chevron.setAttribute('data-lucide', 'chevron-up');
      if (typeof lucide !== 'undefined') lucide.createIcons();
    }, 500);
  }
})();


// ── 计数动画 ──────────────────────────────────────────
function animateCounters() {
  var counters = document.querySelectorAll('[data-count]');
  counters.forEach(function(el) {
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

// 初始排序
filterTable();
// 初始化排序图标
var daysIcon = document.querySelector('.sort-icon[data-col="days_left"]');
if (daysIcon) daysIcon.textContent = ' ▼';

// 初始化每页展示选择器
var ppSel = $['per-page-select'] || document.getElementById('per-page-select');
if (ppSel) ppSel.value = perPage;

// ── 快速筛选（点击统计卡片）──────────────────────────────
function quickFilter(status) {
  var statusSelect = $['filter-status'] || document.getElementById('filter-status');
  var searchInput = $['search-input'] || document.getElementById('search-input');
  if (status === 'all') {
    statusSelect.value = '';
    searchInput.value = '';
  } else {
    statusSelect.value = status;
  }
  currentPage = 1;
  // 视觉反馈：点击时短暂高亮
  var map = { normal: ['green', 'ring-green-300', 'bg-green-50'], expiring: ['orange', 'ring-orange-300', 'bg-orange-50'], expired: ['red', 'ring-red-300', 'bg-red-50'] };
  if (status !== 'all') {
    var info = map[status];
    var ringClass = info[1];
    var bgClass = info[2];
    var selector = '[onclick="quickFilter(\'' + status + '\')"]';
    var activeCard = document.querySelector(selector);
    if (activeCard) {
      activeCard.classList.add(ringClass, 'ring-2', bgClass);
      setTimeout(function() {
        activeCard.classList.remove(ringClass, 'ring-2', bgClass);
      }, 300);
    }
  }
  filterTable();
  // 视觉反馈：高亮当前筛选的统计卡片
  document.querySelectorAll('[onclick^="quickFilter"]').forEach(function(card) {
    card.classList.remove('ring-2', 'ring-offset-2', 'ring-blue-500');
  });
  if (status !== 'all') {
    var map = { normal: ['green', 'ring-green-300', 'bg-green-50'], expiring: ['orange', 'ring-orange-300', 'bg-orange-50'], expired: ['red', 'ring-red-300', 'bg-red-50'] };
    var info = map[status];
    var color = info[0];
    var ringClass = info[1];
    var bgClass = info[2];
    var selector = '[onclick="quickFilter(\'' + status + '\')"]';
    var activeCard = document.querySelector(selector);
    if (activeCard) {
      activeCard.classList.add(ringClass, 'ring-2');
      activeCard.classList.add(bgClass);
    }
  }
  // 滚动到表格
  ($['cert-tbody'] || document.getElementById('cert-tbody')).scrollIntoView({ behavior: 'smooth', block: 'start' });
}
