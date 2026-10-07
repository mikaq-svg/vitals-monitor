#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_package.py — 生成可分发给同事的干净压缩包

用法：
    python build_package.py

产出：dist/Vitals-<日期>.zip
      含 start.bat / server.py / index.html / README.md
      若本目录存在 runtime\\（便携 Python），一并打包，实现零安装运行。

自动排除：__pycache__ / .workbuddy / dist / install.log / *.pyc
并在打包前做一次语法与一致性自检。
"""

import os
import re
import shutil
import sys
import time
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
DIST = os.path.join(HERE, "dist")
NAME = "Vitals"

CORE = ["start.vbs", "start.bat", "stop.bat", "server.py", "index.html",
        "style-preview.html", "README.md"]
EXCLUDE_DIRS = {"__pycache__", ".workbuddy", "dist", ".git", "venv", ".venv", "shots"}
EXCLUDE_FILES = {"install.log", "build_package.py", "start.sh"}
EXCLUDE_EXT = {".pyc", ".pyo", ".log", ".pdb", ".zip"}
# 开发期的临时件：tools/_check.js、tools/_deco_test.js、无头浏览器的临时 profile……
# 一律以下划线开头，靠这条和 EXCLUDE_DIRS 里的 shots 一起挡在包外。
EXCLUDE_PREFIX = ("_",)
OPTIONAL_DIRS = ["runtime", "lib", "tools"]


def log(msg):
    print("  " + msg)


# WMI 降级脚本段的边界：从 `_PS = (` 到 `def _wmi_blank`。回归 2 只扫这一段。
WMI_SEC_START = "_PS = ("
WMI_SEC_STOP = "def _wmi_blank"


def code_only(src):
    """去掉注释与字符串字面量后的代码骨架。

    自检要判断的是"代码里有没有写错"，而注释和 PowerShell 脚本恰恰会
    合法地包含 `ForEach-Object @{`、`text=True` 这类片段，直接全文匹配会
    误报。做法：挖掉三引号字符串，再逐行去掉 `#` 注释。

    注意：只挖三引号，不碰普通引号 —— 注释里出现 `#` 或引号都无所谓，
    而普通字符串里不含需要检测的片段。
    """
    out = []
    i, n = 0, len(src)
    while i < n:
        c = src[i]
        if c == "#":
            j = src.find("\n", i)
            i = n if j < 0 else j
            continue
        # 三引号字符串（PowerShell 脚本都写在这里）：整体剔除
        if src.startswith('"""', i) or src.startswith("'''", i):
            q = src[i:i + 3]
            j = src.find(q, i + 3)
            i = n if j < 0 else j + 3
            continue
        out.append(c)
        i += 1
    return "".join(out)


def wmi_section(src):
    """取 WMI 降级脚本段（_PS = ( ... def _wmi_blank 之间）的原文。

    这段是普通字符串拼接（不是三引号），所以要从原始源码里切，
    而不是从 code_only() 的骨架里切。
    """
    a = src.find(WMI_SEC_START)
    b = src.find(WMI_SEC_STOP)
    if a < 0 or b < 0 or b < a:
        return ""
    return src[a:b]


