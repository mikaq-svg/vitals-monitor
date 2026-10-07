#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Vitals // local metrics agent

Serves the dashboard (static files in this directory) and exposes REAL host
metrics at /api/stats.  A browser sandbox cannot read hardware counters --
there is no web API for CPU load, memory pressure or NIC throughput -- so
this agent is the only way to get genuine numbers onto the page.

    GET /api/ping   ->  {"ok": true, ...}          (used for auto-discovery)
    GET /api/stats  ->  JSON snapshot of the machine

Design note: on Windows, psutil.process_iter() with status/username costs
~2.3s per pass, so collection runs on a background thread and HTTP handlers
only ever read the cached snapshot. Requests stay O(1).

Requires: psutil  (pip install psutil)
Falls back to PowerShell/WMI when psutil is missing (network rate = null).
"""

import json
import os
import platform
import socket
import subprocess
import sys
import threading
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.abspath(__file__))
PORTS = (8765, 8766, 8767, 8768, 8769)


def _port_open(p, timeout=0.12):
    """True if something is listening on 127.0.0.1:p.

    Cheap pre-filter. On this machine a connect() to a *closed* loopback
    port does not fail fast -- it sits there until the timeout expires.
    So the old code (which went straight to urlopen with a 1.5s timeout)
    burned 5 x 1.5s = 7.5s of dead time on every single launch. A raw
    socket with a 0.12s budget short-circuits that: closed ports answer
    in ~0.12s instead of 1.5s, and an open one succeeds immediately.
    """
    s = socket.socket()
    s.settimeout(timeout)
    try:
        s.connect(("127.0.0.1", p))
        return True
    except Exception:
        return False
    finally:
        try:
            s.close()
        except Exception:
            pass


def _live_agent_port():
    """Return the port of an already-running Vitals agent, or None.

    Why this exists: the launcher is just a double-click, and people click
    it more than once. Every start used to spawn a fresh server, and on
    Windows several processes are allowed to bind the same port, so the
    duplicates silently piled up -- each one hammering WMI in the
    background and making the whole machine sluggish. Before we start
    anything of our own, ask whether a sibling is already alive.

    Two stages: a fast TCP probe weeds out the free ports (the common
    case), and only a port that actually has a listener gets the HTTP
    handshake that confirms *who* is listening. We check /api/ping
    because the port alone cannot tell us whether it is our agent or some
    unrelated program.
    """
    import urllib.request
    for p in PORTS:
        if not _port_open(p):
            continue
        try:
            with urllib.request.urlopen(
                    "http://127.0.0.1:%d/api/ping" % p, timeout=1.0) as r:
                body = json.loads(r.read().decode("utf-8", "replace"))
            if body.get("ok") and body.get("agent") == "vitals":
                return p
        except Exception:
            continue
    return None

# Portable runtimes may live next to this script (runtime\python.exe).
# Their Scripts\ dir holds pip-installed packages, so make them importable
# even when the interpreter was not the one that installed them.
_HERE = os.path.dirname(os.path.abspath(__file__))
for _extra in (os.path.join(_HERE, "runtime", "Lib", "site-packages"),
               os.path.join(_HERE, "runtime", "Scripts"),
               os.path.join(_HERE, "venv", "Lib", "site-packages"),
               os.path.join(_HERE, "lib")):
    if os.path.isdir(_extra) and _extra not in sys.path:
        sys.path.insert(0, _extra)

FAST_EVERY = 2.0     # cpu / mem / disk / net
PROC_EVERY = 5.0     # process table (expensive on Windows)
HARD_EVERY = 3600.0  # static hardware inventory (usb plug/unplug rescans)
GPU_EVERY = 3.0      # nvidia-smi
TEMP_EVERY = 3.0     # LibreHardwareMonitor (optional, may be absent)

# Dashboard liveness watchdog. The page polls /api/stats every ~2s, so a
# lack of requests is how we know the window was closed. Warm-up covers the
# launch itself; the idle window is comfortable enough that a brief stall
# (a slow hardware probe, a sleeping laptop) cannot kill a live dashboard.
WATCH_WARMUP = 15.0  # give the window time to open and paint
WATCH_IDLE = 45.0    # no page request for this long -> window is gone
WATCH_TICK = 3.0     # how often to check

# LibreHardwareMonitor is a separate portable app shipped in tools\. Windows
# exposes no public API for CPU package temperature, so the dashboard reads
# LHM's own local web server instead. Not installed / not running is a normal
# state, never an error: we simply report null and the UI shows "--".
LHM_URL = "http://127.0.0.1:8085/data.json"

try:
    import psutil
    HAVE_PSUTIL = True
except Exception:
    psutil = None
    HAVE_PSUTIL = False


# --------------------------------------------------------------------------
# state
# --------------------------------------------------------------------------
_lock = threading.Lock()
_rate = {"net_rx": 0.0, "net_tx": 0.0, "disk_r": 0.0, "disk_w": 0.0,
         "disk_rc": 0.0, "disk_wc": 0.0}
_snap = {"data": None}
_hw = {"static": None, "live": None}
_hw_busy = threading.Event()   # guards the slow (30-60s) hardware probe
_temp = {"v": None}            # last successful LHM reading (None = unavailable)
_last_hit = time.time()        # last time a page was actually served (watchdog)


# --------------------------------------------------------------------------
# collectors
# --------------------------------------------------------------------------
_pcache = {}
PROC_ATTRS = ["pid", "name", "memory_info"]


def _proc_rows():
    """cpu_percent() is delta based: the first sighting of a pid only primes
    the counter, real values show up on the next pass."""
    rows, alive = [], set()
    for proc in psutil.process_iter(PROC_ATTRS):
        pid = proc.pid
        # pid 0 is Windows' System Idle Process: its "cpu" is idle time, not load
        if pid == 0:
            continue
        alive.add(pid)
        info = proc.info
        cached = _pcache.get(pid)
        if cached is None:
            _pcache[pid] = proc
            try:
                proc.cpu_percent(None)
            except Exception:
                pass
            cpu = 0.0
        else:
            try:
                cpu = cached.cpu_percent(None)
            except Exception:
                cpu = 0.0
        mi = info.get("memory_info")
        rows.append({"pid": pid, "name": info.get("name") or "?",
                     "cpu": round(cpu, 1), "mem": mi.rss if mi else 0})
    for dead in [p for p in _pcache if p not in alive]:
        _pcache.pop(dead, None)
    return rows


def _procs(n_cpu=40, n_mem=20):
    rows = _proc_rows()
    return {"cpu": sorted(rows, key=lambda r: (-r["cpu"], -r["mem"]))[:n_cpu],
            "mem": sorted(rows, key=lambda r: (-r["mem"], -r["cpu"]))[:n_mem]}


def _disks():
    out, seen = [], set()
    for part in psutil.disk_partitions(all=False):
        if part.device in seen:
            continue
        seen.add(part.device)
        try:
            u = psutil.disk_usage(part.mountpoint)
        except Exception:
            continue
        out.append({"device": part.device, "mount": part.mountpoint,
                    "fstype": part.fstype, "total": u.total, "used": u.used,
                    "free": u.free, "pct": u.percent})
    out.sort(key=lambda d: -d["total"])
    return out


def _ifaces():
    out = []
    try:
        per = psutil.net_io_counters(pernic=True)
    except Exception:
        per = {}
    addrs = {}
    try:
        for name, lst in psutil.net_if_addrs().items():
            for a in lst:
                if a.family == socket.AF_INET:
                    addrs.setdefault(name, a.address)
    except Exception:
        pass
    stats = {}
    try:
        stats = psutil.net_if_stats()
    except Exception:
        pass
    for name, c in per.items():
        st = stats.get(name)
        out.append({"name": name, "ip": addrs.get(name, ""),
                    "up": bool(st.isup) if st else True,
                    "speed": (st.speed if st else 0) or 0,
                    "rx": c.bytes_recv, "tx": c.bytes_sent,
                    "errin": c.errin, "errout": c.errout})
    out.sort(key=lambda i: -(i["rx"] + i["tx"]))
    return out


def _psutil_fast():
    cpu_total = psutil.cpu_percent(interval=None)
    per_core = psutil.cpu_percent(interval=None, percpu=True)
    try:
        freq = psutil.cpu_freq()
        freq_mhz = round(freq.current, 0) if freq else None
    except Exception:
        freq_mhz = None
    vm = psutil.virtual_memory()
    try:
        sw = psutil.swap_memory()
        swap = {"total": sw.total, "used": sw.used, "pct": sw.percent}
    except Exception:
        swap = None
    try:
        pcount = len(psutil.pids())
    except Exception:
        pcount = 0
    try:
        conns = len(psutil.net_connections(kind="tcp"))
    except Exception:
        conns = -1
    batt = None
    try:
        b = psutil.sensors_battery()
        if b:
            batt = {"pct": b.percent, "plugged": bool(b.power_plugged)}
    except Exception:
        pass
    with _lock:
        rate = dict(_rate)
    return {
        "source": "psutil",
        "host": {
            "name": socket.gethostname(),
            "os": platform.system() + " " + platform.release(),
            "version": platform.version(),
            "arch": platform.machine(),
            "cores": psutil.cpu_count(logical=False) or 0,
            "logical": psutil.cpu_count(logical=True) or 0,
            "boot": psutil.boot_time(),
            "uptime": time.time() - psutil.boot_time(),
            "python": platform.python_version(),
        },
        "cpu": {"total": cpu_total, "per_core": per_core, "freq_mhz": freq_mhz},
        "mem": {"total": vm.total, "used": vm.used, "avail": vm.available,
                "pct": vm.percent, "swap": swap},
        "disk": {"mounts": _disks(), "r_bps": rate["disk_r"], "w_bps": rate["disk_w"],
                 "r_iops": rate["disk_rc"], "w_iops": rate["disk_wc"]},
        "net": {"rx_bps": rate["net_rx"], "tx_bps": rate["net_tx"],
                "ifaces": _ifaces(), "conns": conns},
        "procs": {"total": pcount, "cpu": [], "mem": []},
        "battery": batt,
        "gpu": None,
    }


# ---------- fallback: no psutil, ask Windows through PowerShell ----------
_PS = (
    "$o=Get-CimInstance Win32_OperatingSystem;"
    "$c=Get-CimInstance Win32_ComputerSystem;"
    "$p=Get-CimInstance Win32_Processor;"
    "$d=Get-CimInstance Win32_LogicalDisk -Filter 'DriveType=3';"
    "ConvertTo-Json -Compress -Depth 4 @{"
    "os=$o.Caption; ver=$o.Version; total=[double]$o.TotalVisibleMemorySize*1024;"
    "free=[double]$o.FreePhysicalMemory*1024; cores=$c.NumberOfLogicalProcessors;"
    "load=@($p | ForEach-Object {$_.LoadPercentage});"
    # The leading comma is REQUIRED: '$d | ForEach-Object @{...}' makes
    # ConvertTo-Json emit [null,null] (hashtables get unrolled away).
    "disks=@($d | ForEach-Object {,@{dev=$_.DeviceID;size=[double]$_.Size;free=[double]$_.FreeSpace}});"
    "procs=(Get-Process).Count}"
)


def _wmi_blank(reason=""):
    """Full-schema WMI fallback so no consumer ever hits a missing key.

    Used both when the probe itself errors and when the machine has no
    psutil; the dashboard renders it as an honest zero/-- state, not as
    fabricated activity.
    """
    cores = os.cpu_count() or 1
    return {
        "source": "wmi", "degraded": True, "reason": reason,
        "host": {"name": socket.gethostname(), "os": platform.system(),
                 "version": platform.release(), "arch": platform.machine(),
                 "cores": cores, "logical": cores, "boot": 0, "uptime": 0,
                 "python": platform.python_version()},
        "cpu": {"total": 0.0, "per_core": [0.0] * cores, "freq_mhz": None},
        "mem": {"total": 0, "used": 0, "avail": 0, "pct": 0.0, "swap": None},
        "disk": {"mounts": [], "r_bps": None, "w_bps": None,
                 "r_iops": None, "w_iops": None},
        "net": {"rx_bps": None, "tx_bps": None, "ifaces": [], "conns": -1},
        "procs": {"total": 0, "cpu": [], "mem": []},
        "battery": None,
        "gpu": None,
    }


def _wmi_stats():
    # NOTE: do NOT pass text=True here. On a GBK console Python's internal
    # reader thread decodes with the locale codec and dies with
    # UnicodeDecodeError before our own tolerant decode can run.
    try:
        raw = subprocess.run(["powershell", "-NoProfile", "-NonInteractive",
                              "-Command", _PS],
                             capture_output=True, timeout=25)
        out = (raw.stdout or b"")
        for enc in ("utf-8", "gbk"):
            try:
                txt = out.decode(enc)
                break
            except UnicodeDecodeError:
                continue
        else:
            txt = out.decode("utf-8", "replace")
        d = json.loads(txt.strip())
    except Exception as e:
        return _wmi_blank("wmi failed: %r" % (e,))
    total = d.get("total") or 1
    free = d.get("free") or 0
    used = total - free
    # Win32_Processor.LoadPercentage can be null (VM guests, WMI hiccups,
    # brief sampling gaps). Coerce to 0 instead of letting float(None)
    # raise TypeError, which previously killed the collector thread.
    raw_loads = d.get("load") or [0]
    raw_loads = raw_loads if isinstance(raw_loads, list) else [raw_loads]
    loads = []
    for v in raw_loads:
        try:
            loads.append(float(v))
        except (TypeError, ValueError):
            continue
    if not loads:
        loads = [0.0]
    cores = int(d.get("cores") or 1)
    per = []
    for v in loads:
        per += [v] * max(1, cores // len(loads))
    while len(per) < cores:
        per.append(loads[0])
    per = per[:cores]
    mounts = []
    for dd in (d.get("disks") or []):
        if isinstance(dd, dict):
            size = dd.get("size") or 0
            fr = dd.get("free") or 0
            mounts.append({"device": dd.get("dev", "?"), "mount": dd.get("dev", "?"),
                           "fstype": "", "total": size, "used": size - fr, "free": fr,
                           "pct": round((size - fr) / size * 100, 1) if size else 0})
    return {
        "source": "wmi",
        "host": {"name": socket.gethostname(), "os": d.get("os", platform.system()),
                 "version": d.get("ver", ""), "arch": platform.machine(),
                 "cores": cores, "logical": cores, "boot": 0, "uptime": 0,
                 "python": platform.python_version()},
        "cpu": {"total": loads[0], "per_core": per, "freq_mhz": None},
        "mem": {"total": total, "used": used, "avail": free,
                "pct": round(used / total * 100, 1), "swap": None},
        "disk": {"mounts": mounts, "r_bps": None, "w_bps": None,
                 "r_iops": None, "w_iops": None},
        "net": {"rx_bps": None, "tx_bps": None, "ifaces": [], "conns": -1},
        "procs": {"total": d.get("procs") or 0, "cpu": [], "mem": []},
        "battery": None,
    }


def _collect_fast():
    d = _psutil_fast() if HAVE_PSUTIL else _wmi_stats()
    d["ok"] = "error" not in d
    d["ts"] = time.time()
    return d


def _collect_full():
    d = _collect_fast()
    # Never assume "procs" is present: the WMI fallback and the error path
    # both legitimately omit it, and a bare d["procs"] would crash the
    # collector thread (observed as KeyError on machines without psutil).
    prev = d.get("procs") or {}
    merged = {"total": prev.get("total", 0), "cpu": [], "mem": []}
    if HAVE_PSUTIL:
        try:
            merged.update(_procs())
        except Exception:
            pass
    d["procs"] = merged
    d["ts"] = time.time()
    return d


# --------------------------------------------------------------------------
# hardware inventory (Windows / PowerShell)
#
# Everything below shells out once and caches. The static sections change
# only when hardware is physically attached or detached; the $live block is
# what actually moves (battery, volumes, network links, USB presence).
# --------------------------------------------------------------------------
PS_PRE = "$OutputEncoding=[Console]::OutputEncoding=[Text.Encoding]::UTF8;"

PS_HW_STATIC = PS_PRE + r"""
$ErrorActionPreference='SilentlyContinue'
$o=[ordered]@{}
$g=Get-CimInstance Win32_VideoController | Select-Object -First 1
$o.gpu=@(Get-CimInstance Win32_VideoController | ForEach-Object {
  [ordered]@{name=$_.Name; drv=$_.DriverVersion; vram=[double]$_.AdapterRAM;
             w=$_.CurrentHorizontalResolution; h=$_.CurrentVerticalResolution;
             hz=$_.CurrentRefreshRate; status=$_.Status}})
