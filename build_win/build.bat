rmdir /s /q _dist
rmdir /s /q _build
pyinstaller  --noconfirm --log-level=WARN --distpath=./_dist --workpath=./_build --version-file=./versionInfo llspygui.spec