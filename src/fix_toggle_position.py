#!/usr/bin/env python3
"""Fix desktop sidebar toggle button visibility."""
import pathlib

p = pathlib.Path("/app/templates/base.html")
t = p.read_text()

# Move the desktop sidebar toggle button outside the flex wrapper
old = '''  <div class="flex min-h-screen pt-14 md:pt-0">
    <!-- Sidebar Overlay (Mobile) -->
    <div id="sidebar-overlay" class="fixed inset-0 bg-black/50 z-40 hidden md:hidden"></div>

    <!-- Desktop Sidebar Toggle Button -->
    <button id="desktop-sidebar-toggle" onclick="toggleDesktopSidebar()"
      class="fixed top-4 left-4 z-50 p-2 rounded-lg bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 shadow-sm hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors hidden md:flex items-center justify-center"
      title="切换侧边栏" aria-label="切换侧边栏">
      <svg class="w-5 h-5 text-gray-600 dark:text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"/>
      </svg>
    </button>

    <!-- Sidebar -->'''

new = '''  <!-- Desktop Sidebar Toggle Button (outside flex wrapper) -->
  <button id="desktop-sidebar-toggle" onclick="toggleDesktopSidebar()"
    class="fixed top-4 left-4 z-50 p-2 rounded-lg bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 shadow-sm hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors hidden md:flex items-center justify-center"
    title="切换侧边栏" aria-label="切换侧边栏">
    <svg class="w-5 h-5 text-gray-600 dark:text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"/>
    </svg>
  </button>

  <div class="flex min-h-screen pt-14 md:pt-0 md:pl-12">
    <!-- Sidebar Overlay (Mobile) -->
    <div id="sidebar-overlay" class="fixed inset-0 bg-black/50 z-40 hidden md:hidden"></div>

    <!-- Sidebar -->'''

if old in t:
    t = t.replace(old, new)
    p.write_text(t)
    print("Fixed: moved toggle button outside flex wrapper")
else:
    print("ERROR: old string not found in base.html")
    # Print surrounding context for debugging
    idx = t.find('Desktop Sidebar Toggle Button')
    if idx >= 0:
        print("Found at index", idx)
        print("Context:", repr(t[idx-50:idx+200]))
    else:
        print("String not found at all")