$cs=Get-CimInstance Win32_ComputerSystem
$o.model=[ordered]@{mfr=$cs.Manufacturer; model=$cs.Model; family=$cs.SystemFamily;
                    sku=$cs.SystemSKUNumber; type=$cs.PCSystemType}
$b=Get-CimInstance Win32_BIOS
$o.bios=[ordered]@{mfr=$b.Manufacturer; name=$b.Name; ver=$b.SMBIOSBIOSVersion;
                   date=$b.ReleaseDate}
$bb=Get-CimInstance Win32_BaseBoard
$o.board=[ordered]@{mfr=$bb.Manufacturer; product=$bb.Product; ver=$bb.Version}
$p=Get-CimInstance Win32_Processor | Select-Object -First 1
$o.cpu=[ordered]@{name=$p.Name; cores=$p.NumberOfCores; threads=$p.NumberOfLogicalProcessors;
                  max=$p.MaxClockSpeed; socket=$p.SocketDesignation;
                  l3=[double]$p.L3CacheSize; l2=[double]$p.L2CacheSize}
$o.audio=@(Get-CimInstance Win32_SoundDevice | ForEach-Object {
  [ordered]@{name=$_.Name; mfr=$_.Manufacturer; status=$_.Status}})
$o.disk=@(Get-CimInstance Win32_DiskDrive | ForEach-Object {
  [ordered]@{model=$_.Model; iface=$_.InterfaceType; size=[double]$_.Size;
             media=$_.MediaType; fw=$_.FirmwareRevision}})
