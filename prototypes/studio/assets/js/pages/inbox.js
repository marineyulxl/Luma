/* 收集箱（PRD 7.3）：待整理 / 已归档列表、类型筛选、分页、归档与删除。 */
(function () {
  'use strict';
  const L = window.Luma; const S = L.Store; const U = L.UI; const { h, I } = U;
  const PAGE_SIZE = 8;
  const page = L.Shell.mount({ nav: 'inbox', title: '收集箱', crumbs: [{ label: '收集箱' }] }); if (!page) return;
  const st = { tab: 'inbox', type: '', page: 1 };
  const box = h('div', { class: 'standard' }); page.appendChild(box);

  function listFor() {
    return S.sortByUpdated(S.activeContents().filter((c) => c.organize === st.tab && (!st.type || c.type === st.type)));
  }
  async function trash(c) {
    const ok = await U.confirmDialog({ title: '移入回收站？', desc: '「' + (c.title || '无标题') + '」可以在回收站中恢复。', confirmText: '移入回收站', danger: true });
    if (!ok) return;
    S.moveToTrash(c.id); U.toast('已移入回收站'); render(); L.Shell.renderSidebar();
  }
  function archive(c) { S.organize(c.id, 'archived'); U.toast('已归档'); render(); L.Shell.renderSidebar(); }
  function unarchive(c) {
    S.organize(c.id, c.spaceId ? 'organized' : 'inbox'); U.toast(c.spaceId ? '已恢复为已整理' : '已放回待整理'); render(); L.Shell.renderSidebar();
  }

  function render() {
    U.clear(box);
    const counts = { inbox: S.activeContents().filter((c) => c.organize === 'inbox').length, archived: S.activeContents().filter((c) => c.organize === 'archived').length };
    const list = listFor(); const pg = U.paginate(list, st.page, PAGE_SIZE); st.page = pg.page;
    box.appendChild(h('div', { class: 'eyebrow', text: '先收集，再整理' }));
    box.appendChild(h('h1', { text: '收集箱' }));
    box.appendChild(h('p', { class: 'intro', text: '让碎片先有一个落点，有空时再慢慢梳理。整理不会触发公开发布。' }));
    box.appendChild(h('div', { class: 'tabs', role: 'tablist' },
      h('button', { type: 'button', role: 'tab', class: st.tab === 'inbox' ? 'selected' : '', 'aria-selected': String(st.tab === 'inbox'), text: '待整理 ' + counts.inbox, onclick: () => { st.tab = 'inbox'; st.page = 1; render(); } }),
      h('button', { type: 'button', role: 'tab', class: st.tab === 'archived' ? 'selected' : '', 'aria-selected': String(st.tab === 'archived'), text: '已归档 ' + counts.archived, onclick: () => { st.tab = 'archived'; st.page = 1; render(); } }),
      h('span', { style: 'margin-left:auto;width:160px' }, U.selectEl([{ value: '', label: '全部类型' }].concat(S.CONTENT_TYPES.map((t) => ({ value: t, label: t }))), st.type,
        { 'aria-label': '按内容类型筛选', onchange: (e) => { st.type = e.target.value; st.page = 1; render(); } }))));
    box.appendChild(h('div', { class: 'list-heading' }, h('span', { text: list.length + ' 条内容' }), h('span', { text: '最近更新' })));
    if (!list.length) {
      box.appendChild(U.emptyState('inbox', st.tab === 'inbox' ? '收集箱是空的' : '没有已归档的内容',
        st.tab === 'inbox' ? '从首页写一条记录，或导入已有资料，它们会先落在这里。' : '归档的内容不再出现在日常视图，但仍可搜索与恢复。',
        h('a', { class: 'secondary', href: 'index.html#new', text: '写一条记录' })));
      return;
    }
    pg.items.forEach((c) => box.appendChild(U.noteRow(c, { actions: st.tab === 'inbox'
      ? [U.rowAction('archive', '归档', () => archive(c)), U.rowAction('trash', '移入回收站', () => trash(c))]
      : [U.rowAction('undo', '取消归档', () => unarchive(c)), U.rowAction('trash', '移入回收站', () => trash(c))] })));
    box.appendChild(U.pager(list.length, pg.page, PAGE_SIZE, (p) => { st.page = p; render(); }));
  }
  render();
})();
