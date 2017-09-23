#!/usr/bin/env bash
export DYLD_LIBRARY_PATH="/Users/talley/DropboxHMS/Python/llspylibs/lib/:$DYLD_LIBRARY_PATH"
rm -rf ./_dist
rm -rf ./_build
pyinstaller  --noconfirm --clean \
	--distpath=./_dist \
	--workpath=./_build \
	--upx-dir="/usr/local/bin/" \
	llspygui.spec

# create the dmg
# echo "creating the dmg..."
# mkdir _dist/dmg
# ln -s /Applications _dist/dmg
# cp -r _dist/LLSpy.app _dist/dmg
# hdiutil create _dist/LLSpy.dmg -srcfolder _dist/dmg
# rm -rf _dist/dmg


# rm -rf _dist/LLSpy

# productbuild --component ./_dist/LLSpy.app /Applications LLSpy.pkg \
#   --sign "3rd Party Mac Developer Installer: Talley Lambert"