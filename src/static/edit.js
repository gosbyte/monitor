// edit.js — 编辑记录页面专用 JS
(function () {
  'use strict';

  window.toggleRespLabel = function (username, checked) {
    var label = document.getElementById('resp-label-' + username);
    if (!label) return;
    if (checked) label.classList.add('border-blue-400', 'bg-blue-50');
    else label.classList.remove('border-blue-400', 'bg-blue-50');
  };

})();
