#!/usr/bin/env python3
"""Fix all three issues: light theme, hamburger menu, user management."""
import pathlib

# ====== FIX 1: base.html - 浅色模式 + 汉堡菜单 ======
p = pathlib.Path("/app/templates/base.html")
t = p.read_text()

# Fix 1a: 首页导航active类添加dark变体
t = t.replace(
    "{{ 'bg-blue-50 text-blue-600' if active_page == 'index' else 'text-gray-700' }}",
    "{{ 'bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400' if active_page == 'index' else 'text-gray-700 dark:text-gray-300' }}"
)

# Fix 1b: 更改密码hover添加dark变体
t = t.replace(
    'hover:bg-gray-100 transition-colors text-orange-600 dark:text-orange-400',
    'hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors text-orange-600 dark:text-orange-400'
)

# Fix 1c: 退出登录hover添加dark变体
t = t.replace(
    'hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors text-red-600 dark:text-red-400',
    'hover:bg-red-50 dark:hover:bg-red-900/20 dark:hover:bg-red-900/20 transition-colors text-red-600 dark:text-red-400'
)

# Fix 1d: 汉堡菜单按钮移到sidebar之后，放在sidebar内部作为第一个元素
# 先移除现有的按钮（在flex wrapper之前）
old_button = '''  <!-- Desktop Sidebar Toggle Button (outside flex wrapper) -->
  <button id="desktop-sidebar-toggle" onclick="toggleDesktopSidebar()"
    class="fixed top-4 left-4 z-50 p-2 rounded-lg bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 shadow-sm hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors hidden md:flex items-center justify-center"
    title="切换侧边栏" aria-label="切换侧边栏">
    <svg class="w-5 h-5 text-gray-600 dark:text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"/>
    </svg>
  </button>'''

new_button = ''
t = t.replace(old_button, new_button)

# 把汉堡按钮放到sidebar内部logo之前
old_logo = '''      <!-- Logo -->
      <div class="p-4 border-b border-gray-200 dark:border-gray-700">'''

new_logo = '''      <!-- Desktop Sidebar Toggle Button (inside sidebar, top-left) -->
      <div class="p-3 border-b border-gray-200 dark:border-gray-700 hidden md:block">
        <button onclick="toggleDesktopSidebar()"
          class="w-full flex items-center justify-center gap-2 p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors text-gray-600 dark:text-gray-300"
          title="收起侧边栏" aria-label="切换侧边栏">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"/>
          </svg>
        </button>
      </div>

      <!-- Logo -->
      <div class="p-4 border-b border-gray-200 dark:border-gray-700">'''

t = t.replace(old_logo, new_logo)

# Fix 1e: 移除main wrapper的md:pl-12（因为汉堡按钮不在那个位置了）
t = t.replace('pt-14 md:pt-0 md:pl-12', 'pt-14 md:pt-0')

# Fix 1f: 侧边栏折叠时main content不需要margin-left了，改用sidebar宽度
# main-content已经有md:ml-64，这没问题

p.write_text(t)
print("Fixed base.html: light theme + hamburger menu")

# ====== FIX 2: users.html - 添加用户改为弹窗 ======
p2 = pathlib.Path("/app/templates/users.html")
t2 = p2.read_text()

# 替换添加用户按钮：从scrollIntoView改为打开弹窗
t2 = t2.replace(
    '''<button onclick="document.getElementById('addUserSection').scrollIntoView({behavior:'smooth'})"
          class="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors text-sm font-medium flex items-center gap-1.5 shadow-sm">
          <i data-lucide="user-plus" class="w-4 h-4 inline-block"></i> 添加用户
        </button>''',
    '''<button onclick="openAddUserModal()"
          class="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors text-sm font-medium flex items-center gap-1.5 shadow-sm">
          <i data-lucide="user-plus" class="w-4 h-4 inline-block"></i> 添加用户
        </button>'''
)

# 隐藏原来的添加用户表单区域（改为弹窗）
t2 = t2.replace(
    '<!-- 添加用户 -->\n  <div id="addUserSection" class="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">',
    '<!-- 添加用户（弹窗形式） -->\n  <div id="addUserSection" class="hidden">'
)

