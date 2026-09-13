[app]
title = MathCraft
package.name = mathcraft
package.domain = org.game

source.dir = .
source.include_exts = py,png,jpg,json,txt
source.exclude_dirs = .git,.github,.venv,.web-test-venv,build,bin,.buildozer
source.exclude_patterns = __pycache__/*,*.pyc

version = 1.0
requirements = python3==3.10.11,hostpython3==3.10.11,pygame

orientation = landscape
fullscreen = 1

android.archs = arm64-v8a
android.minapi = 24
android.api = 34
android.ndk = 25b
android.enable_androidx = True
android.allow_backup = True

p4a.bootstrap = sdl2
p4a.branch = v2024.01.21

[buildozer]
log_level = 2
warn_on_root = 1
