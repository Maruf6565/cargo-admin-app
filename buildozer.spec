[app]
# Название и версия
title = Карго Админ
package.name = cargoadmin
package.domain = org.cargoadmin
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json
version = 1.0

# Главный файл
entrypoint = mobile_app.py

# Зависимости Python
requirements = python3,kivy==2.3.0,requests,certifi,urllib3,charset-normalizer,idna

# Ориентация
orientation = portrait

# Android настройки
android.permissions = INTERNET, USE_BIOMETRIC, USE_FINGERPRINT
android.api = 33
android.minapi = 26
android.ndk = 25b
android.archs = arm64-v8a, armeabi-v7a

# Биометрия — нужна androidx.biometric
android.gradle_dependencies = androidx.biometric:biometric:1.1.0
android.enable_androidx = True

# Иконка (положите icon.png рядом с файлом)
# icon.filename = %(source.dir)s/icon.png

# Fullscreen
fullscreen = 0

# Логотип загрузки
# presplash.filename = %(source.dir)s/presplash.png
presplash_color = #0F172A

[buildozer]
log_level = 2
warn_on_root = 1

# ══════════════════════════════════════════════════════════════════
# КАК СОБРАТЬ APK:
#
# 1. Установите buildozer (Linux/macOS или WSL на Windows):
#    pip install buildozer
#
# 2. Установите зависимости (Ubuntu/Debian):
#    sudo apt install -y git zip unzip openjdk-17-jdk python3-pip \
#        autoconf libtool pkg-config zlib1g-dev libncurses5-dev \
#        libncursesw5-dev libtinfo5 cmake libffi-dev libssl-dev
#
# 3. Положите mobile_app.py и этот buildozer.spec в одну папку.
#
# 4. Запустите сборку:
#    buildozer android debug
#
# 5. APK будет в папке:  bin/cargoadmin-1.0-debug.apk
#
# 6. Установите на телефон:
#    adb install bin/cargoadmin-1.0-debug.apk
#    (или просто скопируйте APK на телефон и откройте)
# ══════════════════════════════════════════════════════════════════
