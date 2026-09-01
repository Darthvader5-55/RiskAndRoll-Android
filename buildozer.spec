[app]
title = Risk and Roll
package.name = riskandroll
package.domain = org.darthvader
source.dir = .
source.include_exts = py,png,jpg,jpeg,ttf,otf,wav,ogg,json,csv,txt
version = 0.1

# pygame-ce has updated Android SDL2 recipes
requirements = python3,pygame-ce

orientation = landscape
fullscreen = 1

# Modern 64-bit target
android.archs = arm64-v8a

android.allow_backup = True
android.api = 33
android.minapi = 21
android.ndk = 25b
android.accept_sdk_license = True
android.bootstrap = sdl2
p4a.branch = develop

[buildozer]
log_level = 2
warn_on_root = 1
