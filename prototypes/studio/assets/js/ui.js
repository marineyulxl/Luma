/* 灵脑 Studio 原型：通用 UI 工具、对话框、Markdown 渲染与页面外壳（侧栏 / 顶栏） */
(function (global) {
  'use strict';
  const L = (global.Luma = global.Luma || {});
  const S = L.Store;
  const doc = global.document;

  const languageKey = 'luma-studio-language';
  const language = global.localStorage.getItem(languageKey) === 'en' ? 'en' : 'zh-CN';
  doc.documentElement.lang = language;
  const t = (zh, en) => language === 'en' ? en : zh;

  /* ---------- DOM 辅助 ---------- */
  function h(tag, attrs) {
    const el = doc.createElement(tag);
    if (attrs) {
      Object.keys(attrs).forEach((k) => {
        const v = attrs[k];
        if (v === null || v === undefined || v === false) return;
        if (k === 'class') el.className = v;
        else if (k === 'text') el.textContent = v;
        else if (k === 'dataset') Object.assign(el.dataset, v);
        else if (k.slice(0, 2) === 'on' && typeof v === 'function') el.addEventListener(k.slice(2).toLowerCase(), v);
        else if (v === true) el.setAttribute(k, '');
        else el.setAttribute(k, String(v));
      });
    }
    for (let i = 2; i < arguments.length; i += 1) append(el, arguments[i]);
    return el;
  }
  function append(el, child) {
    if (child === null || child === undefined || child === false) return;
    if (Array.isArray(child)) child.forEach((c) => append(el, c));
    else if (child instanceof global.Node) el.appendChild(child);
    else el.appendChild(doc.createTextNode(String(child)));
  }
  const I = (name, size, cls) => L.icon(name, size, cls);
  function clear(el) { while (el.firstChild) el.removeChild(el.firstChild); return el; }
  function debounce(fn, ms) { let t; const d = function () { const a = arguments; clearTimeout(t); t = setTimeout(() => fn.apply(null, a), ms); }; d.cancel = () => clearTimeout(t); return d; }
  function qs(name) { return new URLSearchParams(global.location.search).get(name) || ''; }
  function selectEl(options, value, attrs) {
    const sel = h('select', attrs);
    options.forEach((o) => { const opt = h('option', { value: o.value, text: o.label }); if (o.disabled) opt.disabled = true; if (o.value === value) opt.selected = true; sel.appendChild(opt); });
    return sel;
  }
  function downloadText(filename, text, mime) {
    const url = global.URL.createObjectURL(new global.Blob([text], { type: mime || 'text/plain;charset=utf-8' }));
    const a = h('a', { href: url, download: filename }); doc.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => global.URL.revokeObjectURL(url), 1000);
  }

  /* ---------- 时间 ---------- */
  const pad = (n) => String(n).padStart(2, '0');
  function fmtTime(iso) {
    const d = new Date(iso); const now = new Date();
    const day = (x) => new Date(x.getFullYear(), x.getMonth(), x.getDate()).getTime();
    const diff = Math.round((day(now) - day(d)) / 86400000);
    const hm = pad(d.getHours()) + ':' + pad(d.getMinutes());
    if (diff === 0) return '今天 ' + hm;
    if (diff === 1) return '昨天 ' + hm;
    if (d.getFullYear() === now.getFullYear()) return (d.getMonth() + 1) + '月' + d.getDate() + '日 ' + hm;
    return d.getFullYear() + '年' + (d.getMonth() + 1) + '月' + d.getDate() + '日';
  }
  function fmtDateLong(d) { if (language === "en") return new Intl.DateTimeFormat("en", { dateStyle: "full" }).format(d); return d.getFullYear() + '年' + (d.getMonth() + 1) + '月' + d.getDate() + '日　星期' + '日一二三四五六'[d.getDay()]; }
  function fmtStamp(d) { return d.getFullYear() + pad(d.getMonth() + 1) + pad(d.getDate()) + '-' + pad(d.getHours()) + pad(d.getMinutes()); }
  function fmtSize(n) { return n < 1024 ? n + ' B' : n < 1048576 ? (n / 1024).toFixed(1) + ' KB' : (n / 1048576).toFixed(1) + ' MB'; }

  /* ---------- 文本：纯文本预览 / 高亮 ---------- */
  function stripMd(src) {
    return (src || '').replace(/```[\s\S]*?```/g, ' ').replace(/^#{1,3}\s+/gm, '').replace(/^>\s?/gm, '').replace(/^\s*([-*]|\d+\.)\s+/gm, '')
      .replace(/\[\[([^\]]+)\]\]/g, '$1').replace(/\[([^\]]+)\]\([^)]+\)/g, '$1').replace(/[*_`~]/g, '').replace(/\s+/g, ' ').trim();
  }
  function highlight(text, q) {
    const frag = doc.createDocumentFragment(); const needle = (q || '').trim().toLowerCase();
    if (!needle) { frag.appendChild(doc.createTextNode(text)); return frag; }
    const low = text.toLowerCase(); let i = 0;
    for (;;) {
      const j = low.indexOf(needle, i);
      if (j < 0) { frag.appendChild(doc.createTextNode(text.slice(i))); break; }
      frag.appendChild(doc.createTextNode(text.slice(i, j)));
      frag.appendChild(h('mark', { text: text.slice(j, j + needle.length) }));
      i = j + needle.length;
    }
    return frag;
  }
  function snippet(body, q, len) {
    const plain = stripMd(body); const size = len || 110; const at = q ? plain.toLowerCase().indexOf(q.trim().toLowerCase()) : -1;
    if (at < 0) return plain.slice(0, size);
    const start = Math.max(0, at - 28);
    return (start > 0 ? '…' : '') + plain.slice(start, start + size);
  }

  /* ---------- Markdown（受控子集；所有文本先转义，再生成标签） ---------- */
  function esc(s) { return String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c])); }
  function inlineMd(raw, wiki) {
    const tokens = []; const stash = (html) => { tokens.push(html); return '\u0001' + (tokens.length - 1) + '\u0001'; };
    let s = raw.replace(/`([^`]+)`/g, (_, c) => stash('<code>' + esc(c) + '</code>'));
    s = s.replace(/\[\[([^\]\n]+)\]\]/g, (_, t) => stash(wiki(t.trim())));
    s = s.replace(/\[([^\]\n]+)\]\(([^)\s]+)\)/g, (m, text, url) => /^(https?:\/\/|mailto:)/i.test(url)
      ? stash('<a href="' + esc(url) + '" target="_blank" rel="noopener noreferrer">' + esc(text) + '</a>') : m);
    s = esc(s).replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>').replace(/~~([^~]+)~~/g, '<del>$1</del>').replace(/\*([^*\s][^*]*)\*/g, '<em>$1</em>');
    return s.replace(/\u0001(\d+)\u0001/g, (_, i) => tokens[Number(i)]);
  }
  function renderMarkdown(src, wikiResolver) {
    const wiki = wikiResolver || ((t) => '<span class="wikilink missing">' + esc(t) + '</span>');
    const lines = String(src || '').replace(/\r\n?/g, '\n').split('\n'); const out = []; let i = 0;
    const isBlock = (l) => /^(#{1,3}\s|>\s?|[-*]\s+|\d+\.\s+|```|---+\s*$)/.test(l);
    while (i < lines.length) {
      const line = lines[i];
      if (/^```/.test(line)) { const buf = []; i += 1; while (i < lines.length && !/^```/.test(lines[i])) { buf.push(lines[i]); i += 1; } i += 1; out.push('<pre><code>' + esc(buf.join('\n')) + '</code></pre>'); continue; }
      const hd = /^(#{1,3})\s+(.*)$/.exec(line);
      if (hd) { out.push('<h' + hd[1].length + '>' + inlineMd(hd[2], wiki) + '</h' + hd[1].length + '>'); i += 1; continue; }
      if (/^---+\s*$/.test(line)) { out.push('<hr>'); i += 1; continue; }
      if (/^>\s?/.test(line)) { const buf = []; while (i < lines.length && /^>\s?/.test(lines[i])) { buf.push(lines[i].replace(/^>\s?/, '')); i += 1; } out.push('<blockquote>' + buf.map((b) => inlineMd(b, wiki)).join('<br>') + '</blockquote>'); continue; }
      if (/^[-*]\s+/.test(line)) { const buf = []; while (i < lines.length && /^[-*]\s+/.test(lines[i])) { buf.push('<li>' + inlineMd(lines[i].replace(/^[-*]\s+/, ''), wiki) + '</li>'); i += 1; } out.push('<ul>' + buf.join('') + '</ul>'); continue; }
      if (/^\d+\.\s+/.test(line)) { const buf = []; while (i < lines.length && /^\d+\.\s+/.test(lines[i])) { buf.push('<li>' + inlineMd(lines[i].replace(/^\d+\.\s+/, ''), wiki) + '</li>'); i += 1; } out.push('<ol>' + buf.join('') + '</ol>'); continue; }
      if (!line.trim()) { i += 1; continue; }
      const para = []; while (i < lines.length && lines[i].trim() && !isBlock(lines[i])) { para.push(inlineMd(lines[i], wiki)); i += 1; }
      out.push('<p>' + para.join('<br>') + '</p>');
    }
    return out.join('');
  }
  /** Studio 内预览：[[标题]] 指向对应内容的编辑页；找不到则显示为未解析。 */
  function studioWiki(title) {
    const t = S.findByTitle(title);
    return t ? '<a class="wikilink" href="editor.html?id=' + esc(t.id) + '">' + esc(title) + '</a>' : '<span class="wikilink missing" title="未找到同名内容">' + esc(title) + '</span>';
  }
  /** 公开预览：仅已发布内容可成为链接，其余只显示为纯文本，不输出私人内容 ID。 */
  function publicWiki(title) {
    const t = S.findByTitle(title);
    return t && t.publish.status === 'published' ? '<span class="wikilink">' + esc(title) + '</span>' : esc(title);
  }

  /* ---------- 提示 ---------- */
  let toastWrap = null;
  function toast(message, kind) {
    if (!toastWrap) { toastWrap = h('div', { class: 'toast-wrap', role: 'status', 'aria-live': 'polite' }); doc.body.appendChild(toastWrap); }
    const el = h('div', { class: 'toast' + (kind === 'error' ? ' error' : '') }, I(kind === 'error' ? 'alert' : 'check', 18), message);
    toastWrap.appendChild(el); setTimeout(() => el.remove(), 3400);
  }

  /* ---------- 对话框 ---------- */
  function dialog(opts) {
    return new Promise((resolve) => {
      const prev = doc.activeElement; const id = 'dlg-' + Math.random().toString(36).slice(2, 7);
      const actions = h('div', { class: 'actions' });
      const box = h('section', { class: 'modal' + (opts.wide ? ' wide' : ''), role: 'dialog', 'aria-modal': 'true', 'aria-labelledby': id },
        h('h2', { id, text: opts.title }), opts.desc ? h('p', { class: 'desc', text: opts.desc }) : null, opts.content || null, actions);
      const back = h('div', { class: 'modal-backdrop' }, box);
      let done = false;
      const close = (value) => { if (done) return; done = true; doc.removeEventListener('keydown', onKey, true); back.remove(); if (prev && prev.focus) prev.focus(); resolve(value); };
      const onKey = (e) => {
        if (e.key === 'Escape') { e.stopPropagation(); close(opts.cancelValue === undefined ? null : opts.cancelValue); }
        if (e.key === 'Tab') {
          const f = box.querySelectorAll('button:not([disabled]), input:not([disabled]), select, textarea, [tabindex="0"]'); if (!f.length) return;
          const first = f[0], last = f[f.length - 1];
          if (e.shiftKey && doc.activeElement === first) { e.preventDefault(); last.focus(); }
          else if (!e.shiftKey && doc.activeElement === last) { e.preventDefault(); first.focus(); }
        }
      };
      (opts.actions || [{ label: '关闭', value: null }]).forEach((a) => {
        const btn = h('button', { class: a.primary ? 'primary' + (a.danger ? ' danger' : '') : 'secondary', type: 'button', text: a.label });
        btn.addEventListener('click', async () => {
          if (a.validate) { const ok = await a.validate(); if (!ok) return; }
          close(a.value === undefined ? true : a.value);
        });
        actions.appendChild(btn);
      });
      back.addEventListener('mousedown', (e) => { if (e.target === back) close(opts.cancelValue === undefined ? null : opts.cancelValue); });
      doc.addEventListener('keydown', onKey, true);
      doc.body.appendChild(back);
      const focusTarget = box.querySelector('input, select, textarea') || actions.querySelector('.primary') || actions.lastChild;
      if (focusTarget) focusTarget.focus();
      if (opts.onOpen) opts.onOpen(box, close);
    });
  }
  function confirmDialog(o) {
    return dialog({ title: o.title, desc: o.desc, content: o.content, wide: o.wide, cancelValue: false, actions: [
      { label: o.cancelText || '取消', value: false },
      { label: o.confirmText || '确认', value: true, primary: true, danger: !!o.danger }] });
  }
  function alertDialog(title, desc, content) { return dialog({ title, desc, content, actions: [{ label: '我知道了', value: true, primary: true }] }); }
  /** 表单对话框：fields = [{name,label,type,value,options,placeholder,help}]；validate(values) 返回错误文案或空串。 */
  function formDialog(o) {
    const inputs = {}; const err = h('p', { class: 'field-error', role: 'alert' });
    const content = h('div', null, o.fields.map((f) => {
      let control;
      if (f.type === 'select') control = selectEl(f.options, f.value || '', { 'aria-label': f.label });
      else if (f.type === 'textarea') control = h('textarea', { class: 'field', rows: 3, placeholder: f.placeholder || '', 'aria-label': f.label }), control.value = f.value || '';
      else control = h('input', { class: 'field', type: 'text', maxlength: 60, placeholder: f.placeholder || '', 'aria-label': f.label, value: f.value || '' });
      inputs[f.name] = control;
      return h('label', { class: 'field-label' }, f.label, control, f.help ? h('span', { class: 'hint', text: f.help }) : null);
    }), err);
    const values = () => { const v = {}; o.fields.forEach((f) => { v[f.name] = inputs[f.name].value; }); return v; };
    return dialog({ title: o.title, desc: o.desc, content, cancelValue: null, actions: [
      { label: '取消', value: null },
      { label: o.confirmText || '确认', primary: true, value: 'ok', validate: () => { const msg = o.validate ? o.validate(values()) : ''; err.textContent = msg || ''; return !msg; } }] })
      .then((r) => (r === 'ok' ? values() : null));
  }

  /* ---------- 未保存修改保护 ---------- */
  const Guard = {
    dirty: false,
    set(v) { Guard.dirty = !!v; },
    init() {
      global.addEventListener('beforeunload', (e) => { if (Guard.dirty) { e.preventDefault(); e.returnValue = ''; } });
      doc.addEventListener('click', async (e) => {
        const a = e.target.closest && e.target.closest('a[href]');
        if (!a || !Guard.dirty || a.target === '_blank' || e.defaultPrevented || a.hasAttribute('download')) return;
        e.preventDefault();
        if (await Guard.confirmLeave()) { Guard.dirty = false; global.location.href = a.href; }
      }, true);
    },
    confirmLeave() { return confirmDialog({ title: '离开前保存修改？', desc: '当前内容尚未保存。你可以继续编辑，或放弃本次修改。', confirmText: '放弃修改', cancelText: '继续编辑', danger: true }); },
    async go(url) { if (!Guard.dirty || await Guard.confirmLeave()) { Guard.dirty = false; global.location.href = url; } }
  };

  /* ---------- 列表组件 ---------- */
  function paginate(list, page, size) { const pages = Math.max(1, Math.ceil(list.length / size)); const p = Math.min(Math.max(1, page), pages); return { items: list.slice((p - 1) * size, p * size), page: p, pages }; }
  function pager(total, page, size, onChange) {
    const pages = Math.ceil(total / size); if (pages <= 1) return h('div');
    const wrap = h('div', { class: 'pager' });
    const btn = (label, p, disabled, selected) => h('button', { type: 'button', class: selected ? 'selected' : '', disabled, 'aria-label': '第 ' + p + ' 页', 'aria-current': selected ? 'page' : null, text: label, onclick: () => onChange(p) });
    wrap.appendChild(btn('‹', page - 1, page <= 1, false));
    for (let p = 1; p <= pages; p += 1) wrap.appendChild(btn(String(p), p, false, p === page));
    wrap.appendChild(btn('›', page + 1, page >= pages, false));
    return wrap;
  }
  function publishPill(c) {
    if (c.publish.status === 'published') return h('span', { class: 'pill ok', text: '已发布' });
    if (c.publish.status === 'withdrawn') return h('span', { class: 'pill warn', text: '已撤回' });
    return null;
  }
  function contentMeta(c) {
    const place = c.spaceId ? (S.getSpace(c.spaceId) ? S.getSpace(c.spaceId).name : '') + (c.categoryId ? ' / ' + S.categoryPath(c.categoryId) : '') : '';
    const tags = c.tagIds.map((id) => S.getTag(id)).filter(Boolean);
    return h('small', null, c.type, place ? '· ' + place : null, c.organize === 'archived' ? h('span', { class: 'pill mute', text: '已归档' }) : null, publishPill(c), tags.map((t) => h('span', { class: 'pill', text: '#' + t.name })));
  }
  /** 内容行：整行是链接，打开内容编辑页。opts.query 用于高亮；opts.actions 为右侧操作节点。 */
  function noteRow(c, opts) {
    const o = opts || {};
    const title = c.title || '（无标题）';
    return h('div', { class: 'note-row' },
      I('file', 22),
      h('div', { class: 'body' },
        h('strong', null, o.query ? highlight(title, o.query) : title),
        h('p', null, o.query ? highlight(snippet(c.body, o.query), o.query) : stripMd(c.body).slice(0, 140)),
        contentMeta(c)),
      h('time', { text: fmtTime(c.updatedAt) }),
      o.actions ? h('div', { class: 'row-actions' }, o.actions) : null,
      h('a', { href: 'editor.html?id=' + encodeURIComponent(c.id), 'aria-label': '打开：' + title, style: 'position:absolute;inset:0;z-index:0' }));
  }
  function rowAction(iconName, label, handler) {
    const b = h('button', { class: 'icon-button', type: 'button', title: label, 'aria-label': label, style: 'position:relative;z-index:1' }, I(iconName, 19));
    b.addEventListener('click', (e) => { e.preventDefault(); e.stopPropagation(); handler(e); });
    return b;
  }
  function emptyState(iconName, title, text, actionNode) {
    return h('div', { class: 'empty' }, I(iconName, 42), h('h2', { text: title }), h('p', { text }), actionNode || null);
  }

  /* ---------- 页面外壳 ---------- */
  const NAV = [
    { key: 'home', label: t('首页', 'Home'), icon: 'home', href: 'index.html' },
    { key: 'inbox', label: t('收集箱', 'Inbox'), icon: 'inbox', href: 'inbox.html' },
    { key: 'spaces', label: t('知识空间', 'Spaces'), icon: 'layers', href: 'spaces.html' },
    { key: 'threads', label: t('思考脉络', 'Thought threads'), icon: 'link', href: 'threads.html' },
    { key: 'imports', label: t('导入中心', 'Imports'), icon: 'download', href: 'imports.html' },
    { key: 'learning', label: t('学习中心', 'Learning'), icon: 'book', href: 'learning.html' }
  ];
  const EXPAND_KEY = 'luma-studio-proto-expanded-v1';
  const Shell = {
    ctx: null, sidebarEl: null, mainEl: null, topEl: null,
    mount(cfg) {
      if (!L.Auth.isLoggedIn()) { global.location.replace('login.html?next=' + encodeURIComponent(global.location.pathname.split('/').pop() + global.location.search)); return null; }
      Shell.ctx = cfg; Guard.init();
      const root = doc.getElementById('app');
      Shell.sidebarEl = h('aside', { class: 'sidebar', id: 'studio-navigation', 'aria-label': t('主导航', 'Main navigation') });
      Shell.topEl = h('header', { class: 'topbar' });
      Shell.mainEl = h('main', { id: 'main' }, Shell.topEl);
      root.appendChild(Shell.sidebarEl); root.appendChild(Shell.mainEl);
      Shell.renderSidebar(); Shell.renderTop(cfg.crumbs);
      doc.addEventListener('keydown', (e) => { if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') { e.preventDefault(); Guard.go('search.html'); } });
      const body = h('div', { id: 'page' }); Shell.mainEl.appendChild(body);
      doc.title = (cfg.title || '') + (cfg.title ? ' · ' : '') + '灵脑 Studio';
      return body;
    },
    renderTop(crumbs) {
      clear(Shell.topEl);
      const toggle = h('button', { class: 'mobile-nav-toggle', type: 'button', 'aria-controls': 'studio-navigation', 'aria-expanded': 'false', }, h('span', { class: 'mobile-more-icon', 'aria-hidden': 'true', text: '···' }), h('span', { text: t('更多', 'More') }));
      const close = () => { Shell.sidebarEl.classList.remove('mobile-open'); toggle.setAttribute('aria-expanded', 'false'); };
      toggle.addEventListener('click', () => {
        const open = Shell.sidebarEl.classList.toggle('mobile-open');
        toggle.setAttribute('aria-expanded', String(open));
      });
      doc.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && Shell.sidebarEl.classList.contains('mobile-open')) { close(); toggle.focus(); }
      });
      Shell.sidebarEl.addEventListener('click', (e) => { if (e.target.closest('a')) close(); });
      const mobileLinks = [NAV[0], { label: t('搜索', 'Search'), href: 'search.html', icon: 'search' }, NAV[1]];
      const currentPath = global.location.pathname.split('/').pop();
      const mobileNav = h('nav', { class: 'mobile-tabbar', 'aria-label': t('快捷导航', 'Quick navigation') },
        mobileLinks.map((item) => h('a', {
          href: item.href, 'aria-current': currentPath === item.href ? 'page' : null
        }, I(item.icon, 19), h('span', { text: item.label }))), toggle);
      Shell.mainEl.appendChild(mobileNav);
      Shell.topEl.appendChild(h('span', null, h('a', { href: 'index.html', text: 'Studio' })));
      (crumbs || []).forEach((c) => { Shell.topEl.appendChild(h('span', { class: 'slash', text: '/' })); Shell.topEl.appendChild(c.href ? h('a', { href: c.href, text: c.label }) : h('span', { text: c.label })); });
      Shell.topEl.appendChild(h('button', {
        class: 'language-toggle', type: 'button', text: t('English', '简体中文'),
        onclick: async () => {
          if (Guard.dirty && !(await Guard.confirmLeave())) return;
          global.localStorage.setItem(languageKey, t('en', 'zh-CN'));
          Guard.dirty = false;
          global.location.reload();
        }
      }));
      Shell.topEl.appendChild(h('span', { class: 'prototype-label', text: t('交互原型 · 数据仅保存在当前浏览器', 'Prototype · Data stays in this browser') }));
    },
    renderSidebar() {
      const cfg = Shell.ctx || {}; const sb = clear(Shell.sidebarEl);
      const expanded = JSON.parse(global.sessionStorage.getItem(EXPAND_KEY) || '{}');
      const owner = L.Auth.owner(); const inbox = S.inboxCount(); const curSpace = cfg.spaceId || ''; const curCat = cfg.categoryId || '';
      sb.appendChild(h('a', { class: 'brand', href: 'index.html', 'aria-label': 'Luma 灵脑 Studio 首页' }, h('img', { src: 'assets/img/luma-mark.png', alt: '' }), h('span', null, 'Luma 灵脑 ', h('em', { text: 'Studio' }))));
      sb.appendChild(h('a', { class: 'search-launch', href: 'search.html' }, I('search', 19), h('span', { text: t('搜索记录、知识与空间…', 'Search notes and spaces…') }), h('kbd', { text: 'Ctrl K' })));
      sb.appendChild(h('a', { class: 'primary new-note', href: 'index.html#new' }, I('plus', 22), h('span', { text: t('新建记录', 'New note') })));
      sb.appendChild(h('nav', { 'aria-label': t('功能', 'Studio sections') }, NAV.map((n) => h('a', { class: 'nav-item' + (cfg.nav === n.key ? ' active' : ''), href: n.href, 'aria-current': cfg.nav === n.key ? 'page' : null },
        I(n.icon, 21), h('span', { text: n.label }), n.key === 'inbox' && inbox > 0 ? h('b', { class: 'count', text: String(inbox) }) : null))));
      const tree = h('div', { class: 'spaces-nav' }, h('div', { class: 'nav-label', text: t('我的空间', 'My spaces') }));
      const catNodes = (spaceId, parentId, depth) => S.childCategories(spaceId, parentId).map((c) => h('div', null,
        h('a', { class: 'category' + (curCat === c.id ? ' chosen' : ''), style: 'padding-left:' + (36 + depth * 14) + 'px', href: 'space.html?id=' + spaceId + '&cat=' + c.id, text: c.name }),
        catNodes(spaceId, c.id, depth + 1)));
      S.listSpaces().forEach((s) => {
        const isOpen = !!expanded[s.id] || curSpace === s.id;
        tree.appendChild(h('div', { class: 'space-line' + (curSpace === s.id && !curCat ? ' active' : '') },
          h('a', { href: 'space.html?id=' + s.id }, I('folder', 20), h('span', { text: s.name })),
          h('button', { class: 'chevron', type: 'button', 'aria-label': (isOpen ? '收起 ' : '展开 ') + s.name, 'aria-expanded': String(isOpen), onclick: () => { expanded[s.id] = !isOpen; global.sessionStorage.setItem(EXPAND_KEY, JSON.stringify(expanded)); Shell.renderSidebar(); } },
            I('chevronDown', 15))));
        if (isOpen) tree.appendChild(h('div', null, catNodes(s.id, '', 0)));
      });
      if (!S.listSpaces().length) tree.appendChild(h('p', { class: 'hint', text: t('还没有知识空间', 'No spaces yet') }));
      sb.appendChild(tree);
      sb.appendChild(h('div', { class: 'sidebar-bottom' },
        h('a', { class: 'nav-item' + (cfg.nav === 'settings' ? ' active' : ''), href: 'settings.html' }, I('settings', 21), h('span', { text: t('设置', 'Settings') })),
        h('a', { class: 'nav-item' + (cfg.nav === 'trash' ? ' active' : ''), href: 'trash.html' }, I('trash', 21), h('span', { text: t('回收站', 'Trash') })),
        h('div', { class: 'profile' }, h('span', { class: 'avatar', text: owner.displayName.slice(0, 1) }), h('span', { text: owner.displayName }), h('span', { class: 'private-note', text: t('私人工作室', 'Private studio') }),
          h('button', { class: 'icon-button', type: 'button', title: t('退出登录', 'Sign out'), 'aria-label': t('退出登录', 'Sign out'), onclick: async () => {
            if (Guard.dirty && !(await Guard.confirmLeave())) return;
            Guard.dirty = false; L.Auth.logout(); global.location.href = 'login.html'; } }, I('logout', 18)))));
    },
    /** 设置区域的页签：账户 / 外观 / 数据管理 */
    settingsTabs(active) {
      const tabs = [['account', t('账户', 'Account'), 'settings.html'], ['appearance', t('外观', 'Appearance'), 'appearance.html'], ['data', t('数据管理', 'Data management'), 'data.html']];
      return h('div', { class: 'tabs', role: 'navigation', 'aria-label': t('设置分区', 'Settings sections') }, tabs.map((t) => h('a', { href: t[2], class: active === t[0] ? 'selected' : '', 'aria-current': active === t[0] ? 'page' : null, text: t[1] })));
    }
  };

  L.UI = { t, h, I, clear, debounce, qs, selectEl, downloadText, fmtTime, fmtDateLong, fmtStamp, fmtSize, stripMd, highlight, snippet, esc, renderMarkdown, studioWiki, publicWiki,
    toast, dialog, confirmDialog, alertDialog, formDialog, Guard, paginate, pager, noteRow, rowAction, emptyState, contentMeta, publishPill };
  L.Shell = Shell;
})(window);
