# -*- coding: utf-8 -*-
"""The dashboard: what the desk looks like right now, as the person looking at it.

Every number comes from campus.py called AS the logged-in user, so the scope,
masking and audit rules that bind the chat bind the dashboard too. A student
sees their deadlines, grades and requests; a tutor their courses' queue; the
registrar everything, plus the latest denials from the audit log. The payload
goes through _pii.redact on the way out, like every chat message.

    data(user_id) -> {"me", "hero", "tiles", "charts", "tables"}
    PAGE          the HTML; it renders whatever data() returns, nothing role-specific in JS

Served by the chat server at /dashboard (page) and /api/dashboard (data, behind CHAT_SECRET).
"""
from __future__ import annotations

from datetime import date

import campus as C
from _pii import redact

ASSIGN_TITLES = {"1": "A1", "2": "A2", "FINAL": "Final"}


def _short(aid: str) -> str:
    return ASSIGN_TITLES.get(aid.rsplit("-", 1)[-1], aid)


def _days(d: str, today: date) -> int:
    return (date.fromisoformat(d) - today).days


def _when(n: int) -> str:
    return "today" if n == 0 else ("tomorrow" if n == 1 else (f"in {n} days" if n > 0 else f"{-n} days ago"))


def _student(me: dict, today: date) -> dict:
    sid = me["student_id"]
    courses = sorted(me["courses"])
    due = []
    for c in courses:
        for a in C.list_assignments(me["id"], c):
            n = _days(a["your_due"], today)
            if n >= 0:
                due.append({"Assignment": a["title"], "Due": a["your_due"], "When": _when(n),
                            "Extended": "yes" if a["your_due"] != a["due"] else "",
                            "Type": "exam" if a["is_exam"] else "assignment", "_n": n,
                            "_ask": (f"can I get 3 more days on {a['title']}?" if not a["is_exam"]
                                     else f"what are my options if I can't sit the {a['title']}?")})
    due.sort(key=lambda r: r["_n"])
    subs = C.list_submissions(me["id"])
    tickets = C.list_tickets(me["id"], limit=200)
    exts = [a for a in due if a["Extended"]]
    nxt = due[0] if due else None
    return {
        "hero": ({"label": "Next deadline", "value": nxt["When"], "note": f"{nxt['Assignment']} · {nxt['Due']}"}
                 if nxt else {"label": "Next deadline", "value": "none", "note": "nothing due this term"}),
        "tiles": [
            {"label": "Courses this term", "value": len(courses)},
            {"label": "Average grade so far", "value": (round(sum(s["grade"] for s in subs) / len(subs))
                                                        if subs else "–"), "unit": "%" if subs else ""},
            {"label": "Extensions granted", "value": len(exts)},
            {"label": "Open requests", "value": sum(t["status"] in ("open", "pending") for t in tickets)},
        ],
        "charts": [{"id": "grades", "title": "My grades", "sub": "graded work so far, out of 100",
                    "max": 100, "unit": "%",
                    "rows": [{"label": f"{s['course_id']} {_short(s['assignment_id'])}", "value": s["grade"],
                              "detail": (f"{s['late_days']} day(s) late · " if s["late_days"] else "")
                              + s["feedback"]} for s in subs]}],
        "tables": [
            {"title": "Coming up", "columns": ["Assignment", "Due", "When", "Extended", "Type"],
             "rows": due[:8], "ask_label": "Ask"},
            {"title": "My requests", "columns": ["id", "subject", "status"],
             "rows": [dict(t, _ask=f"what's happening with my request {t['id']}?") for t in tickets[:8]],
             "ask_label": "Ask", "empty": "No requests yet."},
        ],
    }


