// change_password.js — 修改密码页面专用 JS
(function () {
  'use strict';

  window.checkSelfPwd = function () {
    var pwd = document.getElementById('selfPwdField').value;
    var confirm = document.getElementById('selfPwdConfirm').value;
    if (pwd.length < 8) { showToast('密码至少8位', 'error'); return false; }
    if (pwd !== confirm) { showToast('两次密码不一致', 'error'); return false; }
    return true;
  };

  window.openPwdModalSelf = function () {
    var modal = document.getElementById('selfPwdModal');
    if (modal) {
      modal.classList.remove('hidden');
      modal.classList.add('flex');
    }
  };

  window.closeSelfPwdModal = function () {
    var modal = document.getElementById('selfPwdModal');
    if (modal) {
      modal.classList.add('hidden');
      modal.classList.remove('flex');
    }
  };

  document.addEventListener('DOMContentLoaded', function () {
    var modal = document.getElementById('selfPwdModal');
    if (modal) {
      modal.addEventListener('click', function (e) {
        if (e.target === modal) closeSelfPwdModal();
      });
    }
  });

})();
