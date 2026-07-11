// restore.js — 数据恢复页面专用 JS
(function () {
  'use strict';

  window.submitRestore = function (e) {
    e.preventDefault();
    var fileInput = document.getElementById('backup-file');
    if (!fileInput || !fileInput.files.length) { showToast('请选择备份文件'); return false; }
    var btn = document.getElementById('restore-btn');
    btn.disabled = true;
    btn.innerHTML = '<svg class="animate-spin w-4 h-4 mr-1" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="3" fill="none" opacity=".25"/><path d="M4 12a8 8 0 018-8" stroke="currentColor" stroke-width="3" fill="none"/></svg> 恢复中...';

    var formData = new FormData();
    formData.append('backup_file', fileInput.files[0]);
    var csrfInput = document.querySelector('input[name="_csrf_token"]');
    if (csrfInput) formData.append('_csrf_token', csrfInput.value);

    fetch('/api/restore', { method: 'POST', body: formData })
      .then(function (r) { return r.json(); })
      .then(function (result) {
        var area = document.getElementById('result-area');
        area.classList.remove('hidden', 'bg-green-50', 'text-green-700', 'border-green-200', 'bg-red-50', 'text-red-700', 'border-red-200');
        if (result.ok) {
          area.classList.add('bg-green-50', 'text-green-700', 'border', 'border-green-200');
          area.innerHTML = '<span style="font-size:14px"><i data-lucide="check-circle-2" class="w-4 h-4 inline-block text-green-600 mr-1"></i></span> ' + (result.message || '恢复成功！');
          setTimeout(function () { window.location.href = '/'; }, 2000);
        } else {
          area.classList.add('bg-red-50', 'text-red-700', 'border', 'border-red-200');
          area.innerHTML = '<span style="font-size:14px"><i data-lucide="x-circle" class="w-4 h-4 inline-block text-red-600 mr-1"></i></span> ' + (result.message || '恢复失败');
        }
        if (typeof lucide !== 'undefined') lucide.createIcons();
      })
      .catch(function (err) {
        var area = document.getElementById('result-area');
        area.classList.remove('hidden');
        area.classList.add('bg-red-50', 'text-red-700', 'border', 'border-red-200');
        area.innerHTML = '<span style="font-size:14px"><i data-lucide="x-circle" class="w-4 h-4 inline-block text-red-600 mr-1"></i></span> 网络错误：' + err.message;
        if (typeof lucide !== 'undefined') lucide.createIcons();
      })
      .finally(function () {
        btn.disabled = false;
        btn.innerHTML = '<span style="font-size:14px"><i data-lucide="rotate-ccw" class="w-4 h-4 inline-block"></i></span> 确认恢复';
      });
    return false;
  };

})();
