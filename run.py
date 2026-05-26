import os
import sys
# 确保项目根目录在 path 中
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "src"))

if __name__ == "__main__":
    missing = []
    for mod in ["pyautogui", "xlrd", "pyperclip", "PIL"]:
        try:
            __import__(mod)
        except ImportError:
            missing.append(mod)

    if missing:
        print("缺少依赖库，请运行:")
        print("  pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple")
        print(f"\n缺失: {', '.join(missing)}")
        sys.exit(1)

    from ACRPA import root
    root.mainloop()