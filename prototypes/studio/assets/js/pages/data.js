/* 数据管理（PRD 7.13）：Markdown 导出、完整备份、从备份恢复到空白工作区。
   Markdown 导出用于迁移与阅读，完整备份用于恢复，二者不能互相替代。 */
(function () {
  'use strict';
  const L = window.Luma; const S = L.Store; const U = L.UI; const { h, I } = U;
  const page = L.Shell.mount({ nav: 'settings', title: '数据管理', crumbs: [{ label: '设置', href: 'settings.html' }, { label: '数据管理' }] }); if (!page) return;
  const box = h('div', { class: 'standard settings' }); page.appendChild(box);
  const state = { selected: new Set(), restore: null };
  const SEPARATOR = '\n\n<!-- ======== 下一条内容 ======== -->\n\n';

  function toMarkdown(c) {
    const q = (v) => JSON.stringify(v == null ? '' : v);
    const tags = c.tagIds.map((id) => S.getTag(id)).filter(Boolean).map((t) => t.name);
    const lines = ['---', 'id: ' + q(c.id), 'title: ' + q(c.title), 'type: ' + q(c.type),
      'space: ' + q(c.spaceId && S.getSpace(c.spaceId) ? S.getSpace(c.spaceId).name : ''), 'category: ' + q(c.categoryId ? S.categoryPath(c.categoryId) : ''),
      'tags: [' + tags.map(q).join(', ') + ']', 'created: ' + q(c.createdAt), 'updated: ' + q(c.updatedAt)];
    if (c.sources.length) { lines.push('sources:'); c.sources.forEach((s) => { lines.push('  - kind: ' + q(s.kind)); if (s.url) lines.push('    url: ' + q(s.url)); if (s.fileName) lines.push('    file: ' + q(s.fileName)); if (s.platform) lines.push('    platform: ' + q(s.platform)); if (s.occurredAt) lines.push('    occurredAt: ' + q(s.occurredAt)); }); }
    lines.push('---', '', '# ' + (c.title || '无标题'), '', c.body);
    return lines.join('\n');
  }
  const safeName = (s) => (s || '未命名').replace(/[\\/:*?"<>|\s]+/g, '-').slice(0, 40);

  function exportSelected() {
    const items = S.activeContents().filter((c) => state.selected.has(c.id)); if (!items.length) { U.toast('请先选择要导出的内容', 'error'); return; }
    try {
      if (items.length === 1) U.downloadText(safeName(items[0].title) + '.md', toMarkdown(items[0]), 'text/markdown;charset=utf-8');
      else U.downloadText('luma-export-' + U.fmtStamp(new Date()) + '.md', items.map(toMarkdown).join(SEPARATOR), 'text/markdown;charset=utf-8');
      U.toast('已导出 ' + items.length + ' 条内容（Markdown）');
    } catch (e) { console.error(e); U.toast('导出失败，请重试', 'error'); }
  }
  function makeBackup() {
    try {
      const backup = S.buildBackup();
      U.downloadText('luma-backup-' + U.fmtStamp(new Date()) + '.json', JSON.stringify(backup, null, 2), 'application/json;charset=utf-8');
      const c = backup.manifest.counts; U.toast('备份已生成：' + c.contents + ' 条内容、' + c.attachments + ' 个附件记录');
    } catch (e) { console.error(e); U.toast('备份生成失败', 'error'); }
  }

  async function onBackupFile(file) {
    state.restore = null;
    if (!file) return renderRestore();
    try {
      const obj = JSON.parse(await file.text()); const chk = S.validateBackup(obj);
      state.restore = chk.ok ? { ok: true, obj, chk, name: file.name } : { ok: false, message: chk.message, name: file.name };
    } catch (e) { state.restore = { ok: false, message: '文件无法解析为 JSON，请确认选择的是灵脑备份文件', name: file.name }; }
    renderRestore();
  }
  async function doRestore() {
    const r = state.restore; if (!r || !r.ok) return;
    const ok = await U.confirmDialog({ title: '恢复到空白工作区？', desc: '将导入 ' + r.chk.counts.contents + ' 条内容、' + r.chk.counts.attachments + ' 个附件记录。恢复期间如果失败，会整体回滚，不留下半成品数据。', confirmText: '确认恢复' });
    if (!ok) return;
    const res = S.restoreBackup(r.obj);
    if (!res.ok) { U.toast(res.message, 'error'); return; }
    state.restore = null; U.toast('恢复完成，已校验内容、关系、来源与附件数量一致'); L.Shell.renderSidebar(); render();
  }
  async function wipe() {
    const ok = await U.confirmDialog({ title: '清空整个工作区？（仅原型）', danger: true, confirmText: '清空工作区', desc: '将删除所有内容、空间、分类、标签与关联，用来演示“恢复到空白工作区”。请先确认已生成备份。此操作无法撤销。' });
    if (!ok) return; S.resetWorkspace(); state.selected.clear(); U.toast('工作区已清空'); L.Shell.renderSidebar(); render();
  }

  function renderRestore() {
    const slot = box.querySelector('#restore-slot'); if (!slot) return; U.clear(slot);
    const r = state.restore; if (!r) return;
    if (!r.ok) { slot.appendChild(h('div', { class: 'banner warn', role: 'alert' }, I('alert', 18), r.name + '：' + r.message)); return; }
    const c = r.chk.counts; const blank = S.isBlankWorkspace();
    slot.appendChild(h('div', { class: 'data-card' }, h('h3', { text: '备份预览 · ' + r.name }),
      h('dl', { class: 'kv' }, h('dt', { text: '备份格式版本' }), h('dd', { text: String(r.chk.manifest.formatVersion) }), h('dt', { text: '生成时间' }), h('dd', { text: U.fmtTime(r.chk.manifest.generatedAt) }),
        h('dt', { text: '内容' }), h('dd', { text: c.contents + ' 条' }), h('dt', { text: '空间 / 分类' }), h('dd', { text: c.spaces + ' / ' + c.categories }), h('dt', { text: '标签 / 关联' }), h('dd', { text: c.tags + ' / ' + c.relations }),
        h('dt', { text: '来源 / 附件' }), h('dd', { text: c.sources + ' / ' + c.attachments + '（原型仅含附件元数据）' })),
      blank ? h('button', { class: 'primary', type: 'button', onclick: doRestore }, I('upload', 17), '恢复到当前空白工作区')
        : h('div', { class: 'banner warn', role: 'alert' }, I('alert', 18), 'V1.0 仅支持恢复到空白工作区，不会与现有内容合并。当前工作区有内容，请先导出备份，再到下方“原型演示工具”清空后恢复。')));
  }

  function render() {
    U.clear(box); const items = S.sortByUpdated(S.activeContents());
    box.appendChild(h('div', { class: 'eyebrow', text: '你的数据属于你' })); box.appendChild(h('h1', { text: '设置' }));
    box.appendChild(h('p', { class: 'intro', text: '导出可读的 Markdown 用于迁移与阅读；生成完整备份用于恢复。私人备份仅所有者可下载。' }));
    box.appendChild(L.Shell.settingsTabs('data'));

    const list = h('div', { class: 'select-list', role: 'group', 'aria-label': '选择要导出的内容' }, items.length ? items.map((c) => h('label', null,
      h('input', { type: 'checkbox', checked: state.selected.has(c.id), onchange: (e) => { e.target.checked ? state.selected.add(c.id) : state.selected.delete(c.id); } }), c.title || '（无标题）', h('small', { style: 'margin-left:auto;color:var(--muted)', text: c.type }))) : h('p', { class: 'hint', style: 'padding:0 12px', text: '没有可导出的内容。' }));
    box.appendChild(h('section', { class: 'setting-section' }, h('h2', { text: 'Markdown 导出' }), h('p', { text: '保留标题、正文，并尽可能附带来源、标签、空间和分类等元数据（YAML 头）。多选时合并为一个 .md 文件（正式版本可打包为压缩包）。' }),
      h('div', { style: 'display:flex;gap:10px;margin-bottom:6px;flex-wrap:wrap' },
        h('button', { class: 'secondary', type: 'button', text: '全选', onclick: () => { items.forEach((c) => state.selected.add(c.id)); render(); } }),
        h('button', { class: 'secondary', type: 'button', text: '清除选择', onclick: () => { state.selected.clear(); render(); } })),
      list, h('button', { class: 'primary', type: 'button', onclick: exportSelected }, I('download', 17), '导出所选内容')));

    const cnt = S.counts();
    box.appendChild(h('section', { class: 'setting-section' }, h('h2', { text: '完整备份' }), h('p', { text: '包含内容与正文、类型、空间与分类、标签、关联、来源、附件元数据、整理 / 学习 / 发布状态，以及备份清单、格式版本和生成时间。' }),
      h('p', { class: 'hint', text: '当前工作区：' + cnt.contents + ' 条内容 · ' + cnt.spaces + ' 个空间 · ' + cnt.categories + ' 个分类 · ' + cnt.tags + ' 个标签 · ' + cnt.relations + ' 条关联 · ' + cnt.attachments + ' 个附件记录' }),
      h('button', { class: 'primary', type: 'button', onclick: makeBackup }, I('database', 17), '生成并下载完整备份')));

    const fileIn = h('input', { type: 'file', accept: '.json,application/json', hidden: true, onchange: (e) => { onBackupFile(e.target.files[0]); e.target.value = ''; } });
    box.appendChild(h('section', { class: 'setting-section' }, h('h2', { text: '从备份恢复' }), h('p', { text: '选择灵脑备份文件，先预览版本与数量，再确认恢复。恢复保留稳定 ID、关联与来源；仅支持恢复到空白工作区。' }),
      h('button', { class: 'secondary', type: 'button', onclick: () => fileIn.click() }, I('upload', 17), '选择备份文件'), fileIn, h('div', { id: 'restore-slot', style: 'margin-top:14px' })));

    box.appendChild(h('section', { class: 'setting-section' }, h('h2', { text: '原型演示工具' }), h('p', { text: '仅用于演示与测试，正式版本不包含这些入口。' }),
      h('div', { style: 'display:flex;gap:10px;flex-wrap:wrap' },
        h('button', { class: 'secondary', type: 'button', onclick: wipe }, I('trash', 16), '清空工作区'),
        h('button', { class: 'secondary', type: 'button', onclick: async () => { if (!S.isBlankWorkspace() && !(await U.confirmDialog({ title: '重置为示例数据？', danger: true, confirmText: '重置', desc: '当前工作区的所有内容将被示例数据覆盖。' }))) return; S.loadDemoData(); state.selected.clear(); U.toast('已载入示例数据'); L.Shell.renderSidebar(); render(); } }, I('undo', 16), '载入示例数据'))));
    renderRestore();
  }
  render();
})();
