/* 首页装饰模块的端到端自查。挂在 deco_test.html 上跑，输出一行 ZZRESULT。
   ⚠️ 拖拽放在最后 —— finish() 里有 215ms 的落定延时，无头 dump 不等它，
      放前面会让后面所有断言都跑在"拖到一半"的中间态上。 */
(function(){
  var out=[];
  function log(k,v){out.push(k+'='+v);}
  function $(s){return document.querySelector(s);}
  function cards(){return [].slice.call(document.querySelectorAll('#home-grid .hcard.deco'));}
  function canvases(){return [].slice.call(document.querySelectorAll('#home-grid .hcard.deco canvas'));}
  function ink(c){
    try{
      var d=c.getContext('2d').getImageData(0,0,c.width,c.height).data,n=0;
      for(var i=3;i<d.length;i+=4)if(d[i]>8)n++;
      return n;
    }catch(e){return 'ERR';}
  }
  function wh(c){var r=c.getBoundingClientRect();return Math.round(r.width)+'x'+Math.round(r.height);}

  try{
    var IDS=['cube','sphere','helix','orbit','wave','stars'];

    /* 1. 进编辑态 → 打开添加面板 → 六个装饰按钮在不在 */
    $('#home-edit').click();
    $('#home-add').click();
    var btns=[].slice.call(document.querySelectorAll('#pick-list button[data-t]'));
    log('decoButtons',btns.length);
    log('decoIds',btns.map(function(b){return b.dataset.t;}).join(','));
    log('metricsStillThere',document.querySelectorAll('#pick-list button[data-k]').length);

    /* 2. 一个一个加。每加一个面板会重建，所以每次都得重新查按钮 */
    IDS.forEach(function(t){
      var b=document.querySelector('#pick-list button[data-t="'+t+'"]');
      if(b)b.click();
    });
    log('cards',cards().length);
    log('canvases',canvases().length);
    log('keys',cards().map(function(c){return c.dataset.key;}).join(','));

    /* 3. 每块画布占多大、绘制缓冲区多大 */
    log('sizes',canvases().map(function(c){
      return c.dataset.deco+':'+wh(c)+'@'+c.width+'x'+c.height;
    }).join(' '));

    /* 4. 六件都得真画上东西 */
    log('pixels',canvases().map(ink).join(','));

    /* 4b. 卡面上不写字：没有标题标签，卡内文本里也不该出现任何装饰名 */
    var NAMES=['旋转立方体','线框球体','双螺旋','电子轨道','波形','星场'];
    log('nameLabels',cards().filter(function(c){return c.querySelector('.hlbl');}).length);
    log('nameInText',cards().filter(function(c){
      var t=c.textContent||'';
      return NAMES.some(function(n){return t.indexOf(n)>=0;});
    }).length);

    /* 5. 存进 localStorage 没有 */
    var saved=JSON.parse(localStorage.getItem('ws_home')||'[]');
    log('savedDeco',saved.filter(function(x){return x.t;}).map(function(x){return x.t+'/'+x.s;}).join(','));

    /* 6. 换个主题，颜色得跟着变 */
    function sample(c){
      var d=c.getContext('2d').getImageData(0,0,c.width,c.height).data;
      for(var i=0;i<d.length;i+=4)if(d[i+3]>150)return d[i]+','+d[i+1]+','+d[i+2];
      return 'none';
    }
    var c0=canvases()[0];
    var before=sample(c0);
    applyTheme('cyber');
    var after=sample(c0);
    log('themeColor',before+' -> '+after+(before!==after?' CHANGED':' SAME'));
    log('cyberInk',ink(c0));
    applyTheme('soviet');
    log('sovietInk',ink(c0));
    applyTheme('mono');

    /* 7. 尺寸档：M -> L -> S，每档都要量得到、也还画着东西 */
    var card0=cards()[0], seq=[];
    for(var i=0;i<3;i++){
      seq.push(card0.className.replace('hcard ','').replace(' deco','')+'='+wh(card0.querySelector('canvas'))
        +'/'+ink(card0.querySelector('canvas')));
      card0.querySelector('.hsize').click();
    }
    log('sizeCycle',seq.join(' -> '));

    /* 8. 删一张，剩下的还得继续画 */
    var n0=cards().length;
    cards()[0].querySelector('.hdel').click();
    log('afterDel',n0+' -> '+cards().length);
    log('stillInked',canvases().map(ink).join(','));
    log('savedAfterDel',JSON.parse(localStorage.getItem('ws_home')||'[]')
      .filter(function(x){return x.t;}).map(function(x){return x.t;}).join(','));

    /* 9. 退出编辑态 */
    $('#home-edit').click();
    log('editingOff',document.getElementById('home-grid').classList.contains('editing')?0:1);

    /* 10. 切走视图再回来 */
    go('cpu'); go('home');
    log('viewRoundTrip','ok');

    /* 11. 拖拽起手：卡片该被拎到 body 上、原位留个占位块 */
    $('#home-edit').click();
    var g=$('#home-grid');
    var beforeKids=g.children.length;
    var src=cards()[0], rs=src.getBoundingClientRect();
    var rd=g.children[0].getBoundingClientRect();
    src.dispatchEvent(new PointerEvent('pointerdown',{bubbles:true,button:0,pointerId:7,
      clientX:rs.left+30,clientY:rs.top+30}));
    window.dispatchEvent(new PointerEvent('pointermove',{bubbles:true,pointerId:7,
      clientX:rd.left+30,clientY:rd.top+6}));
    log('dragStart','ph='+document.querySelectorAll('#home-grid .hph').length+
      ' onBody='+document.querySelectorAll('body > .hcard').length+
      ' kids='+beforeKids+'->'+g.children.length);
    window.dispatchEvent(new PointerEvent('pointerup',{bubbles:true,pointerId:7,
      clientX:rd.left+30,clientY:rd.top+6}));
    log('dragUp','ok');

    /* 12. 清空：装饰件和画布都得跟着没 */
    while(cards().length)cards()[0].querySelector('.hdel').click();
    log('emptied',cards().length+'/'+canvases().length);
  }catch(e){
    out.push('EXCEPTION='+(e&&e.message||e));
  }

  var pre=document.createElement('pre');
  pre.textContent='ZZRESULT '+out.join(' | ')+' ZZEND';
  document.body.appendChild(pre);
})();
