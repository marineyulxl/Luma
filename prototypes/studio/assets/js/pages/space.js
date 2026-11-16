/* 空间详情（PRD 7.5）：多级分类树、新建 / 重命名 / 移动 / 删除分类，按分类浏览内容。 */
(function () {
  'use strict';
  const L = window.Luma; const S = L.Store; const U = L.UI; const { h, I } = U;
  const PAGE_SIZE = 8; const UNCATEGORIZED = '__none';
  const spaceId = U.qs('id'); const space = S.getSpace(spaceId);
  const page = L.Shell.mount({ nav: 'spaces', title: space ? space.name : '空间不存在', spaceId, categoryId: U.qs('cat'),
    crumbs: [{ label: '知识空间', href: 'spaces.html' }, { label: space ? space.name : '未找到' }] });
  if (!page) return;
  const box = h('div', { class: 'standard' }); page.appendChild(box);
  if (!space) { box.appendChild(U.emptyState('folder', '没有找到这个空间', '它可能已被删除。', h('a', { class: 'secondary', href: 'spaces.html', text: '返回知识空间' }))); return; }

  const st = { cat: S.getCategory(U.qs('cat')) && S.getCategory(U.qs('cat')).spaceId === spaceId ? U.qs('cat') : (U.qs('cat') === UNCATEGORIZED ? UNCATEGORIZED : ''), page: 1 };

  function select(cat) {
    st.cat = cat; st.page = 1; L.Shell.ctx.categoryId = cat === UNCATEGORIZED ? '' : cat; L.Shell.renderSidebar();
    window.history.replaceState(null, '', 'space.html?id=' + spaceId + (cat ? '&cat=' + cat : '')); render();
  }
  const countIn = (catId) => S.contentsInCategory(catId, true).length;
  const selectedCat = () => (st.cat && st.cat !== UNCATEGORIZED ? S.getCategory(st.cat) : null);

  async function addCat() {
    const parent = selectedCat();
    const v = await U.formDialog({ title: parent ? '在「' + parent.name + '」下新建分类' : '新建顶层分类', confirmText: '创建',
      fields: [{ name: 'name', label: '分类名称', placeholder: '例如：前端开发' }],
      validate: (val) => {
        const name = val.name.trim(); if (!name) return '分类名称不能为空';
        return S.childCategories(spaceId, parent ? parent.id : '').some((c) => c.name === name) ? '同级已存在同名分类' : '';
      } });
    if (!v) return;
    const r = S.addCategory(spaceId, parent ? parent.id : '', v.name);
    if (!r.ok) { U.toast(r.message, 'error'); return; }
    U.toast('分类已创建'); select(r.category.id); L.Shell.renderSidebar();
  }
  async function renameCat() {
    const c = selectedCat(); if (!c) return;
    const v = await U.formDialog({ title: '重命名分类', confirmText: '保存', fields: [{ name: 'name', label: '分类名称', value: c.name }],
      validate: (val) => {
        const name = val.name.trim(); if (!name) return '分类名称不能为空';
        return S.childCategories(spaceId, c.parentId).some((x) => x.id !== c.id && x.name === name) ? '同级已存在同名分类' : '';
      } });
    if (!v) return;
    const r = S.renameCategory(c.id, v.name);
    r.ok ? (U.toast('已重命名，内容归属不受影响'), render(), L.Shell.renderSidebar()) : U.toast(r.message, 'error');
  }
  async function moveCat() {
    const c = selectedCat(); if (!c) return;
    const banned = new Set([c.id].concat(S.descendantCategoryIds(c.id)));
    const options = [{ value: '', label: '（移到顶层）' }];
    const walk = (parentId, depth) => S.childCategories(spaceId, parentId).forEach((x) => {
      options.push({ value: x.id, label: '　'.repeat(depth) + x.name + (x.id === c.id ? '（自身）' : banned.has(x.id) ? '（子分类）' : '') }); walk(x.id, depth + 1);
    });
    walk('', 0);
    const v = await U.formDialog({ title: '移动「' + c.name + '」', desc: '不能移动到自身或自己的子分类下。移动不会改变分类内内容的归属。', confirmText: '移动',
      fields: [{ name: 'parent', label: '新的父分类', type: 'select', options, value: c.parentId }],
      validate: (val) => { const chk = S.canMoveCategory(c.id, val.parent); return chk.ok ? '' : chk.message; } });
    if (!v) return;
    const r = S.moveCategory(c.id, v.parent);
    r.ok ? (U.toast('分类已移动'), render(), L.Shell.renderSidebar()) : U.toast(r.message, 'error');
  }
  async function deleteCat() {
    const c = selectedCat(); if (!c) return;
    const r = S.deleteCategory(c.id);
    if (r.ok) { U.toast('分类已删除'); select(''); return; }
    await U.alertDialog('无法直接删除「' + c.name + '」', '该分类下还有 ' + r.subs + ' 个子分类、' + r.contents + ' 条内容。请先迁移或处理它们，再删除分类。');
  }
  function newContent() {
    const c = S.createContent({ title: '未命名内容', type: '知识', spaceId, categoryId: selectedCat() ? selectedCat().id : '', organize: 'organized' });
    window.location.href = 'editor.html?id=' + encodeURIComponent(c.id);
  }

  function treeNodes(parentId, depth) {
    return S.childCategories(spaceId, parentId).map((c) => h('div', { role: 'treeitem' },
      h('button', { type: 'button', class: 'tree-item' + (st.cat === c.id ? ' selected' : ''), style: 'padding-left:' + (10 + depth * 18) + 'px', onclick: () => select(c.id) },
        I('folder', 16), h('span', { text: c.name }), h('span', { class: 'count', text: String(countIn(c.id)) })),
      treeNodes(c.id, depth + 1)));
  }

  function render() {
    U.clear(box);
    const all = S.contentsInSpace(spaceId);
    let list = all; let heading = '全部内容';
    if (st.cat === UNCATEGORIZED) { list = all.filter((c) => !c.categoryId); heading = '未分类'; }
    else if (st.cat) { list = S.contentsInCategory(st.cat, true); heading = S.categoryPath(st.cat); }
    list = S.sortByUpdated(list); const pg = U.paginate(list, st.page, PAGE_SIZE); st.page = pg.page;
    const sel = selectedCat();

    box.appendChild(h('div', { class: 'eyebrow', text: '空间' }));
    box.appendChild(h('h1', { text: space.name }));
    box.appendChild(h('p', { class: 'intro', text: space.desc || '在这里用多级分类整理这个空间下的内容。' }));
    box.appendChild(h('div', { class: 'space-layout' },
      h('aside', { class: 'tree-panel', 'aria-label': '分类' },
        h('div', { role: 'tree' },
          h('button', { type: 'button', class: 'tree-item' + (!st.cat ? ' selected' : ''), onclick: () => select('') }, I('layers', 16), h('span', { text: '全部内容' }), h('span', { class: 'count', text: String(all.length) })),
          treeNodes('', 0),
          h('button', { type: 'button', class: 'tree-item' + (st.cat === UNCATEGORIZED ? ' selected' : ''), onclick: () => select(UNCATEGORIZED) }, I('inbox', 16), h('span', { text: '未分类' }), h('span', { class: 'count', text: String(all.filter((c) => !c.categoryId).length) }))),
        h('div', { class: 'tree-actions' },
          h('button', { class: 'secondary', type: 'button', onclick: addCat }, I('plus', 15), sel ? '子分类' : '新建分类'),
          sel ? [h('button', { class: 'secondary', type: 'button', onclick: renameCat }, I('edit', 15), '重命名'),
            h('button', { class: 'secondary', type: 'button', onclick: moveCat }, I('folder', 15), '移动'),
            h('button', { class: 'secondary', type: 'button', onclick: deleteCat }, I('trash', 15), '删除')] : null)),
      h('section', null,
        h('div', { style: 'display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;gap:12px;flex-wrap:wrap' },
          h('h2', { style: 'font-size:20px', text: heading }),
          h('button', { class: 'primary', type: 'button', onclick: newContent }, I('plus', 18), '在此新建内容')),
        h('div', { class: 'list-heading' }, h('span', { text: list.length + ' 条内容' + (sel ? '（含子分类）' : '') }), h('span', { text: '最近更新' })),
        list.length ? pg.items.map((c) => U.noteRow(c)) : U.emptyState('folder', '这里暂时没有内容', '新建内容，或在内容编辑页把它归入这个分类。'),
        U.pager(list.length, pg.page, PAGE_SIZE, (p) => { st.page = p; render(); }))));
  }
  render();
})();
