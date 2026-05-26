# -*- mode: python ; coding: utf-8 -*-


block_cipher = None


a = Analysis(
    ['D:\\ACRPA\\run.py'],
    pathex=['D:\\ACRPA\\src'],
    binaries=[],
    datas=[('D:\\ACRPA\\src', '.'), ('D:\\ACRPA\\res', 'res'), ('D:\\ACRPA\\使用说明.txt', '.'), ('D:\\ACRPA\\README.md', '.')],
    hiddenimports=['state', 'scriptdata', 'templates', 'utils', 'commands', 'engine', 'recorder', 'scheduler', 'updater', 'tkinter.ttk', 'tkinter.filedialog', 'tkinter.messagebox', 'pyautogui', 'pyperclip', 'xlrd', 'xlwt', 'PIL.Image', 'PIL.ImageTk', 'PIL.ImageGrab', 'requests', 'urllib3', 'charset_normalizer', 'certifi', 'idna', 'email', 'email.mime', 'email.message', 'email.utils', 'email.encoders', 'queue', 'json', 'datetime', 'ctypes', 'shutil', 're'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['matplotlib', 'scipy', 'pandas', 'PIL.ImageQt', 'PIL.ImageDraw2', 'PIL.ImageFont', 'PIL.ImageFilter', 'PIL.ImageMath', 'PIL.ImagePath', 'PIL.ImageStat', 'PIL.ImageWin', 'PIL.TiffImagePlugin', 'PIL.WebPImagePlugin', 'PIL.PdfImagePlugin', 'PIL.EpsImagePlugin', 'PIL.GifImagePlugin', 'PIL.MpoImagePlugin', 'PIL.PcxImagePlugin', 'PIL.FpxImagePlugin', 'PIL.MicImagePlugin', 'PIL.XbmImagePlugin', 'PyQt5', 'PyQt5.*', 'PySide2', 'PySide6', 'wx', 'kivy', 'aiohttp', 'flask', 'django', 'http.server', 'wsgiref', 'xmlrpc', 'sqlite3', 'sqlalchemy', 'pymysql', 'psycopg2', 'smtplib', 'imaplib', 'poplib', 'pygame', 'pydub', 'astropy', 'IPython', 'jupyter', 'notebook', 'nbformat', 'pip', 'setuptools', 'pkg_resources', 'wheel', 'pytest', 'unittest', 'distutils', 'docx', 'docutils', 'markdown', 'sphinx', 'cryptography', 'cffi', 'bcrypt', 'paramiko', 'bs4', 'html5lib', 'selenium', 'sympy', 'numba', 'dask', 'multiprocessing', 'asyncio', 'tkinter.test', 'tkinter.test.*'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='ACRPA',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=['*.png', '*.ico', '*.jpg', '*.jpeg'],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['D:\\ACRPA\\res\\automation.ico'],
)
