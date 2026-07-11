#!/usr/bin/env python3
"""Fix desktop sidebar hamburger menu and light theme issues."""
import pathlib

# Fix 1: Update base.html to add desktop hamburger menu
p = pathlib.Path("/opt/data/workspace/cert-monitor/templates/base.html")
t = p.read_text()

# Replace the sidebar to add desktop hamburger toggle
old_sidebar = '''  <div class="flex min-h-screen pt-14 md:pt-0">
    <!-- Sidebar Overlay (Mobile) -->
    <div id="sidebar-overlay" class="fixed inset-0 bg-black/50 z-40 hidden md:hidden"></div>

    <!-- Sidebar -->
    <aside id="sidebar" class="fixed md:sticky top-0 left-0 z-50 md:z-auto h-screen w-64 bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 transform -translate-x-full md:translate-x-0 transition-transform duration-200 ease-in-out flex flex-col">'''

new_sidebar = '''  <div class="flex min-h-screen pt-14 md:pt-0">
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

    <!-- Sidebar -->
    <aside id="sidebar" class="fixed md:sticky top-0 left-0 z-50 md:z-auto h-screen w-64 bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 transform -translate-x-full md:translate-x-0 transition-transform duration-200 ease-in-out flex flex-col">'''

t = t.replace(old_sidebar, new_sidebar)

# Add desktop sidebar state class
old_main_wrapper = '<main id="main-content" class="flex-1 p-4 md:p-6 lg:p-8 pt-14 md:pt-0">'
new_main_wrapper = '<main id="main-content" class="flex-1 p-4 md:p-6 lg:p-8 pt-14 md:pt-0 md:ml-64 transition-all duration-200">'

t = t.replace(old_main_wrapper, new_main_wrapper)

# Add desktop sidebar closed state
old_desktop_css = '''    /* On mobile, sidebar hidden by default */
    @media (max-width: 767px) {'''

new_desktop_css = '''    /* Desktop: sidebar collapsed by default */
    @media (min-width: 768px) {
      #sidebar.collapsed {
        translate: -100% 0 !important;
        transform: none !important;
      }
      #main-content.sidebar-collapsed {
        margin-left: 0 !important;
      }
    }
    /* On mobile, sidebar hidden by default */
    @media (max-width: 767px) {'''

t = t.replace(old_desktop_css, new_desktop_css)

p.write_text(t)
print("Fixed base.html sidebar")

# Fix 2: Add desktop sidebar toggle JS to dark.js
js_p = pathlib.Path("/opt/data/workspace/cert-monitor/static/dark.js")
js_t = js_p.read_text()

# Add desktop sidebar functions before the closing IIFE
old_js_end = '''  // Listen for system theme changes
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function(e) {'''

new_js_end = '''  // Desktop sidebar toggle
  window.toggleDesktopSidebar = function() {
    var sb = document.getElementById('sidebar');
    var mc = document.getElementById('main-content');
    sb.classList.toggle('collapsed');
    mc.classList.toggle('sidebar-collapsed');
  };

  // Listen for system theme changes
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function(e) {'''

js_t = js_t.replace(old_js_end, new_js_end)
js_p.write_text(js_t)
print("Added desktop sidebar JS")

print("Done!")
