// users.js — 用户管理页面专用 JS
(function () {
  'use strict';

  window.openEditModal = function (username, name, role, dingtalkId, email, wecomId) {
    document.getElementById('editUsername').textContent = username;
    document.getElementById('editFormUsername').value = username;
    document.getElementById('editForm').action = '/users/edit/' + encodeURIComponent(username);
    document.getElementById('editName').value = name || '';
    document.getElementById('editRole').value = role || 'user';
    document.getElementById('editPassword').value = '';
    document.getElementById('editDingtalkId').value = dingtalkId || '';
    document.getElementById('editEmail').value = email || '';
    document.getElementById('editWecomId').value = wecomId || '';
    document.getElementById('editModal').classList.remove('hidden');
    document.getElementById('editModal').classList.add('flex');
    document.body.style.overflow = 'hidden';
    setTimeout(function () { document.getElementById('editName').focus(); }, 100);
  };

  window.closeEditModal = function () {
    document.getElementById('editModal').classList.add('hidden');
    document.getElementById('editModal').classList.remove('flex');
    document.body.style.overflow = '';
  };

  document.addEventListener('DOMContentLoaded', function () {
    var modal = document.getElementById('editModal');
    if (modal) {
      modal.addEventListener('click', function (e) {
        if (e.target === modal) closeEditModal();
      });
    }
  });

})();
