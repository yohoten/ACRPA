"""
ACRPA — 自动化工作流工具
Features: Script Editor | Execution Control | Action Recorder | Templates
          Log Export | Screenshot Tool | Error Retry | Dark Mode | Config | Hotkeys

P0 Optimization #1: Lazy imports for heavy libraries (PIL)
"""
import tkinter
from tkinter import ttk
from tkinter import filedialog
from tkinter import messagebox
import os, sys, time, queue, json, re
import pyautogui  # type: ignore
import pyperclip, shutil, threading, datetime
# P0 Optimization #1: Lazy import PIL modules
_PIL_loaded = False
Image = None
ImageTk = None
ImageGrab = None

def _load_pil():
    """Lazy load PIL modules on first use"""
    global Image, ImageTk, ImageGrab, _PIL_loaded
    if not _PIL_loaded:
        from PIL import Image as Img, ImageTk as ITk, ImageGrab as IGr
        Image, ImageTk, ImageGrab = Img, ITk, IGr
        _PIL_loaded = True

import state
from utils import (C, FONT_TITLE, FONT_BODY, FONT_LOG, FONT_SMALL, FONT_BUTTON,
                    PAD, PI, create_card, _btn, _darken, apply_theme,
                    ThreadSafeLog, set_tlog, log1)
from scriptdata import ScriptData
from templates import TEMPLATES
from engine import engine
import recorder
import scheduler as sched
import updater

state.load_config()


# ══════════════════════════════════════════════════
# SECTION: Path Configuration
# ══════════════════════════════════════════════════
if getattr(sys, "frozen", False):
    APP_ROOT = os.path.dirname(sys.executable)
    RES_DIR = os.path.join(APP_ROOT, "res")
    if not os.path.exists(APP_ROOT): os.makedirs(APP_ROOT)
    try:
        bundle_res = os.path.join(sys._MEIPASS, "res")
        if os.path.isdir(bundle_res) and not os.path.isdir(RES_DIR):
            shutil.copytree(bundle_res, RES_DIR)
    except Exception: pass
else:
    APP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    RES_DIR = os.path.join(APP_ROOT, "res")

LOG_DIR = os.path.join(APP_ROOT, "logs")
SCREENSHOT_DIR = os.path.join(APP_ROOT, "screenshots")
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

# ══════════════════════════════════════════════════
# SECTION: Core Logic
# ══════════════════════════════════════════════════

def help1():
    def _write_cmd_table(txt_widget, cmds):
        for name, desc, params, _ in cmds:
            txt_widget.insert("end", "  {}  ".format(name), "cmd")
            txt_widget.insert("end", "{}\n".format(desc), "desc")
            txt_widget.insert("end", "        参数: {}\n".format(params), "param")

    try:
        dlg = tkinter.Toplevel(root); dlg.title("帮助 — A/C RPA"); dlg.geometry("500x600+450+150")
        dlg.transient(root); dlg.grab_set(); dlg.configure(bg=C["bgc"])
        _set_window_icon(dlg)
        dlg.columnconfigure(0, weight=1); dlg.rowconfigure(1, weight=1)
        dlg.resizable(width=True, height=True); dlg.minsize(400, 500)

        contact_card = tkinter.Frame(dlg, bg=C["bgc"], highlightbackground=C["bd"], highlightthickness=1)
        contact_card.grid(row=0, column=0, sticky="ew", padx=10, pady=(10,4))
        contact_card.columnconfigure(1, weight=1)

        tkinter.Label(contact_card, text="联系与支持", font=FONT_TITLE, bg=C["bgc"],
            fg=C["fgt"]).grid(row=0, column=0, columnspan=2, sticky="w", padx=12, pady=(8,4))

        wp = None
        search_dirs = [RES_DIR, APP_ROOT]
        if getattr(sys, "frozen", False):
            search_dirs.insert(0, os.path.join(sys._MEIPASS, "res"))
        for d in search_dirs:
            p = os.path.join(d, "wechat_qrcode.png")
            if os.path.exists(p): wp = p; break

        qr_frame = tkinter.Frame(contact_card, bg=C["bgc"])
        qr_frame.grid(row=1, column=0, sticky="nw", padx=(12,8), pady=(0,8), rowspan=3)

        # Load QR from external file only — drop wechat_qrcode.png next to the exe or in res/
        qr_loaded = False
        for d in [APP_ROOT, RES_DIR]:
            qp = os.path.join(d, "wechat_qrcode.png")
            if os.path.exists(qp):
                try:
                    _load_pil()  # Ensure PIL is loaded before using Image
                    img = Image.open(qp)
                    qr_size = 140
                    ratio = min(qr_size / img.width, qr_size / img.height)
                    img = img.resize((int(img.width * ratio), int(img.height * ratio)), Image.LANCZOS)
                    pimg = ImageTk.PhotoImage(img)
                    qr_lbl = tkinter.Label(qr_frame, image=pimg, bg=C["bgc"], bd=0)
                    qr_lbl.image = pimg
                    qr_lbl.pack()
                    qr_loaded = True
                except Exception as e:
                    log1("二维码加载异常 ({}): {}".format(qp, e), "warning")
                break
        if not qr_loaded:
            log1("未找到二维码图片，请将 wechat_qrcode.png 放到程序目录", "warning")

        info_frame = tkinter.Frame(contact_card, bg=C["bgc"])
        info_frame.grid(row=1, column=1, sticky="w", padx=(0,12), pady=(4,0))

        tkinter.Label(info_frame, text="微信扫描二维码添加好友", font=FONT_BODY, bg=C["bgc"],
            fg=C["fgb"]).pack(anchor="w")
        tkinter.Label(info_frame, text="邮箱: yoho12138@aliyun.com", font=FONT_SMALL, bg=C["bgc"],
            fg=C["ac"], cursor="hand2").pack(anchor="w", pady=(4,0))
        tkinter.Label(info_frame, text="版本: v0.1.13  |  Python tkinter + pyautogui",
            font=FONT_SMALL, bg=C["bgc"], fg=C["fgm"]).pack(anchor="w", pady=(8,0))

        btn_row = tkinter.Frame(contact_card, bg=C["bgc"])
        btn_row.grid(row=2, column=1, sticky="w", padx=(0,12), pady=(8,8))

        def _open_doc(path):
            try: os.startfile(path)
            except Exception as e: log1("打开文档失败: {} — {}".format(path, e))

        doc_path = os.path.join(APP_ROOT, "使用说明.txt")
        readme_path = os.path.join(APP_ROOT, "README.md")

        if os.path.exists(doc_path):
            tkinter.Button(btn_row, text="打开使用说明", font=FONT_SMALL, bg=C["ac"], fg="white",
                relief="raised", bd=3, cursor="hand2", padx=12, pady=3,
                activebackground=C["ach"], activeforeground="white",
                command=lambda p=doc_path: _open_doc(p)).pack(side="left", padx=(0,4))
        if os.path.exists(readme_path):
            tkinter.Button(btn_row, text="查看 README", font=FONT_SMALL, bg=C["bgc"], fg=C["fgb"],
                relief="raised", bd=3, cursor="hand2", padx=12, pady=3,
                activebackground=C["acl"], activeforeground=C["fgb"],
                command=lambda p=readme_path: _open_doc(p)).pack(side="left", padx=(0,4))
        tkinter.Button(btn_row, text="关闭", font=FONT_SMALL, bg=C["bgc"], fg=C["fgb"],
            relief="raised", bd=3, cursor="hand2", padx=12, pady=3,
            activebackground=C["acl"], activeforeground=C["fgb"],
            command=dlg.destroy).pack(side="left")

        cmd_card = tkinter.Frame(dlg, bg=C["bgc"], highlightbackground=C["bd"], highlightthickness=1)
        cmd_card.grid(row=1, column=0, sticky="nsew", padx=10, pady=(4,10))
        cmd_card.columnconfigure(0, weight=1); cmd_card.rowconfigure(1, weight=1)

        tkinter.Label(cmd_card, text="命令速查", font=FONT_TITLE, bg=C["bgc"],
            fg=C["fgt"]).grid(row=0, column=0, sticky="w", padx=12, pady=(8,4))

        txt_frame = tkinter.Frame(cmd_card, bg=C["bgc"])
        txt_frame.grid(row=1, column=0, sticky="nsew", padx=6, pady=(0,6))
        txt_frame.columnconfigure(0, weight=1); txt_frame.rowconfigure(0, weight=1)

        help_txt = tkinter.Text(txt_frame, font=("Microsoft YaHei UI", 9), wrap="word",
            bg=C["logbg"], fg=C["logfg"], relief="flat", bd=0, padx=10, pady=8,
            selectbackground=C["acl"], selectforeground=C["fgt"], cursor="arrow")
        help_txt.grid(row=0, column=0, sticky="nsew")

        help_scroll = tkinter.Scrollbar(txt_frame, width=6, relief="flat", elementborderwidth=0,
            bg=C["bd"], activebackground=C["fgm"], troughcolor=C["logbg"])
        help_scroll.grid(row=0, column=1, sticky="ns")
        help_txt.config(yscrollcommand=help_scroll.set); help_scroll.config(command=help_txt.yview)

        help_txt.tag_configure("h", font=("Microsoft YaHei UI", 9, "bold"), foreground=C["fgt"])
        help_txt.tag_configure("cmd", font=("Microsoft YaHei UI", 9, "bold"), foreground=C["ac"])
        help_txt.tag_configure("desc", foreground=C["fgb"])
        help_txt.tag_configure("param", foreground=C["fgm"], font=("Microsoft YaHei UI", 8))
        help_txt.tag_configure("sep", foreground=C["bd"])

        import commands
        all_cmds = commands.list_all()
        base_ops = all_cmds[:10]
        more_ops = all_cmds[10:]

        help_txt.insert("end", "基础操作\n", "h")
        _write_cmd_table(help_txt, base_ops)
        help_txt.insert("end", "\n更多操作\n", "h")
        _write_cmd_table(help_txt, more_ops)
        help_txt.insert("end", "\n")
        help_txt.insert("end", "━" * 40 + "\n", "sep")
        help_txt.insert("end", "提示: 脚本必须为 .xls 格式, Excel中不填的参数写 None\n", "param")
        help_txt.insert("end", "图片路径不能含中文, 图片名不要用纯数字\n", "param")
        help_txt.insert("end", "True/False 参数前加单引号, 如 'True\n", "param")
        help_txt.insert("end", "━" * 40 + "\n", "sep")
        help_txt.config(state="disabled")

        dlg.bind("<Escape>", lambda e: dlg.destroy())
        dlg.lift(); dlg.focus_force()
    except Exception:
        import traceback
        log1("帮助窗口加载失败:\n{}".format(traceback.format_exc()), "error")

def zuobiaohuoqu():
    if getattr(zuobiaohuoqu, '_active', False):
        state.quit3 = True; zuobiaohuoqu._active = False
        log1("坐标获取已停止"); return
    state.quit3 = False
    zuobiaohuoqu._active = True
    rz.delete(0.0, "end")
    log1("坐标获取已启动 — 每2秒更新一次，再次点击按钮停止")

    def _poll():
        while not state.quit3:
            pos = pyautogui.position()
            log1("当前鼠标坐标是: {}".format(str(pos)))
            for _ in range(20):
                if state.quit3: break
                time.sleep(0.1)
            if not state.quit3:
                log1("--- 2秒后再次定位 ---")
        zuobiaohuoqu._active = False

    t = threading.Thread(target=_poll); t.daemon = True; t.start()

def log1(ims, tag=None): _tlog.put(ims, tag)

def quit1():
    state.quit3=True; state.quit2=True; state.running=False
    state.pause_event.set(); state.exec_state["loop"]=0; state.exec_state["row"]=0
    log1("停止")

def main_run():
    if not state.xuanjb: messagebox.showwarning("错误","没有选择要执行的脚本文件"); return
    if state.running: log1("点击停止按钮再开始运行"); return
    state.quit2=False; state.quit3=True; state.pause_event.set()
    engine.retry = state.RETRY_MAX; engine.retry_interval = state.RETRY_INTERVAL
    loop_val = ComboBox_22_Variable.get()
    tn = 9999800001 if loop_val == "无限循环" else int(loop_val)
    log1("启动任务 (最大重试:{}次, 间隔:{}s)".format(state.RETRY_MAX,state.RETRY_INTERVAL))
    t=threading.Thread(target=autorun, args=(tn,)); t.daemon=True; t.start()

def autorun(tn):
    state.exec_state["total_loops"]=tn; state.exec_state["start_time"]=time.time()
    state.exec_state["loop"]=0; state.exec_state["row"]=0
    while state.exec_state["loop"]<tn:
        if state.quit2: break
        state.exec_state["loop"]+=1
        log1("开始第{}次循环".format(state.exec_state["loop"]))
        
        # Use xlrd to load the script for auto-run
        import xlrd
        from scriptdata import ScriptData
        
        try:
            wb = xlrd.open_workbook(state.filename)
            s1 = wb.sheet_by_index(0)
            rows_data = []
            # Skip header rows (usually first 2 rows in ACRPA format)
            for row_idx in range(2, s1.nrows):
                row = s1.row_values(row_idx)
                if not row or not row[0]: continue
                cmd_type = str(row[0]) if row[0] else ""
                args = [str(cell) if cell else "" for cell in row[1:10]]
                while len(args) < 9: args.append("")
                rows_data.append(ScriptData(cmd_type, args[:9]))
            
            state.exec_state["total_rows"] = len(rows_data)
            wb.release_resources()
        except Exception as e:
            log1("自动运行加载失败: {}".format(e), "error")
            break

        # Use the new execute_script method that supports conditions and loops
        state.running=True
        engine.execute_script(rows_data, state.zname)
        
        state.exec_state["elapsed"]=time.time()-state.exec_state["start_time"]
    state.running=False; state.exec_state["row"]=0; log1("任务终止")