$o.monitor=@(Get-CimInstance WmiMonitorID -Namespace root\wmi | ForEach-Object {
  [ordered]@{code=($_.UserFriendlyName | Where-Object {$_ -gt 0} | ForEach-Object {[char]$_}) -join '';
             mfr=($_.ManufacturerName | Where-Object {$_ -gt 0} | ForEach-Object {[char]$_}) -join '';
             sn=($_.SerialNumberID | Where-Object {$_ -gt 0} | ForEach-Object {[char]$_}) -join '';
             year=$_.YearOfManufacture}})
$o.printers=@(Get-Printer | ForEach-Object {
  [ordered]@{name=$_.Name; drv=$_.DriverName; port=$_.PortName}})
$o.vol=@(Get-Volume | Where-Object { $_.DriveLetter } | ForEach-Object {
  [ordered]@{letter=$_.DriveLetter; label=$_.FileSystemLabel; fs=$_.FileSystem;
             size=[double]$_.Size; free=[double]$_.SizeRemaining}})
$o.net=@(Get-NetAdapter | ForEach-Object {
  [ordered]@{name=$_.Name; desc=$_.InterfaceDescription; mac=$_.MacAddress;
             speed=[double]$_.LinkSpeed; st=[string]$_.Status;
             media=[string]$_.MediaType}})
