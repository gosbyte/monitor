// config.js — 推送配置页面专用 JS
(function () {
  'use strict';

  window._configCsrfToken = window._configCsrfToken || '{{ csrf_token }}';

  function _showResult(areaId, ok, message) {
    var area = document.getElementById(areaId);
    area.classList.remove('hidden', 'bg-green-50', 'text-green-700', 'border', 'border-green-200', 'bg-red-50', 'text-red-700', 'border-red-200', 'bg-yellow-50', 'text-yellow-700', 'border-yellow-200');
    if (ok) {
      area.classList.add('bg-green-50', 'text-green-700', 'border', 'border-green-200');
      area.innerHTML = '<span style="font-size:14px"><i data-lucide="check-circle-2" class="w-4 h-4 inline-block text-green-600 mr-1"></i></span> ' + message;
    } else {
      area.classList.add('bg-red-50', 'text-red-700', 'border', 'border-red-200');
      area.innerHTML = '<span style="font-size:14px"><i data-lucide="x-circle" class="w-4 h-4 inline-block text-red-600 mr-1"></i></span> ' + message;
    }
    if (typeof lucide !== 'undefined') lucide.createIcons();
  }

  window.saveDingtalkConfig = function () {
    var data = {
      webhook_url: document.getElementById('dingtalk-webhook').value.trim(),
      secret: document.getElementById('dingtalk-secret').value.trim(),
      remind_days: Array.from(document.querySelectorAll('input[name="remind_days"]:checked')).map(function (cb) { return parseInt(cb.value); }),
      _csrf_token: window._configCsrfToken
    };
    fetch('/api/save_config', { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': window._configCsrfToken }, body: JSON.stringify(data) })
      .then(function (r) { return r.json(); })
      .then(function (result) {
        if (result.csrf_token) window._configCsrfToken = result.csrf_token;
        _showResult('dingtalk-result', result.ok, result.message || (result.ok ? '保存成功' : '保存失败'));
      })
      .catch(function (err) { _showResult('dingtalk-result', false, '网络错误：' + err.message); });
  };

  window.testDingtalk = function () {
    var btn = document.getElementById('dingtalk-test-btn');
    btn.disabled = true;
    btn.innerHTML = '<svg class="animate-spin w-4 h-4" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="3" fill="none" opacity=".25"/><path d="M4 12a8 8 0 018-8" stroke="currentColor" stroke-width="3" fill="none"/></svg> 发送中...';
    fetch('/api/test_push', { method: 'POST', headers: { 'X-CSRF-Token': window._configCsrfToken } })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data.csrf_token) window._configCsrfToken = data.csrf_token;
        _showResult('dingtalk-result', data.ok, data.ok ? '测试消息发送成功！请检查钉钉群' : '发送失败：' + (data.message || '未知错误'));
      })
      .catch(function (e) { _showResult('dingtalk-result', false, '网络错误：' + e.message) })
      .finally(function () {
        btn.disabled = false;
        btn.innerHTML = '<span style="font-size:14px"><i data-lucide="send" class="w-4 h-4 inline-block"></i></span> 发送测试消息';
        if (typeof lucide !== 'undefined') lucide.createIcons();
      });
  };

  window.saveEmailConfig = function () {
    var passField = document.getElementById('smtp-pass');
    var data = {
      smtp_host: document.getElementById('smtp-host').value.trim(),
      smtp_port: document.getElementById('smtp-port').value.trim(),
      smtp_user: document.getElementById('smtp-user').value.trim(),
      smtp_pass: passField.value || passField.getAttribute('data-original-value') || '',
      smtp_to: document.getElementById('smtp-to').value.trim(),
      email_enabled: document.getElementById('email-enabled').checked,
      _csrf_token: window._configCsrfToken
    };
    fetch('/api/save_config', { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': window._configCsrfToken }, body: JSON.stringify(data) })
      .then(function (r) { return r.json(); })
      .then(function (result) {
        if (result.csrf_token) window._configCsrfToken = result.csrf_token;
        _showResult('email-result', result.ok, result.message || (result.ok ? '保存成功' : '保存失败'));
      })
      .catch(function (err) { _showResult('email-result', false, '网络错误：' + err.message); });
  };

  window.testEmail = function () {
    var btn = document.getElementById('email-test-btn');
    btn.disabled = true;
    btn.innerHTML = '<svg class="animate-spin w-4 h-4" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="3" fill="none" opacity=".25"/><path d="M4 12a8 8 0 018-8" stroke="currentColor" stroke-width="3" fill="none"/></svg> 发送中...';
    fetch('/api/test_email', { method: 'POST', headers: { 'X-CSRF-Token': window._configCsrfToken } })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data.csrf_token) window._configCsrfToken = data.csrf_token;
        _showResult('email-result', data.ok, data.ok ? '测试邮件发送成功！请检查收件箱' : '发送失败：' + (data.message || '未知错误'));
      })
      .catch(function (e) { _showResult('email-result', false, '网络错误：' + e.message) })
      .finally(function () {
        btn.disabled = false;
        btn.innerHTML = '<span style="font-size:14px"><i data-lucide="send" class="w-4 h-4 inline-block"></i></span> 发送测试邮件';
        if (typeof lucide !== 'undefined') lucide.createIcons();
      });
  };

  window.saveWecomConfig = function () {
    var data = {
      wecom_enabled: document.getElementById('wecom-enabled').checked,
      wecom_webhook: document.getElementById('wecom-webhook').value.trim(),
      _csrf_token: window._configCsrfToken
    };
    fetch('/api/config/wecom', { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': window._configCsrfToken }, body: JSON.stringify(data) })
      .then(function (r) { return r.json(); })
      .then(function (result) {
        if (result.csrf_token) window._configCsrfToken = result.csrf_token;
        _showResult('wecom-result', result.ok, result.message || (result.ok ? '保存成功' : '保存失败'));
      }).catch(function (err) { _showResult('wecom-result', false, '网络错误：' + err.message); });
  };

  window.testWecom = function () {
    var btn = document.getElementById('wecom-test-btn');
    btn.disabled = true;
    btn.innerHTML = '<svg class="animate-spin w-4 h-4" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="3" fill="none" opacity=".25"/><path d="M4 12a8 8 0 018-8" stroke="currentColor" stroke-width="3" fill="none"/></svg> 发送中...';
    var data = {
      wecom_enabled: document.getElementById('wecom-enabled').checked,
      wecom_webhook: document.getElementById('wecom-webhook').value.trim(),
      _csrf_token: window._configCsrfToken
    };
    fetch('/api/test_wecom', { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': window._configCsrfToken }, body: JSON.stringify(data) })
      .then(function (r) { return r.json(); })
      .then(function (result) {
        if (result.csrf_token) window._configCsrfToken = result.csrf_token;
        _showResult('wecom-result', result.ok, result.message || (result.ok ? '测试推送成功' : '测试失败'));
      }).catch(function (err) { _showResult('wecom-result', false, '网络错误：' + err.message); })
      .finally(function () {
        btn.disabled = false;
        btn.innerHTML = '<span style="font-size:14px"><i data-lucide="send" class="w-4 h-4 inline-block"></i></span> 测试推送';
        if (typeof lucide !== 'undefined') lucide.createIcons();
      });
  };

})();
