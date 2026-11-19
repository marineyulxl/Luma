/* 私人搜索（PRD 7.9）：标题 / 正文关键词；空间、分类、类型、标签、时间筛选；排序、分页、高亮。
   中文检索采用子串匹配仅作原型演示，正式分词 / n-gram 方案待确认（PRD T-05）。 */
(function () {
  'use strict';
  const L = window.Luma; const S = L.Store; const U = L.UI; const { h, I, t } = U;
  const PAGE_SIZE = 8;
  const page = L.Shell.mount({ nav: '', title: t('搜索', 'Search'), crumbs: [{ label: t('搜索', 'Search') }] }); if (!page) return;
  const st = { q: U.qs('q'), spaceId: '', categoryId: '', type: '', tagId: '', range: '', sort: 'relevance', page: 1 };
  const box = h('div', { class: 'standard' }); page.appendChild(box);
  const input = h('input', { type: 'search', placeholder: t('输入关键词搜索标题与正文…', 'Search titles and note text…'), 'aria-label': t('搜索关键词', 'Search keywords'), value: st.q, style: 'border:0;outline:0;background:none;flex:1;min-width:0;font-size:18px' });
  const clearBtn = h('button', { class: 'icon-button', type: 'button', 'aria-label': t('清除搜索', 'Clear search'), hidden: !st.q, onclick: () => { input.value = ''; onQuery(); input.focus(); } }, I('x', 18));
  const results = h('div'); const filters = h('div', { style: 'display:flex;gap:10px;flex-wrap:wrap;margin-bottom:22px' });

  const onQuery = U.debounce(() => { st.q = input.value; st.page = 1; clearBtn.hidden = !st.q; window.history.replaceState(null, '', st.q ? 'search.html?q=' + encodeURIComponent(st.q) : 'search.html'); renderResults(); }, 180);
  input.addEventListener('input', onQuery);

  function sel(label, value, options, onChange) {
    return U.selectEl(options, value, { 'aria-label': label, style: 'width:auto;min-width:130px', onchange: (e) => { onChange(e.target.value); st.page = 1; renderFilters(); renderResults(); } });
  }
  function catOptions(spaceId) {
    const opts = [{ value: '', label: t('全部分类', 'All categories') }];
    const walk = (p, d) => S.childCategories(spaceId, p).forEach((c) => { opts.push({ value: c.id, label: '　'.repeat(d) + c.name }); walk(c.id, d + 1); });
    walk('', 0); return opts;
  }
  function renderFilters() {
    U.clear(filters);
    filters.appendChild(sel(t('按知识空间筛选', 'Filter by space'), st.spaceId, [{ value: '', label: t('全部空间', 'All spaces') }].concat(S.listSpaces().map((s) => ({ value: s.id, label: s.name }))), (v) => { st.spaceId = v; st.categoryId = ''; }));
    if (st.spaceId) filters.appendChild(sel(t('按分类筛选', 'Filter by category'), st.categoryId, catOptions(st.spaceId), (v) => { st.categoryId = v; }));
    filters.appendChild(sel(t('按内容类型筛选', 'Filter by type'), st.type, [{ value: '', label: t('全部类型', 'All types') }].concat(S.CONTENT_TYPES.map((t) => ({ value: t, label: t }))), (v) => { st.type = v; }));
    filters.appendChild(sel(t('按标签筛选', 'Filter by tag'), st.tagId, [{ value: '', label: t('全部标签', 'All tags') }].concat(S.allTags().map((t) => ({ value: t.id, label: '#' + t.name }))), (v) => { st.tagId = v; }));
    filters.appendChild(sel(t('按更新时间筛选', 'Filter by update time'), st.range, [{ value: '', label: t('不限时间', 'Any time') }, { value: 'today', label: t('最近 24 小时', 'Last 24 hours') }, { value: 'week', label: t('最近 7 天', 'Last 7 days') }, { value: 'month', label: t('最近 30 天', 'Last 30 days') }], (v) => { st.range = v; }));
    filters.appendChild(sel(t('排序方式', 'Sort by'), st.sort, [{ value: 'relevance', label: t('按相关度', 'Relevance') }, { value: 'updated', label: t('按最近更新', 'Last updated') }], (v) => { st.sort = v; }));
    const active = st.spaceId || st.categoryId || st.type || st.tagId || st.range;
    if (active) filters.appendChild(h('button', { class: 'text-button', type: 'button', text: t('清除筛选', 'Clear filters'), onclick: () => { Object.assign(st, { spaceId: '', categoryId: '', type: '', tagId: '', range: '', page: 1 }); renderFilters(); renderResults(); } }));
  }
  function renderResults() {
    U.clear(results);
    const list = S.search(st); const pg = U.paginate(list, st.page, PAGE_SIZE); st.page = pg.page;
    results.appendChild(h('div', { class: 'list-heading', role: 'status' }, h('span', { text: (st.q ? '“' + st.q + '”：' : '') + list.length + t(' 条结果', ' results') }), h('span', { text: st.sort === 'updated' || !st.q ? t('最近更新', 'Last updated') : t('相关度', 'Relevance') })));
    if (!list.length) { results.appendChild(U.emptyState('search', t('没有找到匹配的内容', 'No matching notes'), st.q ? t('换一个关键词，或放宽筛选条件再试试。', 'Try a different search or fewer filters.') : t('还没有内容。', 'No notes yet.'), h('a', { class: 'secondary', href: 'index.html#new', text: t('写一条记录', 'Write a note') }))); return; }
    pg.items.forEach((c) => results.appendChild(U.noteRow(c, { query: st.q })));
    results.appendChild(U.pager(list.length, pg.page, PAGE_SIZE, (p) => { st.page = p; renderResults(); window.scrollTo({ top: 0 }); }));
  }

  box.appendChild(h('div', { class: 'eyebrow', text: t('找回曾经留下的线索', 'Find your notes') }));
  box.appendChild(h('h1', { text: t('搜索', 'Search') }));
  box.appendChild(h('p', { class: 'intro', text: t('搜索标题和正文，范围包含你有权访问的全部私人内容（含收集箱与已归档）。快捷键 Ctrl K。', 'Search your private notes, including the inbox and archive. Shortcut: Ctrl K.') }));
  box.appendChild(h('div', { style: 'display:flex;align-items:center;gap:12px;border:1px solid var(--line);border-radius:8px;padding:12px 14px;margin-bottom:18px' }, I('search', 22), input, clearBtn));
  box.appendChild(filters); box.appendChild(results);
  renderFilters(); renderResults(); input.focus();
})();