# 在</main>之前添加添加用户弹窗
add_user_modal = '''
  <!-- 添加用户弹窗 -->
  <div id="addUserModal" class="fixed inset-0 z-50 hidden items-center justify-center bg-black/30 backdrop-blur-sm p-4">
    <div class="bg-white rounded-2xl shadow-2xl w-full max-w-lg mx-auto overflow-hidden max-h-[90vh] flex flex-col">
      <div class="px-6 py-4 bg-gradient-to-r from-indigo-500 to-purple-600 text-white flex items-center justify-between">
        <h3 class="font-semibold flex items-center gap-2 text-sm">
          <i data-lucide="user-plus" class="w-4 h-4 inline-block"></i>
          添加新用户
        </h3>
        <button type="button" onclick="closeAddUserModal()" class="p-1 hover:bg-white/20 rounded-lg transition-colors">
          <i data-lucide="x" class="w-4 h-4 inline-block"></i>
        </button>
      </div>
      <form method="POST" action="/users/add" class="p-6 space-y-4 overflow-y-auto">
        <input type="hidden" name="_csrf_token" value="{{ csrf_token }}">
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label class="block text-xs font-medium text-gray-500 mb-1">姓名</label>
            <input type="text" name="name" placeholder="姓名" required
              class="w-full px-3 py-2.5 border border-gray-200 rounded-lg focus:ring-2 focus:ring-indigo-400 focus:border-indigo-400 outline-none text-sm transition-shadow">
          </div>
          <div>
            <label class="block text-xs font-medium text-gray-500 mb-1">用户名</label>
            <input type="text" name="username" placeholder="用户名" required
              class="w-full px-3 py-2.5 border border-gray-200 rounded-lg focus:ring-2 focus:ring-indigo-400 focus:border-indigo-400 outline-none text-sm transition-shadow">
          </div>
        </div>
        <div>
          <label class="block text-xs font-medium text-gray-500 mb-1">密码</label>
          <input type="password" name="password" placeholder="密码" required
            class="w-full px-3 py-2.5 border border-gray-200 rounded-lg focus:ring-2 focus:ring-indigo-400 focus:border-indigo-400 outline-none text-sm transition-shadow">
        </div>
        <div>
          <label class="block text-xs font-medium text-gray-500 mb-1">角色</label>
          <select name="role"
            class="w-full px-3 py-2.5 border border-gray-200 rounded-lg focus:ring-2 focus:ring-indigo-400 focus:border-indigo-400 outline-none text-sm bg-white transition-shadow">
            <option value="user">普通用户</option>
            <option value="admin">管理员</option>
          </select>
        </div>
        <div class="border-t border-gray-100 pt-4">
          <p class="text-xs font-medium text-gray-400 mb-3">联系方式（可选）</p>
          <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div>
              <label class="block text-xs font-medium text-gray-500 mb-1">
                <i data-lucide="mail" class="w-3 h-3 inline-block text-green-500 mr-0.5"></i> 邮箱
              </label>
              <input type="email" name="email" placeholder="邮箱地址"
                class="w-full px-3 py-2.5 border border-gray-200 rounded-lg focus:ring-2 focus:ring-indigo-400 focus:border-indigo-400 outline-none text-sm transition-shadow">
            </div>
            <div>
              <label class="block text-xs font-medium text-gray-500 mb-1">
                <i data-lucide="message-square" class="w-3 h-3 inline-block text-blue-500 mr-0.5"></i> 钉钉ID
              </label>
              <input type="text" name="dingtalk_id" placeholder="钉钉用户ID"
                class="w-full px-3 py-2.5 border border-gray-200 rounded-lg focus:ring-2 focus:ring-indigo-400 focus:border-indigo-400 outline-none text-sm transition-shadow">
            </div>
            <div>
              <label class="block text-xs font-medium text-gray-500 mb-1">
                <i data-lucide="smartphone" class="w-3 h-3 inline-block text-indigo-500 mr-0.5"></i> 企微ID
              </label>
              <input type="text" name="wecom_id" placeholder="企业微信用户ID"
                class="w-full px-3 py-2.5 border border-gray-200 rounded-lg focus:ring-2 focus:ring-indigo-400 focus:border-indigo-400 outline-none text-sm transition-shadow">
            </div>
          </div>
        </div>
        <div class="flex justify-end gap-3 pt-2">
          <button type="button" onclick="closeAddUserModal()"
            class="px-5 py-2.5 text-sm text-gray-500 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors">取消</button>
          <button type="submit"
            class="px-5 py-2.5 text-sm text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 transition-colors shadow-sm">添加用户</button>
        </div>
      </form>
    </div>
  </div>
'''

# 在</main>之前插入弹窗
t2 = t2.replace('</main>\n', add_user_modal + '</main>\n')

# 添加JS函数
t2 = t2.replace(
    '<script src="{{ url_for(\'static\', filename=\'users.js\') }}" nonce="{{ csp_nonce }}"></script>',
    '''<script src="{{ url_for('static', filename='users.js') }}" nonce="{{ csp_nonce }}"></script>

<script nonce="{{ csp_nonce }}">
  function openAddUserModal() {
    var modal = document.getElementById('addUserModal');
    modal.classList.remove('hidden');
    modal.classList.add('flex');
  }
  function closeAddUserModal() {
    var modal = document.getElementById('addUserModal');
    modal.classList.add('hidden');
    modal.classList.remove('flex');
  }
</script>'''
)

p2.write_text(t2)
print("Fixed users.html: add user modal")

print("All fixes applied!")