$o.netcim=@(Get-CimInstance Win32_NetworkAdapter -Filter 'PhysicalAdapter=True' |
  ForEach-Object {[ordered]@{name=$_.Name; desc=$_.ProductName; mac=$_.MACAddress;
    speed=[double]$_.Speed; net=[bool]$_.NetEnabled}})
$o.usb=@(Get-PnpDevice -Status OK -Class USB,Mouse,Keyboard,HIDClass,Bluetooth,Camera,
         AudioEndpoint,Image,Printer,Monitor,Media,SmartCard,Biometric |
  ForEach-Object {[ordered]@{name=$_.FriendlyName; cls=$_.Class; inst=$_.InstanceId}})
$o.pnp=@(Get-PnpDevice -Status OK | ForEach-Object {
  [ordered]@{name=$_.FriendlyName; cls=$_.Class}})
ConvertTo-Json -Compress -Depth 6 $o
"""

PS_HW_LIVE = PS_PRE + r"""
$ErrorActionPreference='SilentlyContinue'
$o=[ordered]@{}
$bat=Get-CimInstance Win32_Battery | Select-Object -First 1
if($bat){$o.battery=[ordered]@{name=$bat.Name; status=[int]$bat.BatteryStatus;
  pct=[double]$bat.EstimatedChargeRemaining;
  remain=[int]$bat.EstimatedRunTime}}
$o.vol=@(Get-Volume | Where-Object { $_.DriveLetter } | ForEach-Object {
  [ordered]@{letter=$_.DriveLetter; free=[double]$_.SizeRemaining}})
$o.net=@(Get-NetAdapter | ForEach-Object {
  [ordered]@{name=$_.Name; st=[string]$_.Status; speed=[double]$_.LinkSpeed}})
$o.usb=@(Get-PnpDevice -Status OK -Class USB,Mouse,Keyboard,HIDClass,Bluetooth,
         Camera,AudioEndpoint,Monitor | ForEach-Object {
  [ordered]@{name=$_.FriendlyName; cls=$_.Class}})