# ══════════════════════════════════════════════════
# SECTION: GUI
# ══════════════════════════════════════════════════

def _colors():
    if state.DARK_MODE:
        return dict(bg="#1a1a2e", bgc="#2d2d44", fgt="#e0e0f0", fgb="#c0c0d0",
            fgm="#8888a0", ac="#7c8cf8", ach="#5b6be0", acl="#2a2a40",
            sc="#22c55e", dg="#ef4444", wn="#f59e0b", bd="#3d3d54",
            logbg="#252538", logfg="#d0d0e0", ebg="#2a2a40")
    return dict(bg="#f0f2f5", bgc="#ffffff", fgt="#1a1a2e", fgb="#333344",
        fgm="#888899", ac="#4f6ef7", ach="#3b54d4", acl="#e8ecff",
        sc="#22c55e", dg="#ef4444", wn="#f59e0b", bd="#e2e4e9",
        logbg="#f8f9fb", logfg="#2d2d3d", ebg="#f8f9fb")

C = _colors()
FONT_TITLE = ("Microsoft YaHei UI",10,"bold"); FONT_BODY = ("Microsoft YaHei UI",9)
FONT_LOG = ("Consolas",9); FONT_SMALL = ("Microsoft YaHei UI",8); FONT_BUTTON = ("Microsoft YaHei UI",9,"bold")

# ── Icon helper for child windows ──
def _set_window_icon(window):
    """Set the ACRPA icon on a child Toplevel window."""
    ico_path = os.path.join(RES_DIR, "automation.ico")
    if not os.path.exists(ico_path):
        ico_path = os.path.join(APP_ROOT, "automation.ico")
    if os.path.exists(ico_path):
        try:
            window.iconbitmap(ico_path)
        except Exception:
            pass

root = tkinter.Tk()
root.title("A/C RPA")
root.geometry("500x600+400+80"); root.minsize(450,550)
root.configure(bg=C["bg"]); root.resizable(width=True,height=True)

ico_path = os.path.join(RES_DIR,"automation.ico")
if not os.path.exists(ico_path): ico_path = os.path.join(APP_ROOT,"automation.ico")
if os.path.exists(ico_path):
    root.iconbitmap(ico_path)
    # Set taskbar icon via AppUserModelID (Windows taskbar group/icon fix)
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("ACRPA.RPA.v0.1.13")
        hwnd = ctypes.windll.user32.GetParent(root.winfo_id())
        ctypes.windll.user32.SetWindowTextW(hwnd, "A/C RPA")
    except Exception: pass

# ttk Style
style = ttk.Style(); style.theme_use("clam")

apply_theme(root, style)

def create_card(parent):
    return tkinter.Frame(parent,bg=C["bgc"],bd=0,
        highlightbackground=C["bd"],highlightthickness=1)

def window_close():
    """Handle window close event with app protection.
    
    Protection levels:
    - Script running → BLOCK close (must stop first)
    - Recording active → BLOCK close (must stop first)
    - Scheduler enabled → WARNING with confirm (user can choose to close)
    - Otherwise → close normally
    """
    # ── Check if app protection is disabled ──
    if not state.APP_PROTECT:
        return _do_close()
    
    # ── Level 1: Script actively running (BLOCK) ──
    if state.running:
        messagebox.showinfo(
            "应用保护 - 无法关闭",
            "脚本正在运行中，无法关闭程序。\n\n"
            "请先点击「停止」按钮结束脚本运行后再关闭窗口。",
            icon=messagebox.WARNING
        )
        return
    
    # ── Level 2: Recording active (BLOCK) ──
    if state.recording:
        messagebox.showinfo(
            "应用保护 - 无法关闭",
            "正在录制操作中，无法关闭程序。\n\n"
            "请先点击「停止录制」按钮结束录制后再关闭窗口。",
            icon=messagebox.WARNING
        )
        return
    
    # ── Level 3: Scheduler enabled (WARNING) ──
    if state.SCHED_ENABLED:
        result = messagebox.askyesno(
            "应用保护",
            "检测到定时任务已启用（下次执行: {}）。\n\n"
            "确定要退出程序吗？\n退出后定时任务将停止执行。".format(
                state.SCHED_NEXT_RUN if state.SCHED_NEXT_RUN else "未计算"),
            icon=messagebox.WARNING
        )
        if not result:
            return  # User cancelled, don't close
    
    # ── No protection needed or user confirmed ──
    _do_close()

def _do_close():
    """Perform the actual close sequence."""
    state._closing = True
    state.save_config()
    
    # Stop scheduler if running
    try:
        import scheduler as sched
        sched.stop_scheduler()
    except Exception:
        pass
    
    if state.quit2:
        root.destroy()
    else:
        state.quit2 = True
        state.pause_event.set()
        root.destroy()

root.protocol("WM_DELETE_WINDOW", window_close)

# ── Layout - compact spacing ──
root.columnconfigure(0,weight=1)
root.rowconfigure(0,weight=0); root.rowconfigure(1,weight=1); root.rowconfigure(2,weight=0)
PAD = {"padx":6,"pady":3}; PI = {"padx":6,"pady":2}

# Title bar - compact design
title_bar = tkinter.Frame(root,bg=C["bg"])
title_bar.grid(row=0,column=0,sticky="ew",padx=10,pady=(6,2))
title_bar.columnconfigure(0,weight=1)

title_lbl = tkinter.Label(title_bar,text="A/C RPA 自动化工作流",
    font=("Microsoft YaHei UI",10,"bold"),fg=C["fgt"],bg=C["bg"])
title_lbl.grid(row=0,column=0,sticky="w")

# Dark mode toggle - compact
dark_frame = tkinter.Frame(title_bar,bg=C["bg"])
dark_frame.grid(row=0,column=1,sticky="e")
status_dot = tkinter.Label(dark_frame,text="● 就绪",font=("Microsoft YaHei UI",8),fg=C["fgm"],bg=C["bg"])
status_dot.pack(side="left",padx=(0,6))
pin_btn = tkinter.Label(dark_frame,text="△",font=("Segoe UI Symbol",9),
    fg=C["fgm"],bg=C["bg"],cursor="hand2",padx=2)
pin_btn.pack(side="left",padx=(0,2))
pin_pinned = False
def toggle_pin():
    global pin_pinned
    pin_pinned = not pin_pinned
    root.attributes("-topmost", pin_pinned)
    pin_btn.config(text="▲" if pin_pinned else "△",
        fg=C["ac"] if pin_pinned else C["fgm"])
pin_btn.bind("<Button-1>", lambda e: toggle_pin())

dark_btn = tkinter.Label(dark_frame,text="◑" if state.DARK_MODE else "◐",
    font=("Segoe UI Symbol",12),fg=C["fgm"],bg=C["bg"],cursor="hand2")
dark_btn.pack(side="left")

# Simple tooltip for dark mode toggle
_tip_win = None
def _show_tip(event):
    global _tip_win
    if _tip_win: _tip_win.destroy()
    _tip_win = tkinter.Toplevel(root)
    _tip_win.wm_overrideredirect(True)
    _tip_win.wm_geometry("+{}+{}".format(event.x_root+12, event.y_root-8))
    tkinter.Label(_tip_win, text="切换暗色模式" if not state.DARK_MODE else "切换亮色模式",
        font=FONT_SMALL, bg=C["bgc"], fg=C["fgb"], relief="solid", bd=1, padx=6, pady=2).pack()
def _hide_tip(event):
    global _tip_win
    if _tip_win: _tip_win.destroy(); _tip_win = None
dark_btn.bind("<Enter>", _show_tip)
dark_btn.bind("<Leave>", _hide_tip)

def _refresh_theme():
    global C
    C = _colors()
    apply_theme(root, style)

    def _walk(p):
        for w in p.winfo_children():
            try:
                cls = w.winfo_class()
                if cls in ("Frame", "TFrame"):
                    # Card = has non-default highlightthickness + highlightbackground
                    ht = int(w.cget("highlightthickness"))
                    if ht > 0:
                        w.configure(bg=C["bgc"], highlightbackground=C["bd"])
                    else:
                        w.configure(bg=C["bg"])
                elif cls in ("Label", "TLabel"):
                    # Labels on main bg have same bg as their parent
                    parent_bg = str(p.cget("bg"))
                    fg_color = C["fgm"]
                    # Preserve accent color for important labels
                    txt = w.cget("text")
                    if txt and ("●" in txt or "运行" in txt or "就绪" in txt):
                        fg_color = C["ac"] if "就绪" in txt else (C["sc"] if "运行" in txt else C["fgm"])
                    w.configure(bg=parent_bg, fg=fg_color)
                elif cls == "Text":
                    w.configure(bg=C["logbg"], fg=C["logfg"],
                        insertbackground=C["fgt"],
                        selectbackground=C["acl"], selectforeground=C["fgt"])
                elif cls == "Scrollbar":
                    w.configure(bg=C["bd"], activebackground=C["fgm"], troughcolor=C["logbg"])
                elif cls == "Button":
                    # Update button colors based on their current bg
                    cur_bg = w.cget("bg")
                    # Keep semantic colors (green/red/yellow/blue) but update neutral buttons
                    if cur_bg in (C.get("old_sc"), C.get("old_dg"), C.get("old_wn"), C.get("old_ac")) or \
                       cur_bg in ("#22c55e", "#ef4444", "#f59e0b", "#4f6ef7", "#7c8cf8"):
                        # Semantic colored buttons - keep color, just update active state
                        pass
                    else:
                        # Neutral buttons - update to new theme
                        w.configure(bg=C["bgc"], fg=C["fgb"],
                            activebackground=C["acl"],
                            highlightbackground=C["bd"])
                elif cls == "Entry":
                    w.configure(bg=C["ebg"], fg=C["fgb"],
                        insertbackground=C["fgt"])
                elif cls == "Combobox":
                    w.configure(background=C["bgc"], fieldbackground=C["bgc"],
                        foreground=C["fgb"])
            except Exception:
                pass
            _walk(w)

    _walk(root)

    # Fix specific overrides
    root.configure(bg=C["bg"])
    title_lbl.configure(bg=C["bg"], fg=C["fgt"])
    status_dot.configure(bg=C["bg"])
    pin_btn.configure(bg=C["bg"])
    dark_btn.configure(bg=C["bg"])
    
    # Update log area
    rz.configure(bg=C["logbg"], fg=C["logfg"],
        selectbackground=C["acl"], selectforeground=C["fgt"])
    scroll.configure(bg=C["bd"], activebackground=C["fgm"], troughcolor=C["logbg"])
    
    # Update status bar
    status_bar.configure(bg=C["bg"])
    status_text.configure(bg=C["bg"])
    
    # Update progress bar container - force ttk style refresh
    progress_bar.configure(style="Success.Horizontal.TProgressbar")
    
    # Update all tab frames
    for widget in [tab_edit, tab_exec, tab_settings]:
        widget.configure(bg=C["bg"])
    
    # Force refresh all ttk widgets by re-applying styles
    notebook.update_idletasks()
    
    # Update checkmark save buttons for dark mode
    try:
        _save_checkmark.configure(bg=C["sc"], fg="white")
    except Exception:
        pass
    # Update all semantic colored buttons to use current theme colors
    # This ensures buttons maintain their semantic meaning across theme changes
    for widget in [btn_run, btn_pause, btn_step]:
        try:
            cur_bg = widget.cget("bg")
            if cur_bg == C.get("old_sc") or cur_bg == "#22c55e" or cur_bg == "#16a34a":
                widget.configure(bg=C["sc"])
            elif cur_bg == C.get("old_wn") or cur_bg == "#f59e0b" or cur_bg == "#d97706":
                widget.configure(bg=C["wn"])
            elif cur_bg == C.get("old_ac") or cur_bg == "#4f6ef7" or cur_bg == "#7c8cf8":
                widget.configure(bg=C["ac"])
        except Exception:
            pass
    
    # Update record button color
    try:
        cur_bg = btn_record.cget("bg")
        if cur_bg == C.get("old_dg") or cur_bg == "#ef4444" or cur_bg == "#dc2626":
            btn_record.configure(bg=C["dg"])
        elif cur_bg == C.get("old_wn") or cur_bg == "#f59e0b" or cur_bg == "#d97706":
            btn_record.configure(bg=C["wn"])
    except Exception:
        pass
    
    # Save old colors for next toggle
    C["old_sc"] = C["sc"]
    C["old_dg"] = C["dg"]
    C["old_wn"] = C["wn"]
    C["old_ac"] = C["ac"]

def toggle_dark():
    state.DARK_MODE = not state.DARK_MODE
    _refresh_theme()
    dark_btn.config(text="◑" if state.DARK_MODE else "◐")
    state.save_config()

dark_btn.bind("<Button-1>", lambda e: toggle_dark())

# Notebook - compact padding
notebook = ttk.Notebook(root)
notebook.grid(row=1,column=0,sticky="nsew",padx=8,pady=(0,3))

