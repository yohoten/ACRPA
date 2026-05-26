"""
ACRPA 精简打包脚本 — 最小化 EXE 体积
用法:
  python build.py              → 单文件 EXE（发布用）
  python build.py --clean      → 清理 + 打包
  python build.py --dir        → 文件夹模式（调试）
  python build.py --console    → 显示控制台（调试）
"""
import os, sys, shutil, subprocess

BASE = os.path.dirname(os.path.abspath(__file__))
SRC  = os.path.join(BASE, "src")
RES  = os.path.join(BASE, "res")
DIST = os.path.join(BASE, "dist")

APP = "ACRPA"
ICON = os.path.join(RES, "automation.ico")
ENTRY = os.path.join(BASE, "run.py")

# ── 仅导入真正需要的模块 ──
HIDDEN_IMPORTS = [
    # 项目模块
    "state", "scriptdata", "templates", "utils", "commands",
    "engine", "recorder", "scheduler", "updater",
    # tkinter
    "tkinter.ttk", "tkinter.filedialog", "tkinter.messagebox",
    # 核心依赖
    "pyautogui", "pyperclip", "xlrd", "xlwt",
    "PIL.Image", "PIL.ImageTk", "PIL.ImageGrab",
    # AI客户端相关
    "requests", "urllib3", "charset_normalizer", "certifi", "idna",
    # requests依赖的标准库
    "email", "email.mime", "email.message", "email.utils", "email.encoders",
    # stdlib 可能遗漏
    "queue", "json", "datetime", "ctypes", "shutil", "re",
]

# ── 附加数据文件（随 exe 解压到运行目录）──
EXTRA_DATAS = [
    os.path.join(BASE, "使用说明.txt"),
    os.path.join(BASE, "README.md"),
]

# ── 排除所有无关节省体积 ──
EXCLUDE_MODULES = [
    # 科学计算 / 数据分析（保留numpy给opencv使用）
    "matplotlib", "scipy", "pandas",
    # 图像处理（PIL 的子格式 — 保留 PNG/JPEG 用于二维码和识图）
    "PIL.ImageQt", "PIL.ImageDraw2", "PIL.ImageFont", "PIL.ImageFilter",
    "PIL.ImageMath", "PIL.ImagePath", "PIL.ImageStat", "PIL.ImageWin",
    "PIL.TiffImagePlugin",
    "PIL.WebPImagePlugin", "PIL.PdfImagePlugin", "PIL.EpsImagePlugin",
    "PIL.GifImagePlugin", "PIL.MpoImagePlugin", "PIL.PcxImagePlugin",
    "PIL.FpxImagePlugin", "PIL.MicImagePlugin", "PIL.XbmImagePlugin",
    # GUI（非 tkinter）
    "PyQt5", "PyQt5.*", "PySide2", "PySide6", "wx", "kivy",
    # 网络 / Web (保留不需要的,移除requests)
    "aiohttp", "flask", "django",
    "http.server", "wsgiref", "xmlrpc",
    # 数据库
    "sqlite3", "sqlalchemy", "pymysql", "psycopg2",
    # 邮件 (保留不需要的,移除email)
    "smtplib", "imaplib", "poplib",
    # 多媒体 (移除opencv_python和cv2，因为我们需要它们)
    "pygame", "pydub", "astropy",
    # 开发工具
    "IPython", "jupyter", "notebook", "nbformat",
    "pip", "setuptools", "pkg_resources", "wheel",
    "pytest", "unittest", "distutils",
    # 文档
    "docx", "docutils", "markdown", "sphinx",
    # 其他重量级
    "cryptography", "cffi", "bcrypt", "paramiko",
    "bs4", "html5lib", "selenium",
    "sympy", "numba", "dask",
    # 系统
    "multiprocessing", "asyncio",
    "tkinter.test", "tkinter.test.*",
]

def check_pyinstaller():
    try:
        import PyInstaller
        print("[OK] PyInstaller {}".format(PyInstaller.__version__))
    except ImportError:
        print("[!] Installing PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

def clean():
    for d in (DIST, os.path.join(BASE, "build")):
        if os.path.exists(d): shutil.rmtree(d)
    spec = os.path.join(BASE, "{}.spec".format(APP))
    if os.path.exists(spec): os.remove(spec)
    print("[CLEAN] Done")

def build(onefile=True, console=False, clean_first=False):
    if clean_first: clean()
    check_pyinstaller()

    cmd = [
        sys.executable, "-m", "PyInstaller",
        ENTRY, "--name", APP,
        "--paths", SRC,
        "--add-data", "{}{}.".format(SRC, os.pathsep),
        "--distpath", DIST,
        "--workpath", os.path.join(BASE, "build"),
        "--clean", "--noconfirm",
    ]

    if onefile: cmd.append("--onefile")
    else:       cmd.append("--onedir")

    if not console: cmd.append("--windowed")

    if os.path.exists(ICON): cmd += ["--icon", ICON]
    if os.path.isdir(RES):   cmd += ["--add-data", "{}{}res".format(RES, os.pathsep)]
    for fp in EXTRA_DATAS:
        if os.path.exists(fp):
            cmd += ["--add-data", "{}{}.".format(fp, os.pathsep)]

    for h in HIDDEN_IMPORTS: cmd += ["--hidden-import", h]
    for e in EXCLUDE_MODULES: cmd += ["--exclude-module", e]

    # UPX 压缩（如果安装了）— 排除图片避免二次压缩损坏
    upx_path = r"H:\UPX\upx.exe"
    if os.path.exists(upx_path):
        cmd += ["--upx-dir", os.path.dirname(upx_path)]
    cmd += ["--upx-exclude", "*.png", "--upx-exclude", "*.ico",
            "--upx-exclude", "*.jpg", "--upx-exclude", "*.jpeg"]

    mode_str = '单文件' if onefile else '文件夹'
    print("\n{}\n  打包 {}\n  模式: {}\n{}\n".format('='*50, APP, mode_str, '='*50))

    r = subprocess.run(cmd, cwd=BASE)
    if r.returncode != 0:
        print("\n[FAIL]")
        return 1

    # 查找输出的 exe
    exe = None
    for root, _, files in os.walk(DIST):
        for f in files:
            if f == "{}.exe".format(APP):
                exe = os.path.join(root, f)
                break
    if exe and os.path.exists(exe):
        size = os.path.getsize(exe) / (1024*1024)
        print("\n[OK] {} ({:.1f} MB)".format(exe, size))
    else:
        print("\n[WARN] EXE not found in {}".format(DIST))
    return 0

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="ACRPA 精简打包")
    p.add_argument("--clean", action="store_true", help="清理缓存")
    p.add_argument("--dir", action="store_true", help="文件夹模式")
    p.add_argument("--console", action="store_true", help="显示控制台")
    args = p.parse_args()
    sys.exit(build(onefile=not args.dir, console=args.console, clean_first=args.clean))
