# Vitals — 本机监测台

一个跑在自己电脑上的硬件监测面板。深色、硬核，数据全留在本机。

---

## 怎么打开

双击文件夹里的 `start.vbs`。

黑窗口不会出现，浏览器会自己开出来，而且没有地址栏、标签页那些东西，看着就跟一个正经的桌面软件一样。

第一次打开的时候，它会先问一句要不要在桌面放个快捷方式，你说要它才建。建好以后就不用再去文件夹里翻了，直接点桌面上那个。文件夹挪到别处也不怕，下次启动会把快捷方式重新指过去。

要是你点了"不要"，它就不再问了，桌面也不会有图标——想建的话，把文件夹里的 `start.vbs` 右键发一个快捷方式到桌面也一样使。

想关掉，双击文件夹里的 `stop.bat`，然后关掉那个窗口就行了。

文件夹放哪儿都行——桌面、D 盘、U 盘，随便挪。

---

## 界面怎么看

左边一条竖栏管完所有事：最上面是机器名和连接状态，中间是页面清单，下面是实时读数和网卡。右上角按数字键 `1` 到 `9` 也能跳页。

**0 首页**

不是"概览"，是一张你自己排的台面。默认放了几张最常看的：CPU 占用、CPU 温度、GPU 温度、GPU 占用、内存、存储、网络、进程数、开机时长。

想改成自己的，点右上角 **EDIT**：

- **+ 添加**：从二十多个指标里挑，按处理器／温度／内存／存储／网络／显卡／系统分了组。挑过的不让重复加。面板最下面还有一组**装饰**——旋转立方体、线框球、双螺旋这些会动的线框件，不显示任何数据，纯粹是摆着好看。线条颜色跟着当前主题走，想摆几个摆几个，尺寸也能像卡片一样切。
- **拖动重排**：按住卡片拖到别的位置。
- **切尺寸**：卡片右下角那个 S／M／L 点一下换一档。S 占一格，M 占两格宽，L 又宽又高。
- **删掉**：卡片右上角的 ✕。

排好之后按 **DONE** 退出编辑态。这套排布存在这台电脑上，下次打开还是你排的样子。想推倒重来就点**恢复默认**。

**1 概览**  
CPU、内存、存储、网络四张卡片，加上曲线、进程榜和事件流。平时看这一页就够了。

**2 处理器**  
每个核心各自的实时负载、使用率历史、温度，以及最吃 CPU 的几个进程。

温度那一块分上下两层：上面是六个实时读数（封装、平均、GPU 核心、显存、内存、功耗），下面是一条**温度曲线**——CPU 封装温度按真实时间画的走势图，标出了窗口内的峰值和它出现的时刻。温度源没起来的时候下面显示一片 `--`，曲线也空着。

**3 显卡**  
利用率、显存、温度、功耗、频率。只有 NVIDIA 的显卡会显示实时数值，其他显卡只能显示型号。

**4 内存**  
占用条、物理和虚拟内存的明细，以及最吃内存的几个进程。

**5 存储**  
各个分区的容量、读写吞吐曲线和每秒读写次数。

**6 网络**  
上下行曲线，网卡列表（IP、物理地址、协商速率、累计流量）。

**7 外设**  
目前插着的设备——鼠标、键盘、摄像头、蓝牙、USB 之类的，还有音视频设备、网线/WiFi 链路状态、物理硬盘、显示器。

**8 进程**  
占 CPU 最高的四十个和占内存最高的二十个。

**9 系统**  
电脑型号、主板、BIOS、处理器型号，还有采集开关和完整的事件记录。

**游戏**

侧栏点"游戏"，进去是一个**全屏的独立界面**，跟监控信息完全不挤在一起。顶上两个按钮切游戏，右上角 ✕ 或者按 **Esc** 退出。两个游戏：

- **贪吃蛇**：方向键或 WASD 转向，空格暂停。最高分记在这台电脑上，下次打开还在。
- **五子棋**：15×15 的棋盘，你和一个电脑对手下。电脑会堵你的三、堵你的四，自己有机会也会直接连五——不是随便乱下的那种。棋盘上标了 A 到 O 和 1 到 15，正规棋盘的样子。你可以点"执黑先行／执白后行"换先后手，下错了能"悔棋"（一次退两步，退回到该你走的时候）。胜负和的手数记着。

**两个游戏都跟着当前风格走**——棋盘、蛇身、棋子的颜色全是从当前主题里取的，换皮自动跟着换，不用单独设置。

游戏只在你进去的时候才跑，退出就停——不会在后台偷偷占处理器。