# ═══════════════════════════════════════
# TAB 1: 编辑
# ═══════════════════════════════════════
tab_edit = tkinter.Frame(notebook,bg=C["bg"])
notebook.add(tab_edit,text="  脚本编辑  ")
tab_edit.columnconfigure(0,weight=1)
tab_edit.rowconfigure(0,weight=0); tab_edit.rowconfigure(1,weight=1)

# ── Toolbar functions
def _darken(hex_color, factor=0.15):
    """Darken a hex color by multiplying RGB channels."""
    try:
        h = hex_color.lstrip("#")
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        r, g, b = max(0, int(r * (1 - factor))), max(0, int(g * (1 - factor))), max(0, int(b * (1 - factor)))
        return "#{:02x}{:02x}{:02x}".format(r, g, b)
    except Exception:
        return C["acl"]

def _btn(parent,text,cmd,bg_c=None,fg_c=None):
    """Create a button with hover effect."""
    if bg_c is None: bg_c = C["bgc"]
    if fg_c is None: fg_c = C["fgb"]
    if bg_c in ("white", "#ffffff", C["bgc"]):
        abg = C["acl"]
    else:
        abg = _darken(bg_c)
    
    btn = tkinter.Button(parent,text=text,font=FONT_SMALL,bg=bg_c,fg=fg_c,
        activebackground=abg,activeforeground=fg_c,
        relief="raised",bd=3,cursor="hand2",
        padx=4,pady=2,command=cmd)
    
    # Add hover effect
    original_relief = "raised"
    
    def on_enter(e):
        btn.config(relief="sunken")
    
    def on_leave(e):
        btn.config(relief=original_relief)
    
    btn.bind("<Enter>", on_enter)
    btn.bind("<Leave>", on_leave)
    
    return btn

# ── Toolbar with horizontal scrolling for 500px width ──
toolbar = tkinter.Frame(tab_edit,bg=C["bg"])
toolbar.grid(row=0,column=0,sticky="ew",padx=3,pady=(3,2))

# Create a canvas with scrollbar for the toolbar buttons
toolbar_canvas = tkinter.Canvas(toolbar, bg=C["bg"], height=28, 
    highlightthickness=0, bd=0)
toolbar_scrollbar = tkinter.Scrollbar(toolbar, orient="horizontal", 
    command=toolbar_canvas.xview, width=6)
toolbar_inner = tkinter.Frame(toolbar_canvas, bg=C["bg"])

toolbar_inner.bind(
    "<Configure>",
    lambda e: toolbar_canvas.configure(scrollregion=toolbar_canvas.bbox("all"))
)

toolbar_canvas.create_window((0, 0), window=toolbar_inner, anchor="w")

toolbar_canvas.configure(xscrollcommand=toolbar_scrollbar.set)

toolbar_canvas.pack(side="left", fill="x", expand=True)
toolbar_scrollbar.pack(side="right", fill="x")

# Mouse wheel support for horizontal scrolling
def _on_mousewheel(event):
    if event.delta > 0:
        toolbar_canvas.xview_scroll(-1, "units")
    else:
        toolbar_canvas.xview_scroll(1, "units")

toolbar_canvas.bind_all("<MouseWheel>", _on_mousewheel)

# Filename label (right-aligned, outside scrollable area)
edit_file_label = tkinter.Label(toolbar,text="",font=("Microsoft YaHei UI",8),
    fg=C["fgm"],bg=C["bg"],anchor="e")
edit_file_label.pack(side="right", padx=(4,3))

# TreeView - compact layout
tree_frame = tkinter.Frame(tab_edit,bg=C["bgc"],
    highlightbackground=C["bd"],highlightthickness=1)
tree_frame.grid(row=1,column=0,sticky="nsew",padx=3,pady=(0,4))
tree_frame.columnconfigure(0,weight=1); tree_frame.rowconfigure(0,weight=1)

state._editor_rows = []
tree = ttk.Treeview(tree_frame,
    columns=("cmd",)+tuple("p{}".format(i) for i in range(1,10)),
    show="tree headings",selectmode="browse")
tree.grid(row=0,column=0,sticky="nsew")
tree.heading("#0",text=""); tree.column("#0",width=24,minwidth=24,stretch=False)
tree.heading("cmd",text="命令类型"); tree.column("cmd",width=100,minwidth=80)
for i in range(1,10):
    c="p{}".format(i); tree.heading(c,text="参数{}".format(i))
    tree.column(c,width=65,minwidth=50)

tsy=tkinter.Scrollbar(tree_frame,orient="vertical",command=tree.yview,
    width=8,relief="flat",elementborderwidth=0,bg=C["bd"],troughcolor=C["bgc"])
tsx=tkinter.Scrollbar(tree_frame,orient="horizontal",command=tree.xview,
    width=8,relief="flat",elementborderwidth=0,bg=C["bd"],troughcolor=C["bgc"])
tree.configure(yscrollcommand=tsy.set,xscrollcommand=tsx.set)
tsy.grid(row=0,column=1,sticky="ns"); tsx.grid(row=1,column=0,sticky="ew")

tree.bind("<Double-1>",lambda e: _edit_cell())
tree.tag_configure("even", background=C["acl"])
tree.tag_configure("running", background="#FEF3C7")
tree.tag_configure("breakpoint", foreground="#EF4444")

# Breakpoint toggle on #0 column click
def _toggle_breakpoint(event):
    region = tree.identify_region(event.x, event.y)
    if region != "tree": return
    item = tree.identify_row(event.y)
    if not item: return
    row_idx = tree.index(item) + 1  # 1-based to match exec_state["row"]
    if row_idx in state.breakpoints:
        state.breakpoints.discard(row_idx)
        tree.item(item, text="")
    else:
        state.breakpoints.add(row_idx)
        tree.item(item, text="●")
tree.bind("<Button-1>", _toggle_breakpoint, add=True)

# P1 Enhancement: Conditional breakpoint context menu
def _show_conditional_breakpoint_menu(event):
    """Show context menu for setting conditional breakpoints"""
    item = tree.identify_row(event.y)
    if not item:
        return
    
    row_idx = tree.index(item) + 1  # 1-based
    
    # Create context menu
    menu = tkinter.Menu(root, tearoff=0, bg=C["bgc"], fg=C["fgt"],
                       activebackground=C["ac"], activeforeground="white",
                       relief="solid", bd=1)
    
    def set_conditional_bp():
        """Set a conditional breakpoint"""
        cond_win = tkinter.Toplevel(root)
        cond_win.title("设置条件断点 - 行{}".format(row_idx))
        cond_win.geometry("450x180")
        cond_win.resizable(False, False)
        _set_window_icon(cond_win)
        
        tkinter.Label(cond_win, text="条件表达式 (使用 ${var} 引用变量)", 
            font=("Microsoft YaHei UI", 9), bg=C["bgc"]).pack(pady=(10, 5))
        
        # Example conditions
        examples = ["${count} > 10", "${found} == True", "${x} >= 100 and ${y} <= 200"]
        example_frame = tkinter.Frame(cond_win, bg=C["bgc"])
        example_frame.pack(fill="x", padx=10, pady=2)
        tkinter.Label(example_frame, text="示例:", font=("Microsoft YaHei UI", 8), 
            fg=C["fgm"], bg=C["bgc"]).pack(anchor="w")
        for ex in examples:
            tkinter.Label(example_frame, text="• " + ex, font=("Consolas", 8), 
                fg=C["ac"], bg=C["bgc"]).pack(anchor="w")
        
        cond_entry = tkinter.Entry(cond_win, font=("Consolas", 10), width=50)
        cond_entry.pack(pady=10, padx=10, fill="x")
        
        # Check if there's already a conditional breakpoint
        if hasattr(engine, 'conditional_breakpoints') and row_idx in engine.conditional_breakpoints:
            cond_entry.insert(0, engine.conditional_breakpoints[row_idx])
        
        def confirm_condition():
            condition = cond_entry.get().strip()
            if hasattr(engine, 'set_conditional_breakpoint'):
                engine.set_conditional_breakpoint(row_idx, condition)
                
                # Update tree display
                if condition:
                    tree.item(item, text="⚡")  # Lightning bolt for conditional BP
                else:
                    tree.item(item, text="●" if row_idx in state.breakpoints else "")
            
            cond_win.destroy()
        
        btn_frame = tkinter.Frame(cond_win, bg=C["bgc"])
        btn_frame.pack(pady=10)
        
        tkinter.Button(btn_frame, text="确定", command=confirm_condition,
            bg=C["ac"], fg="white", font=FONT_BUTTON, width=10).pack(side="left", padx=5)
        tkinter.Button(btn_frame, text="取消", command=cond_win.destroy,
            bg=C["dg"], fg="white", font=FONT_BUTTON, width=10).pack(side="left", padx=5)
    
    def remove_conditional_bp():
        """Remove conditional breakpoint"""
        if hasattr(engine, 'set_conditional_breakpoint'):
            engine.set_conditional_breakpoint(row_idx, "")
            tree.item(item, text="●" if row_idx in state.breakpoints else "")
    
    menu.add_command(label="设置条件断点...", command=set_conditional_bp)
    menu.add_command(label="移除条件断点", command=remove_conditional_bp)
    menu.add_separator()
    menu.add_command(label="普通断点", command=lambda: _toggle_breakpoint(event))
    
    try:
        menu.tk_popup(event.x_root, event.y_root)
    finally:
        menu.grab_release()

tree.bind("<Button-3>", _show_conditional_breakpoint_menu)

# Keyboard shortcuts for editor
def _kb_copy(event=None):
    sel = tree.selection()
    if not sel: return
    state._editor_clipboard = []
    for item in sel:
        idx = tree.index(item)
        if idx < len(state._editor_rows):
            sd = state._editor_rows[idx]
            state._editor_clipboard.append(ScriptData(sd.cmd_type, list(sd.args)))
    log1("已复制 {} 行".format(len(state._editor_clipboard)))
def _kb_paste(event=None):
    if not state._editor_clipboard: return
    sel = tree.selection()
    insert_at = tree.index(sel[-1]) + 1 if sel else len(state._editor_rows)
    for sd in state._editor_clipboard:
        state._editor_rows.insert(insert_at, ScriptData(sd.cmd_type, list(sd.args)))
        insert_at += 1
    _editor_sync_to_tree()
    log1("已粘贴 {} 行".format(len(state._editor_clipboard)))
tree.bind("<Control-c>", _kb_copy)
tree.bind("<Control-v>", _kb_paste)
tree.bind("<Delete>", lambda e: _cmd_del_row())

# Editor row operations
def _cmd_add_row():
    """Add a new empty row to the editor."""
    sd = ScriptData("", [""] * 9)
    state._editor_rows.append(sd)
    _editor_sync_to_tree()
    # Scroll to the new row
    tree.see(tree.get_children()[-1])
    log1("已添加新行")

def _cmd_del_row():
    """Delete selected rows from the editor."""
    sel = tree.selection()
    if not sel:
        log1("请先选择要删除的行", "warning")
        return
    indices = sorted([tree.index(item) for item in sel], reverse=True)
    for idx in indices:
        if 0 <= idx < len(state._editor_rows):
            state._editor_rows.pop(idx)
    _editor_sync_to_tree()
    log1("已删除 {} 行".format(len(indices)))

def _cmd_move_up():
    """Move selected rows up."""
    sel = tree.selection()
    if not sel: return
    indices = [tree.index(item) for item in sel]
    if not indices or min(indices) == 0: return
    for idx in sorted(indices):
        if idx > 0:
            state._editor_rows[idx-1], state._editor_rows[idx] = \
                state._editor_rows[idx], state._editor_rows[idx-1]
    _editor_sync_to_tree()
    # Reselect moved rows
    for idx in sorted(indices):
        if idx > 0:
            tree.selection_add(tree.get_children()[idx-1])

def _cmd_move_down():
    """Move selected rows down."""
    sel = tree.selection()
    if not sel: return
    indices = [tree.index(item) for item in sel]
    if not indices or max(indices) >= len(state._editor_rows) - 1: return
    for idx in sorted(indices, reverse=True):
        if idx < len(state._editor_rows) - 1:
            state._editor_rows[idx], state._editor_rows[idx+1] = \
                state._editor_rows[idx+1], state._editor_rows[idx]
    _editor_sync_to_tree()
    # Reselect moved rows
    for idx in sorted(indices, reverse=True):
        if idx < len(state._editor_rows) - 1:
            tree.selection_add(tree.get_children()[idx+1])


# Editor ops
def _editor_load_xls(fp):
    state._editor_rows=[]; tree.delete(*tree.get_children())
    try:
        # Use xlrd for reading Excel files
        import xlrd
        wb = xlrd.open_workbook(fp)
        ws = wb.sheet_by_index(0)
        # Skip first 2 rows (header and description)
        for row_idx in range(2, ws.nrows):
            row = ws.row_values(row_idx)
            if not row or not row[0]:  # Skip empty rows
                continue
            sd = ScriptData.from_xlrd_row_values(row)
            state._editor_rows.append(sd)
            tree.insert("", "end", values=sd.to_tuple())
    except Exception as e: 
        log1("加载失败: {}".format(e), "error")
        messagebox.showerror("加载失败", str(e))

