/* 内容编辑与详情（PRD 7.4 / 7.10 / 7.11 / 7.12）
   - 自动保存 + 手动保存，只有“服务端”成功后才显示已保存；失败保留本地修改
   - 属性：类型、空间、分类、标签、学习状态、整理状态
   - 来源、关联、反向引用（含 [[ 选择器）
   - 发布 / 撤回（含公开预览与隐私提醒） */
(function () {
  'use strict';
  const L = window.Luma; const S = L.Store; const U = L.UI; const { h, I } = U;
  const AUTOSAVE_MS = 1200;
  const SOURCE_LABEL = { manual: '手动创建', file: '文件导入', web: '网页', ai: 'AI 对话', other: '其他' };
  const id = U.qs('id'); const initial = S.getContent(id);

  const page = L.Shell.mount({
    nav: initial && initial.organize === 'inbox' ? 'inbox' : '', title: initial ? initial.title || '内容编辑' : '内容编辑',
    spaceId: initial ? initial.spaceId : '', categoryId: initial ? initial.categoryId : '',
    crumbs: [initial && initial.organize === 'inbox' ? { label: '收集箱', href: 'inbox.html' } : { label: '知识空间', href: 'spaces.html' }, { label: '内容编辑' }]
  });
  if (!page) return;
  if (!initial) { page.appendChild(h('div', { class: 'standard' }, U.emptyState('file', '没有找到这条内容', '它可能已被永久删除。', h('a', { class: 'secondary', href: 'inbox.html', text: '返回收集箱' })))); return; }
  if (initial.deletedAt) { page.appendChild(h('div', { class: 'standard' }, U.emptyState('trash', '这条内容在回收站中', '恢复后才能继续编辑。', h('a', { class: 'secondary', href: 'trash.html', text: '前往回收站' })))); return; }

  /* ---------- 状态 ---------- */
  let pending = {}; let saving = false; let status = 'saved'; let mode = 'edit'; let timer = null;
  const cur = () => S.getContent(id);
  const view = () => Object.assign({}, cur(), pending); // 已保存内容 + 尚未提交的修改

  const statusEl = h('span', { class: 'save-status ok' }); const metaEl = h('div', { class: 'document-meta' });
  const bannerEl = h('div'); const propsEl = h('aside', { class: 'properties', 'aria-label': '内容属性' });
  const titleIn = h('input', { class: 'doc-title', type: 'text', 'aria-label': '内容标题', placeholder: '无标题', maxlength: 120, value: initial.title });
  const bodyTa = h('textarea', { class: 'doc-body', 'aria-label': '内容正文（Markdown）', placeholder: '开始写作…支持 Markdown，输入 [[ 可以关联其他内容。' }); bodyTa.value = initial.body;
  const previewEl = h('div', { class: 'preview-body', hidden: true });
  const pickerEl = h('div', { class: 'picker', role: 'listbox', 'aria-label': '选择要关联的内容', hidden: true });
  const saveBtn = h('button', { class: 'primary', type: 'button' }, I('save', 17), '保存');

  function setStatus(s) {
    status = s;
    const map = { saved: ['已保存 · ' + (cur().publish.status === 'published' ? '公开' : '私人'), 'ok'], dirty: ['尚未保存', ''], saving: ['保存中…', ''], error: ['保存失败，修改已保留在本页', 'error'] };
    statusEl.className = 'save-status ' + map[s][1]; statusEl.textContent = map[s][0]; statusEl.setAttribute('role', 'status');
  }
  function schedule() { clearTimeout(timer); timer = setTimeout(() => flush(false), AUTOSAVE_MS); }
  function change(patch) { Object.assign(pending, patch); U.Guard.set(true); if (status !== 'saving') setStatus('dirty'); schedule(); }

  /** 提交待保存修改。仅在“服务端”成功回调之后才显示已保存。 */
  let inflight = null;
  async function flush(manual) {
    clearTimeout(timer);
    if (saving) { try { await inflight; } catch (e) { /* 失败已由发起方处理 */ } return flush(manual); } // 等待进行中的保存结束，避免并发覆盖
    if (!Object.keys(pending).length) { if (manual) U.toast('没有需要保存的修改'); return status !== 'error'; }
    const patch = pending; pending = {}; saving = true; setStatus('saving');
    try {
      inflight = S.saveContentAsync(id, patch).catch((e) => { throw e; }); inflight.catch(() => {});
      await inflight; saving = false;
      if (Object.keys(pending).length) { setStatus('dirty'); schedule(); } else { U.Guard.set(false); setStatus('saved'); }
      renderMeta(); renderBanner(); L.Shell.renderSidebar(); if (manual) U.toast(cur().publish.status === 'published' ? '已保存，线上内容已同步更新' : '修改已保存');
      return true;
    } catch (e) {
      console.error(e); saving = false; pending = Object.assign({}, patch, pending); U.Guard.set(true); setStatus('error');
      U.toast('保存失败：' + e.message + '。你的修改仍保留在本页，可稍后重试。', 'error'); return false;
    }
  }

  /* ---------- 文档区 ---------- */
  function renderBanner() {
    U.clear(bannerEl); const c = cur();
    if (c.publish.status === 'published') bannerEl.appendChild(h('div', { class: 'banner warn', role: 'note' }, I('globe', 18), '此内容已发布到 Explore。保存后将立即更新线上内容；如需停止公开，请在右侧“发布”中撤回。'));
    else if (c.organize === 'inbox') bannerEl.appendChild(h('div', { class: 'banner info', role: 'note' }, I('inbox', 18), '这条内容还在收集箱。选择知识空间后点击“完成整理”即可，整理不会触发公开发布。'));
  }
  function renderMeta() {
    const c = cur(); U.clear(metaEl);
    metaEl.appendChild(h('span', { text: '创建于 ' + U.fmtTime(c.createdAt) })); metaEl.appendChild(h('span', { text: '更新于 ' + U.fmtTime(c.updatedAt) }));
    metaEl.appendChild(h('span', { class: 'pill' + (c.organize === 'inbox' ? ' warn' : ''), text: S.ORGANIZE_LABEL[c.organize] }));
    metaEl.appendChild(c.publish.status === 'published' ? h('span', { class: 'pill ok', text: '已发布' }) : h('span', { class: 'pill mute', text: c.publish.status === 'withdrawn' ? '已撤回 · 仅自己可见' : '私有 · 仅自己可见' }));
  }
  function renderPreview() {
    previewEl.innerHTML = U.renderMarkdown(bodyTa.value, U.studioWiki) || '<p style="color:var(--muted)">暂无正文。</p>'; // 内容已在 renderMarkdown 中转义
  }
  function setMode(m) {
    mode = m; bodyTa.hidden = m !== 'edit'; previewEl.hidden = m === 'edit'; if (m === 'preview') renderPreview();
    modeBtns.forEach((b) => { b.classList.toggle('selected', b.dataset.mode === m); b.setAttribute('aria-pressed', String(b.dataset.mode === m)); }); toolsWrap.style.visibility = m === 'edit' ? 'visible' : 'hidden';
  }
  const modeBtns = [['edit', '编辑'], ['preview', '预览']].map(([m, label]) => h('button', { type: 'button', dataset: { mode: m }, text: label, onclick: () => setMode(m) }));
  const toolsWrap = h('div', null, L.EditTools.toolbar(bodyTa));

  /* ---------- [[ 关联选择器 ---------- */
  let pickerState = { open: false, start: 0, items: [], index: 0 };
  function wikiContext() {
    const pos = bodyTa.selectionStart; const m = /\[\[([^\]\n]*)$/.exec(bodyTa.value.slice(0, pos));
    return m ? { start: pos - m[0].length, query: m[1] } : null;
  }
  function closePicker() { pickerState.open = false; pickerEl.hidden = true; }
  function updatePicker() {
    const ctx = wikiContext(); if (!ctx) { closePicker(); return; }
    const q = ctx.query.trim().toLowerCase();
    const items = S.sortByUpdated(S.activeContents().filter((c) => c.id !== id && (!q || c.title.toLowerCase().includes(q)))).slice(0, 8);
    pickerState = { open: true, start: ctx.start, items, index: 0 }; drawPicker();
  }
  function drawPicker() {
    U.clear(pickerEl); pickerEl.hidden = false;
    if (!pickerState.items.length) { pickerEl.appendChild(h('div', { class: 'picker-empty', text: '没有匹配的内容，继续输入或按 Esc 取消' })); return; }
    pickerState.items.forEach((c, i) => pickerEl.appendChild(h('button', { type: 'button', role: 'option', class: i === pickerState.index ? 'active' : '', 'aria-selected': String(i === pickerState.index),
      onmousedown: (e) => { e.preventDefault(); pick(c); } }, c.title || '（无标题）', h('small', { text: c.spaceId ? S.getSpace(c.spaceId).name : '收集箱' }))));
  }
  function pick(target) {
    const pos = bodyTa.selectionStart; const link = '[[' + target.title + ']]';
    bodyTa.value = bodyTa.value.slice(0, pickerState.start) + link + bodyTa.value.slice(pos);
    const caret = pickerState.start + link.length; bodyTa.selectionStart = bodyTa.selectionEnd = caret; closePicker(); bodyTa.focus();
    change({ body: bodyTa.value });
    const r = S.addRelation(id, target.id, 'related', '');
    if (r.ok) { U.toast('已建立关联：相关'); renderProps(); } else if (r.message.indexOf('已存在') < 0) U.toast(r.message, 'error');
  }
  bodyTa.addEventListener('keydown', (e) => {
    if (!pickerState.open) return;
    const n = pickerState.items.length;
    if (e.key === 'ArrowDown' && n) { e.preventDefault(); pickerState.index = (pickerState.index + 1) % n; drawPicker(); }
    else if (e.key === 'ArrowUp' && n) { e.preventDefault(); pickerState.index = (pickerState.index - 1 + n) % n; drawPicker(); }
    else if ((e.key === 'Enter' || e.key === 'Tab') && n) { e.preventDefault(); pick(pickerState.items[pickerState.index]); }
    else if (e.key === 'Escape') { e.preventDefault(); closePicker(); }
  });
  bodyTa.addEventListener('input', () => { change({ body: bodyTa.value }); updatePicker(); });
  bodyTa.addEventListener('click', updatePicker); bodyTa.addEventListener('blur', () => setTimeout(closePicker, 120));
  titleIn.addEventListener('input', () => change({ title: titleIn.value }));

  /* ---------- 属性面板 ---------- */
  function categoryOptions(spaceId) {
    const opts = [{ value: '', label: '暂不选择' }];
    const walk = (parentId, depth) => S.childCategories(spaceId, parentId).forEach((c) => { opts.push({ value: c.id, label: '　'.repeat(depth) + c.name }); walk(c.id, depth + 1); });
    if (spaceId) walk('', 0); return opts;
  }
  function group(title, right, ...children) { return h('div', { class: 'prop-group' }, h('h4', null, title, right || null), children); }

  function tagsGroup(v) {
    const input = h('input', { class: 'field', type: 'text', list: 'tag-suggestions', placeholder: '输入标签，回车添加', 'aria-label': '添加标签', maxlength: 20 });
    const list = h('datalist', { id: 'tag-suggestions' }, S.allTags().map((t) => h('option', { value: t.name })));
    const add = () => {
      const names = input.value.split(/[,，]/).map((x) => x.trim()).filter(Boolean); if (!names.length) return;
      const ids = v.tagIds.slice(); names.forEach((n) => { const t = S.ensureTag(n); if (t && !ids.includes(t.id)) ids.push(t.id); });
      change({ tagIds: ids }); renderProps('tag');
    };
    input.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ',' || e.key === '，') { e.preventDefault(); add(); } });
    return group('标签', null,
      h('div', { class: 'tag-list' }, v.tagIds.map((tid) => S.getTag(tid)).filter(Boolean).map((t) => h('span', { class: 'tag-chip' }, '#' + t.name,
        h('button', { type: 'button', 'aria-label': '移除标签 ' + t.name, onclick: () => { change({ tagIds: v.tagIds.filter((x) => x !== t.id) }); renderProps('tag'); } }, I('x', 13))))),
      input, list);
  }

  function relationsGroups() {
    const rel = S.relationsFor(id);
    const label = (r) => S.RELATION_TYPES[r.type];
    const linkItems = rel.links.map((l) => h('div', { class: 'rel-item' }, h('span', { text: l.arrow }),
      h('div', { style: 'flex:1;min-width:0' }, h('a', { href: 'editor.html?id=' + encodeURIComponent(l.other.id), text: l.other.title || '（无标题）' }), h('small', { text: label(l.relation) + (l.relation.note ? ' · ' + l.relation.note : '') })),
      U.rowAction('x', '删除关联', async () => { if (await U.confirmDialog({ title: '删除这条关联？', desc: '只删除两条内容之间的关系，两条内容本身都会保留。', confirmText: '删除关联', danger: true })) { S.removeRelation(l.relation.id); renderProps(); } })));
    const backItems = rel.backlinks.map((b) => h('div', { class: 'rel-item' }, h('span', { text: '←' }),
      h('div', { style: 'flex:1;min-width:0' }, h('a', { href: 'editor.html?id=' + encodeURIComponent(b.other.id), text: b.other.title || '（无标题）' }), h('small', { text: label(b.relation) }))));
    return [
      group('关联 · ' + rel.links.length, h('button', { class: 'text-button', type: 'button', onclick: addRelationDialog }, '+ 添加'), linkItems.length ? linkItems : h('p', { class: 'hint', style: 'margin:0', text: '还没有关联。在正文输入 [[ 可快速选择目标。' })),
      group('反向引用 · ' + rel.backlinks.length, null, backItems.length ? backItems : h('p', { class: 'hint', style: 'margin:0', text: '暂无其他内容指向这里。' }))
    ];
  }

  const addRelationDialog = guarded(async function () {
    let selected = null; const err = h('p', { class: 'field-error', role: 'alert' });
    const q = h('input', { class: 'field modal-search', type: 'text', placeholder: '搜索要关联的内容标题…', 'aria-label': '搜索内容' });
    const list = h('div', { class: 'result-list', role: 'listbox', 'aria-label': '候选内容' });
    const typeSel = U.selectEl(Object.keys(S.RELATION_TYPES).map((k) => ({ value: k, label: S.RELATION_TYPES[k] })), 'related', { 'aria-label': '关系类型' });
    const note = h('input', { class: 'field', type: 'text', maxlength: 60, placeholder: '关系说明（可选）', 'aria-label': '关系说明' });
    function draw() {
      U.clear(list); const t = q.value.trim().toLowerCase();
      const items = S.sortByUpdated(S.activeContents().filter((c) => c.id !== id && (!t || c.title.toLowerCase().includes(t)))).slice(0, 30);
      if (!items.length) list.appendChild(h('p', { class: 'hint', style: 'padding:0 14px', text: '没有匹配的内容' }));
      items.forEach((c) => list.appendChild(h('button', { type: 'button', role: 'option', class: selected && selected.id === c.id ? 'selected' : '', 'aria-selected': String(!!(selected && selected.id === c.id)), onclick: () => { selected = c; draw(); } },
        c.title || '（无标题）', h('small', { text: c.type + (c.spaceId ? ' · ' + S.getSpace(c.spaceId).name : ' · 收集箱') }))));
    }
    q.addEventListener('input', draw); draw();
    const content = h('div', null, q, list, h('div', { style: 'display:grid;grid-template-columns:1fr 1.4fr;gap:12px;margin-top:14px' }, typeSel, note), err);
    const r = await U.dialog({ title: '添加关联', desc: '关联基于稳定的内容 ID，不依赖标题。“相关”按双向展示，其余关系保留方向（当前内容 → 目标）。', content, cancelValue: null, actions: [
      { label: '取消', value: null },
      { label: '建立关联', primary: true, value: 'ok', validate: () => {
        if (!selected) { err.textContent = '请先选择目标内容'; return false; }
        const res = S.addRelation(id, selected.id, typeSel.value, note.value); if (!res.ok) { err.textContent = res.message; return false; } return true; } }] });
    if (r) { U.toast('关联已建立'); renderProps(); }
  });

  function sourcesGroup(c) {
    const fmt = (s) => {
      const parts = [SOURCE_LABEL[s.kind] || SOURCE_LABEL.other];
      if (s.title && s.kind !== 'manual') parts.push(s.title); if (s.fileName) parts.push(s.fileName); if (s.platform) parts.push(s.platform); if (s.url) parts.push(s.url); if (s.externalId) parts.push('ID ' + s.externalId);
      return parts.join(' · ');
    };
    return group('来源 · ' + c.sources.length, null, c.sources.map((s) => h('div', { class: 'source-item' }, fmt(s), h('br'),
      '发生于 ' + (s.occurredAt ? U.fmtTime(s.occurredAt) : '未知') + (s.importedAt ? '　导入于 ' + U.fmtTime(s.importedAt) : ''))),
    c.attachments.length ? c.attachments.map((a) => h('div', { class: 'source-item' }, '附件：' + a.name + '（' + U.fmtSize(a.size) + '）· ' + (a.isPublic ? '已公开' : '私有'))) : null);
  }

  function publishGroup(c) {
    const issues = S.publishIssues(c); const p = c.publish;
    const nodes = [];
    nodes.push(h('div', { style: 'margin-bottom:10px' }, p.status === 'published' ? h('span', { class: 'pill ok', text: '已发布' }) : h('span', { class: 'pill mute', text: S.PUBLISH_LABEL[p.status] })));
    if (p.status === 'published') {
      nodes.push(h('p', { class: 'hint', style: 'margin:0 0 10px', text: '公开地址：/knowledge/' + p.slug + '　发布于 ' + U.fmtTime(p.publishedAt) }));
      nodes.push(h('div', { style: 'display:flex;gap:8px;flex-wrap:wrap' },
        h('button', { class: 'secondary', type: 'button', onclick: () => publishFlow(true) }, I('eye', 16), '公开预览'),
        h('button', { class: 'secondary', type: 'button', onclick: withdrawFlow }, I('lock', 16), '撤回发布')));
    } else {
      if (p.status === 'withdrawn') nodes.push(h('p', { class: 'hint', style: 'margin:0 0 10px', text: '已撤回：匿名访问已失效，内容仍保留在 Studio。再次发布将沿用原公开地址。' }));
      if (issues.length) nodes.push(h('p', { class: 'field-error', text: '暂不可发布：' + issues.join('、') }));
      nodes.push(h('button', { class: 'secondary full', type: 'button', onclick: () => publishFlow(false) }, I('globe', 16), '预览并发布'));
    }
    return group('发布到 Explore', null, nodes);
  }

  function organizeGroup(c) {
    const nodes = [];
    if (c.organize === 'inbox') {
      nodes.push(h('p', { class: 'hint', style: 'margin:0 0 10px', text: '先选择知识空间，再完成整理。正文与来源会保留在同一条记录中，ID 不变。' }));
      nodes.push(h('button', { class: 'primary full', type: 'button', onclick: finishOrganize }, I('check', 17), '完成整理'));
      nodes.push(h('button', { class: 'text-button', type: 'button', onclick: () => setOrganize('archived') }, '直接归档'));
    } else if (c.organize === 'organized') nodes.push(h('button', { class: 'text-button', type: 'button', onclick: () => setOrganize('archived') }, '归档这条内容'));
    else nodes.push(h('button', { class: 'secondary full', type: 'button', onclick: () => setOrganize(c.spaceId ? 'organized' : 'inbox') }, I('undo', 16), '取消归档'));
    return group('整理状态 · ' + S.ORGANIZE_LABEL[c.organize], null, nodes);
  }
  const finishOrganize = guarded(async function () {
    if (!view().spaceId) { U.toast('请先选择知识空间', 'error'); return; } // 是否同时要求分类：待确认（PRD 未规定），原型仅要求空间
    if (!(await flush(false))) return;
    S.organize(id, 'organized'); U.toast('已完成整理，内容仍为私人内容'); renderAll();
  });
  const setOrganize = guarded(async function (next) { if (!(await flush(false))) return; S.organize(id, next); U.toast(next === 'archived' ? '已归档' : next === 'organized' ? '已恢复为已整理' : '已放回待整理'); renderAll(); });

  function renderProps(focus) {
    const c = cur(); const v = view(); U.clear(propsEl);
    const sel = (opts, value, label, onChange) => U.selectEl(opts, value, { 'aria-label': label, onchange: (e) => onChange(e.target.value) });
    propsEl.appendChild(h('h3', { text: '内容属性' }));
    propsEl.appendChild(h('label', { class: 'field-label' }, '内容类型', sel(S.CONTENT_TYPES.map((t) => ({ value: t, label: t })), v.type, '内容类型', (val) => change({ type: val }))));
    propsEl.appendChild(h('label', { class: 'field-label' }, '知识空间', sel([{ value: '', label: '暂不选择' }].concat(S.listSpaces().map((s) => ({ value: s.id, label: s.name }))), v.spaceId, '知识空间',
      (val) => { change({ spaceId: val, categoryId: '' }); renderProps(); })));
    propsEl.appendChild(h('label', { class: 'field-label' }, '分类', sel(categoryOptions(v.spaceId), v.categoryId, '分类', (val) => change({ categoryId: val }))));
    propsEl.appendChild(tagsGroup(v));
    propsEl.appendChild(h('label', { class: 'field-label' }, '学习状态（手动维护）', sel([{ value: '', label: '不设置' }].concat(S.LEARNING_STATES.map((t) => ({ value: t, label: t }))), v.learning, '学习状态', (val) => change({ learning: val }))));
    propsEl.appendChild(organizeGroup(c));
    relationsGroups().forEach((g) => propsEl.appendChild(g));
    propsEl.appendChild(publishGroup(c));
    propsEl.appendChild(sourcesGroup(c));
    propsEl.appendChild(h('label', { class: 'hint', style: 'display:flex;gap:8px;align-items:center;border-top:1px solid var(--line);padding-top:14px' },
      h('input', { type: 'checkbox', checked: S.debug.failSave, onchange: (e) => { S.debug.failSave = e.target.checked; }, style: 'width:auto;min-height:0' }), '原型调试：模拟保存失败'));
    if (focus === 'tag') { const t = propsEl.querySelector('input[list]'); if (t) t.focus(); }
  }

  /** 异步交互统一兜底：记录错误并给出可理解的提示，避免静默失败。 */
  function guarded(fn) {
    return async function () {
      try { return await fn.apply(null, arguments); } catch (e) { console.error(e); U.toast('操作失败：' + e.message, 'error'); return undefined; }
    };
  }

  /* ---------- 发布 / 撤回 ---------- */
  const publishFlow = guarded(async function (previewOnly) {
    if (!previewOnly && !(await flush(false))) return;
    const c = cur(); const issues = S.publishIssues(c);
    const rels = S.publicRelations(id); const wikiNames = Array.from(c.body.matchAll(/\[\[([^\]\n]+)\]\]/g)).map((m) => m[1].trim());
    const leaking = wikiNames.filter((n) => { const t = S.findByTitle(n); return !t || t.publish.status !== 'published'; });
    const attachChecks = c.attachments.map((a) => ({ a, box: h('input', { type: 'checkbox', checked: !!a.isPublic, style: 'width:auto;min-height:0' }) }));
    const preview = h('div', { class: 'public-preview' }, h('h1', { style: 'font-size:26px;margin:14px 0 4px', text: c.title || '（无标题）' }), h('div', { class: 'preview-body' }));
    preview.querySelector('.preview-body').innerHTML = U.renderMarkdown(c.body, U.publicWiki);
    const check = (ok, text) => h('li', { class: ok ? '' : 'bad' }, I(ok ? 'check' : 'alert', 17), text);
    const content = h('div', null,
      h('ul', { class: 'checklist' }, check(!!c.title.trim(), '具有标题'), check(!!c.body.trim(), '具有可展示的正文')),
      c.type === '记忆记录' ? h('div', { class: 'banner warn', role: 'alert' }, I('alert', 18), '这是一条“记忆记录”，通常包含个人事实与经历。发布后任何访客都能阅读，请确认其中没有不想公开的信息。') : null,
      leaking.length ? h('div', { class: 'banner warn' }, I('alert', 18), '正文引用了未发布或不存在的内容：' + leaking.join('、') + '。它们不会成为公开链接，但标题文字会出现在正文中。') : null,
      h('h4', { style: 'margin:14px 0 4px;font-weight:400;color:var(--muted);font-size:13px', text: '公开预览（访客将看到的内容）' }), preview,
      rels.length ? h('p', { class: 'hint', text: '公开关联（仅两端均已发布）：' + rels.map((r) => r.other.title).join('、') }) : h('p', { class: 'hint', text: '没有可公开展示的关联。未发布内容的标题、摘要与 ID 不会被公开。' }),
      attachChecks.length ? h('div', null, h('h4', { style: 'margin:10px 0 4px;font-weight:400;color:var(--muted);font-size:13px', text: '附件默认私有，勾选后才会公开' }),
        attachChecks.map((x) => h('label', { style: 'display:flex;gap:8px;font-size:14px;align-items:center' }, x.box, x.a.name))) : null);
    if (previewOnly) { await U.dialog({ title: '公开预览', wide: true, content, actions: [{ label: '关闭', value: true, primary: true }] }); return; }
    const ok = await U.dialog({ title: '发布到 Explore', desc: '发布后任何访客都能阅读公开页面。保存、整理与 AI 处理都不会自动公开，只有你确认后才会发布。', wide: true, content, cancelValue: false, actions: [
      { label: '取消', value: false }, { label: '确认发布', value: true, primary: true, validate: () => { if (issues.length) U.toast('暂不可发布：' + issues.join('、'), 'error'); return issues.length === 0; } }] });
    if (!ok) return;
    const r = S.publish(id, { publicAttachmentIds: attachChecks.filter((x) => x.box.checked).map((x) => x.a.id) });
    if (!r.ok) { U.toast(r.message, 'error'); return; }
    U.toast('已发布：/knowledge/' + cur().publish.slug); renderAll();
  });
  const withdrawFlow = guarded(async function () {
    const ok = await U.confirmDialog({ title: '撤回发布？', confirmText: '撤回发布', danger: true,
      desc: '撤回后，公开详情页、公开列表与搜索、公开关联、站点地图和公开附件都会停止提供该内容。内容仍保留在 Studio，可以再次发布。' });
    if (!ok) return; S.withdraw(id); U.toast('已撤回，公开访问已失效'); renderAll();
  });

  const removeContent = guarded(async function () {
    const pub = cur().publish.status === 'published';
    const ok = await U.confirmDialog({ title: '移入回收站？', confirmText: '移入回收站', danger: true,
      desc: '「' + (cur().title || '无标题') + '」可以在回收站中恢复。' + (pub ? '该内容当前已发布，移入回收站将同时撤回公开访问。' : '') });
    if (!ok) return; clearTimeout(timer); pending = {}; U.Guard.set(false); S.moveToTrash(id); U.toast('已移入回收站');
    setTimeout(() => { window.location.href = initial.organize === 'inbox' ? 'inbox.html' : 'index.html'; }, 400);
  });

  function renderAll() { renderMeta(); renderBanner(); renderProps(); setStatus(status); L.Shell.renderSidebar(); }

  /* ---------- 组装页面 ---------- */
  saveBtn.addEventListener('click', () => flush(true));
  document.addEventListener('keydown', (e) => { if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 's') { e.preventDefault(); flush(true); } });
  setMode('edit');
  page.appendChild(h('div', { class: 'editor-page' },
    h('div', { class: 'page-heading' },
      h('a', { class: 'back', href: initial.organize === 'inbox' ? 'inbox.html' : (initial.spaceId ? 'space.html?id=' + initial.spaceId : 'index.html') }, I('arrowLeft', 18), '返回'),
      h('div', { class: 'edit-actions' }, statusEl, h('button', { class: 'icon-button', type: 'button', title: '移入回收站', 'aria-label': '移入回收站', onclick: removeContent }, I('trash', 20)), saveBtn)),
    h('div', { class: 'editor-layout' },
      h('article', { class: 'document' }, bannerEl, titleIn, metaEl,
        h('div', { class: 'doc-toolbar' }, h('div', { class: 'segmented', role: 'group', 'aria-label': '编辑模式' }, modeBtns), toolsWrap),
        bodyTa, previewEl, pickerEl),
      propsEl)));
  renderMeta(); renderBanner(); renderProps(); setStatus('saved');
})();
