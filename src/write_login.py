#!/usr/bin/env python3
"""Write login_standalone.html into the Docker container."""
import sys

# Read from file
with open(sys.argv[1], 'r') as f:
    content = f.read()

# Write to server file
with open('/app/templates/login_standalone.html', 'w') as f:
    f.write(content)

print("Written", len(content), "bytes to /app/templates/login_standalone.html")
