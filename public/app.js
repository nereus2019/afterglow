const $ = s => document.querySelector(s);
const categories = {movie:['电影','已看','◉'],tv:['电视剧','已看','▣'],variety:['综艺','已看','✧'],book:['书籍','已读','▤'],game:['游戏','已玩','✥'],album:['专辑','已听','◎']};
let records=[], token='', active='all', editing={}, searching=0, selectedMonth='', searchData=null;
const esc = v => String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const today=()=>{const d=new Date();return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`};
function toast(message){$('#toast').textContent=message;$('#toast').classList.add('show');clearTimeout(toast.timer);toast.timer=setTimeout(()=>$('#toast').classList.remove('show'),4000)}
async function api(path, body){const r=await fetch(path,body?{method:'POST',headers:{'Content-Type':'application/json','X-App-Token':token},body:JSON.stringify(body)}:{});const data=await r.json();if(!r.ok)throw Error(data.error||'请求失败');return data}
async function load(){const data=await api('/api/records');records=data.records;token=data.token;render()}
function cover(x){return `<div class="cover ${esc(x.category)}"><div class="cover-type">${esc(categories[x.category][0])} / COLLECTION</div><div class="cover-title">${esc(x.title)}</div><div class="cover-symbol">${categories[x.category][2]}</div>${/^https?:\/\//.test(x.cover||'')?`<img src="${esc(x.cover)}" loading="lazy" referrerpolicy="no-referrer" alt="${esc(x.title)}封面">`:''}</div>`}
function imageFallback(){document.querySelectorAll('.cover img').forEach(img=>{img.onerror=()=>img.remove()})}
function render(){
 $('#total').textContent=records.length;
 $('#nav').innerHTML=[['all',['全部作品','','▦']],...Object.entries(categories)].map(([id,c])=>`<button data-category="${id}" class="${active===id?'selected':''}"><span>${c[2]}　${c[0]}</span><small>${id==='all'?records.length:records.filter(x=>x.category===id).length}</small></button>`).join('');
 $('#stats').innerHTML=Object.entries(categories).map(([id,c])=>`<button data-category="${id}" class="stat ${active===id?'selected':''}"><span>${c[2]} ${c[0]}</span><strong>${records.filter(x=>x.category===id).length}<small>部</small></strong></button>`).join('');
 const q=$('#filter').value.trim().toLowerCase();let list=records.filter(x=>(active==='all'||x.category===active)&&(!selectedMonth||x.date.startsWith(selectedMonth))&&[x.title,x.creator,x.note].join(' ').toLowerCase().includes(q));
 list.sort((a,b)=>$('#sort').value==='name'?a.title.localeCompare(b.title,'zh'):$('#sort').value==='old'?a.date.localeCompare(b.date):b.date.localeCompare(a.date));
 $('#shelf-title').textContent=active==='all'?'全部作品':categories[active][0];$('#count').textContent=`${list.length} 部收藏`;
 $('#grid').innerHTML=list.length?list.map(x=>`<button class="work" data-id="${esc(x.id)}">${cover(x)}<div class="work-info"><div class="work-top"><span>${categories[x.category][0]}${x.year?' · '+esc(x.year):''}</span><span class="status">${categories[x.category][1]}</span></div><h3>${esc(x.title)}</h3><p>${esc(x.creator||'我的私人收藏')}</p><div class="work-date">✓ ${esc(x.date)}${x.note?' <span>有感想 ·</span>':''}</div></div></button>`).join(''):`<div class="empty"><div class="empty-art">▤ <span>◎</span> ✧</div><h3>${records.length?'这里暂时没有作品':'你的故事，从第一部作品开始'}</h3><p>${q?'试试其他关键词。':'电影的片尾、书的末页、游戏的终章。<br>把那些留下余味的瞬间，收藏在这里。'}</p><button class="primary" id="empty-add">＋ 添加第一份余味</button></div>`;
 $('#month-filter').hidden=!selectedMonth;$('#month-filter span').textContent=selectedMonth+' 标记的作品';
 $('#empty-add')?.addEventListener('click',openSearch);imageFallback();if($('#monthly-dialog').open)renderMonthly();
}
function openSearch(){if(searchData)renderResults();$('#search-category').value=active==='all'?'movie':active;$('#search-dialog').showModal();$('#query').focus()}
function openEdit(item={}){editing={...item};$('#edit-form').reset();for(const name of ['title','category','date','year','creator','cover','note'])$('#edit-form').elements[name].value=item[name]||(name==='date'?today():name==='category'?$('#search-category').value:'');$('#delete').hidden=!item.id;$('#edit-title').textContent=item.id?'这一份余味':'留下记录';$('#save').textContent=item.id?'保存修改':'标记并收藏';$('#edit-dialog').showModal()}
for(const id of ['#search-category','#edit-category'])$(id).innerHTML=Object.entries(categories).map(([k,v])=>`<option value="${k}">${v[0]}</option>`).join('');
document.addEventListener('click',e=>{const c=e.target.closest('[data-category]');if(c){active=c.dataset.category;render()}const w=e.target.closest('[data-id]');if(w)openEdit(records.find(x=>x.id===w.dataset.id));if(e.target.closest('[data-close]'))e.target.closest('dialog').close()});
$('#add').onclick=openSearch;$('#manual').onclick=()=>openEdit();$('#backup').onclick=()=>$('#backup-dialog').showModal();$('#filter').oninput=render;$('#sort').onchange=render;
function renderResults(){
 if(!searchData)return;
 const source=$('#result-source').value,query=$('#result-filter').value.trim().toLocaleLowerCase();
 const list=searchData.results.filter(x=>(!source||x.source===source)&&[x.title,x.creator,x.year,x.edition,x.language].join(' ').toLocaleLowerCase().includes(query));
 $('#results').innerHTML=list.length?list.map((x,i)=>{const exists=records.some(r=>r.source===x.source&&r.sourceId===x.sourceId&&r.category===x.category);return `<article class="result">${cover(x)}<div><h3>${esc(x.title)}</h3><p>${esc([x.year,x.creator].filter(Boolean).join(' · '))}</p><p class="edition">${esc([x.edition,x.language].filter(Boolean).join(' · '))}</p><a href="${esc(x.url)}" target="_blank" rel="noopener noreferrer">${esc(x.source)} ↗</a></div><button data-result="${i}" ${exists?'disabled':''}>${exists?'已收藏':'+ 标记'}</button></article>`}).join(''):'<div class="empty small">没有匹配的作品。<br><span>清除筛选，尝试其他译名，或手动添加。</span></div>';
 $('#results').querySelectorAll('[data-result]').forEach(b=>b.onclick=()=>openEdit(list[Number(b.dataset.result)]));imageFallback();
}
$('#result-source').onchange=renderResults;$('#result-filter').oninput=renderResults;
$('#search-form').onsubmit=async e=>{
 e.preventDefault();const generation=++searching;const button=e.target.querySelector('button');button.disabled=true;button.textContent='搜索中…';
 $('#result-tools').hidden=true;$('#search-summary').textContent='正在查询多个来源与译名，首次搜索可能需要几十秒…';
 $('#results').innerHTML='<div class="empty small"><div class="spinner"></div>正在寻找作品与分册…</div>';
 try{
  const d=await api('/api/search?'+new URLSearchParams({q:$('#query').value,category:$('#search-category').value,alternate:$('#alternate').value}));if(generation!==searching)return;
  searchData=d;$('#result-filter').value='';
  $('#result-source').innerHTML='<option value="">全部来源</option>'+[...new Set(d.results.map(x=>x.source))].map(s=>`<option value="${esc(s)}">${esc(s)}</option>`).join('');
  $('#result-tools').hidden=!d.results.length;
  $('#search-summary').innerHTML=`<div>检索名称：${esc(d.queries.join(' / '))}</div><div>${d.sources.map(s=>esc(s.source)+': '+s.count+' 条'+(s.state==='error'?'（连接失败）':s.state==='partial'?'（部分失败）':'')).join(' · ')}</div>`+(d.notes.length?`<div>${esc(d.notes.join('；'))}</div>`:'')+(d.warnings.length?`<div class="warning">${esc(d.warnings.join('；'))}，其他来源的结果仍可使用。</div>`:'');
  renderResults();
 }catch(err){$('#search-summary').textContent='';$('#results').innerHTML=`<div class="warning">搜索失败：${esc(err.message)}。请稍后重试，或手动添加。</div>`}finally{button.disabled=false;button.textContent='搜索'}
};
$('#edit-form').onsubmit=async e=>{e.preventDefault();const button=$('#save');button.disabled=true;try{await api('/api/records',{...editing,...Object.fromEntries(new FormData(e.target))});await load();$('#edit-dialog').close();if($('#search-dialog').open)$('#search-dialog').close();toast('已保存，这份余味留下了。')}catch(err){toast(err.message)}finally{button.disabled=false}};
$('#delete').onclick=async()=>{if(!confirm(`删除《${editing.title}》的记录？此操作无法撤销。`))return;try{await api('/api/delete',{id:editing.id});await load();$('#edit-dialog').close();toast('记录已删除')}catch(err){toast(err.message)}};
function download(content,name,type){const url=URL.createObjectURL(new Blob([content],{type}));const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)}
$('#export').onclick=async()=>{try{const d=await api('/api/export');download(JSON.stringify(d,null,2),`余味备份-${today()}.json`,'application/json');toast('备份已导出')}catch(err){toast(err.message)}};
$('#csv').onclick=async()=>{try{const d=await api('/api/export');const cell=v=>'"'+String(v??'').replace(/^[=+@\-\t\r]/,"'$&").replace(/"/g,'""')+'"';const rows=[['名称','分类','标记日期','年份/版本','作者/原名','感想','来源','作品链接'],...d.records.map(x=>[x.title,categories[x.category][0],x.date,x.year,x.creator,x.note,x.source,x.url])];download('\uFEFF'+rows.map(r=>r.map(cell).join(',')).join('\r\n'),`余味作品-${today()}.csv`,'text/csv;charset=utf-8')}catch(err){toast(err.message)}};
$('#import').onclick=()=>$('#file').click();$('#file').onchange=async e=>{const file=e.target.files[0];if(!file)return;try{if(file.size>10000000)throw Error('备份不能超过 10 MB');const body=JSON.parse(await file.text());const d=await api('/api/import',body);await load();toast(`恢复完成，新增 ${d.count} 部作品`)}catch(err){toast('导入失败：'+err.message)}finally{e.target.value=''}};
$('#connect').onclick=async()=>{$('#connect-dialog').showModal();try{const d=await api('/api/info');$('#addresses').innerHTML=d.urls.length?d.urls.map(url=>`<div class="address">${esc(url)}</div>`).join(''):'未找到局域网地址，请检查电脑网络连接。'}catch(err){$('#addresses').textContent=err.message}};
function renderMonthly(){
 const previous=$('#stats-year').value||String(new Date().getFullYear());
 const years=[...new Set([new Date().getFullYear(),...records.map(x=>Number(x.date.slice(0,4)))])].sort((a,b)=>b-a);
 $('#stats-year').innerHTML=years.map(y=>`<option value="${y}">${y} 年</option>`).join('');
 $('#stats-year').value=years.includes(Number(previous))?previous:String(years[0]);
 const months=AfterglowStats.monthlyCounts(records,Number($('#stats-year').value));
 const total=months.reduce((n,m)=>n+m.total,0),max=Math.max(1,...months.map(m=>m.total));
 $('#year-total').textContent=`全年 ${total} 部 · ${months.filter(m=>m.total).length} 个月留下记录`;
 $('#month-chart').innerHTML=months.map((m,i)=>`<button class="month-column" data-month="${m.month}" aria-label="${i+1}月 ${m.total} 部作品"><span>${m.total}</span><div class="bar-track"><div class="bar" style="height:${m.total/max*100}%"></div></div><span>${i+1}月</span></button>`).join('');
 $('#month-table').innerHTML=months.map((m,i)=>`<tr><th><button class="text-button" data-month="${m.month}">${i+1}月</button></th><td><strong>${m.total}</strong></td>${Object.keys(categories).map(k=>`<td>${m.counts[k]}</td>`).join('')}</tr>`).join('');
}
$('#monthly').onclick=()=>{renderMonthly();$('#monthly-dialog').showModal()};$('#stats-year').onchange=renderMonthly;
$('#monthly-dialog').addEventListener('click',e=>{const button=e.target.closest('[data-month]');if(!button)return;selectedMonth=button.dataset.month;active='all';$('#filter').value='';$('#monthly-dialog').close();render();$('#shelf-title').scrollIntoView({behavior:'smooth',block:'start'})});
$('#clear-month').onclick=()=>{selectedMonth='';render()};
load().catch(err=>{$('#grid').innerHTML='<div class="empty"><h3>暂时无法连接本地服务</h3><p>请启动工具后刷新页面。</p></div>';toast(err.message)});
