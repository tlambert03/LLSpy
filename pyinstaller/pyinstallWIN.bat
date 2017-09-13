SET MY_PATH=C:\Users\CBMF\Dropbox (HMS)\Python\lib
SET PATH=%PATH%;%MY_PATH%
pyinstaller  --noconfirm --log-level=WARN ^
			--distpath=./distWIN ^
			--workpath=./buildWIN ^
			llspygui.spec