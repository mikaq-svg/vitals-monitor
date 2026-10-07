/* Vitals 开发自查 —— 不打包进分发。

   用法：
     node tools/_check.js          语法 + CSS 括号 + 首页装饰模块的端到端断言
     node tools/_check.js shots    上面全部，再出一套九主题的首页截图

   为什么要单开一个文件、放到 tools/ 下：
   首页那些会动的装饰件（canvas 画的 3D 线框）肉眼很难判断"到底有没有在画"——
   一块没画上东西的 canvas 和一块画了但恰好很淡的 canvas 长得一模一样。
   所以用无头 Chrome 真跑一遍，直接数 canvas 上非透明像素的个数。
   产物全在 tools/ 下，以 _ 开头或落在 shots/，打包脚本会跳过它们。
*/
const fs = require('fs');
const path = require('path');
const cp = require('child_process');

const ROOT = path.dirname(__dirname);
const CHROME = 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const INDEX = path.join(ROOT, 'index.html');
/* Chrome 的配置目录扔到系统临时区，别落在项目里 —— 每次跑都会生成几百个
   小文件，删起来还可能撞上环境的删除保护。 */
const TMP = require('os').tmpdir();
const UD = path.join(TMP, 'vitals-check-cp');
function wipe(dir) { try { fs.rmSync(dir, { recursive: true, force: true }); } catch (e) {} }

let fails = 0;
function ok(name, cond, extra) {
  console.log((cond ? '  OK   ' : '  FAIL ') + name + (extra ? '   ' + extra : ''));
  if (!cond) fails++;
}
function head(t) { console.log('\n== ' + t + ' =='); }

/* ---------- 1. 静态检查 ---------- */
head('静态检查');
const src = fs.readFileSync(INDEX, 'utf8');

{
  const re = /<script(?![^>]*\bsrc=)[^>]*>([\s\S]*?)<\/script>/g;
  let m, n = 0, bad = 0;
  while ((m = re.exec(src))) {
    n++;
    try { new Function(m[1]); } catch (e) { bad++; console.log('     #' + n + ' ' + e.message); }
  }
  ok('script 语法（' + n + ' 段）', bad === 0, bad ? bad + ' 处错误' : '');
}
{
  const st = /<style[^>]*>([\s\S]*?)<\/style>/.exec(src);
  let css = st ? st[1] : '';
  css = css.replace(/\/\*[\s\S]*?\*\//g, '')
           .replace(/"(?:[^"\\]|\\.)*"/g, '""')
           .replace(/'(?:[^'\\]|\\.)*'/g, "''");
  const b = (css.match(/\{/g) || []).length - (css.match(/\}/g) || []).length;
  const p = (css.match(/\(/g) || []).length - (css.match(/\)/g) || []).length;
  ok('CSS 括号平衡', b === 0 && p === 0, '{}差 ' + b + '  ()差 ' + p);
}
['window.DECO_ARM', 'window.DECO_PRUNE', 'window.DECO_SYNC', 'window.DECO_REPAINT',
 'MODS.cube', 'MODS.sphere', 'MODS.helix', 'MODS.orbit', 'MODS.wave', 'MODS.stars',
 '--deco-w', '--deco-glow', 'cardKey'].forEach(k => {
  ok('锚点 ' + k, src.indexOf(k) >= 0);
});

/* ---------- 2. 装饰模块端到端 ---------- */
head('首页装饰模块（无头 Chrome 实跑）');

