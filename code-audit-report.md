# 代码复用审计报告 — monitor-optimize

审计文件:
- `templates/index.html` (1626行)
- `static/index.js` (634行, 全为注释的死代码)
- `static/app.js` (397行)
- `static/common.css` (105行)
- `static/index.css` (172行)

---

## 一、内联事件处理器 → 事件委托 (67个 onclick/onchange/oninput/onkeydown)

### 1.1 统计卡片筛选 — 4个 onclick + 4个 onkeydown (index.html:62-95)

```
index.html:62 → 4个 stat-card 各有 onclick="quickFilter(...)" + onkeydown="..."
index.html:73 → 同上 (normal)
index.html:84 → 同上 (expiring)
index.html:95 → 同上 (expired)
```
→ **problem**: 4个统计卡片各有 onclick 和 onkeydown 内联事件, 共8个处理器
→ **suggested fix**: 给 `.stat-card` 添加 `data-filter` 属性, 用事件委托监听父容器 click/keydown
→ **confidence**: high | **risk**: SAFE

### 1.2 图表折叠 — 1个 onclick (index.html:110)

```
index.html:110 → onclick="toggleChart()" 在 chart section header 上
```
→ **problem**: 内联 onclick 绑定折叠行为
→ **suggested fix**: 给 header div 添加 `data-action="toggle-chart"` 属性, 事件委托处理
→ **confidence**: high | **risk**: SAFE

### 1.3 搜索输入 — 2个 oninput + 1个 onkeydown (index.html:178)

```
index.html:178 → oninput="filterTable(); showSearchSuggestions(this.value)" + onkeydown="..."
```
→ **problem**: 内联事件直接调用多个函数, 无法统一维护
→ **suggested fix**: 移除内联事件, 在 $ 对象缓存后于 DOMContentLoaded 绑定
→ **confidence**: high | **risk**: SAFE

### 1.4 筛选器 — 4个 onchange (index.html:183-199)

```
index.html:183 → onchange="filterTable()" (#filter-status)
index.html:192 → onchange="filterTable()" (#filter-type)
index.html:198 → onchange="filterTable()" (#filter-date-from)
index.html:199 → onchange="filterTable()" (#filter-date-to)
```
→ **problem**: 4个筛选器各自绑定 onchange, 逻辑完全相同
→ **suggested fix**: 统一给 filter 元素添加 `data-filter` 类, 事件委托到 filter-bar 容器
→ **confidence**: high | **risk**: SAFE

### 1.5 重置筛选按钮 — 1个 onclick (index.html:200)

```
index.html:200 → onclick="resetFilters()"
```
→ **problem**: 单个内联事件
→ **suggested fix**: 添加 `data-action="reset-filters"` 属性, 委托到 #filter-bar-mobile
→ **confidence**: high | **risk**: SAFE

### 1.6 全选复选框 — 2个 onchange (index.html:211, 265)

```
index.html:211 → onchange="toggleSelectAll()" (#select-all)
index.html:265 → onchange="toggleSelectAll()" (#select-all-header)
```
→ **problem**: 两处 onchange 调用同一函数
→ **suggested fix**: 事件委托到批量操作工具栏容器, 用 `.row-checkbox, #select-all, #select-all-header` 选择器
→ **confidence**: high | **risk**: SAFE

### 1.7 批量操作按钮组 — 7个 onclick (index.html:219-245)

```
index.html:219 → onclick="toggleBatchDropdown()"
index.html:224 → onclick="batchHandle(true)"
index.html:228 → onclick="batchHandle(false)"
index.html:233 → onclick="batchRemind(true)"
index.html:237 → onclick="batchRemind(false)"
index.html:242 → onclick="batchDelete()"
```
→ **problem**: 批量操作下拉菜单有6个内联事件, 每个按钮都写死函数名
→ **suggested fix**: 给按钮添加 `data-batch-action="handle|remind|delete"` + `data-batch-value="true|false"` 属性, 单一委托处理器
→ **confidence**: high | **risk**: SAFE

### 1.8 添加记录按钮 — 2个 onclick (index.html:249, 364)

```
index.html:249 → onclick="openAddModal()" (toolbar)
index.html:364 → onclick="openAddModal()" (empty state)
```
→ **problem**: 两处调用 openAddModal(), 应统一委托
→ **suggested fix**: 添加 `data-action="open-add"` 属性, 事件委托到 body 或各自容器
→ **confidence**: high | **risk**: SAFE