# Command-type color map
_CMD_COLORS = {
    "找图":"#2563EB","区域找图":"#2563EB","点图":"#10B981","区域点图":"#10B981",
    "按键":"#8B5CF6","热键":"#EF4444","输入":"#F59E0B","等待":"#6366F1",
    "坐标":"#6B7280","滚轮":"#EC4899","复制":"#14B8A6","粘贴":"#14B8A6",
    "悬停":"#F97316","拖拽":"#F97316","截屏":"#0EA5E9","相移":"#84CC16",
    "按下":"#8B5CF6","释放":"#8B5CF6","代码":"#DC2626",
}



def _editor_sync_to_tree():
    tree.delete(*tree.get_children())
    for i, sd in enumerate(state._editor_rows):
        tag = sd.cmd_type if sd.cmd_type in _CMD_COLORS else ""
        vals = sd.to_tuple()
        item = tree.insert("", "end", values=vals, tags=(tag,))
        if tag and not tree.tag_has(tag):
            tree.tag_configure(tag, foreground=_CMD_COLORS.get(tag, C["fgb"]))
        tags = tree.item(item, "tags")
        if i % 2 == 0: tags = tags + ("even",)
        tree.item(item, tags=tags)
        # Restore breakpoint marker
        if (i + 1) in state.breakpoints:
            tree.item(item, text="●")


def _cmd_clear():
    if messagebox.askyesno("确认","确定要清空所有行吗？"):
        state._editor_rows=[]; state.breakpoints.clear(); tree.delete(*tree.get_children())

def _cmd_new():
    state._editor_rows=[]; state.breakpoints.clear(); tree.delete(*tree.get_children())
    state.xuanjb=False; state.filename=None; state.zname=None
    Entry_19_Variable.set("新建脚本（未保存）")
    edit_file_label.config(text="未保存")
    log1("已创建新脚本")

def _cmd_open():
    fp=filedialog.askopenfilename(title="打开脚本",filetypes=[('Excel 文件','*.xlsx *.xls'), ('xlsx','*.xlsx'), ('xls','*.xls')],initialdir=APP_ROOT)
    if fp:
        state.filename=fp; state.xuanjb=True; state.zname=os.path.dirname(fp)
        Entry_19_Variable.set(os.path.basename(fp))
        edit_file_label.config(text=os.path.basename(fp))
        _editor_load_xls(fp)

def _cmd_save():
    """Save current script to Excel file."""
    if not state._editor_rows:
        messagebox.showwarning("提示", "脚本为空，无法保存")
        return
    
    fp=filedialog.asksaveasfilename(title="保存脚本",defaultextension=".xls",
        filetypes=[('Excel 文件','*.xls')],initialdir=APP_ROOT)
    if fp:
        try:
            # Use xlwt for writing Excel files
            import xlwt
            wb = xlwt.Workbook()
            ws = wb.add_sheet("Sheet1")
            
            # Write header row
            ws.write(0, 0, "命令类型")
            for j in range(1, 10):
                ws.write(0, j, "参数{}".format(j))
            
            # Write description row
            ws.write(1, 0, "（标题行）")
            
            # Write data rows
            for i, sd in enumerate(state._editor_rows, start=2):
                ws.write(i, 0, sd.cmd_type)
                for j in range(9):
                    arg_value = sd.args[j] if j < len(sd.args) else ""
                    ws.write(i, j+1, arg_value)
            
            wb.save(fp)
            state.filename=fp; state.xuanjb=True
            Entry_19_Variable.set(os.path.basename(fp))
            edit_file_label.config(text=os.path.basename(fp))
            log1("脚本已保存: {}".format(fp))
            from utils import show_toast
            show_toast(root, "✓ 脚本已保存 ({} 行)".format(len(state._editor_rows)), "success")
        except ImportError:
            messagebox.showerror("错误","需要安装 xlwt: pip install xlwt")
        except Exception as e: 
            messagebox.showerror("保存失败",str(e))
            from utils import show_toast
            show_toast(root, "保存失败: {}".format(e), "error")


def _open_ai_panel():
    """Open AI script generation dialog with new layout."""
    dlg = tkinter.Toplevel(root)
    dlg.title("AI 脚本生成器")
    dlg.geometry("500x600+400+80")
    dlg.minsize(400, 500)
    dlg.transient(root)
    dlg.grab_set()
    dlg.configure(bg=C["bgc"])
    _set_window_icon(dlg)
    
    # Configure grid for the main container
    dlg.columnconfigure(0, weight=1)
    dlg.rowconfigure(4, weight=1)  # Preview area expands
    
    # === Row 0: Title Label ===
    title_label = tkinter.Label(dlg, text="描述你要实现的操作", 
        font=("Microsoft YaHei UI", 10, "bold"),
        bg=C["bgc"], fg=C["fgt"])
    title_label.grid(row=0, column=0, sticky="w", padx=16, pady=(12, 4))
    
    # === Row 1: Input Text Area ===
    prompt_txt = tkinter.Text(dlg, height=4, font=("Microsoft YaHei UI", 10),
        bg=C["logbg"], fg=C["logfg"], wrap="word", relief="solid", bd=1,
        padx=8, pady=6)
    prompt_txt.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 8))
    prompt_txt.insert("1.0", "快速示例：打开记事本程序，输入'Hello World'，然后保存文件到桌面")
    prompt_txt.tag_add("placeholder", "1.0", "end")
    prompt_txt.tag_configure("placeholder", foreground="#9CA3AF")
    
    def _on_prompt_focus_in(event):
        if prompt_txt.tag_ranges("placeholder"):
            prompt_txt.delete("1.0", "end")
            prompt_txt.tag_remove("placeholder", "1.0", "end")
    
    def _on_prompt_focus_out(event):
        if not prompt_txt.get("1.0", "end-1c").strip():
            prompt_txt.insert("1.0", "快速示例：打开记事本程序，输入'Hello World'，然后保存文件到桌面")
            prompt_txt.tag_add("placeholder", "1.0", "end")
    
    prompt_txt.bind("<FocusIn>", _on_prompt_focus_in)
    prompt_txt.bind("<FocusOut>", _on_prompt_focus_out)
    
    # === Quick Example Buttons Frame ===
    quick_frame = tkinter.Frame(dlg, bg=C["bgc"])
    quick_frame.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 6))
    quick_frame.columnconfigure(0, weight=1)
    
    def _set_quick_example(example_text):
        prompt_txt.delete("1.0", "end")
        prompt_txt.insert("1.0", example_text)
        prompt_txt.tag_remove("placeholder", "1.0", "end")
    
    from templates import AI_QUICK_PROMPTS
    example_names = list(AI_QUICK_PROMPTS.keys())[:4]  # Show first 4 examples
    
    btn_frame = tkinter.Frame(quick_frame, bg=C["bgc"])
    btn_frame.grid(row=0, column=0, sticky="w")
    
    for i, name in enumerate(example_names):
        btn = tkinter.Button(btn_frame, text=name, font=("Microsoft YaHei UI", 7),
            bg=C["bgc"], fg=C["ac"], relief="raised", bd=2, cursor="hand2",
            activebackground=C["acl"], activeforeground=C["ach"],
            command=lambda n=name: _set_quick_example(AI_QUICK_PROMPTS[n]))
        btn.grid(row=0, column=i, padx=2, sticky="w")
    
    # === Row 3: Preview Label ===
    preview_label = tkinter.Label(dlg, text="生成的脚本预览", 
        font=FONT_BODY, fg=C["fgm"], bg=C["bgc"])
    preview_label.grid(row=3, column=0, sticky="w", padx=16, pady=(8, 2))
    
    # === Row 4: Preview Text Area (expands) ===
    result_txt = tkinter.Text(dlg, height=12, font=("Consolas", 10), 
        bg=C["logbg"], fg=C["logfg"], wrap="word", relief="solid", bd=1, 
        padx=8, pady=6)
    result_txt.grid(row=4, column=0, sticky="nsew", padx=16, pady=(0, 8))
    
    # === Row 5: Progress Bar ===
    progress_frame = tkinter.Frame(dlg, bg=C["bgc"])
    progress_frame.grid(row=5, column=0, sticky="ew", padx=16, pady=(0, 4))
    progress_frame.columnconfigure(0, weight=1)
    
    progress_var = tkinter.DoubleVar(value=0)
    progress_bar = ttk.Progressbar(progress_frame, variable=progress_var,
        maximum=100, mode='indeterminate', length=400)
    progress_bar.grid(row=0, column=0, sticky="ew")
    
    # === Row 6: Status Text ===
    status_var = tkinter.StringVar(value="输入操作描述后点击生成（支持Ctrl+Enter快捷生成）")
    status_label = tkinter.Label(dlg, textvariable=status_var, 
        font=FONT_SMALL, bg=C["bgc"], fg=C["fgm"])
    status_label.grid(row=6, column=0, sticky="w", padx=16, pady=(0, 8))
    
    # === Row 7: Action Buttons ===
    button_frame = tkinter.Frame(dlg, bg=C["bgc"])
    button_frame.grid(row=7, column=0, sticky="ew", padx=16, pady=(0, 14))
    button_frame.columnconfigure(1, weight=1)
    
    # Generate button
    gen_btn = tkinter.Button(button_frame, text="▶ 生成脚本", 
        font=FONT_BUTTON, bg=C["ac"], fg="white",
        relief="raised", bd=3, padx=16, pady=4, cursor="hand2",
        activebackground=C["ach"], activeforeground="white")
    gen_btn.grid(row=0, column=0, padx=(0, 6))
    
    # Spacer to push buttons to right
    spacer = tkinter.Frame(button_frame, bg=C["bgc"])
    spacer.grid(row=0, column=1, sticky="ew")
    
    # Insert button
    insert_btn = tkinter.Button(button_frame, text="↓ 插入表格", 
        font=FONT_BUTTON, bg=C["sc"], fg="white",
        relief="raised", bd=3, padx=16, pady=4, cursor="hand2",
        activebackground=_darken(C["sc"]), activeforeground="white")
    insert_btn.grid(row=0, column=2, padx=3)
    
    # Cancel button
    cancel_btn = tkinter.Button(button_frame, text="取消", 
        font=FONT_BUTTON, bg=C["bgc"], fg=C["fgb"],
        relief="raised", bd=3, padx=16, pady=4, cursor="hand2",
        activebackground=_darken(C["bgc"]), activeforeground=C["fgb"],
        highlightbackground=C["bd"], highlightthickness=1,
        command=dlg.destroy)
    cancel_btn.grid(row=0, column=3, padx=(6, 0))
    
    # Define generate function
    def _do_generate():
        """Generate RPA script using AI."""
        user_input = prompt_txt.get("1.0", "end-1c").strip()
        
        # Check if placeholder is still present
        if "快速示例" in user_input or not user_input:
            from utils import show_toast
            show_toast(root, "请先输入操作描述", "warning")
            return
        
        # Start progress animation
        progress_bar.start(10)
        status_var.set("正在生成脚本...")
        gen_btn.config(state="disabled")
        result_txt.delete("1.0", "end")
        
        def _generate_thread():
            try:
                from ai_client import create_client, APIError, APIAuthError, APIRateLimitError, APITimeoutError
                from templates import build_ai_prompt, normalize_ai_output
                
                # Build prompt
                prompt = build_ai_prompt(user_input)
                
                # Create AI client
                client = create_client(state.API_KEY, state.API_MODEL)
                
                # Call AI API
                response = client.chat_completions(
                    model=state.API_MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                    max_tokens=2000,
                    timeout=60
                )
                
                # Get generated content
                raw_output = response.choices[0].message.content.strip()
                
                # ✨ 关键修复：使用normalize_ai_output进行规范化处理
                generated_script = normalize_ai_output(raw_output)
                
                if not generated_script:
                    raise ValueError("AI返回的内容为空或格式无效")
                
                # Display in result text
                result_txt.delete("1.0", "end")
                result_txt.insert("1.0", generated_script)
                
                # Update status
                dlg.after(0, lambda: [
                    progress_bar.stop(),
                    status_var.set(f"✓ 生成成功 ({len(generated_script)} 字符)"),
                    gen_btn.config(state="normal")
                ])
                
            except APIAuthError as e:
                dlg.after(0, lambda err=e: [
                    progress_bar.stop(),
                    status_var.set(f"✗ 认证失败: {err}"),
                    gen_btn.config(state="normal"),
                    messagebox.showwarning("认证失败", str(err))
                ])
            except APIRateLimitError as e:
                dlg.after(0, lambda err=e: [
                    progress_bar.stop(),
                    status_var.set(f"✗ 频率超限: {err}"),
                    gen_btn.config(state="normal"),
                    messagebox.showwarning("请求频率超限", str(err))
                ])
            except APITimeoutError as e:
                dlg.after(0, lambda err=e: [
                    progress_bar.stop(),
                    status_var.set(f"✗ 请求超时: {err}"),
                    gen_btn.config(state="normal"),
                    messagebox.showwarning("请求超时", str(err))
                ])
            except APIError as e:
                dlg.after(0, lambda err=e: [
                    progress_bar.stop(),
                    status_var.set(f"✗ API 错误: {err}"),
                    gen_btn.config(state="normal"),
                    messagebox.showerror("API 错误", str(err))
                ])
            except Exception as e:
                dlg.after(0, lambda err=e: [
                    progress_bar.stop(),
                    status_var.set(f"✗ 生成失败: {err}"),
                    gen_btn.config(state="normal"),
                    messagebox.showerror("生成失败", f"发生未知错误:\n{err}")
                ])
        
        # Start generation in background thread
        import threading
        thread = threading.Thread(target=_generate_thread, daemon=True)
        thread.start()
    
    def _insert_to_editor():
        """Insert generated script into editor."""
        generated_content = result_txt.get("1.0", "end-1c").strip()
        
        if not generated_content:
            from utils import show_toast
            show_toast(root, "没有可插入的内容", "warning")
            return
        
        try:
            # Parse CSV format
            lines = generated_content.split("\n")
            
            # Skip header rows (支持多种标题格式)
            data_lines = []
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                # 跳过标题行和说明行
                if line.startswith("操作") or line.startswith("命令类型") or line.startswith("（标题行）"):
                    continue
                data_lines.append(line)
            
            if not data_lines:
                from utils import show_toast
                show_toast(root, "未找到有效的脚本数据", "warning")
                return
            
            # Parse each line
            from scriptdata import ScriptData
            imported_count = 0
            skipped_count = 0
            
            for line in data_lines:
                parts = line.split(",")
                if len(parts) < 1:
                    skipped_count += 1
                    continue
                
                cmd_type = parts[0].strip()
                
                # 处理None值：将字符串"None"转换为实际的None
                args = []
                for p in parts[1:10]:
                    p_stripped = p.strip()
                    if p_stripped.lower() == 'none' or p_stripped == '':
                        args.append(None)
                    else:
                        args.append(p_stripped)
                
                # Pad args to 9 elements
                while len(args) < 9:
                    args.append(None)
                
                # Validate command type
                if cmd_type in ScriptData.COMMANDS:
                    state._editor_rows.append(ScriptData(cmd_type, args))
                    imported_count += 1
                else:
                    log1(f"⚠️  跳过未知命令: {cmd_type}", "warning")
                    skipped_count += 1
            # Show success message
            msg = f"✓ 已导入 {imported_count} 条命令"
            if skipped_count > 0:
                msg += f" (跳过 {skipped_count} 条)"
            
            log1(msg)
            from utils import show_toast
            show_toast(root, msg, "success")
            
            # Close dialog
            dlg.destroy()
            
        except Exception as e:
            messagebox.showerror("导入失败", f"解析脚本时出错:\n{e}")
            from utils import show_toast
            show_toast(root, f"导入失败: {e}", "error")
    
    # Bind button commands
    gen_btn.config(command=_do_generate)
    insert_btn.config(command=_insert_to_editor)
    
    # Bind Ctrl+Enter to generate
    def _on_ctrl_enter(event):
        if event.state & 0x4:  # Ctrl key
            _do_generate()
            return "break"
    
    prompt_txt.bind("<Control-Return>", _on_ctrl_enter)
    result_txt.bind("<Control-Return>", _on_ctrl_enter)

