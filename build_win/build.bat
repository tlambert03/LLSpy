rmdir /s /q _dist
rmdir /s /q _build
pyinstaller  --noconfirm --upx-dir "C:\Program Files\myapps" --log-level=INFO --distpath=./_dist --workpath=./_build --version-file=./versionInfo llspygui.spec