#!/usr/bin/env python3
"""Fix modal z-index in users.html"""
import pathlib

p = pathlib.Path("/app/templates/users.html")
t = p.read_text()

# 修复模态框z-index
t = t.replace('id="addUserModal" class="fixed inset-0 z-50', 'id="addUserModal" class="fixed inset-0 z-[9999]')

p.write_text(t)
print("Fixed modal z-index")
