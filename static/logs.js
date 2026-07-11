// logs.js — 操作日志页面专用 JS
(function () {
  'use strict';

  window.applyFilter = function () {
    var user = document.getElementById('filterUser').value;
    var action = document.getElementById('filterAction').value;
    var date = document.getElementById('filterDate').value;
    var rows = document.querySelectorAll('.log-row');
    rows.forEach(function (row) {
      var match = true;
      if (user && row.dataset.user !== user) match = false;
      if (action && row.dataset.action !== action) match = false;
      if (date && row.dataset.date !== date) match = false;
      row.style.display = match ? '' : 'none';
    });
  };

  window.resetFilter = function () {
    document.getElementById('filterUser').value = '';
    document.getElementById('filterAction').value = '';
    document.getElementById('filterDate').value = '';
    document.querySelectorAll('.log-row').forEach(function (row) { row.style.display = ''; });
  };

  window.exportLogs = function () {
    var rows = document.querySelectorAll('.log-row');
    var logs = [];
    rows.forEach(function (row) {
      logs.push({
        time: row.dataset.time,
        user: row.dataset.user,
        action: row.dataset.action,
        target: row.querySelector('td:nth-child(3)').textContent.trim(),
        detail: row.querySelector('td:nth-child(4)').textContent.trim(),
        ip: row.dataset.ip
      });
    });
    var blob = new Blob([JSON.stringify(logs, null, 2)], { type: 'application/json' });
    var url = URL.createObjectURL(blob);
    var a = document.createElement('a');
    a.href = url; a.download = 'logs_' + new Date().toISOString().slice(0, 10) + '.json';
    a.click(); URL.revokeObjectURL(url);
  };

})();
