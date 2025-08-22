#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pablo L0 Flask Viewer

• One-file Flask app that reads your existing SQLite (l0.sqlite3)
• Renders lemmas alphabetically; click a lemma to see a collapsible JSON-shaped tree
• The JSON mirrors your original structure: lemma → entries (variant, pronunciation, pos blocks)

Run:
  pip install flask
  DB_PATH=/absolute/path/to/l0.sqlite3 python app.py   # or place l0.sqlite3 next to this file
Then open: http://127.0.0.1:5000
"""

import os
import json
import sqlite3
from flask import Flask, request, jsonify, abort, Response
from markupsafe import escape
import threading
DB_PATH = os.environ.get("DB_PATH", os.path.abspath(os.path.join(os.path.dirname(__file__), "l0.sqlite3")))
PAGE_SIZE_DEFAULT = 50
PAGE_SIZE_MAX = 200

app = Flask(__name__)

# -------------------------------
# DB helpers
# -------------------------------

def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn

VIEW_SQL = r"""
CREATE VIEW IF NOT EXISTS v_lemma_tree_json AS
SELECT
  l.lemma,
  (
    SELECT json_object(
      'lemma', l.lemma,

      'variants', COALESCE((
        SELECT json_group_array(vv.variant)
        FROM (
          SELECT v.variant
          FROM VARIANT v
          WHERE v.lemma_id = l.lemma_id
          GROUP BY v.variant
          ORDER BY v.variant COLLATE NOCASE
        ) AS vv
      ), '[]'),

      'entries', COALESCE((
        SELECT json_group_array(
          json_object(
            'word', v.variant,

            'pronunciation', COALESCE((
              SELECT json_group_array(pv.p_val)
              FROM (
                SELECT
                  CASE
                    WHEN p.ipa IS NOT NULL THEN p.ipa
                    WHEN p.audio_ref IS NOT NULL THEN p.audio_ref
                    WHEN p.dialect IS NOT NULL THEN p.dialect
                  END AS p_val
                FROM PRONUNCIATION p
                WHERE p.variant_id = v.variant_id
                  AND (p.ipa IS NOT NULL OR p.audio_ref IS NOT NULL OR p.dialect IS NOT NULL)
                ORDER BY p.pron_id
              ) AS pv
            ), '[]'),

            'pos', COALESCE((
              SELECT json_group_object(
                       g.pos_tag,
                       json(g.entries_json)
                     )
              FROM (
                SELECT
                  pe.pos_tag,
                  (
                    SELECT json_group_array(json(pe2.pos_meta_json))
                    FROM POS_ENTRY pe2
                    WHERE pe2.variant_id = v.variant_id
                      AND pe2.pos_tag    = pe.pos_tag
                      AND pe2.pos_meta_json IS NOT NULL
                      AND json_valid(pe2.pos_meta_json) = 1
                    ORDER BY pe2.pos_id
                  ) AS entries_json
                FROM POS_ENTRY pe
                WHERE pe.variant_id = v.variant_id
                GROUP BY pe.pos_tag
                ORDER BY pe.pos_tag
              ) AS g
            ), json('{}'))
          )
        )
        FROM VARIANT v
        WHERE v.lemma_id = l.lemma_id
        ORDER BY v.variant COLLATE NOCASE
      ), '[]')
    )
  ) AS json