### 1.9 表头排序 — 4个 onclick (index.html:268-271)

```
index.html:268 → onclick="sortTable('customer')"
index.html:269 → onclick="sortTable('cert_type')"
index.html:270 → onclick="sortTable('expire_date')"
index.html:271 → onclick="sortTable('days_left')"
```
→ **problem**: 4个表头列各自内联绑定 sortTable()
→ **suggested fix**: 在 th 上添加 `data-sort-col="customer|cert_type|expire_date|days_left"`, 委托到 thead
→ **confidence**: high | **risk**: SAFE

### 1.10 行内编辑/删除按钮 — 每行 1个 onclick (index.html:319)

```
index.html:319 → onclick="openEditModal({{ c.id }})"
```
→ **problem**: 每行记录一个编辑按钮, 动态生成无法预绑定
→ **suggested fix**: 按钮添加 `data-action="edit"` + `data-row-id="{{ c.id }}"`, 委托到 #cert-tbody
→ **confidence**: high | **risk**: SAFE

### 1.11 行操作三点菜单 — 每行 1个 onclick (index.html:324)

```
index.html:324 → onclick="toggleRowMenu({{ c.id }}, this, event)"
```
→ **problem**: 每行动态生成, 必须用委托
→ **suggested fix**: 按钮添加 `data-action="toggle-row-menu"` + `data-row-id="{{ c.id }}"`, 委托到 #cert-tbody
→ **confidence**: high | **risk**: SAFE

### 1.12 行菜单内按钮 — 每行 4-6个 onclick (index.html:329-348)

```
index.html:329 → onclick="closeRowMenu(...);pushCert(...)"
index.html:333 → onclick="closeRowMenu(...);toggleStatus(...)"
index.html:337 → onclick="closeRowMenu(...);toggleHandled(...)"
index.html:341 → onclick="closeRowMenu(...);duplicateCert(...)"
index.html:346 → onclick="closeRowMenu(...);confirmDelete(...)"
```
→ **problem**: 每个行菜单项都有 closeRowMenu + 业务函数组合调用
→ **suggested fix**: 菜单按钮添加 `data-action="push|toggle-status|toggle-handled|duplicate|delete"`, 委托到 row-menu 容器, 由单一 handler 分发
→ **confidence**: high | **risk**: SAFE

### 1.13 模态框关闭按钮 — 2个 onclick (index.html:418, 495)

```
index.html:418 → onclick="closeAddModal()" (add-modal 关闭按钮)
index.html:495 → onclick="closeEditModal()" (edit-modal 关闭按钮)
```
→ **problem**: 模态框关闭按钮内联绑定
→ **suggested fix**: 关闭按钮添加 `data-action="close-modal"`, 委托到各自 modal 容器
→ **confidence**: high | **risk**: SAFE

### 1.14 快捷日期按钮 — 每模态框 5个 onclick (index.html:442-446, 527-531)

```
index.html:442-446 → 5个 setExpiryDays(7/30/90/180/365) in add-modal
index.html:527-531 → 5个 setExpiryDays(7/30/90/180/365) in edit-modal
```
→ **problem**: 10个按钮绑定同一函数, 传参不同
→ **suggested fix**: 按钮添加 `data-set-days="7|30|90|180|365"`, 委托到 add-modal/edit-modal 内的快捷区域
→ **confidence**: high | **risk**: SAFE

### 1.15 模态框提交/取消按钮 — 2个 onclick (index.html:483, 569)

```
index.html:483 → onclick="closeAddModal()" (add-modal 取消)
index.html:569 → onclick="closeEditModal()" (edit-modal 取消)
```
→ **problem**: 与1.13重复覆盖, 但需区分上下文
→ **suggested fix**: 统一用 `data-action="close-modal"` 委托, 由 handler 判断是哪个 modal
→ **confidence**: high | **risk**: SAFE

### 1.16 负责人复选框 — 动态 onchange (index.html:550)

```
index.html:550 → onchange="toggleEditRespLabel('{{ u.username }}', this.checked)"
```
→ **problem**: 动态生成的复选框, 每次渲染都要重新绑定
→ **suggested fix**: 委托到 #edit-responsible-users 容器, 读取 checkbox 的 value 属性
→ **confidence**: high | **risk**: SAFE

### 1.17 分页按钮 — 动态 onclick (index.html:452, 459, 461)

