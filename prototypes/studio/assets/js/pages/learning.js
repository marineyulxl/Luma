/* 学习中心（PRD 7.11）：按手动维护的学习状态查看、筛选与调整；不自动推断掌握度。 */
(function () {
  'use strict';
  const L = window.Luma; const S = L.Store; const U = L.UI; const { h, I } = U;
  const page = L.Shell.mount({ nav: 'learning', title: '学习中心', crumbs: [{ label: '学习中心' }] }); if (!page) return;
  const st = { tab: '' };
  const box = h('div', { class: 'standard' }); page.appendChild(box);

  function render() {
    U.clear(box);
    const all = S.sortByUpdated(S.activeContents().filter((c) => c.learning));
    const list = st.tab ? all.filter((c) => c.learning === st.tab) : all;
    box.appendChild(h('div', { class: 'eyebrow', text: '让积累再次发生作用' }));
    box.appendChild(h('h1', { text: '学习中心' }));
    box.appendChild(h('p', { class: 'intro', text: '按你主动设置的学习状态回到内容。状态完全由你手动维护，不会根据阅读次数自动推断；复习调度与出题不在 V1.0 范围。' }));
    const tab = (value, label) => h('button', { type: 'button', class: st.tab === value ? 'selected' : '', text: label + ' ' + (value ? all.filter((c) => c.learning === value).length : all.length), onclick: () => { st.tab = value; render(); } });
    box.appendChild(h('div', { class: 'tabs' }, tab('', '全部'), S.LEARNING_STATES.map((s) => tab(s, s))));
    box.appendChild(h('div', { class: 'list-heading' }, h('span', { text: list.length + ' 条内容' }), h('span', { text: '学习状态' })));
    if (!list.length) { box.appendChild(U.emptyState('book', all.length ? '这个状态下还没有内容' : '还没有设置学习状态的内容', '打开任意内容，在右侧“学习状态”中选择即可加入学习中心。')); return; }
    list.forEach((c) => {
      const select = U.selectEl([{ value: '', label: '清除状态' }].concat(S.LEARNING_STATES.map((s) => ({ value: s, label: s }))), c.learning, { 'aria-label': '修改《' + c.title + '》的学习状态', style: 'width:130px;position:relative;z-index:1' });
      select.addEventListener('click', (e) => e.stopPropagation());
      select.addEventListener('change', () => { S.setLearning(c.id, select.value); U.toast(select.value ? '学习状态已更新为「' + select.value + '」' : '已清除学习状态'); render(); });
      box.appendChild(U.noteRow(c, { actions: select }));
    });
  }
  render();
})();
