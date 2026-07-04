// add_batch.js — 批量添加记录页面专用 JS
(function () {
  'use strict';

  var _csrfToken = '{{ csrf_token }}';
  var selectedFile = null;

  window.showResult = function (success, message, detail) {
    var area = document.getElementById('result-area');
    area.classList.remove('hidden', 'bg-green-50', 'text-green-700', 'border-green-200', 'bg-red-50', 'text-red-700', 'border-red-200');
    if (success) {
      area.classList.add('bg-green-50', 'text-green-700', 'border', 'border-green-200');
      area.innerHTML = '<div class="flex items-center gap-2"><i data-lucide="check-circle-2" class="w-4 h-4 inline-block text-green-600"></i>' + message + '</div>';
    } else {
      area.classList.add('bg-red-50', 'text-red-700', 'border', 'border-red-200');
      area.innerHTML = '<div class="flex items-center gap-2"><i data-lucide="alert-triangle" class="w-4 h-4 inline-block text-yellow-600"></i>' + message + '</div>';
    }
    if (detail && detail.length > 0) {
      area.innerHTML += '<div class="mt-2 pt-2 border-t border-current/20 text-xs space-y-0.5">' + detail.map(function (d) { return '<div>' + d + '</div>'; }).join('') + '</div>';
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
    selectedFile = file;
    var formData = new FormData();
    formData.append('file', file);
    fetch('/import/preview', { method: 'POST', body: formData })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (!data.ok) { showResult(false, data.message || '预览失败'); return; }
        var tbody = document.getElementById('preview-tbody');
        tbody.innerHTML = '';
        data.preview.forEach(function (item) {
          var tr = document.createElement('tr');
          tr.innerHTML = '<td class="px-3 py-2 text-gray-900">' + (item['客户名称'] || '') + '</td>' +
            '<td class="px-3 py-2 text-gray-600">' + (item['提醒类型'] || '-') + '</td>' +
            '<td class="px-3 py-2 text-gray-600">' + (item['域名'] || '-') + '</td>' +
            '<td class="px-3 py-2 text-gray-600">' + (item['到期日期'] || '') + '</td>' +
            '<td class="px-3 py-2 text-gray-500">' + (item['备注'] || '-') + '</td>';
          tbody.appendChild(tr);
        });
        document.getElementById('preview-info').textContent = '共 ' + data.total_rows + ' 行数据';
        document.getElementById('preview-area').classList.remove('hidden');
        if (typeof lucide !== 'undefined') lucide.createIcons();
      })
      .catch(function (e) { showResult(false, '预览失败：' + e.message); });
  };

  window.confirmImport = function () {
    if (!selectedFile) return;
    var btn = document.getElementById('confirm-btn');
    btn.disabled = true;
    btn.innerHTML = '<svg class="animate-spin w-4 h-4 mr-1" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="3" fill="none" opacity=".25"/><path d="M4 12a8 8 0 018-8" stroke="currentColor" stroke-width="3" fill="none"/></svg> 导入中...';
    var formData = new FormData();
    formData.append('file', selectedFile);
    formData.append('_csrf_token', _csrfToken);
    fetch('/import/excel', { method: 'POST', body: formData })
      .then(function (r) { return r.json(); })
      .then(function (result) {
        if (result.ok) {
          showResult(true, '成功导入 ' + result.imported + ' 条记录', result.errors.length ? result.errors : null);
          setTimeout(function () { window.location.href = '/'; }, 2500);
        } else {
          showResult(false, result.message || '导入失败');
        }
      })
      .catch(function (err) { showResult(false, '网络错误：' + err.message) })
      .finally(function () {
        btn.disabled = false;
        btn.innerHTML = '<i data-lucide="check" class="w-4 h-4 inline-block"></i> 确认导入';
        if (typeof lucide !== 'undefined') lucide.createIcons();
      });
  };

  window.resetUpload = function () {
    selectedFile = null;
    document.getElementById('excel-file').value = '';
    document.getElementById('preview-area').classList.add('hidden');
    document.getElementById('result-area').classList.add('hidden');
  };

  window.doImport = function (e) {
    e.preventDefault();
    var input = document.getElementById('json-input').value.trim();
    var btn = document.getElementById('json-submit-btn');
    if (!input) { showResult(false, '请先粘贴 JSON 数据'); return false; }
    var data;
    try { data = JSON.parse(input); } catch (err) { showResult(false, 'JSON 格式错误:' + err.message); return false; }
    if (!Array.isArray(data)) { showResult(false, '数据必须是 JSON 数组 []'); return false; }
    if (data.length === 0) { showResult(false, '数组为空'); return false; }
    btn.disabled = true;
    fetch('/import/json', { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': _csrfToken }, body: JSON.stringify(data) })
      .then(function (r) { return r.json(); })
      .then(function (result) {
        if (result.ok) {
          showResult(true, '成功导入 ' + result.imported + ' 条记录', result.errors.length ? result.errors : null);
          setTimeout(function () { window.location.href = '/'; }, 2500);
        } else {
          showResult(false, result.message || '导入失败');
        }
      })
      .catch(function (err) { showResult(false, '网络错误：' + err.message) })
      .finally(function () { btn.disabled = false; });
    return false;
  };

  window.previewJSON = function () {
    var btn = document.getElementById('preview-json-btn');
    btn.disabled = true;
    btn.innerHTML = '<svg class="animate-spin w-4 h-4 mr-1" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="3" fill="none" opacity=".25"/><path d="M4 12a8 8 0 018-8" stroke="currentColor" stroke-width="3" fill="none"/></svg> 加载中...';
    fetch('/export/json')
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data.ok && data.records) {
          document.getElementById('json-preview').value = JSON.stringify(data.records, null, 2);
          document.getElementById('json-preview-area').classList.remove('hidden');
        } else {
          alert('预览失败：' + (data.message || '未知错误'));
        }
      })
      .catch(function (err) { alert('网络错误：' + err.message) })
      .finally(function () {
        btn.disabled = false;
        btn.innerHTML = '<i data-lucide="eye" class="w-4 h-4 inline-block"></i> 预览 JSON 数据';
        if (typeof lucide !== 'undefined') lucide.createIcons();
      });
  };

  window.copyJSON = function () {
    var textarea = document.getElementById('json-preview');
    textarea.select();
    document.execCommand('copy');
    alert('已复制到剪贴板');
  };

})();
