#!/usr/bin/env python3
"""Patch index.html to add mobile CSS and fix login page reference."""
import sys

file_path = sys.argv[1]
action = sys.argv[2]

with open(file_path, 'r') as f:
    content = f.read()

if action == 'add_mobile_css':
    mobile_css = """
    /* ── 移动端优化 ───────────────────────── */
    @media (max-width: 767px) {
      /* 统计卡片：缩小间距和图标 */
      .stat-card { padding: 0.75rem !important; }
      .stat-card .w-10 { width: 2rem !important; height: 2rem !important; }
      .stat-card .text-2xl { font-size: 1.25rem !important; }
      .stat-card .text-sm { font-size: 0.75rem !important; }
      .stat-card .flex { gap: 0.5rem !important; }
      /* 主内容区：缩小 padding */
      main { padding-left: 0.5rem !important; padding-right: 0.5rem !important; }
      /* 表格：更紧凑的行高 */
      #cert-tbody td { padding: 0.5rem 0.375rem !important; font-size: 0.75rem !important; }
      #cert-thead th { padding: 0.375rem 0.375rem !important; font-size: 0.7rem !important; }
      /* 卡片圆角缩小 */
      .rounded-xl { border-radius: 0.5rem !important; }
    }
"""
    # Insert before </style>
    content = content.replace('  </style>', mobile_css + '  </style>')
    
elif action == 'add_mobile_js':
    # Add mobile viewport fix for the main content
    mobile_js = """
  // ── 移动端主内容区 padding 自适应 ────────────
  (function() {
    function adjustMobilePadding() {
      var main = document.getElementById('main-content');
      if (!main) return;
      if (window.innerWidth < 768) {
        main.style.paddingLeft = '0.5rem';
        main.style.paddingRight = '0.5rem';
      } else {
        main.style.paddingLeft = '';
        main.style.paddingRight = '';
      }
    }
    adjustMobilePadding();
    window.addEventListener('resize', adjustMobilePadding);
  })();
"""
    # Insert before closing </main>
    content = content.replace('</main>', mobile_js + '</main>')

with open(file_path, 'w') as f:
    f.write(content)

print(f"Patched {file_path} ({action})")
