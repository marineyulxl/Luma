/* 回收站（PRD 5.11）：恢复到原位置（原位置不存在则进入收集箱）；永久删除需明确确认并说明影响。 */
(function () {
  'use strict';
  const L = window.Luma; const S = L.Store; const U = L.UI; const { h, I } = U;
  const page = L.Shell.mount({ nav: 'trash', title: '回收站', crumbs: [{ label: '回收站' }] }); if (!page) return;
  const box = h('div', { class: 'standard' }); page.appendChild(box);

  function restore(c) {
    const r = S.restoreFromTrash(c.id);
    U.toast(r.fallbackToInbox ? '原空间或分类已不存在，内容已恢复到收集箱' : '内容已恢复'); L.Shell.renderSidebar(); render();
  }
  async function purge(c) {
    const impact = S.purgeImpact(c.id);
    const ok = await U.confirmDialog({ title: '永久删除这条内容？', danger: true, confirmText: '永久删除',
      desc: '「' + (c.title || '无标题') + '」将被永久删除，此操作无法撤销。同时会移除 ' + impact.relations + ' 条关联和 ' + impact.attachments + ' 个附件记录。' });
    if (!ok) return; S.permanentDelete(c.id); U.toast('已永久删除'); render();
  }
  async function emptyAll() {
    const list = S.trashedContents();
    const ok = await U.confirmDialog({ title: '清空回收站？', danger: true, confirmText: '全部永久删除', desc: '将永久删除回收站中的 ' + list.length + ' 条内容及其关联，此操作无法撤销。' });
    if (!ok) return; list.forEach((c) => S.permanentDelete(c.id)); U.toast('回收站已清空'); render();
  }

  function render() {
    U.clear(box); const list = S.sortByUpdated(S.trashedContents().map((c) => Object.assign({}, c, { updatedAt: c.deletedAt })));
    box.appendChild(h('div', { class: 'eyebrow', text: '给误删留一点余地' }));
    box.appendChild(h('h1', { text: '回收站' }));
    box.appendChild(h('p', { class: 'intro', text: '删除的内容保留在这里，你可以随时恢复。V1.0 不设置自动清理期限，永久删除前会提示影响。' }));
    box.appendChild(h('div', { class: 'list-heading' }, h('span', { text: list.length + ' 条内容' }), list.length ? h('button', { class: 'danger-text', type: 'button', text: '清空回收站', onclick: emptyAll }) : h('span', { text: '恢复后返回原位置' })));
    if (!list.length) { box.appendChild(U.emptyState('trash', '回收站是空的', '被删除的内容会先来到这里。')); return; }
    list.forEach((c) => {
      const origin = c.trashOrigin && c.trashOrigin.spaceId && S.getSpace(c.trashOrigin.spaceId) ? S.getSpace(c.trashOrigin.spaceId).name : '收集箱';
      box.appendChild(h('div', { class: 'note-row', style: 'align-items:center' }, I('file', 22),
        h('div', { class: 'body' }, h('strong', { text: c.title || '（无标题）' }), h('small', null, '删除于 ' + U.fmtTime(c.deletedAt), '· 恢复到：' + origin, c.publish.status === 'withdrawn' ? h('span', { class: 'pill warn', text: '已撤回公开' }) : null)),
        h('div', { class: 'row-actions', style: 'gap:8px' },
          h('button', { class: 'secondary', type: 'button', onclick: () => restore(S.getContent(c.id)) }, I('undo', 16), '恢复'),
          h('button', { class: 'danger-text', type: 'button', text: '永久删除', onclick: () => purge(S.getContent(c.id)) }))));
    });
  }
  render();
})();
