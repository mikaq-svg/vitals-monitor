# Vitals

本机硬件监测面板。跑在自己的电脑上，只监听本机地址，数据不出本机。

## 打开

双击 `start.vbs`。退出双击 `stop.bat`。

如果文件夹里没有 `runtime` 目录，本机需要先装 Python 3，安装时勾上 `Add python.exe to PATH`。

## 页面

| 页 | 内容 |
|---|---|
| 首页 | 自己排的指标台面。22 个指标任选，可拖动重排、可切 S／M／L；另有一组会动的线框装饰件 |
| 概览 | CPU、内存、存储、网络四张卡，加曲线、进程榜、事件流 |
| 处理器 | 每核心负载与使用率历史、六个温度读数加温度曲线、最吃 CPU 的进程 |
| 显卡 | 利用率、显存、温度、功耗、频率。实时值仅 NVIDIA |
| 内存 | 占用条、物理与虚拟内存明细、最吃内存的进程 |
| 存储 | 各分区容量、读写吞吐曲线、每秒读写次数 |
| 网络 | 上下行曲线、网卡列表（IP、物理地址、协商速率、累计流量） |
| 外设 | 当前接入的设备、音视频设备、网线／WiFi 链路、物理硬盘、显示器 |
| 进程 | CPU 前四十、内存前二十 |
| 系统 | 机器型号、主板、BIOS、处理器；告警阈值；完整事件记录 |
| 游戏 | 贪吃蛇、五子棋。全屏独立界面，退出即停 |

侧栏数字键 `1` 到 `9` 跳页。

## 主题

九套：Default、Modern、Frutiger Aero、Rococo、Soviet、Ink、Cyberpunk、NASA、Hacker。侧栏顶部 STYLE 按钮切换，每套自带字体与配色，字体全用系统已有的。强调色只有 Default 可调。首页排布、主题选择和游戏记录都存在本机。

样式对照板：双击 `style-preview.html`，静态页，不用启动服务。

## 数据来源

系统计数器、Windows 硬件管理接口、NVIDIA 驱动自带的查询工具，全部只读。服务只监听本机地址，局域网内其他机器访问不到，也不往任何地方上传。

Windows 不开放读取 CPU 温度，所以附带了 `LibreHardwareMonitor`。首次启动会弹一次权限窗口，点是即可。它没跑起来时温度显示 `--`，其余功能不受影响。

## 排障

温度一栏是 `--`：`LibreHardwareMonitor` 没在跑，到 `tools\LibreHardwareMonitor\` 里手动双击一次。

页面显示探针离线，或网络速率与进程 CPU 榜为空：在文件夹里开命令行运行 `python server.py`，报错会直接打出来。

---

# Vitals

A local hardware dashboard for Windows. It runs on your own machine, listens on the loopback address only, and sends nothing anywhere.

## Running it

Double-click `start.vbs`. To quit, double-click `stop.bat`.

If there is no `runtime` directory in the folder, this machine needs Python 3 first — tick `Add python.exe to PATH` during setup.

## Pages

| Page | Contents |
|---|---|
| Home | A board you arrange yourself. Any of 22 metrics, draggable and resizable (S / M / L), plus a set of animated wireframe decorations |
| Overview | CPU, memory, disk and network cards, with charts, a process ranking and an event feed |
| CPU | Per-core load and usage history, six temperature readings with a temperature curve, top CPU processes |
| GPU | Utilization, VRAM, temperature, power draw, clocks. Live values are NVIDIA-only |
| Memory | Usage bars, physical and virtual breakdown, top memory processes |
| Disk | Per-partition capacity, read/write throughput, IOPS |
| Network | Upload/download charts, adapter list (IP, MAC, link speed, cumulative traffic) |
| Devices | Attached devices, audio/video endpoints, Ethernet and Wi-Fi link state, physical drives, monitors |
| Processes | Top forty by CPU, top twenty by memory |
| System | Machine model, motherboard, BIOS, CPU; alert threshold; full event log |
| Games | Snake and Gomoku, in a full-screen standalone view that stops when you leave it |

Number keys `1` through `9` jump between pages.

## Themes

Nine: Default, Modern, Frutiger Aero, Rococo, Soviet, Ink, Cyberpunk, NASA, Hacker. Switch with the STYLE button at the top of the sidebar. Each carries its own typeface and palette, all using fonts already on the system. The accent picker is available on Default only. Home layout, theme choice and game records are stored locally.

Static comparison board: double-click `style-preview.html` — no service required.

## Data sources

System counters, Windows hardware management interfaces, and the query tool bundled with NVIDIA's driver. All read-only. The service listens on the loopback address only, so nothing on your LAN can reach it, and nothing is uploaded.

Windows does not expose CPU temperature, so `LibreHardwareMonitor` is bundled. The first launch asks for permission once — click Yes. If it isn't running, temperatures read `--` and everything else keeps working.

## Troubleshooting

Temperatures read `--`: `LibreHardwareMonitor` isn't running. Start it once by hand from `tools\LibreHardwareMonitor\`.

The page reports the agent offline, or network rates and the process CPU ranking are empty: open a command line in the folder and run `python server.py` — errors print directly.