```
index.html:452 → onclick="goPage(currentPage-1)"
index.html:459 → onclick="goPage(p)" (循环生成)
index.html:461 → onclick="goPage(currentPage+1)"
```
→ **problem**: 分页按钮动态生成, 必须用委托
→ **suggested fix**: 按钮添加 `data-page="N"` 属性, 委托到 #page-buttons
→ **confidence**: high | **risk**: SAFE

### 1.18 搜索建议 — 动态 onclick (index.html:500)

```
index.html:500 → onclick="selectSuggestion(i)" (动态生成)
```
→ **problem**: 搜索建议动态生成, 必须用委托
→ **suggested fix**: div 添加 `data-index="i"`, 委托到 #search-suggestions
→ **confidence**: high | **risk**: SAFE

### 1.19 使用说明折叠 — 1个 onclick (index.html:391)

```
index.html:391 → onclick="toggleHelp()"
```
→ **problem**: 内联绑定
→ **suggested fix**: 添加 `data-action="toggle-help"` 委托到 #help-section
→ **confidence**: high | **risk**: SAFE

### 1.20 模态框遮罩层 — 2个 onclick (index.html:415, 492)

```
index.html:415 → onclick="event.stopPropagation()" (add-modal overlay)
index.html:492 → onclick="event.stopPropagation()" (edit-modal overlay)
```
→ **problem**: 阻止事件冒泡到遮罩层的关闭逻辑
→ **suggested fix**: 改用 CSS `pointer-events: none` 在 overlay 上, 内容区 `pointer-events: auto`
→ **confidence**: medium | **risk**: SAFE

### 1.21 修改密码弹窗 — 2个 onclick (index.html:1614, 1601)

```
index.html:1601 → onsubmit="return checkSelfPwd()"
index.html:1614 → onclick="closeSelfPwdModal()"
```
→ **problem**: 内联提交验证和关闭
→ **suggested fix**: 移除内联, 在 app.js 中绑定 submit handler 和 click handler
→ **confidence**: medium | **risk**: SAFE

### 1.22 base.html 中的内联事件

```
base.html:85 → onclick="toggleDesktopSidebar()"
base.html:132 → onclick="setTimeout(()=>{...})" (数据备份链接)
base.html:148 → onclick="toggleDarkMode()"
base.html:169 → onclick="this.parentElement.remove()" (flash消息关闭)
base.html:243 → onclick="closeConfirmModal()"
```
→ **problem**: base.html 有5个内联事件, 其中 flash 消息关闭按钮尤其需要委托
→ **suggested fix**: flash 消息关闭按钮添加 `data-action="dismiss-flash"`, 委托到 #flash-container
→ **confidence**: high | **risk**: SAFE

---

## 二、DOM 查询缓存 → $ 对象设计

### 2.1 index.js 中的死代码注释 (index.js:1-11)

```
index.js:1 → "// NOTE: This file is NOT loaded by any template"
index.js:7 → "// DEAD CODE — not loaded by any template"
```
→ **problem**: index.js 整个文件未被加载, 是死代码, 而 index.html 内有重复的相同逻辑
→ **suggested fix**: 要么从 index.html 移除内联脚本并加载 index.js, 要么删除 index.js
→ **confidence**: high | **risk**: CAREFUL

### 2.2 $ 对象设计方案

当前代码中存在大量重复的 `document.getElementById()` 和 `document.querySelector()` 调用。建议创建 `$` 缓存对象:

