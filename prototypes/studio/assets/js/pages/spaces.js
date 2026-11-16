/* 知识空间列表（PRD 7.5）：创建、重命名、排序；非空空间阻止直接删除。 */
(function () {
  'use strict';
  const L = window.Luma; const S = L.Store; const U = L.UI; const { h, I } = U;
  const page = L.Shell.mount({ nav: 'spaces', title: '知识空间', crumbs: [{ label: '知识空间' }] }); if (!page) return;
  const box = h('div', { class: 'standard' }); page.appendChild(box);

  async function editSpace(space) {
    const isNew = !space;
    const v = await U.formDialog({
      title: isNew ? '新建知识空间' : '编辑知识空间', confirmText: isNew ? '创建' : '保存',
      fields: [{ name: 'name', label: '空间名称', value: space ? space.name : '', placeholder: '例如：技术研究' }, { name: 'desc', label: '简介（可选）', type: 'textarea', value: space ? space.desc : '' }],
      validate: (val) => {
        const name = val.name.trim();
        if (!name) return '空间名称不能为空';
        if (name.length > 30) return '空间名称不能超过 30 个字符';
        return S.listSpaces().some((s) => s.name === name && (!space || s.id !== space.id)) ? '已存在同名空间' : '';
      }
    });
    if (!v) return;
    const r = isNew ? S.addSpace(v.name, v.desc) : S.updateSpace(space.id, { name: v.name, desc: v.desc });
    if (!r.ok) { U.toast(r.message, 'error'); return; }
    U.toast(isNew ? '空间已创建' : '空间已更新'); render(); L.Shell.renderSidebar();
  }
  async function removeSpace(space) {
    const r = S.deleteSpace(space.id);
    if (r.ok) { U.toast('空间已删除'); render(); L.Shell.renderSidebar(); return; }
    await U.alertDialog('无法直接删除「' + space.name + '」',
      '该空间下还有 ' + r.categories + ' 个分类、' + r.contents + ' 条内容（含回收站）。为避免误删，请先迁移或处理这些分类与内容，再删除空间。');
  }
  function move(space, dir) { if (S.moveSpace(space.id, dir)) { render(); L.Shell.renderSidebar(); } }

  function render() {
    U.clear(box);
    const spaces = S.listSpaces();
    box.appendChild(h('div', { class: 'eyebrow', text: '慢慢积累，自成体系' }));
    box.appendChild(h('h1', { text: '知识空间' }));
    box.appendChild(h('p', { class: 'intro', text: '按自己的方式组织知识、经历与想法。空间名称与数量由你决定，没有固定目录。' }));
    const grid = h('div', { class: 'space-grid' });
    spaces.forEach((s, i) => {
      const cats = S.allCategories().filter((c) => c.spaceId === s.id).length;
      grid.appendChild(h('article', { class: 'space-card' },
        h('a', { href: 'space.html?id=' + s.id }, I('folder', 30, 'big'), h('h2', { text: s.name }), h('p', { text: s.desc || '暂无简介' }),
          h('small', { text: S.contentsInSpace(s.id).length + ' 条内容 · ' + cats + ' 个分类' })),
        h('div', { class: 'card-actions' },
          U.rowAction('edit', '编辑空间', () => editSpace(s)),
          h('button', { class: 'icon-button', type: 'button', title: '上移', 'aria-label': '上移 ' + s.name, disabled: i === 0, onclick: () => move(s, -1) }, I('arrowUp', 18)),
          h('button', { class: 'icon-button', type: 'button', title: '下移', 'aria-label': '下移 ' + s.name, disabled: i === spaces.length - 1, onclick: () => move(s, 1) }, I('arrowDown', 18)),
          U.rowAction('trash', '删除空间', () => removeSpace(s)))));
    });
    grid.appendChild(h('button', { class: 'space-card new', type: 'button', onclick: () => editSpace(null) }, I('plus', 30), h('span', { text: '新建知识空间' })));
    box.appendChild(grid);
    if (!spaces.length) box.insertBefore(h('p', { class: 'hint', text: '还没有知识空间。内容可以暂时不属于任何空间，也可以先创建一个。' }), grid);
  }
  render();
})();