ConvertTo-Json -Compress -Depth 5 $o
"""


def _ps_run(script, timeout=180):
    """Run PowerShell, decoding output as UTF-8 (Console set to UTF-8)."""
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive",
                            "-Command", script],
                           capture_output=True, timeout=timeout)
    except Exception as e:
        return None, "spawn failed: %r" % (e,)
    raw = r.stdout or b""
    if not raw.strip():
        err = (r.stderr or b"").decode("gbk", "replace")[:400]
        return None, "empty stdout. %s" % err
    for enc in ("utf-8", "gbk"):
        try:
            txt = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        txt = raw.decode("utf-8", "replace")
    try:
        return json.loads(txt.strip()), None
    except Exception as e:
        return None, "json: %r" % (e,)


def _nvidia():
    """Live GPU utilisation. nvidia-smi ships with the driver."""
    fields = ("name,utilization.gpu,memory.used,memory.total,"
              "temperature.gpu,power.draw,power.limit,clocks.current.graphics")
    try:
        r = subprocess.run(["nvidia-smi", "--query-gpu=" + fields,
                            "--format=csv,noheader,nounits"],
                           capture_output=True, timeout=15)
        line = (r.stdout or b"").decode("utf-8", "replace").strip().split("\n")[0]
        if not line:
            return None
        v = [x.strip() for x in line.split(",")]

        def num(s):
            try:
                return float(s)
            except Exception:
                return None
        return {"name": v[0], "util": num(v[1]), "mem_used": (num(v[2]) or 0) * 2**20,
                "mem_total": (num(v[3]) or 0) * 2**20, "temp": num(v[4]),
                "power": num(v[5]), "power_limit": num(v[6]), "clock": num(v[7])}
    except Exception:
        return None


# device classes worth surfacing as "attached devices", in display order
DEV_CLASSES = [
    ("Mouse", "鼠标"), ("Keyboard", "键盘"), ("Touchpad", "触摸板"),
    ("HIDClass", "人机接口"), ("Bluetooth", "蓝牙"), ("USB", "USB"),
    ("Camera", "摄像头"), ("Image", "影像"), ("AudioEndpoint", "音频端点"),
    ("Media", "音频设备"), ("Monitor", "显示器"), ("Printer", "打印机"),
    ("SmartCard", "智能卡"), ("Biometric", "生物识别"),
]


def _lhm_walk(node, hw_name, hw_id, grp, out):
    """Flatten one LHM hardware node into {"group/sensor": value}.

    LHM returns a nested tree: hardware -> sensor group -> sensor leaf.
    The group name matters: "GPU Core" exists both as a temperature and as a
    load percentage, so a bare sensor name would collide. We keep the path.
    hw_id is the device's HardwareId (e.g. /intelcpu/0) — far more reliable
    for classifying a device than its display name, which is localised.
    """
    kids = node.get("Children") or []
    if node.get("SensorId"):                  # a leaf: an actual reading
        txt = node.get("Text") or ""
        if txt:
            out.setdefault(hw_id or hw_name,
                           {})["%s/%s" % (grp, txt)] = _lhm_parse(node.get("Value"))
        return
    for c in kids:
        name = (c.get("Text") or "").strip()
        if c.get("HardwareId"):               # child is itself a device
            _lhm_walk(c, name or hw_name, c["HardwareId"], "", out)
        elif c.get("Children"):               # child is a sensor group
            _lhm_walk(c, hw_name, hw_id, name or grp, out)
        else:                                 # sensor leaf directly under grp
            _lhm_walk(c, hw_name, hw_id, grp, out)


def _lhm_parse(raw):
    """'81.0 °C' -> 81.0 ; '34.9 %' -> 34.9 ; 'NaN %' -> None"""
    if not isinstance(raw, str):
        return None
    tok = raw.strip().split(" ")[0].replace(",", ".")
    try:
        v = float(tok)
    except ValueError:
        return None
    # LHM prints NaN / Infinity for sensors that are present but not answering
    if v != v or v in (float("inf"), float("-inf")):
        return None
    return v


def _lhm_temps():
    """Read CPU / GPU / DIMM temperatures from LibreHardwareMonitor.

    Returns a dict, or None when LHM is not running. The dashboard treats
    None as "this machine has no temperature source" and shows "--" rather
    than inventing a number.
    """
    import urllib.request
    try:
        with urllib.request.urlopen(LHM_URL, timeout=4) as r:
            tree = json.loads(r.read().decode("utf-8", "replace"))
    except Exception:
        return None

    flat = {}
    _lhm_walk(tree, "", "", "", flat)

    cpu_c = gpu_c = dimm = cpu_pkg_w = None
    cpu_max = cpu_avg = None
    gpu_hot = gpu_mem_j = None
    cpu_name = None
    for hw_id, sensors in flat.items():
        # classify by HardwareId — stable across languages, unlike the name
        is_cpu = hw_id.startswith("/intelcpu") or hw_id.startswith("/amdcpu")
        is_gpu = hw_id.startswith("/gpu-nvidia") or hw_id.startswith("/gpu-amd")
        is_dimm = hw_id.startswith("/memory/dimm")
        t = {k.split("/", 1)[-1]: v for k, v in sensors.items()
             if k.startswith("Temperatures/")}
        if is_cpu:
            cpu_name = cpu_name or _lhm_name(tree, hw_id)
            cpu_c = t.get("CPU Package") if cpu_c is None else cpu_c
            cpu_max = t.get("Core Max")
            cpu_avg = t.get("Core Average")
            if cpu_c is None:
                cpu_c = cpu_max
            p = {k.split("/", 1)[-1]: v for k, v in sensors.items()
                 if k.startswith("Powers/")}
            cpu_pkg_w = p.get("CPU Package")
        elif is_gpu:
            gpu_c = t.get("GPU Core")
            gpu_hot = t.get("GPU Hot Spot")
            gpu_mem_j = t.get("GPU Memory Junction")
        elif is_dimm:
            for k, v in t.items():
                if k.startswith("DIMM") and v is not None:
                    dimm = v if dimm is None else max(dimm, v)

    if cpu_c is None and cpu_max is None and gpu_c is None and dimm is None:
        return None
    return {
        "cpu": cpu_c, "cpu_max": cpu_max, "cpu_avg": cpu_avg,
        "cpu_w": cpu_pkg_w, "cpu_name": cpu_name,
        "gpu": gpu_c, "gpu_hot": gpu_hot, "gpu_mem": gpu_mem_j,
        "dimm": dimm,
    }


def _lhm_name(tree, hw_id):
    """Display name of the hardware node whose HardwareId matches."""
    found = [None]

    def seek(n):
        if found[0] is not None:
            return
        if n.get("HardwareId") == hw_id:
            found[0] = (n.get("Text") or "").strip() or None
            return
        for c in (n.get("Children") or []):
            seek(c)
    seek(tree)
    return found[0]


def _collect_hardware():
    d, err = _ps_run(PS_HW_STATIC, timeout=240)
    if err or not d:
        return {"ok": False, "error": err or "no data"}
    d["ok"] = True
    d["ts"] = time.time()
    return d


def _collect_hw_live():
    d, err = _ps_run(PS_HW_LIVE, timeout=90)
    if err or not d:
        return {"ok": False, "error": err or "no data"}
    d["ok"] = True
    d["ts"] = time.time()
    return d


def _tick_rate():
    """update byte/io counters delta (called ~1/s)"""
    if not HAVE_PSUTIL:
        return
    prev = getattr(_tick_rate, "prev", None)
    try:
        cur_n = psutil.net_io_counters()
        cur_d = psutil.disk_io_counters()
    except Exception:
        return
    now = time.time()
    if prev is not None:
        pn, pdv, pt = prev
        dt = max(now - pt, 1e-3)
        with _lock:
            _rate["net_rx"] = (cur_n.bytes_recv - pn.bytes_recv) / dt
            _rate["net_tx"] = (cur_n.bytes_sent - pn.bytes_sent) / dt
            if cur_d is not None and pdv is not None:
                _rate["disk_r"] = (cur_d.read_bytes - pdv.read_bytes) / dt
                _rate["disk_w"] = (cur_d.write_bytes - pdv.write_bytes) / dt
                _rate["disk_rc"] = (cur_d.read_count - pdv.read_count) / dt
                _rate["disk_wc"] = (cur_d.write_count - pdv.write_count) / dt
    _tick_rate.prev = (cur_n, cur_d, now)


def collector():
    """background loop: keeps _snap['data'] fresh so requests stay instant"""
    last_fast = last_proc = last_rate = last_hw = last_hwl = last_gpu = 0.0
    last_temp = 0.0
    base = {}
    while True:
        time.sleep(0.4)
        now = time.time()
        if now - last_temp >= TEMP_EVERY:
            try:
                t = _lhm_temps()
                with _lock:
                    _temp["v"] = t          # None is a valid answer (= no LHM)
            except Exception:
                pass
            last_temp = now
        if now - last_rate >= 1.0:
            try:
                _tick_rate()
            except Exception:
                pass
            last_rate = now
        if now - last_gpu >= GPU_EVERY:
            try:
                g = _nvidia()
                if g is not None and base:
                    base["gpu"] = g
                    with _lock:
                        _snap["data"] = dict(base)
            except Exception:
                pass
            last_gpu = now
        if now - last_fast >= FAST_EVERY or not base:
            try:
                fresh = _collect_fast()
                with _lock:
                    prev = _snap["data"]
                # never blank the process table while a slow proc pass is out
                if prev is not None and prev.get("procs", {}).get("cpu"):
                    fresh["procs"] = prev["procs"]
                if prev is not None and prev.get("gpu"):
                    fresh["gpu"] = prev["gpu"]
                base = fresh
                with _lock:
                    _snap["data"] = dict(base)
            except Exception as e:
                sys.stderr.write("[agent] fast collect failed: %r\n" % (e,))
            last_fast = now
        if now - last_proc >= PROC_EVERY and HAVE_PSUTIL and base:
            try:
                base["procs"] = {"total": len(psutil.pids())}
                base["procs"].update(_procs())
                base["ts"] = time.time()
                with _lock:
                    _snap["data"] = dict(base)
            except Exception as e:
                sys.stderr.write("[agent] proc collect failed: %r\n" % (e,))
            last_proc = now
        if (now - last_hw >= HARD_EVERY or not _hw["static"]) and not _hw_busy.is_set():
            _hw_busy.set()
            try:
                hw = _collect_hardware()
                if hw.get("ok"):
                    with _lock:
                        _hw["static"] = hw
                    sys.stderr.write("[agent] hardware inventory refreshed\n")
            except Exception as e:
                sys.stderr.write("[agent] hw collect failed: %r\n" % (e,))
            finally:
                _hw_busy.clear()
            last_hw = now
        if now - last_hwl >= 10.0 or not _hw["live"]:
            try:
                hwl = _collect_hw_live()
                if hwl.get("ok"):
                    with _lock:
                        _hw["live"] = hwl
            except Exception as e:
                sys.stderr.write("[agent] hw live failed: %r\n" % (e,))
            last_hwl = now


def get_stats():
    with _lock:
        d = _snap["data"]
        hw = dict(_hw["static"] or {})
        hwl = dict(_hw["live"] or {})
        tmp = _temp["v"]
    if d is None:                      # cold start: block once
        d = _collect_full()
        with _lock:
            _snap["data"] = d
    d["hw"] = hw
    d["hw_live"] = hwl
    # temperatures come from LibreHardwareMonitor; None means "no source
    # installed", which the page renders as "--" rather than a fake number
    d["temp"] = tmp
    # prefer the fresher battery reading: psutil is instant, PowerShell has SOC
    if hwl.get("battery") and hwl["battery"].get("pct") is not None:
        d["battery"] = {"pct": hwl["battery"]["pct"],
                        "plugged": hwl["battery"]["status"] in (2, 6, 7, 8, 9),
                        "remain_min": hwl["battery"].get("remain"),
                        "name": hwl["battery"].get("name")}
    return d


def get_hardware():
    with _lock:
        st = dict(_hw["static"] or {})
        lv = dict(_hw["live"] or {})
    if not st:
        st = _collect_hardware()
        with _lock:
            _hw["static"] = st
    if not lv:
        lv = _collect_hw_live()
        with _lock:
            _hw["live"] = lv
    out = dict(st)
    out["hw_live"] = lv
    return out


# --------------------------------------------------------------------------
# http
# --------------------------------------------------------------------------
class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=ROOT, **kw)

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        super().end_headers()

    def _json(self, obj):
        body = json.dumps(obj, default=str).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        try:
            self.wfile.write(body)
        except Exception:
            pass

    def _page_seen(self):
        """Record that a real dashboard page is alive.

        CRITICAL: this must NOT be called for /api/ping. The single-instance
        probe uses ping, so counting it would mean a second launch keeps the
        first agent's watchdog happy forever -- the agent would never exit,
        would hold the port, and the next launch would find "already
        running" and never open a window. That was the bug.
        """
        global _last_hit
        _last_hit = time.time()

    def do_GET(self):
        path = self.path.split("?", 1)[0].rstrip("/")
        if path in ("/api/stats", "/api/stats/"):
            self._page_seen()
            return self._json(get_stats())
        if path in ("/api/hardware", "/api/hardware/"):
            self._page_seen()
            return self._json(get_hardware())
        if path in ("/api/bye", "/api/bye/"):
            # The page said goodbye (window/tab closing). Shut down at once.
            self._json({"ok": True})
            threading.Thread(target=_shutdown, daemon=True).start()
            return
        if path in ("/api/ping", "/api/ping/"):
            # Deliberately does NOT touch _last_hit -- see _page_seen.
            return self._json({"ok": True, "agent": "vitals",
                               "psutil": HAVE_PSUTIL, "ts": time.time()})
        # Serving the html/js itself also counts as "a page is alive".
        if path.endswith(".html") or path in ("", "/index"):
            self._page_seen()
        return super().do_GET()

    def do_HEAD(self):
        if self.path.split("?", 1)[0].startswith("/api/"):
            return self._json({})
        return super().do_HEAD()

    def _json(self, obj):
        body = json.dumps(obj, default=str).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        try:
            self.wfile.write(body)
        except Exception:
            pass

    def log_message(self, fmt, *args):
        pass


def _stop_lhm():
    """Stop the bundled LibreHardwareMonitor, if we can.

    LHM runs elevated (it needs administrator rights to read the sensors),
    so an ordinary terminate is refused -- we try anyway, and failing is
    harmless: worst case the tray icon lingers, which is exactly today's
    behaviour.
    """
    if not HAVE_PSUTIL:
        return
    try:
        for proc in psutil.process_iter(["pid", "name"]):
            if (proc.info.get("name") or "").lower().startswith("librehardware"):
                try:
                    proc.terminate()
                except Exception:
                    pass
    except Exception:
        pass


def _shutdown(*_a):
    """Tidy up and exit: stop LHM, then hard-exit the process.

    Called when the dashboard window is closed. sys.exit() only unwinds the
    calling thread, and we are on a worker thread, so os._exit() is used to
    make sure the daemon collector threads cannot keep the process alive.
    """
    print("\n[agent] dashboard closed -- shutting down")
    _stop_lhm()
    try:
        sys.stdout.flush()
    except Exception:
        pass
    os._exit(0)


def _open_window(url, on_close=None):
    """Open the dashboard in a chromeless app window when possible.

    Edge/Chrome ship an "app mode" that drops the address bar, tabs and
    bookmarks — the result looks like a native desktop app rather than a
    browser page. If neither is installed we fall back to the default
    browser, which still works, just with normal browser chrome.

    If on_close is given it runs once the window we launched goes away,
    which is how the agent notices the user closed the dashboard and can
    shut itself (and LHM) down instead of lingering.
    """
    def _go():
        time.sleep(0.8)                      # let serve_forever come up first
        cmds = [
            # Edge app mode
            [os.path.join(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
                          r"Microsoft\Edge\Application\msedge.exe")],
            [os.path.join(os.environ.get("ProgramFiles", r"C:\Program Files"),
                          r"Microsoft\Edge\Application\msedge.exe")],
            # Chrome app mode
            [os.path.join(os.environ.get("ProgramFiles", r"C:\Program Files"),
                          r"Google\Chrome\Application\chrome.exe")],
            [os.path.join(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
                          r"Google\Chrome\Application\chrome.exe")],
        ]
        for (exe,) in cmds:
            if os.path.isfile(exe):
                try:
                    proc = subprocess.Popen(
                        [exe, "--app=" + url,
                         "--window-size=1360,900",
                         "--user-data-dir=" + os.path.join(ROOT, ".browser")],
                        close_fds=True)
                    _watch_window(proc, on_close)
                    return
                except Exception:
                    continue
        # No Edge/Chrome: fall back to the default browser, which we cannot
        # track, so the watchdog stays off and the agent keeps running.
        try:
            import webbrowser
            webbrowser.open(url)
        except Exception:
            pass

    threading.Thread(target=_go, daemon=True).start()


def _watch_window(proc, on_close):
    """Shut down once the dashboard stops talking to us.

    This is deliberately heartbeat-based rather than process-based. The pid
    we spawn is unreliable: app-mode browsers hand the window off to an
    already-running process, so our pid can die immediately (window still
    open) or survive long after the window closed. What we CAN trust is
    whether a page is still asking us for data.

    The dashboard polls /api/stats every couple of seconds, and *only* a
    real page does that -- /api/ping does not count (see _page_seen). So
    "no stats request for N seconds" is an accurate "the window is gone".

    A short warm-up covers the launch itself, before the page has painted.
    """
    def _w():
        time.sleep(WATCH_WARMUP)     # launch + cold first paint
        while True:
            time.sleep(WATCH_TICK)
            silent = time.time() - _last_hit
            if silent >= WATCH_IDLE:
                if on_close is not None:
                    try:
                        on_close()
                    except Exception:
                        pass
                return

    threading.Thread(target=_w, daemon=True).start()


def main():
    # --- single instance -------------------------------------------------
    # The launcher is a double-click, and people click it more than once.
    # Without this guard every start spawned another server, and Windows
    # happily let them all bind the same port, so the machine ended up
    # running three or four collectors at once and felt sluggish. If a
    # sibling is already alive, just surface its window and exit.
    existing = _live_agent_port()
    if existing is not None:
        url = "http://127.0.0.1:%d/index.html" % existing
        print("=" * 54)
        print("  Vitals AGENT  (already running)")
        print("  url     : %s" % url)
        print("  reusing the running instance instead of starting another")
        print("=" * 54)
        if "--no-browser" not in sys.argv:
            _open_window(url, None)     # no watchdog: we do not own that window
        return

    if HAVE_PSUTIL:
        psutil.cpu_percent(interval=None)               # prime delta counters
        psutil.cpu_percent(interval=None, percpu=True)
        _tick_rate()

    srv, port = None, None
    for p in PORTS:
        try:
            srv = ThreadingHTTPServer(("127.0.0.1", p), Handler)
            port = p
            break
        except OSError:
            continue
    if srv is None:
        sys.stderr.write("no free port among %s\n" % (PORTS,))
        sys.exit(1)
    srv.daemon_threads = True

    # Start serving BEFORE the slow warm-up. Binding alone does not accept
    # connections; only serve_forever() does. If we warm up first, the
    # browser hangs on "connecting" for ~1min (first hardware probe is
    # slow on a cold Windows boot). Instead: serve now, warm in background.
    threading.Thread(target=srv.serve_forever, daemon=True).start()

    def _warm():
        try:
            get_stats()                                  # first frame (fast only)
        except Exception as e:
            sys.stderr.write("[agent] warm failed: %r\n" % (e,))
        try:
            if not _hw_busy.is_set():
                _hw_busy.set()
                try:
                    hw = _collect_hardware()             # slow: ~30-60s cold
                    if hw.get("ok"):
                        with _lock:
                            _hw["static"] = hw
                        sys.stderr.write("[agent] hardware inventory refreshed\n")
                finally:
                    _hw_busy.clear()
        except Exception as e:
            sys.stderr.write("[agent] hw warm failed: %r\n" % (e,))

    threading.Thread(target=_warm, daemon=True).start()
    threading.Thread(target=collector, daemon=True).start()
    url = "http://127.0.0.1:%d/index.html" % port
    print("=" * 54)
    print("  Vitals AGENT")
    print("  url     : %s" % url)
    print("  api     : http://127.0.0.1:%d/api/stats" % port)
    print("          : http://127.0.0.1:%d/api/hardware" % port)
    print("  backend : %s" % ("psutil (full)" if HAVE_PSUTIL else "wmi (limited)"))
    print("  root    : %s" % ROOT)
    print("  refresh : metrics %.0fs / processes %.0fs / gpu %.0fs" %
          (FAST_EVERY, PROC_EVERY, GPU_EVERY))
    print("  hardware: inventory %.0fs / live 10s" % HARD_EVERY)
    print("  首次启动硬件清单约需 30-60 秒，页面会自动补全" if HAVE_PSUTIL
          else "  降级模式：无 psutil，进程/磁盘速率不可用，硬件信息正常")
    print("  ctrl-c  : stop")
    print("=" * 54)
    if "--no-browser" not in sys.argv:
        # When the dashboard window closes we shut ourselves down and take
        # LHM with us, so nothing is left running in the background.
        _open_window(url, on_close=_shutdown)
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        print("\nstopped")
        srv.shutdown()


if __name__ == "__main__":
    main()