```javascript
// 建议在 app.js 中定义 (作为全局共享)
var $ = {};
document.addEventListener('DOMContentLoaded', function() {
  // === 统计面板 ===
  $.skeletonLoading = document.getElementById('skeleton-loading');
  
  // === 搜索/筛选 ===
  $.searchInput = document.getElementById('search-input');
  $.searchSuggestions = document.getElementById('search-suggestions');
  $.filterBar = document.getElementById('filter-bar-mobile');
  $.filterStatus = document.getElementById('filter-status');
  $.filterType = document.getElementById('filter-type');
  $.filterDateFrom = document.getElementById('filter-date-from');
  $.filterDateTo = document.getElementById('filter-date-to');
  
  // === 表格 ===
  $.certTbody = document.getElementById('cert-tbody');
  $.pageInfo = document.getElementById('page-info');
  $.pageButtons = document.getElementById('page-buttons');
  $.perPageSelect = document.getElementById('per-page-select');
  
  // === 模态框 ===
  $.addModal = document.getElementById('add-modal');
  $.editModal = document.getElementById('edit-modal');
  $.confirmModal = document.getElementById('confirm-modal');
  $.editCertForm = document.getElementById('edit-cert-form');
  
  // === 批量操作 ===
  $.batchToolbar = document.getElementById('batch-toolbar');
  $.selectAllHeader = document.getElementById('select-all-header');
  $.selectAllToolbar = document.getElementById('select-all');
  $.selectedCount = document.getElementById('selected-count');
  $.batchDropdown = document.getElementById('batch-dropdown');
  
  // === 图表 ===
  $.chartSection = document.getElementById('chart-section');
  $.chartContent = document.getElementById('chart-content');
  $.chartChevron = document.getElementById('chart-chevron');
  
  // === 帮助 ===
  $.helpSection = document.getElementById('help-section');
  $.helpContent = document.getElementById('help-content');
  $.helpChevron = document.getElementById('help-chevron');
  
  // === 时间 ===
  $.lastUpdateTime = document.getElementById('last-update-time');
  
  // === Toast ===
  $.toastContainer = document.getElementById('toast-container');
});
```

→ **confidence**: high | **risk**: SAFE

### 2.3 index.html 内联脚本中大量重复的 getElementById

```
index.html:583-592 → setExpiryDays 中重复 getElementById('add-expire-date') 等
index.html:596-599 → openAddModal 中重复 getElementById
index.html:648-651 → closeAddModal 中重复 getElementById
index.html:656-697 → openEditModal/closeEditModal 中大量重复
index.html:895-905 → toggleChart 中重复 getElementById
index.html:1206-1210 → filterTable 开头5次 getElementById
index.html:1334-1348 → showSearchSuggestions 中重复
index.html:1368-1375 → resetFilters 中5次 getElementById
```
→ **problem**: 同一函数体内多次调用相同的 getElementById, 如 filterTable 中连续5次
→ **suggested fix**: 使用 $ 缓存对象替代, 如 `$.searchInput.value` 代替 `document.getElementById('search-input').value`
→ **confidence**: high | **risk**: SAFE

### 2.4 app.js 中也存在重复 DOM 查询

```
app.js:197-203 → updateBatchUI 中 querySelectorAll('.row-checkbox') 被多次调用
app.js:206-214 → toggleSelectAll 中 querySelectorAll('.row-checkbox') 又被调用
```
→ **problem**: 同一选择器在不同函数中被重复查询
→ **suggested fix**: 缓存到 $ 对象或在函数内部缓存局部变量
→ **confidence**: high | **risk**: SAFE

---

## 三、CSS 硬编码颜色值 → CSS 变量提取

### 3.1 common.css 中硬编码颜色

```
common.css:19 → outline: 2px solid #3b82f6
common.css:28 → background: #3b82f6
common.css:35 → background: #60a5fa
common.css:36 → outline-color: #60a5fa
```
→ **problem**: focus-visible 边框颜色硬编码, 暗色模式下的颜色也硬编码
→ **suggested fix**: 
```css
:root {
  --color-focus-ring: #3b82f6;
  --color-focus-ring-dark: #60a5fa;
}
*:focus-visible { outline-color: var(--color-focus-ring); }
body.dark-mode *:focus-visible { outline-color: var(--color-focus-ring-dark); }
```
→ **confidence**: high | **risk**: SAFE

### 3.2 index.css 中硬编码颜色 (大量)

```
index.css:29 → background: #eff6ff (blue-50)
index.css:30 → background: #fef2f2 (red-50)
index.css:34 → background: #3b82f6 (blue-600)
index.css:41 → scrollbar-color: #d1d5db transparent
index.css:43 → background: #d1d5db
index.css:47 → border-color: #93c5fd (blue-300)
index.css:47 → box-shadow: rgba(0,0,0,0.05)
index.css:51 → background-color: #f3f4f6 (gray-100)
index.css:51 → border-color: #d1d5db (gray-300)
index.css:52 → background-color: #e5e7eb (gray-200)
```
→ **problem**: 10+处 Tailwind 颜色值硬编码, 无法统一主题切换
→ **suggested_fix**: 提取为 CSS 变量, 与 Tailwind 的自定义配置对应
→ **confidence**: high | **risk**: SAFE

### 3.3 app.js 中 Toast 硬编码颜色