def _staff(me: dict, today: date) -> dict:
    uid = me["id"]
    tickets = C.list_tickets(uid, limit=1000)
    live = [t for t in tickets if t["status"] in ("open", "pending")]
    subs = C.list_submissions(uid, assignment_id=None)
    a1 = [s for s in subs if s["assignment_id"].endswith("-1")]
    cats: dict[str, int] = {}
    for t in live:
        cats[t["category"] or "uncategorised"] = cats.get(t["category"] or "uncategorised", 0) + 1
    by_course: dict[str, list[int]] = {}
    for s in a1:
        by_course.setdefault(s["course_id"], []).append(s["grade"])
    bins = [("0–49", 0, 49), ("50–59", 50, 59), ("60–69", 60, 69), ("70–79", 70, 79), ("80–89", 80, 89),
            ("90–100", 90, 100)]
    upcoming = []
    for c in sorted(me["courses"]):
        for a in C.list_assignments(uid, c):
            n = _days(a["due"], today)
            if 0 <= n <= 45:
                waiting = sum(1 for t in live if t.get("assignment_id") == a["id"] and t["category"] == "extension")
                upcoming.append({"Assignment": a["title"], "Due": a["due"], "When": _when(n),
                                 "Extension requests": waiting, "_n": n,
                                 "_ask": f"show me the open extension tickets for {a['id']}"})
    upcoming.sort(key=lambda r: (r["_n"], r["Assignment"]))
    out = {
        "hero": {"label": "Open tickets", "value": len(live),
                 "note": f"{sum(t['status'] == 'pending' for t in live)} pending · across {len(me['courses'])} course(s)"},
        "tiles": [
            {"label": "Extension requests waiting", "value": sum(t["category"] == "extension" for t in live)},
            {"label": "Need triage (no category)", "value": sum(not t["category"] for t in live)},
            {"label": "A1 average", "value": round(sum(s["grade"] for s in a1) / len(a1)) if a1 else "–",
             "unit": "%" if a1 else ""},
            {"label": "A1 submitted late", "value": (round(100 * sum(s["late_days"] > 0 for s in a1) / len(a1))
                                                     if a1 else "–"), "unit": "%" if a1 else ""},
        ],
        "charts": [
            {"id": "queue", "title": "Open tickets by category", "sub": "open and pending", "unit": "",
             "rows": [{"label": k.replace("_", " "), "value": v} for k, v in
                      sorted(cats.items(), key=lambda kv: (-kv[1], kv[0]))]},
            {"id": "course", "title": "A1 average by course", "sub": "out of 100", "max": 100, "unit": "%",
             "rows": [{"label": c, "value": round(sum(g) / len(g)), "detail": f"{len(g)} submissions"}
                      for c, g in sorted(by_course.items())]},
            {"id": "dist", "title": "A1 grade distribution", "sub": "students per band", "unit": "",
             "ordered": True,
             "rows": [{"label": lab, "value": sum(lo <= s["grade"] <= hi for s in a1)} for lab, lo, hi in bins]},
        ],
        "tables": [
            {"title": "Queue", "columns": ["id", "course_id", "subject", "category", "priority", "status"],
             "rows": [dict(t, _ask=f"what is ticket {t['id']} asking for?") for t in live[:12]],
             "ask_label": "Ask the desk", "empty": "Queue is clear.", "wide": True},
            {"title": "Deadlines in the next 45 days", "columns": ["Assignment", "Due", "When", "Extension requests"],
             "rows": upcoming[:10], "ask_label": "Ask", "empty": "Nothing due."},
        ],
    }
    if me["role"] == "registrar":
        denials = [x for x in C.read_audit(uid, limit=500) if not x["allowed"]][-8:][::-1]
        out["tables"].append({"title": "Recent denials (audit log)", "columns": ["ts", "user", "tool", "reason"],
                              "rows": denials, "empty": "No denials."})
    return out


def data(user_id: str, today: date | None = None) -> dict:
    today = today or date.today()
    me = C.whoami(user_id)
    body = _student(me, today) if me["role"] == "student" else _staff(me, today)
    body["me"] = {k: me.get(k) for k in ("id", "name", "role", "title")}
    body["today"] = today.isoformat()
    return redact(body)


