#!/usr/bin/env python3
"""Enhance mobile CSS in index.html"""
import pathlib

p = pathlib.Path("/app/templates/index.html")
t = p.read_text()

old_rules = """      /* 卡片圆角缩小 */
      .rounded-xl { border-radius: 0.5rem !important; }
    }"""

new_rules = """      /* 卡片圆角缩小 */
      .rounded-xl { border-radius: 0.5rem !important; }
      /* 统计卡片网格：更紧凑 */
      .grid-cols-2 { gap: 0.5rem !important; }
      /* 搜索输入：全宽 */
      #search-input { font-size: 0.875rem !important; padding: 0.5rem 0.75rem !important; }
      /* 筛选下拉：紧凑 */
      select { font-size: 0.75rem !important; padding: 0.25rem 0.5rem !important; }
      /* 日期输入：紧凑 */
      input[type=date] { font-size: 0.75rem !important; padding: 0.25rem 0.5rem !important; }
      /* 批量工具栏：更紧凑 */
      #batch-toolbar { padding: 0.5rem !important; }
      #batch-toolbar .batch-btn { padding: 0.25rem 0.5rem !important; font-size: 0.7rem !important; }
      /* 图表区域：更紧凑 */
      #chart-content { padding: 0.5rem !important; }
      #chart-content h3 { font-size: 0.75rem !important; }
      /* 使用说明：更紧凑 */
      #usage-section { padding: 0.75rem !important; }
      #usage-section li { font-size: 0.75rem !important; margin-bottom: 0.25rem !important; }
    }"""

t = t.replace(old_rules, new_rules)
p.write_text(t)
print("Enhanced mobile CSS")