def check():
    """自检：语法 + 关键文件 + 是否残留个人痕迹"""
    ok = True
    for f in CORE:
        p = os.path.join(HERE, f)
        if not os.path.exists(p):
            log("[X] 缺少文件: %s" % f)
            ok = False
    # server.py 语法
    srv = os.path.join(HERE, "server.py")
    if os.path.exists(srv):
        src = open(srv, encoding="utf-8").read()
        try:
            compile(src, srv, "exec")
            log("[OK] server.py 语法通过")
        except SyntaxError as e:
            log("[X] server.py 语法错误: %s" % e)
            ok = False
        # 是否写死了本机绝对路径
        bad = re.findall(r"[A-Z]:\\\\?Users\\\\?[^\"'\s]+", src)
        if bad:
            log("[!] server.py 出现本机绝对路径: %s" % bad[:3])
            ok = False
        else:
            log("[OK] server.py 无硬编码用户路径")
        # 回归 1：subprocess 绝不能再带 text=True（GBK 控制台会崩读线程）
        core = code_only(src)
        if re.search(r"subprocess\.run\([^)]*text\s*=\s*True", core, re.S):
            log("[X] server.py 存在 subprocess.run(text=True) —— GBK 控制台会 UnicodeDecodeError")
            ok = False
        else:
            log("[OK] server.py 未使用 text=True 读子进程")
        # 回归 2：WMI 磁盘数组必须带前导逗号，否则 ConvertTo-Json 输出 [null,null]
        # 只扫 WMI 脚本段，避免把别处（或注释里）的同类写法误判
        scan = wmi_section(src)
        if not scan:
            log("[!] 未找到 WMI 脚本段（%s ... %s），请确认" % (WMI_SEC_START, WMI_SEC_STOP))
            ok = False
        elif "ForEach-Object {,@" in scan:
            log("[OK] WMI 磁盘数组使用前导逗号")
        elif "ForEach-Object @{" in scan:
            log("[X] WMI 磁盘收集语句存在 'ForEach-Object @{' —— 会序列化成 [null,null]")
            ok = False
        else:
            log("[!] 未在 WMI 脚本段内找到磁盘收集语句，请确认")
            ok = False
        # 回归 3：降级路径必须返回完整 schema
        if "_wmi_blank" not in src:
            log("[X] server.py 缺少 _wmi_blank 降级兜底")
            ok = False
        else:
            log("[OK] server.py 含 _wmi_blank 降级兜底")
        # 回归 4：单实例锁必须存在，否则重复双击会堆一堆服务
        if "_live_agent_port" not in core:
            log("[X] server.py 缺少 _live_agent_port 单实例锁 —— 重复启动会堆积进程")
            ok = False
        else:
            log("[OK] server.py 含单实例锁")
        # 回归 5：关窗收尾必须用 os._exit（sys.exit 退不掉 daemon 线程）
        if "_shutdown" not in core:
            log("[X] server.py 缺少 _shutdown 收尾逻辑")
            ok = False
        elif "os._exit(0)" not in core:
            log("[X] _shutdown 未使用 os._exit(0) —— sys.exit 退不掉 daemon 线程")
            ok = False
        else:
            log("[OK] 关窗收尾使用 os._exit(0)")
    # index.html 是否残留模拟数据
    idx = os.path.join(HERE, "index.html")
    if os.path.exists(idx):
        h = open(idx, encoding="utf-8").read()
        left = [k for k in ("SH-07", "kanban", "T-1042", "SIMULATED") if k in h]
        log("[%s] index.html 无模拟数据残留" % ("OK" if not left else "!"))
        if left:
            log("      残留: %s" % left)
            ok = False
    # 启动器：.vbs / .bat 必须是 CRLF，且不得写死本机路径
    for name, enc in (("start.vbs", "gbk"), ("stop.bat", "gbk"), ("start.bat", "gbk")):
        p = os.path.join(HERE, name)
        if not os.path.exists(p):
            continue
        raw = open(p, "rb").read()
        txt = raw.decode(enc, "replace")
        hits = re.findall(r"[A-Z]:\\Users\\[^\"\s]+", txt)
        if hits:
            log("[X] %s 含本机路径: %s" % (name, hits[:2]))
            ok = False
        elif raw.count(b"\r\n") == 0:
            log("[!] %s 换行不是 CRLF，Windows 下可能出错" % name)
            ok = False
        else:
            log("[OK] %s 无本机路径 / CRLF 换行" % name)
    return ok


def collect():
    """返回要打包的 (绝对路径, 包内相对路径) 列表"""
    items = []
    for f in CORE:
        p = os.path.join(HERE, f)
        if os.path.exists(p):
            items.append((p, f))
    for d in OPTIONAL_DIRS:
        base = os.path.join(HERE, d)
        if not os.path.isdir(base):
            continue
        n = 0
        for root, dirs, files in os.walk(base):
            dirs[:] = [x for x in dirs
                       if x not in EXCLUDE_DIRS and not x.startswith(EXCLUDE_PREFIX)]
            for fn in files:
                ext = os.path.splitext(fn)[1].lower()
                if fn.startswith(EXCLUDE_PREFIX):
                    continue
                if ext in EXCLUDE_EXT or fn in EXCLUDE_FILES:
                    continue
                full = os.path.join(root, fn)
                rel = os.path.relpath(full, HERE).replace("\\", "/")
                items.append((full, rel))
                n += 1
        log("[OK] 附带 %s\\（%d 个文件）" % (d, n))
    return items


def human(n):
    for u in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return "%.1f %s" % (n, u)
        n /= 1024.0
    return "%.1f TB" % n


def main():
    print("=" * 56)
    print("  Vitals — 打包分发")
    print("=" * 56)
    print("\n[1/3] 自检")
    good = check()

    print("\n[2/3] 收集文件")
    items = collect()
    # 顶层目录名 = 压缩包解压后的文件夹名
    top = "%s-%s" % (NAME, time.strftime("%Y%m%d"))
    if not os.path.isdir(DIST):
        os.makedirs(DIST)
    out = os.path.join(DIST, top + ".zip")

    print("\n[3/3] 写入 %s" % os.path.relpath(out, HERE))
    total = 0
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for full, rel in items:
            z.write(full, top + "/" + rel)
            total += os.path.getsize(full)
            log("%-40s %s" % (rel, human(os.path.getsize(full))))

    zsize = os.path.getsize(out)
    print("\n" + "-" * 56)
    print("  完成：%s" % out)
    print("  原始 %s  →  压缩 %s  （%d 个文件）" %
          (human(total), human(zsize), len(items)))
    has_rt = any(r.startswith("runtime/") for _, r in items)
    if has_rt:
        print("  模式：零安装 —— 同事解压双击 start.bat 即可，无需装 Python")
    else:
        print("  模式：需要 Python —— 同事电脑要有 python.exe（PATH 里）")
        print("        想做成零安装：把便携版 Python 放到 runtime\\ 后重新打包")
    if not good:
        print("\n  [!] 自检有告警，请先看上面的 [X] / [!] 项")
    print("=" * 56)


if __name__ == "__main__":
    main()