PAGE = r"""<!doctype html><html><head><meta charset="utf-8"><title>Northfield · dashboard</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
.viz-root{color-scheme:light;--page:#f9f9f7;--surface-1:#fcfcfb;--ink:#0b0b0b;--ink-2:#52514e;--muted:#898781;
  --grid:#e1e0d9;--axis:#c3c2b7;--ring:rgba(11,11,11,.10);--series-1:#2a78d6;--series-1-hover:#1c5cab;--accent-bg:#cde2fb}
@media (prefers-color-scheme:dark){:root:where(:not([data-theme="light"])) .viz-root{color-scheme:dark;--page:#0d0d0d;
  --surface-1:#1a1a19;--ink:#f0efec;--ink-2:#c3c2b7;--muted:#898781;--grid:#2c2c2a;--axis:#383835;
  --ring:rgba(255,255,255,.10);--series-1:#3987e5;--series-1-hover:#86b6ef;--accent-bg:#184f95}}
:root[data-theme="dark"] .viz-root{color-scheme:dark;--page:#0d0d0d;--surface-1:#1a1a19;--ink:#f0efec;--ink-2:#c3c2b7;
  --muted:#898781;--grid:#2c2c2a;--axis:#383835;--ring:rgba(255,255,255,.10);--series-1:#3987e5;--series-1-hover:#86b6ef;--accent-bg:#184f95}
*{box-sizing:border-box}
body{margin:0}
.viz-root{min-height:100vh;background:var(--page);color:var(--ink);font:14px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif}
.wrap{max-width:1180px;margin:0 auto;padding:28px 20px 60px}
header{display:flex;align-items:flex-end;justify-content:space-between;gap:16px;flex-wrap:wrap;margin-bottom:20px}
h1{font-size:20px;margin:0;font-weight:600}.who{color:var(--ink-2);margin:2px 0 0}
nav a,button.link{color:var(--ink-2);font:inherit;background:none;border:1px solid var(--ring);border-radius:8px;padding:6px 12px;
  text-decoration:none;cursor:pointer}
nav a:hover,button.link:hover{color:var(--ink);border-color:var(--axis)}
.card{background:var(--surface-1);border:1px solid var(--ring);border-radius:12px;padding:18px 20px}
.top{display:grid;grid-template-columns:minmax(260px,1.2fr) repeat(4,minmax(150px,1fr));gap:12px;margin-bottom:12px}
.hero .v{font-size:52px;font-weight:600;line-height:1.05;margin:6px 0 4px}
.lbl{color:var(--ink-2);font-size:13px}.note{color:var(--muted);font-size:13px}
.tile .v{font-size:28px;font-weight:600;margin-top:6px}
.tile .v small{font-size:16px;color:var(--ink-2);font-weight:500;margin-left:1px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(330px,1fr));gap:12px;margin-bottom:12px}
.chead{display:flex;justify-content:space-between;align-items:baseline;gap:8px;margin-bottom:12px}
h2{font-size:15px;margin:0;font-weight:600}
.bars{position:relative}
.row{display:grid;grid-template-columns:96px 1fr;align-items:center;gap:10px;height:30px;position:relative}
.row .k{color:var(--ink-2);font-size:13px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;text-align:right}
.track{position:relative;height:100%;display:flex;align-items:center;outline:none}
.bar{height:14px;background:var(--series-1);border-radius:0 4px 4px 0;min-width:2px;transition:background .12s}
.track:hover .bar,.track:focus-visible .bar{background:var(--series-1-hover)}
.track:focus-visible{box-shadow:0 0 0 2px var(--series-1) inset;border-radius:4px}
.end{margin-left:8px;color:var(--ink-2);font-size:12px;font-variant-numeric:tabular-nums}
.gridlines{position:absolute;top:0;bottom:22px;left:106px;right:0;pointer-events:none}
.gridlines i{position:absolute;top:0;bottom:0;width:1px;background:var(--grid)}
.gridlines i:first-child{background:var(--axis)}
.ticks{position:relative;height:22px;margin-left:106px;color:var(--muted);font-size:11px;font-variant-numeric:tabular-nums}
.ticks span{position:absolute;top:4px;transform:translateX(-50%)}
.tip{position:fixed;pointer-events:none;background:var(--surface-1);color:var(--ink);border:1px solid var(--ring);border-radius:8px;
  padding:8px 10px;font-size:12px;box-shadow:0 4px 16px rgba(0,0,0,.12);max-width:260px;display:none;z-index:9}
.tip strong{display:block;font-size:14px}.tip .d{color:var(--ink-2)}
table{width:100%;border-collapse:collapse;font-size:13px}
th{text-align:left;color:var(--muted);font-weight:500;padding:6px 8px;border-bottom:1px solid var(--axis)}
td{padding:7px 8px;border-bottom:1px solid var(--grid);vertical-align:top}
td.num{font-variant-numeric:tabular-nums}
tr:last-child td{border-bottom:none}
.tables{display:grid;grid-template-columns:repeat(auto-fit,minmax(460px,1fr));gap:12px}
.pill{display:inline-block;padding:1px 8px;border-radius:999px;border:1px solid var(--ring);color:var(--ink-2);font-size:12px}
a.ask{color:var(--series-1);text-decoration:none;white-space:nowrap}a.ask:hover{text-decoration:underline}
.empty{color:var(--muted);padding:8px 0}
td.nw{white-space:nowrap}.scroll{overflow-x:auto}.wide{grid-column:1/-1}
.err{color:#d03b3b}
@media (max-width:900px){.top{grid-template-columns:1fr 1fr}.hero{grid-column:1/-1}.tables{grid-template-columns:1fr}}
</style></head><body><div class="viz-root"><div class="wrap">
<header><div><h1 id="title">Northfield Help Desk</h1><p class="who" id="who">loading…</p></div>
<nav><a href="/">Open the chat</a> <button class="link" id="refresh">Refresh</button> <button class="link" id="theme">Theme</button></nav></header>
<div id="app"></div></div><div class="tip" id="tip" role="tooltip"></div></div>
<script>
const qs=new URLSearchParams(location.search);const urlKey=qs.get('k')||'';
if(urlKey){localStorage.setItem('chatSecret',urlKey);history.replaceState(null,'',location.pathname)}
const key=urlKey||localStorage.getItem('chatSecret')||'';
if(qs.get('theme'))document.documentElement.dataset.theme=qs.get('theme');
const $=(t,cls,txt)=>{const e=document.createElement(t);if(cls)e.className=cls;if(txt!==undefined)e.textContent=txt;return e};
const tip=document.getElementById('tip');
function showTip(e,value,label,detail){tip.replaceChildren();const s=$('strong','',value);tip.append(s,$('div','',label));
  if(detail)tip.append($('div','d',detail));tip.style.display='block';const r=(e.currentTarget||e.target).getBoundingClientRect();
  const x=e.clientX||r.left+r.width/2,y=e.clientY||r.top;tip.style.left=Math.min(x+14,innerWidth-270)+'px';tip.style.top=(y+14)+'px'}
function hideTip(){tip.style.display='none'}
function scale(max,ints){if(max<=0)max=1;const raw=max/4;const p=Math.pow(10,Math.floor(Math.log10(raw)));
  let step=[1,2,2.5,5,10].map(m=>m*p).find(s=>s>=raw);if(ints)step=Math.max(1,Math.ceil(step));
  let top=Math.ceil(max/step)*step;if(top-max<step*0.25)top+=step;  /* headroom: the peak's label never hits the edge */const ticks=[];for(let v=0;v<=top+1e-9;v+=step)ticks.push(+v.toFixed(2));return{top,ticks}}
const HEAD={id:'Ticket',course_id:'Course',subject:'Subject',category:'Category',priority:'Priority',status:'Status',
  ts:'When',user:'User',tool:'Tool',reason:'Reason',label:'',value:'Value',detail:'Detail'};
function tile(t,hero){const c=$('div','card '+(hero?'hero':'tile'));c.append($('div','lbl',t.label));const v=$('div','v',String(t.value));
  if(t.unit){v.append($('small','',t.unit))}c.append(v);if(t.note)c.append($('div','note',t.note));return c}
function chart(ch){
  const c=$('div','card');const head=$('div','chead');const h=$('div');h.append($('h2','',ch.title),$('div','note',ch.sub||''));
  const tog=$('button','link','Table');tog.setAttribute('aria-pressed','false');head.append(h,tog);c.append(head);
  if(!ch.rows.length){c.append($('div','empty','No data in your scope yet.'));return c}
  const vals=ch.rows.map(r=>r.value);const sc=ch.max?{top:ch.max,ticks:[0,25,50,75,100]}:scale(Math.max(...vals),vals.every(Number.isInteger));
  const max=sc.top;const peak=Math.max(...vals);
  const plot=$('div','bars');const gl=$('div','gridlines');const ticks=$('div','ticks');
  sc.ticks.forEach(v=>{const f=v/max;const i=$('i');i.style.left=(f*100)+'%';gl.append(i);const s=$('span','',String(v));s.style.left=(f*100)+'%';ticks.append(s)});
  plot.append(gl);
  for(const r of ch.rows){const row=$('div','row');row.append($('div','k',r.label));const tr=$('div','track');tr.tabIndex=0;
    const val=r.value+(ch.unit||'');tr.setAttribute('aria-label',r.label+': '+val);
    const b=$('div','bar');b.style.width=Math.max(0.4,100*r.value/max)+'%';tr.append(b);
    if(r.value===peak)tr.append($('span','end',val));       // label the extreme only; tooltip + table carry the rest
    const on=e=>showTip(e,val,r.label,r.detail);tr.addEventListener('pointermove',on);tr.addEventListener('focus',on);
    tr.addEventListener('pointerleave',hideTip);tr.addEventListener('blur',hideTip);row.append(tr);plot.append(row)}
  plot.append(ticks);
  const tbl=table({columns:['label','value'],rows:ch.rows.map(r=>({label:r.label,value:r.value+(ch.unit||''),detail:r.detail||''}))},['label','value','detail']);
  tbl.hidden=true;c.append(plot,tbl);
  tog.onclick=()=>{const t=!tbl.hidden;tbl.hidden=t;plot.hidden=!t;tog.textContent=t?'Table':'Chart';tog.setAttribute('aria-pressed',String(!t))};
  return c}
function table(t,cols){cols=cols||t.columns;const tb=$('table');const hr=$('tr');cols.forEach(k=>hr.append($('th','',k in HEAD?HEAD[k]:k)));
  if(t.ask_label)hr.append($('th','',''));tb.append(hr);
  for(const r of t.rows){const tr=$('tr');cols.forEach(k=>{const v=r[k]==null?'':String(r[k]);const td=$('td',(typeof r[k]==='number'?'num ':'')+(['id','course_id','Due','When','ts','user','tool'].includes(k)?'nw':''));
      if(k==='status'||k==='priority'||k==='category'){if(v)td.append($('span','pill',v.replace('_',' ')))}else td.textContent=v;tr.append(td)});
    if(t.ask_label){const td=$('td');if(r._ask){const a=$('a','ask',t.ask_label+' →');a.href='/?q='+encodeURIComponent(r._ask);td.append(a)}tr.append(td)}
    tb.append(tr)}
  return tb}
function render(d){
  document.getElementById('title').textContent='Northfield Help Desk · dashboard';
  document.getElementById('who').textContent=d.me.name+' · '+d.me.title+' · as of '+d.today;
  const app=document.getElementById('app');app.replaceChildren();
  const top=$('div','top');top.append(tile(d.hero,true));d.tiles.forEach(t=>top.append(tile(t)));app.append(top);
  const g=$('div','grid');d.charts.forEach(ch=>g.append(chart(ch)));app.append(g);
  const ts=$('div','tables');for(const t of d.tables){const c=$('div','card');c.append($('h2','',t.title));c.lastChild.style.marginBottom='10px';
    if(t.wide)c.classList.add('wide');const sc=$('div','scroll');sc.append(t.rows.length?table(t):$('div','empty',t.empty||'Nothing here.'));
    c.append(sc);ts.append(c)}app.append(ts)}
async function load(){const r=await fetch('/api/dashboard',{headers:{'X-Chat-Secret':key}});
  if(!r.ok){document.getElementById('who').replaceChildren($('span','err','server said '+r.status+': '+(await r.text()).slice(0,160)));return}
  render(await r.json())}
document.getElementById('refresh').onclick=load;
document.getElementById('theme').onclick=()=>{const cur=document.documentElement.dataset.theme||(matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light');
  document.documentElement.dataset.theme=cur==='dark'?'light':'dark'};
load();
</script></body></html>"""