```
app.js:108 → background: '#dc2626' (error)
app.js:108 → background: '#16a34a' (success)
app.js:108 → background: '#3b82f6' (info)
```
→ **problem**: toast-progress 进度条颜色硬编码在 JS 字符串中
→ **suggested fix**: 提取到 CSS 变量, 或统一使用 Tailwind 类名
→ **confidence**: medium | **risk**: SAFE

### 3.4 index.html 内联 style 中的硬编码颜色

```
index.html:125 → style="height:{{ ... }}%" (动态, 合理)
index.html:143 → style="width:{{ t.percent }}%" (动态, 合理)
index.html:160 → style="background:{{ s.color }}" (后端传入, 合理)
```
→ **note**: 以上3处为动态数据驱动, 不应提取为CSS变量
→ **confidence**: n/a | **risk**: N/A

---

## 四、模板重复 Modal 结构 → {% include %} 提取

### 4.1 Add Modal vs Edit Modal 高度重复

```
index.html:414-488 → #add-modal (75行)
index.html:491-576 → #edit-modal (86行)
```
→ **problem**: 两个模态框结构高度相似:
- 相同的头部布局 (flex justify-between with title + close button)
- 相同的表单字段 (customer, cert_type, expire_date/time, note)
- 相同的快捷日期按钮 (+7/+30/+90/+半年/+1年)
- 相同的底部操作按钮 (取消 + 提交)
- 相同的负责人选择区域 (当 is_admin 时)
→ **suggested fix**: 提取为 `{% include '_modal_form.html' %}`, 差异部分用 block 覆盖:
```jinja2
<!-- _modal_base.html -->
<div id="{{ modal_id }}-modal" class="fixed inset-0 modal-overlay hidden items-center justify-center z-[60] p-4">
  <div class="bg-white rounded-xl w-full max-w-md shadow-xl" onclick="event.stopPropagation()">
    <div class="flex items-center justify-between p-4 border-b border-gray-200 sticky top-0 bg-white rounded-t-xl">
      <h2 class="text-lg font-semibold text-gray-900">{{ modal_title }}</h2>
      <button onclick="close{{ modal_cap }}Modal()" class="p-1 hover:bg-gray-100 rounded">
        <i data-lucide="x" class="w-4 h-4 inline-block"></i>
      </button>
    </div>
    {% block modal_body %}{% endblock %}
  </div>
</div>
```
→ **confidence**: high | **risk**: CAREFUL (需同步修改 JS 中的 modal ID 引用)

### 4.2 Confirm Modal 已在 base.html 定义

```
base.html:238-247 → #confirm-modal (全局共享)
index.html:966-982 → 重复定义了 showConfirmModal/closeConfirmModal
app.js:129-157 → 又重复定义了 showConfirmModal/closeConfirmModal
```
→ **problem**: confirm-modal 的 JS 逻辑在3个地方重复定义 (base.html 有HTML, index.html 有JS, app.js 也有JS)
→ **suggested fix**: 统一由 app.js 管理, index.html 和 base.html 不再重复定义
→ **confidence**: high | **risk**: SAFE

### 4.3 selfPwdModal 独立存在

```
index.html:1595-1621 → #selfPwdModal (27行)
```
→ **note**: 这是唯一独立的密码修改弹窗, 无重复可提取, 但内联事件可委托
→ **confidence**: low | **risk**: SAFE

### 4.4 骨架屏结构重复

```
index.html:13-47 → skeleton-loading 中有4个完全相同的 stat-card skeleton (line 16-27)
```
→ **problem**: 4个统计卡片的骨架屏 HTML 完全重复
→ **suggested fix**: 使用 Jinja2 循环:
```jinja2
{% for i in range(4) %}
  <div class="bg-white rounded-xl p-4 border border-gray-200 animate-pulse">...</div>
{% endfor %}
```
→ **confidence**: high | **risk**: SAFE

---

## 五、跨文件重复函数 (DRIED CODE)

### 5.1 setExpiryDays — 3处重复

```
index.html:582-593 → 内联脚本定义
index.js:14-25 → 注释中的死代码
app.js → 未定义 (依赖 index.html 或 index.js)
```
→ **problem**: 同一函数在3个文件中出现, 逻辑完全一致
→ **suggested fix**: 统一到 app.js 或 index.js, 删除其他副本
→ **confidence**: high | **risk**: SAFE