def _cmd_template():
    """Pop up template selection dialog."""
    dlg=tkinter.Toplevel(root); dlg.title("选择模板"); dlg.geometry("480x580+500+250")
    dlg.transient(root); dlg.grab_set(); dlg.configure(bg=C["bgc"])
    _set_window_icon(dlg)
    
    # Create a header frame to hold both labels side by side
    header_frame = tkinter.Frame(dlg, bg=C["bgc"])
    header_frame.pack(fill="x", padx=12, pady=(10, 6))
    
    # Title label (left aligned)
    tkinter.Label(header_frame, text="选择脚本模板", font=FONT_TITLE, bg=C["bgc"],
        fg=C["fgt"]).pack(side="left")
    
    # Subtitle label (left aligned, with spacing)
    tkinter.Label(header_frame, text="选择后模板将追加到编辑器末尾", font=FONT_SMALL,
        bg=C["bgc"], fg=C["fgm"]).pack(side="left", padx=(12, 0))
    
    # Create a frame for buttons with grid layout
    btn_frame = tkinter.Frame(dlg, bg=C["bgc"])
    btn_frame.pack(fill="both", expand=True, padx=12, pady=(0, 8))
    
    # Configure grid columns (4 columns per row)
    for i in range(4):
        btn_frame.columnconfigure(i, weight=1, uniform="col")
    
    # P0 Optimization #2: Use lazy-loaded template list
    from templates import list_templates, get_template
    
    template_names = list_templates()
    for idx, tname in enumerate(template_names):
        row = idx // 4
        col = idx % 4
        
        btn = tkinter.Button(btn_frame, text=tname, font=("Microsoft YaHei UI", 9),
            bg=C["ac"], fg="white", relief="raised", bd=1, cursor="hand2",
            padx=4, pady=2, activebackground=C["ach"],
            command=lambda n=tname: (_load_template_lazy(n),dlg.destroy()))
        btn.grid(row=row, column=col, padx=2, pady=1, sticky="ew")

def _load_template_lazy(name):
    """Load template on demand using lazy loading (P0 optimization #2)."""
    from templates import get_template
    rows = get_template(name)
    if rows:
        state._editor_rows.extend([ScriptData(r.cmd_type,list(r.args)) for r in rows])
        _editor_sync_to_tree()
        log1("已加载模板: {} ({} 行)".format(name,len(rows)))
    else:
        log1("模板加载失败: {}".format(name), "error")

def _edit_cell():
    sel=tree.selection()
    if not sel: return
    col=int(tree.identify_column(tree.winfo_pointerx()-tree.winfo_rootx()).replace("#",""))-1
    idx=tree.index(sel[0])
    if idx>=len(state._editor_rows) or col<0: return
    sd=state._editor_rows[idx]

    # Image column? Show preview if value is non-empty
    img_path = None
    if col in (1,2) and sd.args[col-1] and state.zname:
        candidate = os.path.join(state.zname, sd.args[col-1] + ".png")
        if os.path.exists(candidate):
            img_path = candidate
        else:
            candidate = os.path.join(state.zname, sd.args[col-1])
            if os.path.exists(candidate):
                img_path = candidate

    dlg=tkinter.Toplevel(root); dlg.title("编辑"); dlg.geometry("360x280+550+250")
    dlg.transient(root); dlg.grab_set(); dlg.configure(bg=C["bgc"])
    _set_window_icon(dlg)
    tkinter.Label(dlg,text="{} 第{}行".format(ScriptData.COLUMNS[col],idx+1),
        font=FONT_BODY,bg=C["bgc"],fg=C["fgb"]).pack(pady=(10,4))
    if col==0:
        var=tkinter.StringVar(value=sd.cmd_type)
        ttk.Combobox(dlg,textvariable=var,values=ScriptData.COMMANDS,
            state="readonly",width=28).pack(pady=4)
    else:
        var=tkinter.StringVar(value=sd.args[col-1])
        tkinter.Entry(dlg,textvariable=var,font=FONT_BODY,width=30).pack(pady=4)

    # Image preview
    if img_path:
        try:
            _load_pil()  # P0 Optimization #1: Lazy load PIL
            pimg = Image.open(img_path)
            pimg.thumbnail((200, 200), Image.LANCZOS)
            pimg_tk = ImageTk.PhotoImage(pimg)
            pl = tkinter.Label(dlg, image=pimg_tk, bg=C["bgc"])
            pl.image = pimg_tk
            pl.pack(pady=(4,0))
            tkinter.Label(dlg, text=os.path.basename(img_path), font=FONT_SMALL,
                fg=C["fgm"], bg=C["bgc"]).pack()
        except Exception:
            tkinter.Label(dlg, text="(图片无法加载)", font=FONT_SMALL,
                fg=C["dg"], bg=C["bgc"]).pack(pady=2)

    def _save():
        """Save the edited cell value."""
        if col == 0:
            sd.cmd_type = var.get()
        else:
            sd.args[col-1] = var.get()
        _editor_sync_to_tree()
        dlg.destroy()

    def _screenshot_to_cell():
        """Take a screenshot and fill the cell with the filename."""
        dlg.destroy()
        root.withdraw()
        
        # Create fullscreen overlay for screenshot
        ov = tkinter.Toplevel()
        ov.attributes("-fullscreen", True)
        ov.attributes("-alpha", 0.4)
        ov.attributes("-topmost", True)
        ov.configure(bg="black")
        ov.config(cursor="cross")
        
        cv = tkinter.Canvas(ov, bg="black", highlightthickness=0)
        cv.pack(fill="both", expand=True)
        
        # Take initial screenshot for reference
        ss = pyautogui.screenshot()
        _load_pil()  # P0 Optimization #1: Lazy load PIL
        ss_img = ImageTk.PhotoImage(ss)
        cv.create_image(0, 0, image=ss_img, anchor="nw")
        cv.ss_img = ss_img
        
        rect = None
        sx = [0]
        sy = [0]
        
        def on_press(e):
            sx[0] = e.x
            sy[0] = e.y
        
        def on_drag(e):
            nonlocal rect
            if rect:
                cv.delete(rect)
            rect = cv.create_rectangle(sx[0], sy[0], e.x, e.y, outline="#4f6ef7", width=2, dash=(4,2))
        
        def on_release(e):
            x1, y1 = min(sx[0], e.x), min(sy[0], e.y)
            x2, y2 = max(sx[0], e.x), max(sy[0], e.y)
            ov.destroy()
            root.deiconify()
            
            if x2 - x1 > 5 and y2 - y1 > 5:
                ts = datetime.datetime.now().strftime("%m%d_%H%M%S")
                save_dir = state.zname if state.zname else SCREENSHOT_DIR
                fp = os.path.join(save_dir, "shot_{}.png".format(ts))
                pyautogui.screenshot(fp, region=(x1, y1, x2-x1, y2-y1))
                
                # Update the cell value with the screenshot filename
                if col > 0:
                    sd.args[col-1] = "shot_{}".format(ts)
                    _editor_sync_to_tree()
                
                log1("截图已保存并填入: {}".format(fp))
        
        cv.bind("<ButtonPress-1>", on_press)
        cv.bind("<B1-Motion>", on_drag)
        cv.bind("<ButtonRelease-1>", on_release)
        cv.bind("<Escape>", lambda e: (ov.destroy(), root.deiconify()))
        cv.focus_set()

    bf=tkinter.Frame(dlg,bg=C["bgc"]); bf.pack(pady=6)
    tkinter.Button(bf,text="确定",font=FONT_BUTTON,bg=C["ac"],fg="white",
        relief="raised",bd=3,padx=16,pady=3,command=_save).pack(side="left",padx=4)
    if col in (1,2):
        tkinter.Button(bf,text="截取",font=FONT_BUTTON,bg=C["sc"],fg="white",
            relief="raised",bd=3,padx=12,pady=3,command=_screenshot_to_cell).pack(side="left",padx=4)
    tkinter.Button(bf,text="取消",font=FONT_BUTTON,bg=C["bgc"],fg=C["fgb"],
        relief="raised",bd=3,padx=16,pady=3,
        cursor="hand2",
        command=dlg.destroy).pack(side="left",padx=4)

# ── Toolbar buttons (grouped with accent strips) - Deferred initialization ──
def _sep(parent):
    """Vertical separator bar between button groups."""
    s = tkinter.Frame(parent, bg=C["bd"], width=2, height=20)
    s.pack(side="left", fill="y", padx=3)


# ══════════════════════════════════════════════════
# SECTION: Debugger Functions (must be before _init_toolbar_buttons)
# ══════════════════════════════════════════════════

def _toggle_debug_mode():
    """Toggle debug mode on/off"""
    state.debug_mode = not state.debug_mode
    if state.debug_mode:
        btn_debug_mode.config(bg=C["ac"], fg="white")
        log1("调试模式已开启", "info")
    else:
        btn_debug_mode.config(bg=C["bgc"], fg=C["fgb"])
        state.step_mode = False
        btn_step_mode.config(bg=C["bgc"], fg=C["fgb"])
        log1("调试模式已关闭", "info")

def _toggle_step_mode():
    """Toggle step-by-step execution mode"""
    if not state.debug_mode:
        log1("请先开启调试模式", "warning")
        return
    
    state.step_mode = not state.step_mode
    if state.step_mode:
        btn_step_mode.config(bg=C["ac"], fg="white")
        log1("单步执行模式已开启 - 每执行一行将暂停", "info")
        if state.running:
            state.pause_event.clear()
    else:
        btn_step_mode.config(bg=C["bgc"], fg=C["fgb"])
        log1("单步执行模式已关闭", "info")
        if state.running:
            state.pause_event.set()