底栏显示运行状态、告警条数、开机多久、当前多少个进程。

**关于告警**  
CPU、内存、存储任意一项越过阈值（默认 90%，在"系统"页里可以调），就会记一条到事件流里，状态变成红色的告警。

**关于事件流**

概览页和系统页各有一条事件流，显示的是同一份记录。每条带搜索框和级别筛选（全部／INFO／OK／WARN／ALERT）：

- 搜索框里打字，按内容实时过滤。两个面板的搜索是联动的，在左边打了字右边也一起过滤。
- 级别按钮管筛选。搜索和级别是叠加的，可以同时用。
- 右边的数字是"现在显示几条 / 一共几条"。

**换风格**

侧栏顶部有个 STYLE 按钮，点开有九套皮：

- **Default**：纯黑底、直角、灰阶。默认就是这套，硬核仪表盘的路子。
- **Modern**：苹果那一挂。近白底上散着几团很淡的蓝、紫、粉、青光斑，面板是压得很透的白玻璃——白度只有 38%，背后的光透过毛玻璃糊成一片淡淡的颜色。所以它不只是"白色卡片"，玻璃是真看得出来的。圆角开到最大，没有花纹、没有描边线、没有渐变色块。
- **Frutiger Aero**：清透的蓝天、草地、水珠和玻璃气泡，2004 到 2013 那一波"自然 + 科技 + 乐观"的审美。底色是干净的天空蓝转水青，右上角一团阳光；面板是半透明的玻璃壳，光泽是水润的，不是塑料的。
- **Rococo**：18 世纪法国装饰艺术。整块淡粉底色，面板像上釉的瓷器，圆角开到最大，边缘是柔化的玫瑰唇线。洛可可的规矩是不许出现锐利的东西，也不许出现重颜色。
- **Soviet**：苏联构成主义。1920 年代苏联先锋派那一路（罗德琴科、塔特林、李西茨基）。红、黑、米白三色，一道巨大的红色斜切色块，硬边矩形、粗重的字、硬投影。要的是平面上的"力量感"——没有渐变、没有圆角。
- **Ink**：国风。生宣那种带灰黄的暖白打底，墨色是掺了青的松烟墨，只在品牌标记和告警上点一枚朱砂。圆角收到近乎直角、线条细到刚好看得见、标题不用粗体压——留白比装饰重要。
- **Cyberpunk**：深蓝紫的夜，七团霓虹光雾。发光边框、霓虹灯管标题、锋利直角，背景是远近两层城市天际线剪影加一道地平线辉光。参照 synthwave 和赛博朋克 2077。
- **NASA**：近黑的深空，极暗的星云余晖，拉丝金属面板配一道橙红识别条。星点压得很低，不抢戏；那道橙红是整幅画面里唯一的一抹暖色，也是飞行器遥测面板的识别标。
- **Hacker**：千禧年前后互联网对黑客的想象。夜视绿的 CRT 终端，主色只有一味荧光绿，其余全是黑。背景那层往下淌的乱码是真在滚的字符，不是贴图。每一列从自己那套字库里取字：有的滚英文、有的滚日文假名、有的滚汉字、有的滚纯符号。每列的字号、亮度、尾巴长短、下落速度都各不相同，但全收在一条窄带里，整体调子是齐的——看着乱，不会花。上面还罩着一层扫描线。

**九套皮的字体和字色是分开的**，不是换张底图了事。字体全部用你电脑上就有的字，不用额外装任何东西。同一个界面上，字体家族会跟着风格走：洛可可和国风走衬线、楷体；苏式用超粗的 Arial Black 配黑体；赛博朋克和 NASA 走窄体工业风；Hacker 走终端等宽；Modern 用系统里最接近苹果那套的几何无衬线；Default 用系统等宽。正文颜色也跟着底色的冷暖偏。有一点是统一的：所有数字读数都强制等宽，不然换字体的时候数字会左右跳。

**强调色只有 Default 那套能用**，其余八套的配色是风格的一部分，改动会破坏整体，所以不开放。

强调色一共八支，条、曲线、高亮都用它。**它是跟着风格走的**：同一支颜色在深底和浅底上表现差很远——荧光绿搁在浅色底上会糊成一片，深蓝搁在黑底上又基本看不见。所以每套皮都有自己单独的一份色表。

风格、强调色、首页排布、游戏记录，四样都记在这台电脑上，下次打开还是你上次弄的样子。

想看几套风格并排长什么样，直接双击 `style-preview.html`，那是张静态的对照板，不用启动服务。

