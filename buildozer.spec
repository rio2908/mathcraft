[app]
title = MathCraft
package.name = mathcraft
package.domain = org.game
source.dir = .
source.include_exts = py,png,jpg,json,txt
version = 1.0
requirements = python3,pygame-ce
orientation = landscape
fullscreen = 1
android.archs = arm64-v8a
android.allow_backup = True
android.api = 34
android.minapi = 24
android.ndk = 26b
android.enable_androidx = True
p4a.branch = master

[buildozer]
log_level = 2
warn_on_root = 1