def _show_variables_window():
    """Show the variables monitoring window with event-driven updates"""
    # Check if window already exists
    if hasattr(_show_variables_window, '_win') and _show_variables_window._win.winfo_exists():
        _show_variables_window._win.lift()
        _show_variables_window._win.focus_force()
        return
    
    win = tkinter.Toplevel(root)
    win.title("变量监视器 - ACRPA")
    win.geometry("500x600")
    win.resizable(True, True)
    _set_window_icon(win)
    
    # Store window reference
    _show_variables_window._win = win
    
    # Title bar
    title_frame = tkinter.Frame(win, bg=C["ac"])
    title_frame.pack(fill="x")
    tkinter.Label(title_frame, text="[V] 变量监视器", font=FONT_TITLE, 
        fg="white", bg=C["ac"]).pack(pady=5)
    
    # Notebook for tabs (Variables | Call Stack)
    notebook = ttk.Notebook(win)
    notebook.pack(fill="both", expand=True, padx=10, pady=10)
    
    # === Tab 1: Variables ===
    var_frame = tkinter.Frame(notebook, bg=C["bgc"])
    notebook.add(var_frame, text="变量")
    
    # Variables list frame
    list_frame = tkinter.Frame(var_frame, bg=C["bgc"], 
        highlightbackground=C["bd"], highlightthickness=1)
    list_frame.pack(fill="both", expand=True, padx=5, pady=5)
    
    # Create treeview for variables
    var_tree = ttk.Treeview(list_frame, columns=("name", "value"), show="headings")
    var_tree.heading("name", text="变量名")
    var_tree.heading("value", text="值")
    var_tree.column("name", width=180, minwidth=100)
    var_tree.column("value", width=350, minwidth=150)
    
    # Scrollbar
    vsb = ttk.Scrollbar(list_frame, orient="vertical", command=var_tree.yview)
    var_tree.configure(yscrollcommand=vsb.set)
    
    var_tree.pack(side="left", fill="both", expand=True)
    vsb.pack(side="right", fill="y")
    
    # Button frame for variables tab
    btn_frame = tkinter.Frame(var_frame, bg=C["bg"])
    btn_frame.pack(fill="x", padx=5, pady=(0, 5))
    
    def refresh_vars():
        """Refresh the variables display"""
        for item in var_tree.get_children():
            var_tree.delete(item)
        
        # Add engine variables
        if hasattr(engine, 'variables'):
            for var_name, var_value in engine.variables.items():
                var_tree.insert("", "end", values=(var_name, str(var_value)))
        
        # Add state variables
        state_vars = {
            "running": state.running,
            "recording": state.recording,
            "debug_mode": state.debug_mode,
            "step_mode": state.step_mode,
            "breakpoints_count": len(state.breakpoints),
        }
        for var_name, var_value in state_vars.items():
            var_tree.insert("", "end", values=(var_name, str(var_value)), tags=("state",))
        
        var_tree.tag_configure("state", foreground="#7C3AED")
    
    def add_var():
        """Add a new variable"""
        add_win = tkinter.Toplevel(win)
        add_win.title("添加变量")
        add_win.geometry("350x150")
        add_win.resizable(False, False)
        _set_window_icon(add_win)
        
        tkinter.Label(add_win, text="变量名:", font=FONT_BODY).pack(pady=(10, 2))
        name_entry = tkinter.Entry(add_win, font=FONT_BODY, width=30)
        name_entry.pack(pady=2)
        
        tkinter.Label(add_win, text="值:", font=FONT_BODY).pack(pady=(5, 2))
        value_entry = tkinter.Entry(add_win, font=FONT_BODY, width=30)
        value_entry.pack(pady=2)
        
        def confirm_add():
            name = name_entry.get().strip()
            value = value_entry.get().strip()
            if name:
                if hasattr(engine, 'variables'):
                    try:
                        evaluated_value = eval(value)
                        engine.variables[name] = evaluated_value
                        log1("已添加变量: {} = {}".format(name, evaluated_value))
                    except:
                        engine.variables[name] = value
                        log1("已添加变量: {} = '{}'".format(name, value))
                    refresh_vars()
            add_win.destroy()
        
        tkinter.Button(add_win, text="确定", command=confirm_add, 
            bg=C["ac"], fg="white", font=FONT_BUTTON).pack(pady=10)
    
    tkinter.Button(btn_frame, text="刷新", command=refresh_vars,
        bg=C["ac"], fg="white", font=FONT_SMALL).pack(side="left", padx=2)
    tkinter.Button(btn_frame, text="+ 添加", command=add_var,
        bg=C["sc"], fg="white", font=FONT_SMALL).pack(side="left", padx=2)
    
    # Initial refresh
    refresh_vars()
    
    # P1 Enhancement: Event-driven variable updates
    def on_variable_change(changed_vars):
        """Callback when variables change - only update changed items"""
        if not win.winfo_exists():
            return
        
        # Update only changed variables in the tree
        for item in var_tree.get_children():
            values = var_tree.item(item, "values")
            if values and values[0] in changed_vars:
                var_tree.item(item, values=(values[0], str(changed_vars[values[0]])))
                # Highlight changed items briefly
                var_tree.item(item, tags=("changed",))
                var_tree.tag_configure("changed", background="#FEF3C7")
                win.after(1000, lambda i=item: var_tree.item(i, tags=()))
                return
        
        # If variable is new, refresh entire list
        refresh_vars()
    
    # Register the observer with engine's variable watcher
    if hasattr(engine, 'variable_watcher'):
        engine.variable_watcher.register_observer(on_variable_change)
    
    # Cleanup on window close
    def on_close():
        if hasattr(engine, 'variable_watcher'):
            engine.variable_watcher.unregister_observer(on_variable_change)
        win.destroy()
    
    win.protocol("WM_DELETE_WINDOW", on_close)
    
    # === Tab 2: Call Stack ===
    stack_frame = tkinter.Frame(notebook, bg=C["bgc"])
    notebook.add(stack_frame, text="调用栈")
    
    # Call stack display
    stack_text = tkinter.Text(stack_frame, font=("Consolas", 10), 
        bg=C["logbg"], fg=C["logfg"], wrap="word", relief="solid", bd=1,
        padx=10, pady=10, state="disabled")
    stack_text.pack(fill="both", expand=True, padx=5, pady=5)
    
    def refresh_call_stack():
        """Refresh call stack display"""
        if not win.winfo_exists():
            return
        
        if hasattr(engine, 'call_stack'):
            stack_info = engine.call_stack.get_formatted_stack()
            depth = engine.call_stack.get_depth()
            
            stack_text.config(state="normal")
            stack_text.delete("1.0", "end")
            
            if depth == 0:
                stack_text.insert("end", "当前无嵌套执行上下文\n\n", "info")
                stack_text.insert("end", "提示:\n", "heading")
                stack_text.insert("end", "- 循环开始时会自动推入调用栈\n")
                stack_text.insert("end", "- 条件判断时会记录分支结果\n")
                stack_text.insert("end", "- 可用于调试复杂的嵌套逻辑\n")
            else:
                stack_text.insert("end", "嵌套深度: {}\n\n".format(depth), "info")
                stack_text.insert("end", stack_info + "\n")
            
            stack_text.tag_configure("info", foreground="#3B82F6")
            stack_text.tag_configure("heading", foreground="#10B981", font=("Microsoft YaHei UI", 10, "bold"))
            stack_text.config(state="disabled")
        
        # Schedule next refresh
        if win.winfo_exists():
            win.after(1000, refresh_call_stack)
    
    # Start call stack refresh
    refresh_call_stack()


def _init_toolbar_buttons():
    """Initialize toolbar buttons after all command functions are defined."""
    # Group 1: Row editing operations
    _btn(toolbar_inner,"+ 添加",_cmd_add_row,C["ac"],"white").pack(side="left",padx=1)
    _btn(toolbar_inner,"- 删除",_cmd_del_row,C["dg"],"white").pack(side="left",padx=1)
    _sep(toolbar_inner)
    _btn(toolbar_inner,"↑",_cmd_move_up).pack(side="left",padx=1)
    _btn(toolbar_inner,"↓",_cmd_move_down).pack(side="left",padx=1)
    # Group 2: File operations
    _sep(toolbar_inner)
    _btn(toolbar_inner,"模板",_cmd_template).pack(side="left",padx=1)
    _btn(toolbar_inner,"新建",_cmd_new,C["ac"],"white").pack(side="left",padx=1)
    _btn(toolbar_inner,"打开",_cmd_open,C["ac"],"white").pack(side="left",padx=1)
    _btn(toolbar_inner,"保存",_cmd_save,C["sc"],"white").pack(side="left",padx=1)

    # Group 3: AI and utilities
    _sep(toolbar_inner)
    _btn(toolbar_inner,"AI生成",_open_ai_panel,"#7C3AED","white").pack(side="left",padx=1)
    
    # Group 4: Debugger
    _sep(toolbar_inner)
    global btn_debug_mode, btn_step_mode, btn_variables
    btn_debug_mode = _btn(toolbar_inner,"[D] 调试",_toggle_debug_mode,C["bgc"],C["fgb"])
    btn_debug_mode.pack(side="left",padx=1)
    btn_step_mode = _btn(toolbar_inner,"[S] 单步",_toggle_step_mode,C["bgc"],C["fgb"])
    btn_step_mode.pack(side="left",padx=1)
    btn_variables = _btn(toolbar_inner,"[V] 变量",_show_variables_window,C["bgc"],C["fgb"])
    btn_variables.pack(side="left",padx=1)
    
    _sep(toolbar_inner)
    _btn(toolbar_inner,"清空",_cmd_clear,C["dg"],"white").pack(side="left",padx=1)


# Initialize toolbar buttons now that all command functions are defined
_init_toolbar_buttons()

# ── Shared helpers defined before TAB 2 ──
def xuan():
    state.filename = filedialog.askopenfilename(
        title="选择一个脚本文件",filetypes=[('xls','*.xls')],initialdir=APP_ROOT)
    if state.filename and os.path.getsize(state.filename):
        state.xuanjb=True
        Entry_19_Variable.set(os.path.basename(state.filename))
        edit_file_label.config(text=os.path.basename(state.filename))

        state.zname=os.path.dirname(state.filename)
        rz.delete(0.0,"end"); log1("脚本资源存放目录：{}".format(state.zname))
        status_dot.config(text="● 已加载",fg=C["sc"])
        status_text.config(text=" 脚本已加载 — 点击「开始运行」启动",fg=C["fgb"])
        _editor_load_xls(state.filename)
    else: state.xuanjb=False

def toggle_pause():
    if state.pause_event.is_set():
        state.pause_event.clear(); btn_pause.config(text="▶ 继续",bg=C["ac"])
        status_text.config(text=" 已暂停 — 点击「继续」恢复执行",fg=C["wn"])
        status_dot.config(text="● 已暂停",fg=C["wn"])
    else:
        state.pause_event.set(); btn_pause.config(text="⏸ 暂停",bg=C["wn"])
        status_text.config(text=" 运行中 — 正在执行自动化任务",fg=C["sc"])
        status_dot.config(text="● 运行中",fg=C["sc"])


def _screenshot_tool():
    """Region screenshot using transparent overlay."""
    _load_pil()  # P0 Optimization #1: Lazy load PIL
    root.withdraw()
    time.sleep(0.3)
    ss = pyautogui.screenshot()
    overlay = tkinter.Toplevel()
    overlay.attributes("-fullscreen", True)
    overlay.attributes("-alpha", 0.4)
    overlay.attributes("-topmost", True)
    overlay.configure(bg="black")
    overlay.config(cursor="cross")
    canvas = tkinter.Canvas(overlay, bg="black", highlightthickness=0)
    canvas.pack(fill="both", expand=True)
    ss_img = ImageTk.PhotoImage(ss)
    canvas.create_image(0, 0, image=ss_img, anchor="nw")
    canvas.ss_img = ss_img
    rect = None; start_x = [0]; start_y = [0]

    def on_press(event):
        start_x[0] = event.x; start_y[0] = event.y

    def on_drag(event):
        nonlocal rect
        if rect: canvas.delete(rect)
        rect = canvas.create_rectangle(start_x[0], start_y[0], event.x, event.y,
            outline="white", width=2)

    def on_release(event):
        nonlocal rect
        overlay.destroy()
        root.deiconify()
        x1 = min(start_x[0], event.x)
        y1 = min(start_y[0], event.y)
        x2 = max(start_x[0], event.x)
        y2 = max(start_y[0], event.y)
        width = x2 - x1
        height = y2 - y1
        # 确保截图区域有效（至少 1x1 像素）
        if width <= 0 or height <= 0:
            log1("截图区域无效，请重新选择")
            return
        ss = pyautogui.screenshot(region=(x1, y1, width, height))
        ss.save("screenshot.png")
        log1("截图已保存到当前目录：screenshot.png")

    overlay.bind("<Button-1>", on_press)
    overlay.bind("<B1-Motion>", on_drag)
    overlay.bind("<ButtonRelease-1>", on_release)
    overlay.mainloop()


# ═══════════════════════════════════════
# TAB 2: 执行控制 - compact layout
# ═══════════════════════════════════════
tab_exec = tkinter.Frame(notebook,bg=C["bg"])
notebook.add(tab_exec,text="  执行控制  ")
tab_exec.columnconfigure(0,weight=1)
tab_exec.rowconfigure(0,weight=0); tab_exec.rowconfigure(1,weight=1)

# Config card - merged with progress and buttons
card_config = create_card(tab_exec)
card_config.grid(row=0,column=0,sticky="ew",**PAD)
card_config.columnconfigure(1,weight=1)

tkinter.Label(card_config,text="当前脚本",font=("Microsoft YaHei UI",9),fg=C["fgb"],
    bg=C["bgc"]).grid(row=0,column=0,sticky="w",**PI)

Entry_19_Variable=tkinter.StringVar(value="没有选择文件")
tkinter.Label(card_config,textvariable=Entry_19_Variable,font=("Microsoft YaHei UI",9),
    fg=C["fgb"],bg=C["ebg"],anchor="w",relief="flat",padx=6,pady=2).grid(
    row=0,column=1,sticky="ew",padx=(0,4),pady=2)

tkinter.Button(card_config,text="选择脚本",font=("Microsoft YaHei UI",9,"bold"),bg=C["ac"],fg="white",
    activebackground=C["ach"],activeforeground="white",relief="raised",bd=3,
    cursor="hand2",padx=8,pady=2,command=xuan).grid(row=0,column=2,sticky="e",**PI)

tkinter.Label(card_config,text="运行次数",font=("Microsoft YaHei UI",9),fg=C["fgb"],
    bg=C["bgc"]).grid(row=1,column=0,sticky="w",**PI)