---

## 关于采集

服务只监听本机地址，同一个局域网里的其他电脑也访问不到，更不会往任何地方上传。

数据是怎么读的：系统计数器、Windows 的硬件管理接口，以及 NVIDIA 驱动自带的显卡查询工具。全部只读，不改动你电脑上的任何东西。

**关于温度**

Windows 没有开放读取 CPU 温度的口子，所以文件夹里附带了 `LibreHardwareMonitor`，读的是它报出来的数。第一次双击启动时，系统会弹一个权限窗口问你同不同意，点“是”就行，之后就不再问了。如果你把它删了或者没让它跑起来，“处理器”页的温度区域会显示一片 `--`，温度曲线也空着，其他功能不受影响。

---

## 出问题了

**双击之后没反应**  
文件夹可能没完整解压出来。`start.vbs` 和 `start.bat` 必须是挨着的，别单独把其中一个拖出来。

**页面一直显示"探针离线"**  
后台服务没起来。检查一下文件夹路径里有没有被系统拦下来的东西，比如杀毒软件把 `server.py` 隔离了。也可以在文件夹里打开命令行，手动运行：

```
python server.py
```

报错会直接显示出来。

**提示端口被占用**  
不用管，它会自己往后找一个能用的端口。

**温度那一栏是 `--`**  
`LibreHardwareMonitor` 没在跑。正常情况双击启动时会自动带上它，第一次会弹权限窗口。要是当时点了“否”，下次想用的话，到 `tools\LibreHardwareMonitor\` 里手动双击 `LibreHardwareMonitor.exe`，同意权限就行。

**显卡那一页全是空的**  
多半不是 NVIDIA 的显卡。型号仍然会显示，但实时数据只有 NVIDIA 有。

**外设的"在线"状态怎么理解**  
它反映的是驱动有没有启用，不是你有没有物理插拔。拔掉一个 U 盘，可能要过几秒到几十秒才会变成离线。

**中文显示成乱码**  
系统的区域设置需要支持中文。启动脚本本身已经按中文编码处理好，一般是系统区域设置的问题。

**网络速率和进程 CPU 榜是空的**  
这台机器上没有可用的 Python 环境，或者缺一个叫 psutil 的可选组件。此时程序会自动退回用系统接口采集，设备、显卡、型号、硬盘都照常显示，只是少了网络速率和进程 CPU 排名。

**想手动排查**  
在文件夹里打开命令行，输入：

```
python server.py
```

这样会打印详细日志，并且自动打开浏览器。如果不想让它自动开浏览器，加上 `--no-browser`。

---

---

# Vitals — Local Machine Monitor

A hardware monitor that runs on your own PC. Dark, hardcore, and everything stays on your machine.

---

## How to open it

Double-click `start.vbs` inside the folder.

No black window appears. The browser opens by itself, and it has no address bar, no tabs, no bookmarks — it looks like a regular desktop application.

The first time you open it, it asks whether you want a shortcut on the desktop — say yes and it makes one. After that you can skip the folder entirely and just click that icon. Move the folder somewhere else and it still works: the next launch points the shortcut at the new location.

If you say no, it won't ask again and no icon appears. You can still make one yourself any time — right-click `start.vbs` and send a shortcut to the desktop.

To stop it, double-click `stop.bat`, then close the window it leaves open.

The folder can live anywhere: desktop, D drive, a USB stick. Move it however you like.

---


## Reading the interface

One vertical column on the left handles everything: machine name and connection state at the top, the page list in the middle, live readings and network adapters below. You can also press the number keys `1` through `9` to jump between pages.

**0 Home**

Not an "overview" — a surface you arrange yourself. A few of the things you check most are there by default: CPU load, CPU temperature, GPU temperature, GPU load, memory, disk, network, process count, uptime.

To make it yours, click **EDIT** in the top-right:

- **+ Add**: pick from more than twenty metrics, grouped into CPU / temperature / memory / disk / network / GPU / system. Anything already on the board can't be added twice. The bottom group is **Decorations** — a rotating cube, a wireframe globe, a double helix and the like. They carry no data whatsoever, they just move. Their lines take the colour of the current theme, you can place as many as you like, and they resize like any other card.
- **Drag to rearrange**: hold a card and drop it wherever you want it.
- **Resize**: the S / M / L marker in the card's bottom-right cycles through the three sizes. S takes one cell, M takes two columns, L is both wide and tall.
- **Delete**: the ✕ in the card's top-right.

Press **DONE** to leave edit mode. The layout is stored on this machine, so it's still there next time. **Reset to default** throws it away and starts over.

**1 Overview**  
Four cards for CPU, memory, disk and network, plus charts, a process ranking and an event feed. This is the page you'll want most of the time.

**2 CPU**  
Live load for every individual core, usage history, temperature, and the processes eating the most CPU.

Temperature has two layers: six live readings on top (package, average, GPU core, GPU memory, DIMM, power draw) and a **temperature curve** underneath — package temperature plotted against real time, with the window's peak and the moment it happened marked on it. If no temperature source is running, the readings show `--` and the curve stays empty.

**3 GPU**  
Utilization, VRAM, temperature, power draw and clocks. Only NVIDIA cards report live numbers — other cards show their model name only.

**4 Memory**  
Usage bars, a breakdown of physical and virtual memory, and the processes using the most RAM.

**5 Disk**  
Capacity for each partition, read/write throughput charts, and read/write operations per second.

**6 Network**  
Upload/download charts, plus an adapter list with IP, MAC address, negotiated link speed and cumulative traffic.

**7 Devices**  
What's currently plugged in — mouse, keyboard, camera, Bluetooth, USB and so on — along with audio/video devices, Ethernet/Wi-Fi link state, physical drives and monitors.

**8 Processes**  
The top forty by CPU and the top twenty by memory.

**9 System**  
Machine model, motherboard, BIOS and processor model, plus collection controls and the full event log.

**Games**

Click the games entry at the bottom of the sidebar and you get a **full-screen standalone interface** with nothing else competing for room. Two buttons at the top switch games; the ✕ in the corner or the **Esc** key gets you out. Both games:

- **Snake**: arrow keys or WASD to turn, space to pause. Your best score is remembered on this machine, so it's still there next time.
- **Gomoku**: a 15×15 board against a computer opponent. It blocks your threes and fours, and takes the win when it has one — it isn't playing at random. The board is labelled A to O and 1 to 15, like a real one. You can swap who goes first with the black/white button, and take a move back if you slip (it rewinds two plies, back to your turn). Wins, losses and draws are all kept.

**Both games follow the current style** — the board, the snake and the stones all take their colours from whatever theme is active, so switching skins restyles them automatically with nothing extra to set up.

The games only run while you're inside them; leave and they stop, so nothing is quietly burning CPU in the background.

The bottom bar tracks running state, alert count, uptime and current process count.

**About alerts**  
If CPU, memory or disk crosses the threshold (90% by default, adjustable on the System page), it gets logged to the event feed and the state flips to a red alert.

**About the event feed**

There's an event feed on both the Overview and the System page, showing the same log. Each one has a search box and level filter buttons (all / INFO / OK / WARN / ALERT):

- Type in the search box and the list filters live. The two panels are linked — type on the left and the right one filters too.
- The level buttons handle filtering. Search and level stack, so you can use both at once.
- The number on the right reads "how many are showing / how many there are".

**Changing the look**

There's a "STYLE" button at the top of the sidebar. It offers nine skins:

- **Default**: black background, square corners, greyscale. This is the default — a hard-edged instrument-panel look.
- **Modern**: the Apple family. A near-white base carrying a few very pale blue, violet, pink and mint light blooms, with panels made of white glass held at low opacity — only 38% white — so whatever sits behind them comes through the frosted blur as a soft tint. That's the point: it doesn't just read as white cards, the glass is genuinely visible. The largest corner radii in the set, and no patterns, outline strokes or gradient blocks.
- **Frutiger Aero**: clear blue sky, grass, water droplets and glass bubbles — the "nature plus technology plus optimism" look from roughly 2004 to 2013. The base is a clean sky blue shifting into water cyan with a patch of sunlight in the upper right; the panels are translucent glass shells and the sheen is watery rather than plastic.
- **Rococo**: 18th-century French ornamental art. One flat cotton-candy-pink base; the panels look like glazed porcelain, with the largest possible corner radii and soft rose edge lines rather than hard outlines. The rule of Rococo is that nothing sharp and nothing heavy is allowed.
- **Soviet**: Soviet Constructivism — the 1920s Russian avant-garde (Rodchenko, Tatlin, Lissitzky). Red, black and off-white; one huge diagonally-cut red block; hard-edged rectangles, heavy type and hard offset shadows. The point is graphic force on a flat plane — no gradients, no rounded corners.
- **Ink**: Chinese ink-wash. Raw xuan paper — warm off-white with a grey-yellow cast — under a pine-soot ink that carries a hint of blue-green, with a single vermilion seal on the brand mark and on alerts. Corners pulled in to nearly square, hairlines just barely visible, headings left unstressed. Empty space matters more than ornament here.
- **Cyberpunk**: a deep blue-violet night with seven clouds of neon glow. Glowing borders, neon-tube headings, sharp corners, and a background of two layers of city skyline silhouette above a lit horizon. Borrowed from synthwave and Cyberpunk 2077.
- **NASA**: near-black deep space with faint nebula afterglow, brushed-metal panels and an orange-red identification strip. The stars are kept dim so they never steal the show; that orange-red strip is the only warm note in the whole frame, and it's how spacecraft telemetry panels are marked.
- **Hacker**: the turn-of-the-millennium internet's idea of a hacker. Night-vision green on a CRT terminal, with fluorescent green as the only real colour and black everywhere else. The background layer is genuine falling glyph rain, always moving, not a static image: every column draws from its own alphabet — some scroll Latin letters, some Japanese kana, some Chinese characters, some pure symbols — and each column picks its own font size, brightness, tail length and fall speed. All of it stays inside a deliberately narrow band, so the texture reads as even rather than chaotic. Scan lines are laid over the top.

**Each of the nine skins also gets its own typeface and text colour**, rather than just a new background. Every face is one your computer already has, so nothing extra is installed. The font family follows the style: Rococo and Ink use serif and kaiti; Soviet the ultra-heavy Arial Black with a black gothic; Cyberpunk and NASA a condensed industrial face; Hacker a terminal monospace; Modern the closest thing Windows has to Apple's geometric sans; and Default the system monospace. Body text colour shifts warm or cool with the background too. One thing stays consistent: every numeric readout is forced to monospace, otherwise the digits jitter as the font changes.

**The accent picker is only available on Default.** On the other eight the palette is part of the style, and changing it would break the overall look, so it isn't exposed.

There are eight accents, used for bars, curves and highlights. They **follow the style** — one colour reads very differently on dark versus light backgrounds: neon green dissolves on a pale background, dark blue disappears on black. So every skin keeps its own separate palette.

Both choices are remembered, along with your home layout and your game records, so the next time you open it everything is where you left it.

To see the styles side by side, just double-click `style-preview.html` — it's a static comparison board and needs no service running.

---

## About data collection

The service listens only on the local address. Other machines on your LAN can't reach it, and nothing is uploaded anywhere.

How the numbers are read: system counters, Windows hardware management interfaces, and the query tool that ships with NVIDIA's driver. All of it is read-only — nothing on your machine gets modified.

**About temperature**

Windows doesn't expose CPU temperature to ordinary programs, so `LibreHardwareMonitor` is bundled in the folder and the dashboard reads whatever it reports. The first time you double-click to start, Windows asks for permission — click Yes, and it won't ask again. If you delete it or it isn't running, the temperature area on the CPU page shows `--` and everything else keeps working.

---

## Troubleshooting

**Double-click and nothing happens**  
The folder may not have been fully extracted. `start.vbs` and `start.bat` have to sit next to each other — don't drag one of them out on its own.

**The page keeps showing "agent offline"**  
The background service didn't start. Check whether something on the machine quarantined `server.py`, antivirus being the usual suspect. You can also open a command line in the folder and run:

```
python server.py
```

The error will show up directly.

**It says the port is in use**  
Ignore it. It picks the next free port on its own.

**The temperature row shows `--`**  
`LibreHardwareMonitor` isn't running. It normally starts along with the dashboard, and asks for permission the first time. If it was declined back then, open `tools\LibreHardwareMonitor\` and double-click `LibreHardwareMonitor.exe` by hand, then approve the prompt.

**The GPU page is completely empty**  
Most likely not an NVIDIA card. The model still shows up, but live numbers require NVIDIA.

**What does "online" mean for a device?**  
It reflects whether the driver is enabled, not whether you physically plugged something in. Pull a USB stick and it can take seconds to tens of seconds to flip to offline.

**Chinese text shows as garbled characters**  
Your system locale needs Chinese support. The launcher already handles Chinese encoding correctly, so this is almost always a locale setting.

**Network rates and the process CPU list are empty**  
There's no usable Python on this machine, or an optional component called psutil is missing. The program falls back to system interfaces on its own — devices, GPU, model and drives all still work, you just lose network rates and the process CPU ranking.

**I want to debug it manually**  
Open a command line in the folder and type:

```
python server.py
```

That prints a detailed log and opens the browser for you. If you'd rather it not open the browser, add `--no-browser`.
