// data_manage.js — 数据管理页面专用 JS
(function () {
  'use strict';

  var _csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';
  var previewData = null;

  window.switchTab = function (tab) {
    document.getElementById('panel-import').classList.add('hidden');
    document.getElementById('panel-export').classList.add('hidden');
    document.getElementById('panel-json').classList.add('hidden');
    ['import', 'export', 'json'].forEach(function (t) {
      var el = document.getElementById('tab-' + t);
      el.classList.remove('border-blue-600', 'text-blue-600');
      el.classList.add('border-transparent', 'text-gray-500');
    });
    document.getElementById('panel-' + tab).classList.remove('hidden');
    var activeTab = document.getElementById('tab-' + tab);
    activeTab.classList.remove('border-transparent', 'text-gray-500');
    activeTab.classList.add('border-blue-600', 'text-blue-600');
  };

  window.showResult = function (ok, msg) {
    var area = document.getElementById('result-area');
    area.classList.remove('hidden', 'bg-green-50', 'text-green-700', 'border-green-200', 'bg-red-50', 'text-red-700', 'border-red-200');
    if (ok) {
      area.classList.add('bg-green-50', 'text-green-700', 'border', 'border-green-200');
      area.innerHTML = '<span style="font-size:14px"><i data-lucide="check-circle-2" class="w-4 h-4 inline-block text-green-600 mr-1"></i></span> ' + msg;
    } else {
      area.classList.add('bg-red-50', 'text-red-700', 'border', 'border-red-200');
      area.innerHTML = '<span style="font-size:14px"><i data-lucide="x-circle" class="w-4 h-4 inline-block text-red-600 mr-1"></i></span> ' + msg;
    }
    if (typeof lucide !== 'undefined') lucide.createIcons();
  };

  window.onFileSelected = function (event) {
    var file = event.target.files[0];
    if (!file) return;
    if (!file.name.endsWith('.xlsx')) {
      showResult(false, '请选择 .xlsx 格式的文件');
      return;
    }
    var formData = new FormData();
    formData.append('file', file);
    formData.append('_csrf_token', _csrfToken);
    showResult(true, '正在解析文件...');
    fetch('/api/preview_import', { method: 'POST', headers: { 'X-CSRF-Token': _csrfToken }, body: formData })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data.csrf_token) _csrfToken = data.csrf_token;
        if (!data.ok) { showResult(false, data.message || '文件解析失败'); return; }
        previewData = data.data;
        document.getElementById('upload-area').classList.add('hidden');
        document.getElementById('result-area').classList.add('hidden');
        document.getElementById('preview-area').classList.remove('hidden');
        document.getElementById('preview-info').textContent = '共 ' + data.total + ' 条记录';
        var tbody = document.getElementById('preview-tbody');
        tbody.innerHTML = '';
        data.data.slice(0, 5).forEach(function (row) {
          var tr = document.createElement('tr');
          tr.innerHTML = '<td class="px-3 py-2">' + (row.customer || '-') + '</td><td class="px-3 py-2">' + (row.cert_type || '-') + '</td><td class="px-3 py-2">' + (row.expiry_date || row.expire_date || '-') + '</td><td class="px-3 py-2">' + (row.remind_enabled !== false ? '是' : '否') + '</td><td class="px-3 py-2">' + (row.handled ? '是' : '否') + '</td><td class="px-3 py-2">' + (row.responsible_users || '-') + '</td><td class="px-3 py-2">' + (row.note || '-') + '</td>';
          tbody.appendChild(tr);
        });
      })
      .catch(function (err) { showResult(false, '网络错误：' + err.message); });
  };

  window.doImport = function () {
    if (!previewData) return;
    var btn = document.getElementById('import-btn');
    btn.disabled = true;
    btn.innerHTML = '<svg class="animate-spin w-4 h-4" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="3" fill="none" opacity=".25"/><path d="M4 12a8 8 0 018-8" stroke="currentColor" stroke-width="3" fill="none"/></svg> 导入中...';
    fetch('/api/import_excel', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': _csrfToken },
      body: JSON.stringify({ data: previewData, _csrf_token: _csrfToken })
    })
      .then(function (r) { return r.json(); })
      .then(function (result) {
        if (result.csrf_token) _csrfToken = result.csrf_token;
        showResult(result.ok, result.message || (result.ok ? '导入成功！' : '导入失败'));
        if (result.ok) { setTimeout(function () { window.location.href = '/'; }, 1500); }
        else { btn.disabled = false; btn.innerHTML = '<i data-lucide="check" class="w-4 h-4 inline-block"></i> 确认导入'; if (typeof lucide !== 'undefined') lucide.createIcons(); }
      })
      .catch(function (err) {
        showResult(false, '网络错误：' + err.message);
        btn.disabled = false;
        btn.innerHTML = '<i data-lucide="check" class="w-4 h-4 inline-block"></i> 确认导入';
        if (typeof lucide !== 'undefined') lucide.createIcons();
      });
  };

  window.cancelImport = function () {
    previewData = null;
    document.getElementById('preview-area').classList.add('hidden');
    document.getElementById('upload-area').classList.remove('hidden');
    document.getElementById('result-area').classList.add('hidden');
    document.getElementById('excel-file').value = '';
  };

})();