ComboBox_22_Variable=tkinter.StringVar(value="无限循环")
ttk.Combobox(card_config,textvariable=ComboBox_22_Variable,
    values=('无限循环',1,2,3,4,5,6,7,8,9,10),state="readonly",width=10).grid(
    row=1,column=1,sticky="w",padx=(6,4),pady=2)

rf=tkinter.Frame(card_config,bg=C["bgc"]); rf.grid(row=1,column=2,sticky="e",**PI)
btn_run=tkinter.Button(rf,text="▶ 运行",font=("Microsoft YaHei UI",9,"bold"),bg=C["sc"],fg="white",
    activebackground="#16a34a",activeforeground="white",relief="raised",bd=3,
    cursor="hand2",padx=6,pady=2,command=main_run)
btn_run.pack(side="left",padx=(0,2))
btn_pause=tkinter.Button(rf,text="⏸ 暂停",font=("Microsoft YaHei UI",9,"bold"),bg=C["wn"],fg="white",
    activebackground="#d97706",activeforeground="white",relief="raised",bd=3,
    cursor="hand2",padx=6,pady=2,command=toggle_pause)
btn_pause.pack(side="left")
btn_step=tkinter.Button(rf,text="⏭ 单步",font=("Microsoft YaHei UI",9,"bold"),bg=C["ac"],fg="white",
    activebackground=C["ach"],activeforeground="white",relief="raised",bd=3,
    cursor="hand2",padx=6,pady=2,
    command=lambda:(state.pause_event.set(),state.pause_event.clear()))
btn_step.pack(side="left",padx=(2,0))

# Progress bar inline - compact horizontal layout
prog_frame=tkinter.Frame(card_config,bg=C["bgc"])
prog_frame.grid(row=2,column=0,columnspan=3,sticky="ew",padx=8,pady=(3,4))
prog_frame.columnconfigure(1,weight=1)

progress_label=tkinter.Label(prog_frame,text="",font=("Microsoft YaHei UI",8),fg=C["fgm"],bg=C["bgc"])
progress_label.grid(row=0,column=0,sticky="w")
elapsed_label=tkinter.Label(prog_frame,text="",font=("Microsoft YaHei UI",8),fg=C["fgm"],bg=C["bgc"])
elapsed_label.grid(row=0,column=2,sticky="e")
progress_bar=ttk.Progressbar(prog_frame,mode="determinate",style="Success.Horizontal.TProgressbar")
progress_bar.grid(row=0,column=1,sticky="ew",padx=6)

# Log - compact layout
card_log = create_card(tab_exec)
card_log.grid(row=1,column=0,sticky="nsew",**PAD)
card_log.columnconfigure(0,weight=1); card_log.rowconfigure(1,weight=1)

lh=tkinter.Frame(card_log,bg=C["bgc"]); lh.grid(row=0,column=0,sticky="ew",**PI)
lh.columnconfigure(0,weight=1)
tkinter.Label(lh,text="运行日志",font=("Microsoft YaHei UI",9),fg=C["fgm"],bg=C["bgc"]).grid(
    row=0,column=0,sticky="w")
tkinter.Label(lh,text="自动滚动",font=("Microsoft YaHei UI",8),fg=C["fgm"],bg=C["bgc"]).grid(
    row=0,column=1,sticky="e")

log_frame = tkinter.Frame(card_log,bg=C["logbg"])
log_frame.grid(row=1,column=0,sticky="nsew",padx=6,pady=(0,4))
log_frame.columnconfigure(0,weight=1); log_frame.rowconfigure(0,weight=1)

rz=tkinter.Text(log_frame,font=("Consolas",9),fg=C["logfg"],bg=C["logbg"],
    wrap="word",relief="flat",bd=0,padx=6,pady=4,
    selectbackground=C["acl"],selectforeground=C["fgt"],undo=True,maxundo=50)
rz.grid(row=0,column=0,sticky="nsew")
scroll=tkinter.Scrollbar(log_frame,width=6,relief="flat",elementborderwidth=0,
    bg=C["bd"],activebackground=C["fgm"],troughcolor=C["logbg"])
scroll.grid(row=0,column=1,sticky="ns")

scroll.config(command=rz.yview); rz.config(yscrollcommand=scroll.set)
rz.tag_configure("info",foreground=C["fgb"])
rz.tag_configure("success",foreground=C["sc"])
rz.tag_configure("warning",foreground=C["wn"])
rz.tag_configure("error",foreground=C["dg"])

_tlog=ThreadSafeLog(rz); set_tlog(_tlog)

# Action bar inside log card - compact
ab=tkinter.Frame(card_log,bg=C["bgc"])
ab.grid(row=2,column=0,sticky="ew",padx=6,pady=(0,4))
ab.columnconfigure(0,weight=1); ab.columnconfigure(1,weight=1)
ab.columnconfigure(2,weight=1); ab.columnconfigure(3,weight=1)

tkinter.Button(ab,text="■ 停止",font=("Microsoft YaHei UI",9,"bold"),bg=C["dg"],fg="white",
    activebackground="#dc2626",activeforeground="white",relief="raised",bd=3,
    cursor="hand2",padx=8,pady=3,command=quit1).grid(row=0,column=0,sticky="ew",padx=2)
tkinter.Button(ab,text="⊕ 坐标",font=("Microsoft YaHei UI",9,"bold"),bg=C["bgc"],fg=C["fgb"],
    activebackground=C["acl"],activeforeground=C["fgb"],relief="raised",bd=3,cursor="hand2",
    padx=8,pady=3,
    command=zuobiaohuoqu).grid(row=0,column=1,sticky="ew",padx=2)
tkinter.Button(ab,text="截屏",font=("Microsoft YaHei UI",9,"bold"),bg=C["bgc"],fg=C["fgb"],
    activebackground=C["acl"],activeforeground=C["fgb"],relief="raised",bd=3,cursor="hand2",
    padx=8,pady=3,
    command=_screenshot_tool).grid(row=0,column=2,sticky="ew",padx=2)
tkinter.Button(ab,text="? 帮助",font=("Microsoft YaHei UI",9,"bold"),bg=C["bgc"],fg=C["fgb"],
    activebackground=C["acl"],activeforeground=C["fgb"],relief="raised",bd=3,cursor="hand2",
    padx=8,pady=3,
    command=help1).grid(row=0,column=3,sticky="ew",padx=2)

# ═══════════════════════════════════════
# TAB 3: 设置
# ═══════════════════════════════════════
tab_settings = tkinter.Frame(notebook,bg=C["bg"])
notebook.add(tab_settings,text="  设置  ")
tab_settings.columnconfigure(0,weight=1)
tab_settings.rowconfigure(0,weight=0)
tab_settings.rowconfigure(1,weight=0)
tab_settings.rowconfigure(2,weight=0)
tab_settings.rowconfigure(3,weight=1)

# ── 工具函数(需在UI前定义) ──
def _export_log():
    ts=datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    fp=os.path.join(LOG_DIR,"log_{}.txt".format(ts))
    _tlog.export(fp); log1("日志已导出: {}".format(fp))
    messagebox.showinfo("导出成功","日志已保存到:\n{}".format(fp))

def _start_recording():
    if state.recording:
        state.record_stop = True; log1("正在停止录制...")
        btn_record.config(text="● 录制", bg=C["dg"])
        return
    state.recording = True
    btn_record.config(text="■ 停止", bg=C["wn"])
    t = threading.Thread(target=recorder.recorder_thread); t.daemon = True; t.start()

# ═══════════════════════════════════════
# 执行 card (retry + scheduler + API)
# ═══════════════════════════════════════
card_exec = create_card(tab_settings)
card_exec.grid(row=0,column=0,sticky="ew",**PAD)
card_exec.columnconfigure(0,weight=1)

# Title row with inline save button
exec_title = tkinter.Frame(card_exec, bg=C["bgc"])
exec_title.grid(row=0, column=0, sticky="ew", padx=10, pady=(6,2))
exec_title.columnconfigure(0, weight=1)

tkinter.Label(exec_title, text="执行", font=("Microsoft YaHei UI",10,"bold"), bg=C["bgc"],
    fg=C["fgt"]).grid(row=0, column=0, sticky="w")

_save_checkmark = tkinter.Label(exec_title, text="✓", font=("Segoe UI Symbol", 11, "bold"),
    bg=C["sc"], fg="white", width=2, height=1, cursor="hand2")
_save_checkmark.grid(row=0, column=1, sticky="e", padx=(4,0))

def _on_save_enter(event):
    _save_checkmark.configure(bg=_darken(C["sc"]))
def _on_save_leave(event):
    _save_checkmark.configure(bg=C["sc"])
def _on_save_click(event):
    _apply_settings()
    _save_checkmark.configure(bg=C["ac"])
    card_exec.after(300, lambda: _save_checkmark.configure(bg=C["sc"]))

_save_checkmark.bind("<Enter>", _on_save_enter)
_save_checkmark.bind("<Leave>", _on_save_leave)
_save_checkmark.bind("<Button-1>", _on_save_click)

# ── Retry settings row ──
retry_frame = tkinter.Frame(card_exec, bg=C["bgc"])
retry_frame.grid(row=1, column=0, sticky="ew", padx=8, pady=2)

tkinter.Label(retry_frame,text="重试:",font=("Microsoft YaHei UI",9),fg=C["fgb"],
    bg=C["bgc"]).pack(side="left", padx=(0,4))
retry_var = tkinter.StringVar(value=str(state.RETRY_MAX))
ttk.Combobox(retry_frame,textvariable=retry_var,values=(0,1,2,3,5,10),
    state="readonly",width=5).pack(side="left", padx=(0,6))

tkinter.Label(retry_frame,text="间隔:",font=("Microsoft YaHei UI",9),fg=C["fgb"],
    bg=C["bgc"]).pack(side="left", padx=(0,4))
interval_var = tkinter.StringVar(value=str(state.RETRY_INTERVAL))
ttk.Combobox(retry_frame,textvariable=interval_var,
    values=(0.5,1.0,2.0,3.0,5.0),state="readonly",width=5).pack(side="left", padx=(0,6))

tkinter.Label(retry_frame,text="识图超时:",font=("Microsoft YaHei UI",9),fg=C["fgb"],
    bg=C["bgc"]).pack(side="left", padx=(0,4))
timeout_var = tkinter.StringVar(value=str(state.IMAGE_TIMEOUT))
ttk.Combobox(retry_frame,textvariable=timeout_var,
    values=(3.0,5.0,8.0,10.0,15.0,20.0,30.0),state="readonly",width=5).pack(side="left")

# ── Hint + App protection ──
hint_frame = tkinter.Frame(card_exec, bg=C["bgc"])
hint_frame.grid(row=2, column=0, sticky="ew", padx=8, pady=(0,2))

tkinter.Label(hint_frame, text="(默认5秒，超时自动跳过)", font=("Microsoft YaHei UI",8),
    fg=C["fgm"], bg=C["bgc"]).pack(side="left")

app_protect_var = tkinter.BooleanVar(value=state.APP_PROTECT)
ttk.Checkbutton(hint_frame, text="关闭时确认", variable=app_protect_var).pack(side="right")
check_update_var = tkinter.BooleanVar(value=state.CHECK_UPDATE)
ttk.Checkbutton(hint_frame, text="检查更新", variable=check_update_var).pack(side="right", padx=(8,0))

# ── Separator ──
tkinter.Frame(card_exec, bg=C["bd"], height=1).grid(row=3, column=0, sticky="ew", padx=10, pady=(4,2))

# ── Scheduler section (merged into 执行) ──
tkinter.Label(card_exec, text="定时执行", font=("Microsoft YaHei UI",9,"bold"),
    bg=C["bgc"], fg=C["fgb"]).grid(row=4, column=0, sticky="w", padx=10, pady=(2,0))

# UI vars for scheduler
state._sched_enabled_var = tkinter.BooleanVar(value=state.SCHED_ENABLED)
_sched_hour_var = tkinter.StringVar(value="{:02d}".format(state.SCHED_HOUR))
_sched_minute_var = tkinter.StringVar(value="{:02d}".format(state.SCHED_MINUTE))
_repeat_labels = {"once":"仅一次","daily":"每天","weekly":"每周"}
_sched_repeat_var = tkinter.StringVar(value=_repeat_labels.get(state.SCHED_REPEAT_MODE,"仅一次"))
_sched_weekday_labels = ["一","二","三","四","五","六","七"]
_sched_weekday_vars = [tkinter.BooleanVar(value=v) for v in state.SCHED_WEEKDAYS]

# Enable + time
enable_frame = tkinter.Frame(card_exec, bg=C["bgc"])
enable_frame.grid(row=5, column=0, sticky="ew", padx=8, pady=(2,2))

ttk.Checkbutton(enable_frame,text="启用定时",
    variable=state._sched_enabled_var).pack(side="left", padx=(0,8))

tkinter.Label(enable_frame,text="时刻:",font=("Microsoft YaHei UI",9),
    fg=C["fgb"],bg=C["bgc"]).pack(side="left", padx=(0,4))
tf=tkinter.Frame(enable_frame,bg=C["bgc"]); tf.pack(side="left")
ttk.Combobox(tf,textvariable=_sched_hour_var,values=["{:02d}".format(i) for i in range(24)],
    state="readonly",width=4).pack(side="left")
