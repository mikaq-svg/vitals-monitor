#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Place a shortcut to the Vitals launcher in the user's Desktop\\Tool.

Windows .lnk is a fiddly binary format, so we hand it to pylnk3 rather than
writing the bytes ourselves. Falls back to a plain .cmd launcher if pylnk3
is unavailable, so the user always ends up with something double-clickable.
"""

import os
import sys


def desktop_tool_dir():
    """The Desktop may be redirected into OneDrive; ask Windows first."""
    cands = []
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                            r"Software\Microsoft\Windows\CurrentVersion"
                            r"\Explorer\User Shell Folders") as k:
            v, _ = winreg.QueryValueEx(k, "Desktop")
            cands.append(os.path.expandvars(v))
    except Exception:
        pass
    cands.append(os.path.join(os.path.expanduser("~"), "OneDrive", "Desktop"))
    cands.append(os.path.join(os.path.expanduser("~"), "Desktop"))
    for c in cands:
        if c and os.path.isdir(c):
            return os.path.join(c, "Tool")
    return os.path.join(cands[0], "Tool")


def make_lnk(target, workdir, out, icon=None, desc=""):
    import pylnk3
    lnk = pylnk3.for_file(target)
    lnk.work_dir = workdir
    if desc:
        lnk.description = desc
    if icon:
        parts = icon.rsplit(",", 1)
        lnk.icon = parts[0]
        try:
            lnk.icon_index = int(parts[1])
        except (IndexError, ValueError):
            pass
    lnk.save(out)
    return out


def make_cmd(target, out):
    """Fallback: a tiny .cmd that starts the launcher."""
    body = '@echo off\r\nstart "" wscript.exe "%s"\r\n' % target
    with open(out, "w", encoding="gbk", newline="") as f:
        f.write(body)
    return out


if __name__ == "__main__":
    proj = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else r"D:\工作台")
    desk = sys.argv[2] if len(sys.argv) > 2 else desktop_tool_dir()
    os.makedirs(desk, exist_ok=True)
    target = os.path.join(proj, "start.vbs")
    if not os.path.isfile(target):
        sys.exit("launcher not found: %s" % target)

    out = os.path.join(desk, "Vitals.lnk")
    try:
        make_lnk(target, proj, out,
                 icon=r"C:\Windows\System32\shell32.dll,13",
                 desc="Vitals 本机监测台")
        print("wrote %s (%d bytes)" % (out, os.path.getsize(out)))
    except ImportError:
        out = os.path.join(desk, "Vitals.cmd")
        make_cmd(target, out)
        print("pylnk3 missing; wrote %s instead" % out)

    # prove it parses back
    try:
        import pylnk3
        back = pylnk3.parse(out)
        print("verify target : %s" % back.path)
        print("verify workdir: %s" % back.work_dir)
    except Exception as e:
        print("(verify skipped: %s)" % e)