function runDom(page) {
  const out = cp.execFileSync(CHROME, [
    '--headless=new', '--disable-gpu', '--no-sandbox',
    /* 让所有 http 请求走一个不存在的代理，立刻失败，页面直接进离线分支。
       本机要是正跑着一个 Vitals 实例，页面的轮询就一直有挂起的请求，
       --virtual-time-budget 会被它拖住不返回（实测卡死十分钟）。 */
    '--proxy-server=http://127.0.0.1:1',
    '--user-data-dir=' + UD,
    '--window-size=1400,900', '--virtual-time-budget=9000', '--dump-dom',
    'file:///' + page.replace(/\\/g, '/')
  ], { stdio: ['ignore', 'pipe', 'ignore'], maxBuffer: 1 << 28, timeout: 150000 }).toString();
  const m = /ZZRESULT ([\s\S]*?) ZZEND/.exec(out);
  if (!m) return null;
  /* dump-dom 给的是 HTML，`->` 这类会被转成实体，先还原再比对 */
  function unesc(s) {
    return s.replace(/&lt;/g, '<').replace(/&gt;/g, '>')
            .replace(/&quot;/g, '"').replace(/&#39;/g, "'")
            .replace(/&amp;/g, '&');   // & 必须最后还原
  }
  const kv = {};
  unesc(m[1]).split(' | ').forEach(s => {
    const i = s.indexOf('=');
    if (i > 0) kv[s.slice(0, i)] = s.slice(i + 1);
  });
  return kv;
}

(() => {
  const page = path.join(ROOT, 'tools', '_deco_test.html');
  const i = src.lastIndexOf('</body>');
  fs.writeFileSync(page, src.slice(0, i) +
    '<script src="_deco_test.js"></script>\n' + src.slice(i));
  wipe(UD);

  let kv = null;
  try { kv = runDom(page); } catch (e) { console.log('     跑不起来：' + e.message); }
  if (!kv) { ok('端到端拿到结果', false); return; }
  const has = k => kv[k] != null;

  ok('装饰按钮 6 个', kv.decoButtons === '6', kv.decoIds);
  ok('22 个数据指标没被挤掉', kv.metricsStillThere === '22');
  ok('六件都建出了卡和画布', kv.cards === '6' && kv.canvases === '6', kv.keys);
  const px = (kv.pixels || '').split(',').map(Number);
  ok('六件都真画上了东西', px.length === 6 && px.every(v => v > 0), kv.pixels);
  ok('卡面上不写名字', kv.nameLabels === '0' && kv.nameInText === '0',
     '标题标签=' + kv.nameLabels + ' 文本里出现名字=' + kv.nameInText);
  ok('存进了 localStorage', (kv.savedDeco || '').split(',').length === 6, kv.savedDeco);
  ok('换主题颜色跟着变', /CHANGED/.test(kv.themeColor || ''), kv.themeColor);
  ok('赛博主题辉光生效', Number(kv.cyberInk) > Number(px[0] || 0),
     'cyber=' + kv.cyberInk + ' mono=' + px[0]);
  ok('图案没出界（尺寸自洽）', /^m=(\d+)x(\d+)\/\d+ -> l=(\d+)x(\d+)\/\d+ -> s=/.test(kv.sizeCycle || ''), kv.sizeCycle);
  {
    const n = (kv.sizeCycle || '').match(/\/(\d+) -> l=\d+x\d+\/(\d+)/);
    ok('画布缓冲区跟着尺寸档重算', !!n && Number(n[2]) > Number(n[1]), n ? n[1] + ' -> ' + n[2] : kv.sizeCycle);
  }
  ok('删一张后还剩 5 张且都在画',
     kv.afterDel === '6 -> 5' && (kv.stillInked || '').split(',').filter(v => Number(v) > 0).length === 5,
     kv.afterDel + ' | ' + kv.stillInked);
  ok('删除会存盘', (kv.savedAfterDel || '').split(',').length === 5, kv.savedAfterDel);
  ok('退出编辑态', kv.editingOff === '1');
  ok('切走视图再回来不炸', kv.viewRoundTrip === 'ok');
  ok('拖动起手：占位块 1 个、卡片挂到 body 1 张',
     /ph=1 onBody=1/.test(kv.dragStart || ''), kv.dragStart);
  ok('清空后画布也没了', kv.emptied === '0/0', kv.emptied);
  if (has('EXCEPTION')) ok('无异常', false, kv.EXCEPTION);

  fs.rmSync(page, { force: true });
  wipe(UD);
})();

/* ---------- 3. 截图（可选） ---------- */
if (process.argv[2] === 'shots') {
  head('九主题首页截图');
  const OUT = path.join(ROOT, 'tools', 'shots');
  fs.mkdirSync(OUT, { recursive: true });
  const HOME = [
    { t: 'cube', s: 'm' }, { t: 'sphere', s: 'm' }, { t: 'helix', s: 'm' },
    { t: 'orbit', s: 'm' }, { t: 'wave', s: 'm' }, { t: 'stars', s: 'm' },
    { k: 'cpu', s: 'l' }, { k: 'mem', s: 'm' }, { k: 'gputemp', s: 's' }, { k: 'net', s: 'm' }
  ];
  ['mono', 'modern', 'aero', 'rococo', 'soviet', 'ink', 'cyber', 'nasa', 'hacker'].forEach(t => {
    const boot = '<script>try{localStorage.setItem("ws_home",' + JSON.stringify(JSON.stringify(HOME)) +
      ');localStorage.setItem("ws_theme","' + t + '");}catch(e){}<\/script>';
    const i2 = src.indexOf('</head>');
    const page = path.join(ROOT, 'tools', '_shot.html');
    const ud = path.join(TMP, 'vitals-shot-' + t);
    fs.writeFileSync(page, src.slice(0, i2) + boot + src.slice(i2));
    const png = path.join(OUT, t + '.png');
    cp.execFileSync(CHROME, [
      '--headless=new', '--disable-gpu', '--no-sandbox', '--hide-scrollbars',
      '--force-device-scale-factor=1',
      '--proxy-server=http://127.0.0.1:1',
      '--user-data-dir=' + ud,
      '--window-size=1500,1020', '--virtual-time-budget=2500',
      '--screenshot=' + png, 'file:///' + page.replace(/\\/g, '/')
    ], { stdio: 'ignore', timeout: 120000 });
    wipe(ud);
    console.log('  ' + t.padEnd(8) + Math.round(fs.statSync(png).size / 1024) + 'KB');
  });
  fs.rmSync(path.join(ROOT, 'tools', '_shot.html'), { force: true });
}

console.log('\n' + (fails ? fails + ' 项没过' : '全部通过'));
process.exit(fails ? 1 : 0);