tkinter.Label(tf,text=":",font=("Microsoft YaHei UI",9),fg=C["fgb"],bg=C["bgc"]).pack(side="left",padx=2)
ttk.Combobox(tf,textvariable=_sched_minute_var,values=["{:02d}".format(i) for i in range(60)],
    state="readonly",width=4).pack(side="left")

# Repeat + weekdays
repeat_frame = tkinter.Frame(card_exec, bg=C["bgc"])
repeat_frame.grid(row=6, column=0, sticky="ew", padx=8, pady=(0,2))

tkinter.Label(repeat_frame,text="重复:",font=("Microsoft YaHei UI",9),
    fg=C["fgb"],bg=C["bgc"]).pack(side="left", padx=(0,4))
_rep_combo=ttk.Combobox(repeat_frame,textvariable=_sched_repeat_var,
    values=("仅一次","每天","每周"),state="readonly",width=8)
_rep_combo.pack(side="left", padx=(0,8))

_wf=tkinter.Frame(repeat_frame,bg=C["bgc"]); _wf.pack(side="left")
tkinter.Label(_wf,text="星期:",font=("Microsoft YaHei UI",9),fg=C["fgb"],bg=C["bgc"]).pack(side="left",padx=(0,4))
for i,lt in enumerate(_sched_weekday_labels):
    ttk.Checkbutton(_wf,text=lt,variable=_sched_weekday_vars[i]).pack(side="left",padx=1)

def _sched_toggle_weekdays(*_):
    if _sched_repeat_var.get()=="每周": _wf.pack(side="left")
    else: _wf.pack_forget()
_sched_repeat_var.trace_add("write",_sched_toggle_weekdays)
_sched_toggle_weekdays()

# Next run
next_frame = tkinter.Frame(card_exec, bg=C["bgc"])
next_frame.grid(row=7, column=0, sticky="ew", padx=8, pady=(0,2))

tkinter.Label(next_frame,text="下次执行:",font=("Microsoft YaHei UI",9),
    fg=C["fgb"],bg=C["bgc"]).pack(side="left", padx=(0,6))
_sched_next_label=tkinter.Label(next_frame,text=state.SCHED_NEXT_RUN if state.SCHED_NEXT_RUN else "--:--",
    font=("Microsoft YaHei UI",9),fg=C["ac"],bg=C["bgc"])
_sched_next_label.pack(side="left")

# ── API config row ──
api_frame = tkinter.Frame(card_exec, bg=C["bgc"])
api_frame.grid(row=8, column=0, sticky="ew", padx=8, pady=(4,6))
api_frame.columnconfigure(0, weight=0); api_frame.columnconfigure(1, weight=1)

tkinter.Label(api_frame, text="AI Key", font=("Microsoft YaHei UI",9), fg=C["fgb"], bg=C["bgc"]).grid(
    row=0, column=0, sticky="w", padx=(0,6), pady=2)
api_key_var = tkinter.StringVar(value=state.API_KEY)
api_key_entry = tkinter.Entry(api_frame, textvariable=api_key_var, width=28,
    font=("Microsoft YaHei UI",8), show="*", relief="solid", bd=1, bg=C["ebg"], fg=C["fgb"])
api_key_entry.grid(row=0, column=1, sticky="ew", pady=2)

tkinter.Label(api_frame, text="模型", font=("Microsoft YaHei UI",9), fg=C["fgb"], bg=C["bgc"]).grid(
    row=1, column=0, sticky="w", padx=(0,6), pady=2)
api_model_var = tkinter.StringVar(value=state.API_MODEL)
api_model_combo = ttk.Combobox(api_frame, textvariable=api_model_var, width=22,
    values=("gpt-3.5-turbo", "gpt-4", "deepseek-v4-flash", "qwen-plus", "qwen-max"),
    state="readonly")
api_model_combo.grid(row=1, column=1, sticky="ew", pady=2)

# ── Unified save handler (retry + scheduler + API) ──
def _apply_settings():
    state.RETRY_MAX=int(retry_var.get())
    state.RETRY_INTERVAL=float(interval_var.get())
    state.IMAGE_TIMEOUT=float(timeout_var.get())
    state.API_KEY=api_key_var.get()
    state.API_MODEL=api_model_var.get()
    state.APP_PROTECT=app_protect_var.get()
    state.CHECK_UPDATE=check_update_var.get()
    engine.retry=state.RETRY_MAX
    engine.retry_interval=state.RETRY_INTERVAL
    # Scheduler settings
    state.SCHED_ENABLED = state._sched_enabled_var.get()
    state.SCHED_HOUR = int(_sched_hour_var.get())
    state.SCHED_MINUTE = int(_sched_minute_var.get())
    mode_map = {"仅一次": "once", "每天": "daily", "每周": "weekly"}
    state.SCHED_REPEAT_MODE = mode_map.get(_sched_repeat_var.get(), "once")
    state.SCHED_WEEKDAYS = [v.get() for v in _sched_weekday_vars]
    sched_enabled = state.SCHED_ENABLED
    sched.stop_scheduler()
    state.SCHED_ENABLED = sched_enabled  # restore (stop_scheduler sets it False)
    sched.calc_next_run()
    if sched_enabled:
        sched.start_scheduler(main_run, state.save_config)
    state.save_config()
    log1("设置已保存: 重试{}次 间隔{}s 超时{}s 模型{} 定时{} 保护{}".format(
        state.RETRY_MAX, state.RETRY_INTERVAL, state.IMAGE_TIMEOUT, state.API_MODEL,
        "启用" if state.SCHED_ENABLED else "关闭",
        "启用" if state.APP_PROTECT else "禁用"))

# ═══════════════════════════════════════
# 工具 card
# ═══════════════════════════════════════
card_tools = create_card(tab_settings)
card_tools.grid(row=1,column=0,sticky="ew",**PAD)
card_tools.columnconfigure(0,weight=1); card_tools.columnconfigure(1,weight=1)

tools_title = tkinter.Frame(card_tools, bg=C["bgc"])
tools_title.grid(row=0, column=0, columnspan=2, sticky="ew", padx=10, pady=(6,4))
tkinter.Label(tools_title, text="工具", font=("Microsoft YaHei UI",10,"bold"), bg=C["bgc"],
    fg=C["fgt"]).pack(side="left")

tkinter.Button(card_tools,text="导出日志",font=("Microsoft YaHei UI",9,"bold"),bg=C["ac"],fg="white",
    activebackground=C["ach"],activeforeground="white",
    relief="raised",bd=3,padx=10,pady=3,cursor="hand2",command=_export_log).grid(
    row=1,column=0,pady=2,padx=(4,2),sticky="ew")
btn_record = tkinter.Button(card_tools,text="● 录制",font=("Microsoft YaHei UI",9,"bold"),bg=C["dg"],fg="white",
    activebackground="#dc2626",activeforeground="white",
    relief="raised",bd=3,padx=10,pady=3,cursor="hand2",command=_start_recording)
btn_record.grid(row=1,column=1,pady=2,padx=(2,4),sticky="ew")

tkinter.Label(card_tools,text="录制时操作自动生成脚本",
    font=("Microsoft YaHei UI",8),bg=C["bgc"],fg=C["fgm"]).grid(
    row=2,column=0,columnspan=2,pady=(2,4),sticky="w",padx=10)

# Protection info
protect_info = tkinter.Label(tab_settings,
    text="提示：启用关闭时确认后，关闭程序时会检查任务运行状态",
    font=("Microsoft YaHei UI",8), fg=C["fgm"], bg=C["bg"], anchor="w")
protect_info.grid(row=2, column=0, sticky="ew", padx=10, pady=(3,6))

# Wire scheduler to GUI
sched.set_gui_refs(root, state._sched_enabled_var, _sched_next_label)
recorder.set_root(root)

# ── Recording done callback: inject recorded actions into editor ──
def _on_recording_done():
    for sd in state.recorded_actions:
        state._editor_rows.append(sd)
    _editor_sync_to_tree()
    log1("已从录制导入 {} 条命令".format(len(state.recorded_actions)))
state._on_recording_done = _on_recording_done

# ═══════════════════════════════════════
# Status Bar - compact
status_bar = tkinter.Frame(root,bg=C["bg"])
status_bar.grid(row=2,column=0,sticky="ew",padx=10,pady=(3,6))
status_bar.columnconfigure(0,weight=1)
status_text = tkinter.Label(status_bar,text="就绪 — 请选择脚本文件开始",
    font=("Microsoft YaHei UI",8),fg=C["fgm"],bg=C["bg"],anchor="w")
status_text.grid(row=0,column=0,sticky="w")

# ═══════════════════════════════════════
# Periodic Updates
# ═══════════════════════════════════════

def _periodic():
    if state._closing: return
    try: _tlog.flush(root)
    except Exception: return
    _pc = getattr(_periodic, "_cache", {})
    is_running = state.running
    is_paused = is_running and not state.pause_event.is_set()
    is_stopped = bool(state.quit2)
    is_recording = state.recording
    new_status = (1 if is_paused else 2 if is_running else 3 if is_stopped else 0)
    if _pc.get("status") != new_status:
        _pc["status"] = new_status
        if is_paused:
            status_text.config(text=" 已暂停 — 点击继续恢复执行",fg=C["wn"])
            status_dot.config(text="● 已暂停",fg=C["wn"])
        elif is_running:
            status_text.config(text=" 运行中 — 正在执行自动化任务",fg=C["sc"])
            status_dot.config(text="● 运行中",fg=C["sc"])
        elif is_stopped:
            status_text.config(text=" 已停止 — 点击开始运行重新启动",fg=C["dg"])
            status_dot.config(text="● 已停止",fg=C["dg"])
        else:
            status_text.config(text=" 就绪 — 请选择脚本文件开始",fg=C["fgm"])
            status_dot.config(text="● 就绪",fg=C["fgm"])
    if is_running and state.exec_state.get("total_rows",0)>0:
        lp=state.exec_state["loop"]; tl=state.exec_state["total_loops"]
        rw=state.exec_state["row"]; tr=state.exec_state["total_rows"]
        pct = max(0, min(100, int(rw / max(1, tr) * 100)))
        if _pc.get("pct") != pct:
            _pc["pct"] = pct; progress_bar.config(value=pct)
            el=time.time()-state.exec_state["start_time"]
            progress_label.config(text="  循环: {}/{} · 当前行: {}/{}".format(
                lp,"∞" if tl>99999 else tl,rw,tr))
            elapsed_label.config(text="已用时: {:.0f}s  ".format(el))
    elif not is_running and _pc.get("pct",0) != 0:
        _pc["pct"] = 0; progress_bar.config(value=0)
    hl = state.highlight_row
    if _pc.get("hl") != hl:
        children = tree.get_children()
        if _pc.get("hl_old"):
            oi = _pc["hl_old"] - 1
            if 0 <= oi < len(children):
                tags = list(tree.item(children[oi],"tags"))
                if "running" in tags: tags.remove("running"); tree.item(children[oi],tags=tags)
        if hl > 0 and not is_stopped:
            ni = hl - 1
            if 0 <= ni < len(children):
                tags = list(tree.item(children[ni],"tags"))
                if "running" not in tags: tags.append("running"); tree.item(children[ni],tags=tags)
        _pc["hl"] = hl; _pc["hl_old"] = hl
    _periodic._cache = _pc
    if is_recording:
        n = len(state.recorded_actions)
        status_text.config(text=" ● 录制中 · {} 个动作 · Ctrl+Shift+Q 停止".format(n),fg=C["dg"])
        status_dot.config(text="● 录制",fg=C["dg"])
    if state.SCHED_ENABLED or state.SCHED_NEXT_RUN:
        _sched_next_label.config(text=state.SCHED_NEXT_RUN if state.SCHED_NEXT_RUN else "--:--")
    if state.SCHED_ENABLED and not state._sched_thread_active:
        sched.start_scheduler(main_run, state.save_config)
    root.after(100,_periodic)
root.after(100,_periodic)

# ── Update check (runs once, 3s after startup) ──
_update_done = False
def _check_update():
    global _update_done
    if _update_done: return
    _update_done = True
    if state.CHECK_UPDATE:
        def _on_update(ver, url):
            status_text.config(text=" 新版本 v{} 可用 — 点击下载".format(ver), fg=C["wn"])
            status_dot.config(text=" 更新", fg=C["wn"])
            status_text._update_url = url
            status_text.bind("<Button-1>", lambda e: os.startfile(status_text._update_url))
            status_text.config(cursor="hand2")
        updater.check_async(_on_update)
root.after(3000, _check_update)

# ── Global hotkey polling (lightweight: poll keyboard state via ctypes) ──
def _hotkey_poll():
    if state._closing: return
    try:
        import ctypes
        # Check Ctrl+Shift+Q for stop state.recording
        VK_CONTROL = 0x11; VK_SHIFT = 0x10; VK_Q = 0x51
        ctrl = ctypes.windll.user32.GetAsyncKeyState(VK_CONTROL) & 0x8000
        shift = ctypes.windll.user32.GetAsyncKeyState(VK_SHIFT) & 0x8000
        q = ctypes.windll.user32.GetAsyncKeyState(VK_Q) & 0x8000
        if ctrl and shift and q and state.recording:
            state.record_stop = True
            log1("热键: 停止录制")
        elif ctrl and shift:
            s = ctypes.windll.user32.GetAsyncKeyState(0x53) & 0x8000
            if s: quit1()
    except Exception: pass
    root.after(200, _hotkey_poll)

root.after(200, _hotkey_poll)

root.mainloop()