FROM LEMMA l;
"""


def ensure_view():
    conn = get_conn()
    try:
        conn.executescript(VIEW_SQL)
    finally:
        conn.close()

# ---------- JSON doc builder (Python composes nested objects so POS entries are real objects, not strings)

def build_lemma_tree(conn, lemma: str):
    cur = conn.cursor()
    row = cur.execute(
        "SELECT lemma_id, lemma FROM LEMMA WHERE lemma = ? COLLATE NOCASE LIMIT 1;",
        (lemma,)
    ).fetchone()
    if not row:
        return None

    lemma_id = row["lemma_id"]
    lemma_cased = row["lemma"]

    # Variants (ids + names)
    vrows = cur.execute(
        "SELECT variant_id, variant FROM VARIANT WHERE lemma_id=? ORDER BY variant COLLATE NOCASE;",
        (lemma_id,)
    ).fetchall()

    variants = [vr["variant"] for vr in vrows]
    entries = []

    for vr in vrows:
        vid = vr["variant_id"]
        vname = vr["variant"]

        # Pronunciations: prefer IPA, then audio_ref, then dialect
        pr = cur.execute(
            "SELECT ipa, audio_ref, dialect FROM PRONUNCIATION WHERE variant_id=? ORDER BY pron_id;",
            (vid,)
        ).fetchall()
        prons = []
        for p in pr:
            if p["ipa"]:
                prons.append(p["ipa"])
            elif p["audio_ref"]:
                prons.append(p["audio_ref"])
            elif p["dialect"]:
                prons.append(p["dialect"])

        # POS blocks: group by pos_tag, parse each JSON text to a Python dict
        pos_rows = cur.execute(
            "SELECT pos_tag, pos_meta_json FROM POS_ENTRY WHERE variant_id=? AND json_valid(pos_meta_json)=1 ORDER BY pos_id;",
            (vid,)
        ).fetchall()
        pos_map = {}
        for r in pos_rows:
            try:
                obj = json.loads(r["pos_meta_json"])  # real object
            except Exception:
                continue
            pos_map.setdefault(r["pos_tag"], []).append(obj)

        entries.append({
            "word": vname,
            "pronunciation": prons,
            "pos": pos_map,
        })

    return {"lemma": lemma_cased, "variants": variants, "entries": entries}


# Lazy init for Flask ≥3.0 (before_first_request was removed)
_ready = False
_ready_lock = threading.Lock()

def init_once():
    global _ready
    if _ready:
        return
    with _ready_lock:
        if _ready:
            return
        if not os.path.exists(DB_PATH):
            raise RuntimeError(f"SQLite DB not found at {DB_PATH}. Set DB_PATH env var or place l0.sqlite3 next to app.py")
        ensure_view()
        _ready = True

@app.before_request
def _ensure_ready():
    init_once()

# -------------------------------
# API
# -------------------------------

@app.get('/api/lemmas')
def api_lemmas():
    q = request.args.get('q', '').strip()
    page = max(1, int(request.args.get('page', '1') or 1))
    page_size = min(PAGE_SIZE_MAX, max(1, int(request.args.get('page_size', PAGE_SIZE_DEFAULT))))
    offset = (page - 1) * page_size

    like = f"{q}%" if q else "%"

    conn = get_conn()
    try:
        total = conn.execute(
            "SELECT COUNT(*) AS c FROM LEMMA WHERE lemma LIKE ? COLLATE NOCASE;",
            (like,)
        ).fetchone()[0]
        rows = conn.execute(
            """
            SELECT lemma
            FROM LEMMA
            WHERE lemma LIKE ? COLLATE NOCASE
            ORDER BY lemma COLLATE NOCASE
            LIMIT ? OFFSET ?;
            """,
            (like, page_size, offset)
        ).fetchall()
    finally:
        conn.close()

    return jsonify({
        "query": q,
        "page": page,
        "page_size": page_size,
        "total": total,
        "items": [r[0] for r in rows],
    })


@app.get('/api/lemma')
def api_lemma_query():
    lemma = request.args.get('lemma')
    if not lemma:
        abort(400, description="Missing ?lemma=")
    return _fetch_lemma_json(lemma)


@app.get('/api/lemma/<path:lemma>')
def api_lemma_path(lemma: str):
    return _fetch_lemma_json(lemma)


def _fetch_lemma_json(lemma: str):
    conn = get_conn()
    try:
        doc = build_lemma_tree(conn, lemma)
    finally:
        conn.close()
    if doc is None:
        abort(404, description=f"Lemma not found: {lemma}")
    return jsonify(doc)


# -------------------------------
# UI (single page)
# -------------------------------
INDEX_HTML = r"""
<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Pablo L0 Viewer</title>
  <style>
    :root {
      --bg: #0b1020; --panel: #101830; --text: #e9eef9; --muted: #9fb0d3; --accent: #86b7ff; --chip: #1b2547; --border: #223159;
    }
    * { box-sizing: border-box; }
    body { margin:0; background:var(--bg); color:var(--text); font: 15px/1.4 system-ui, -apple-system, Segoe UI, Roboto, Ubuntu, Cantarell, Noto Sans, sans-serif; }
    header { padding: 16px; border-bottom: 1px solid var(--border); background: linear-gradient(180deg, rgba(255,255,255,.04), rgba(0,0,0,0)); position: sticky; top: 0; z-index: 5; }
    .container { display:grid; grid-template-columns: 360px 1fr; gap: 16px; padding: 16px; height: calc(100vh - 64px); }
    .panel { background: var(--panel); border: 1px solid var(--border); border-radius: 14px; overflow: hidden; display:flex; flex-direction: column; min-height: 0; }
    .panel header { padding: 12px 12px; border-bottom: 1px solid var(--border); background: rgba(255,255,255,.02); position: static; }
    .panel .body { padding: 12px; overflow: auto; }
    input[type="search"]{ width:100%; padding:10px 12px; border-radius:10px; border:1px solid var(--border); background:#0c142c; color:var(--text); outline:none; }
    .lemmas { list-style:none; margin:0; padding:0; }
    .lemmas li { padding:8px 10px; cursor:pointer; border-radius:8px; }
    .lemmas li:hover { background:#0d1631; }
    .lemmas li.active { background:#0e1b3c; border:1px solid var(--border); }
    .row { display:flex; gap:8px; align-items:center; }
    .muted{ color:var(--muted); }
    .pill{ display:inline-block; padding:2px 8px; border-radius:999px; background:var(--chip); border:1px solid var(--border); font-size:12px; color:var(--muted); }
    details { padding-left: 12px; border-left: 2px solid rgba(134,183,255,.18); margin: 6px 0; }
    summary { cursor:pointer; user-select:none; padding: 4px 6px; border-radius: 6px; }
    summary:hover { background: rgba(134,183,255,.08); }
    code, pre { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace; font-size: 12.5px; }
    .kv { display:flex; gap:6px; padding:2px 0; }
    .k { color: var(--muted); }
    .v.string { color:#a3e7a8; }
    .v.number { color:#ffd080; }
    .v.boolean { color:#f2a2ea; }
    .v.null { color:#7aa7ff; opacity:.8; }
    .toolbar{ display:flex; gap:10px; align-items:center; }
    .btn { background:#0e1b3c; border:1px solid var(--border); color:var(--text); padding:6px 10px; border-radius:8px; cursor:pointer; }
    .btn:hover{ background:#132350; }
    .right { text-align:right; }
    .footer { padding: 8px 12px; border-top:1px solid var(--border); color:var(--muted); font-size:12px; }
  </style>
</head>
<body>
  <header>
    <div class="row">
      <h2 style="margin:0">Pablo L0 Viewer</h2>
      <span class="pill">SQLite: <span id="dbpath">{{ db_path }}</span></span>
    </div>
  </header>
  <div class="container">
    <section class="panel">
      <header>
        <div class="row">
          <input type="search" id="q" placeholder="Search lemmas (prefix)…" oninput="debouncedLoad()" />
          <button class="btn" onclick="loadLemmas()">Search</button>
        </div>
      </header>
      <div class="body" id="lemmas"></div>
      <div class="footer" id="pager"></div>
    </section>

    <section class="panel">
      <header>
        <div class="row" style="justify-content: space-between; width:100%">
          <div><strong id="currentLemma">Select a lemma →</strong></div>
          <div class="right">
            <button class="btn" onclick="toggleAll(true)">Expand all</button>
            <button class="btn" onclick="toggleAll(false)">Collapse all</button>
            <button class="btn" onclick="downloadJson()">Download JSON</button>
          </div>
        </div>
      </header>
      <div class="body">
        <div id="tree"></div>
      </div>
    </section>
  </div>

  <script>
    let page = 1, pageSize = 50, total = 0, current = null, debounceTimer = null, lemmasCache = []; let lastQuery='';

    function debouncedLoad(){
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(() => { page = 1; loadLemmas(); }, 200);
    }

    async function loadLemmas(){
      const q = document.getElementById('q').value.trim(); lastQuery = q;
      const url = new URL('/api/lemmas', window.location.origin);
      url.searchParams.set('q', q);
      url.searchParams.set('page', page);
      url.searchParams.set('page_size', pageSize);
      let data;
      try {
        const res = await fetch(url);
        if(!res.ok){
          const text = await res.text();
          document.getElementById('lemmas').innerHTML = `<div class="muted">Error loading lemmas: ${escapeHtml(text)}</div>`;
          return;
        }
        data = await res.json();
      } catch(e){
        document.getElementById('lemmas').innerHTML = `<div class="muted">Network error: ${escapeHtml(String(e))}</div>`;
        return;
      }
      total = data.total || 0; page = data.page || 1; pageSize = data.page_size || 50; lemmasCache = Array.isArray(data.items)? data.items : [];
      renderLemmaList();
    }

    function renderLemmaList(){
      const root = document.getElementById('lemmas');
      root.innerHTML = '';
      if(!Array.isArray(lemmasCache)){
        root.innerHTML = `<div class="muted">Bad response: items is not an array.</div>`;
        return;
      }
      if(lemmasCache.length === 0){
        const matchText = lastQuery ? (' matching "' + escapeHtml(lastQuery) + '"') : '';
        root.innerHTML = '<div class="muted">No lemmas' + matchText + '.</div>';
        renderPager();
        return;
      }
      const ul = document.createElement('ul'); ul.className = 'lemmas';
      lemmasCache.forEach(lem => {
        const li = document.createElement('li');
        li.textContent = lem;
        li.onclick = () => selectLemma(lem, li);
        if(current === lem) li.classList.add('active');
        ul.appendChild(li);
      });
      root.appendChild(ul);
      renderPager();
    }

    function renderPager(){
      const p = document.getElementById('pager');
      const pages = Math.max(1, Math.ceil(total / pageSize));
      p.innerHTML = '';
      const info = document.createElement('span'); info.className = 'muted'; info.textContent = `${total} lemmas · Page ${page}/${pages}`;
      const right = document.createElement('span'); right.style.float = 'right';
      const prev = document.createElement('button'); prev.className = 'btn'; prev.textContent = 'Prev'; prev.disabled = page <= 1; prev.onclick = () => { page = Math.max(1, page-1); loadLemmas(); };
      const next = document.createElement('button'); next.className = 'btn'; next.textContent = 'Next'; next.disabled = page >= pages; next.onclick = () => { page = Math.min(pages, page+1); loadLemmas(); };
      right.appendChild(prev); right.appendChild(next);
      p.appendChild(info); p.appendChild(right);
    }

    async function selectLemma(lemma, li){
      current = lemma;
      document.querySelectorAll('.lemmas li').forEach(x=>x.classList.remove('active'));
      if(li) li.classList.add('active');
      document.getElementById('currentLemma').textContent = lemma;
      const url = new URL('/api/lemma', window.location.origin);
      url.searchParams.set('lemma', lemma);
      let res; try { res = await fetch(url); } catch(e){ document.getElementById('tree').textContent = `Network error: ${e}`; return; }
      if(!res.ok){ document.getElementById('tree').textContent = `Not found: ${lemma}`; return; }
      const data = await res.json();
      renderTree(data);
    }

    function renderTree(obj){
      const root = document.getElementById('tree');
      root.innerHTML = '';
      root.appendChild(renderValue(obj, 'root', null));
    }

    // Custom, readable labels + stable key order
    function renderValue(val, key, parentKey){
      if(Array.isArray(val)){
        const det = document.createElement('details'); det.open = true;
        const sum = document.createElement('summary');
        sum.innerHTML = `<strong>${escapeHtml(key)}</strong> <span class="muted">[${val.length}]</span>`;
        det.appendChild(sum);
        val.forEach((v, i) => {
          let label;
          if(parentKey === 'entries' && v && typeof v === 'object' && 'word' in v){
            label = v.word;                          // show variant spelling instead of [0]
          } else if(parentKey === 'definitions'){
            label = `definition_${i}`;               // definition_0
          } else if(parentKey === 'subdefinitions'){
            label = `subdef_${i}`;                   // subdef_0
          } else if(parentKey === 'examples'){
            label = `ex_${i}`;                       // ex_0
          } else {
            label = `[${i}]`;
          }
          const child = renderValue(v, label, key);
          det.appendChild(child);
        });
        return det;
      } else if (val && typeof val === 'object'){
        const det = document.createElement('details'); det.open = true;
        const sum = document.createElement('summary');
        sum.innerHTML = `<strong>${escapeHtml(key)}</strong>`;
        det.appendChild(sum);
        const priority = ['definition','dating_raw','forms','labels','label_groups','examples','subdefinitions','synonyms','antonyms'];
        const keys = Object.keys(val).sort((a,b)=>{
          const ia = priority.indexOf(a), ib = priority.indexOf(b);
          if(ia === -1 && ib === -1) return a.localeCompare(b);
          if(ia === -1) return 1; if(ib === -1) return -1; return ia - ib;
        });
        keys.forEach(k => {
          const child = renderValue(val[k], k, key);
          det.appendChild(child);
        });
        return det;
      } else {
        const row = document.createElement('div'); row.className = 'kv';
        const kEl = document.createElement('span'); kEl.className = 'k'; kEl.textContent = `${key}:`;
        const vEl = document.createElement('span'); vEl.className = 'v ' + valueClass(val); vEl.textContent = formatScalar(val);
        row.appendChild(kEl); row.appendChild(vEl);
        return row;
      }
    }

    function valueClass(v){
      if(v === null) return 'null';
      switch(typeof v){
        case 'string': return 'string';
        case 'number': return 'number';
        case 'boolean': return 'boolean';
        default: return '';
      }
    }
    function formatScalar(v){
      if(v === null) return 'null';
      if(typeof v === 'string') return v;
      if(typeof v === 'number') return String(v);
      if(typeof v === 'boolean') return v ? 'true' : 'false';
      return String(v);
    }
    function escapeHtml(s){
      return String(s).replace(/[&<>\"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;'}[c]));
    }

    function toggleAll(open){
      document.querySelectorAll('#tree details').forEach(d => d.open = open);
    }

    function downloadJson(){
      if(!current) return;
      const url = new URL('/api/lemma', window.location.origin);
      url.searchParams.set('lemma', current);
      fetch(url).then(r=>r.json()).then(data => {
        const blob = new Blob([JSON.stringify(data, null, 2)], {type: 'application/json'});
        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = `${current}.json`;
        a.click();
        URL.revokeObjectURL(a.href);
      });
    }

    // initial load
    window.addEventListener('DOMContentLoaded', () => {
      loadLemmas();
    });
  </script>
</body>
</html>
"""

@app.get('/')
def index():
    html = INDEX_HTML.replace("{{ db_path }}", escape(DB_PATH))
    return Response(html, mimetype='text/html')


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)
