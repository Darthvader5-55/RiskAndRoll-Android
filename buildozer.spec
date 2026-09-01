[app]
title = Risk and Roll
package.name = riskandroll
package.domain = org.darthvader
source.dir = .
source.include_exts = py,png,jpg,jpeg,ttf,otf,wav,ogg,json,csv,txt
version = 0.1

# Includes python3, kivy (for the mobile display wrapper), and your game dependencies
requirements = python3,kivy

orientation = landscape
fullscreen = 1

android.archs = arm64-v8a
android.allow_backup = True
android.api = 33
android.minapi = 21
android.ndk = 25b
android.accept_sdk_license = True
p4a.branch = master

[buildozer]
log_level = 2
warn_on_root = 1