### 5.2 showConfirmModal / closeConfirmModal — 3处重复

```
index.html:966-982 → 内联脚本
app.js:129-157 → IIFE 内定义
index.js → 注释中的死代码
```
→ **problem**: 确认弹窗逻辑在3个位置重复
→ **suggested fix**: 统一到 app.js, 删除 index.html 中的副本
→ **confidence**: high | **risk**: SAFE

### 5.3 getSelectedIds / updateBatchUI / toggleSelectAll / onRowSelect — 2处重复

```
app.js:182-220 → 批量选择相关函数
index.html:927-963 → 相同函数重复定义
```
→ **problem**: 批量操作函数在 app.js 和 index.html 中各有一份
→ **suggested fix**: 统一到 app.js, index.html 中删除
→ **confidence**: high | **risk**: SAFE

### 5.4 toggleRowMenu / closeRowMenu — 2处重复

```
app.js:223-255 → 三点菜单逻辑
index.html:995-1048 → 相同逻辑重复
```
→ **problem**: 行菜单逻辑重复
→ **suggested fix**: 统一到 app.js
→ **confidence**: high | **risk**: SAFE

### 5.5 filterTable — 2处重复

```
index.js:386-470 → 注释中的死代码
index.html:1205-1306 → 活跃的内联脚本
```
→ **problem**: filterTable 在 index.js (死代码) 和 index.html (活跃) 中各有一份
→ **suggested fix**: 激活 index.js 并删除 index.html 中的副本, 或反之
→ **confidence**: high | **risk**: CAREFUL

### 5.6 animateCounters — 2处重复

```
index.js:590-605 → 注释死代码
index.html:1518-1533 → 活跃内联脚本
```
→ **problem**: 计数动画重复
→ **suggested fix**: 统一到一处
→ **confidence**: high | **risk**: SAFE

### 5.7 quickFilter — 2处重复

```
index.js:609-632 → 注释死代码
index.html:1547-1592 → 活跃内联脚本 (且更复杂, 含视觉反馈)
```
→ **problem**: 快速筛选函数重复
→ **suggested fix**: 保留 index.html 版本, 删除 index.js 版本
→ **confidence**: high | **risk**: SAFE

### 5.8 toggleHelp — 2处重复

```
index.js:561-576 → 注释死代码
index.html:1489-1502 → 活跃内联脚本
```
→ **problem**: 帮助折叠重复
→ **suggested fix**: 统一到一处
→ **confidence**: high | **risk**: SAFE

### 5.9 搜索建议相关 — 2处重复

```
index.js:473-520 → 注释死代码 (_buildSearchCache, showSearchSuggestions, etc.)
index.html:1317-1375 → 活跃内联脚本
```
→ **problem**: 搜索建议逻辑重复
→ **suggested fix**: 统一到一处
→ **confidence**: high | **risk**: SAFE

### 5.10 resetFilters — 2处重复

```
index.js:523-531 → 注释死代码
index.html:1367-1375 → 活跃内联脚本
```
→ **problem**: 重置筛选重复
→ **confidence**: high | **risk**: SAFE

---

## 六、关键发现总结

| 类别 | 问题数 | 影响 |
|------|--------|------|
| 内联事件处理器 | ~67个 | 可全部迁移到事件委托 |
| DOM 重复查询 | ~40处 | 应缓存到 $ 对象 |
| CSS 硬编码颜色 | ~15处 | 应提取为 CSS 变量 |
| Modal 重复结构 | 2组 | 可提取为 {% include %} |
| 跨文件函数重复 | 10组 | 严重 DRY violation |
| 死代码文件 | index.js (全部) | 需决定激活或删除 |

## 七、优先级建议

1. **P0 - 修复 index.js 死代码问题**: 要么激活 index.js 并从 index.html 移除内联脚本, 要么删除 index.js — 二者选一
2. **P0 - 消除跨文件函数重复**: 将 index.html 中重复的函数全部移动到 app.js, 统一维护点
3. **P1 - 事件委托重构**: 将67个内联事件处理器迁移到事件委托, 减少模板复杂度
4. **P1 - 创建 $ 缓存对象**: 在 app.js 中集中管理 DOM 引用
5. **P2 - CSS 变量提取**: 将常见 Tailwind 颜色值提取为 CSS 变量
6. **P2 - Modal 结构提取**: 将 add-modal 和 edit-modal 的共同部分提取为 {% include %}
