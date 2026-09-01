[app]
title = Risk and Roll
package.name = riskandroll
package.domain = org.darthvader
source.dir = .
source.include_exts = py,png,jpg,jpeg,ttf,otf,wav,ogg,json,csv,txt
version = 0.1

requirements = python3,kivy

orientation = landscape
fullscreen = 1

android.archs = arm64-v8a
android.allow_backup = True
android.api = 31
android.minapi = 21
android.ndk = 23b
android.accept_sdk_license = True
android.bootstrap = sdl2
p4a.branch = master

[buildozer]
log_level = 2
warn_on_root = 1
