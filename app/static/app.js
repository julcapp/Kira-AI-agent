"use strict";
const catalog=[
["kiryusha","🧠","Кирюша","Координатор и планы"],
["competitors","📊","Аналитик","Конкуренты и рынок"],
["vk","📣","VK-менеджер","Контент и публикации"],
["lawyer","⚖️","Юрист","Договоры и риски"],
["developer","💻","IT-разработчик","Сайты и код"],
["sales","🤝","Продавец","Лиды и продажи"],
["tutor","🎓","Репетитор","Ученики и педагоги"]
];
const el=id=>document.getElementById(id);
let active="kiryusha",initData="";
function addBubble(s,cls){const d=document.createElement("div");d.className="bubble "+cls;d.textContent=s;el("messages").append(d);el("messages").scrollTop=el("messages").scrollHeight;}
function selectAgent(id){active=id;const a=catalog.find(x=>x[0]===id);el("agent-title").textContent=a[2];document.querySelectorAll(".agent-card").forEach(c=>c.classList.toggle("active",c.dataset.id===id));}
for(const [id,icon,title,desc] of catalog){let b=document.createElement("button");b.type="button";b.className="agent-card";b.dataset.id=id;let em=document.createElement("span");em.className="emoji";em.textContent=icon;let name=document.createElement("strong");name.textContent=title;let small=document.createElement("small");small.textContent=desc;b.append(em,name,small);b.addEventListener("click",()=>selectAgent(id));el("agents").append(b);}
selectAgent(active);
const hashParams=new URLSearchParams(location.hash.slice(1));
initData=(window.WebApp && window.WebApp.initData) || hashParams.get("WebAppData") || "";
async function api(path,options={}){if(!initData)throw Error("Откройте приложение через MAX, чтобы подтвердить личность.");let r=await fetch(path,{...options,headers:{"X-Max-Init-Data":initData,...(options.headers||{})}});if(!r.ok)throw Error(r.status===401?"MAX-авторизация не прошла. Откройте приложение заново.":"Ошибка API: "+r.status);return r.json();}
async function refresh(){try{const data=await api("/api/mini/records");el("record-list").replaceChildren();if(!data.records.length){const p=document.createElement("p");p.className="muted";p.textContent="Пока пусто. Добавь задачу командой /task или идею через /idea.";el("record-list").append(p);}for(const r of data.records){const d=document.createElement("div");d.className="record";const symbol=document.createElement("span");symbol.className="symbol";symbol.textContent=r.kind==="idea"?"💡":"☑️";const t=document.createElement("div");const title=document.createElement("b");title.textContent=r.title;const s=document.createElement("small");s.textContent=`#${r.id} · ${r.agent} · ${r.status}`;t.append(title,s);d.append(symbol,t);el("record-list").append(d);}}catch(e){el("record-list").textContent=e.message;}}
el("chat-form").addEventListener("submit",async e=>{e.preventDefault();const msg=el("chat-input").value.trim();if(!msg)return;el("chat-input").value="";addBubble(msg,"userbubble");el("send").disabled=true;try{let data=await api("/api/mini/chat",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({agent:active,message:msg})});addBubble(data.reply,"agentbubble");await refresh();}catch(err){addBubble(err.message,"notice");}finally{el("send").disabled=false;}});
el("refresh").addEventListener("click",refresh);
if(initData){el("connection").textContent="MAX подключён";refresh();}else{el("connection").textContent="Предпросмотр";el("record-list").textContent="Для работы с данными откройте мини-приложение через MAX."; }

async function refreshSocial(){const list=el("social-list");list.textContent="Загрузка…";try{const data=await api("/api/mini/social/channels");list.replaceChildren();for(const c of data.channels){const row=document.createElement("div");row.className="record";const name=document.createElement("b");name.textContent=c.label;const status=document.createElement("small");status.textContent=c.connected?"Подключён":"Не подключён · "+(c.manual_draft?"Черновик вручную":"Недоступен");const detail=document.createElement("div");detail.append(name,status);row.append(detail);list.append(row);}}catch(e){list.textContent=e.message;}}
el("social-refresh").addEventListener("click",refreshSocial);
refreshSocial();
