/* Studio 控制台（PRD 7.2 / 7.3）：快速记录、最近内容、收集箱入口、空间入口、空状态引导。 */
(function () {
  'use strict';
  const L = window.Luma; const S = L.Store; const U = L.UI; const { h, I } = U;
  const page = L.Shell.mount({ nav: 'home', title: '控制台', crumbs: [{ label: '控制台' }] }); if (!page) return;

  const typeSel = { value: '想法' };
  const typeLabel = h('span', { text: typeSel.value });
  const typeButton = h('button', { class: 'type-trigger', type: 'button', 'aria-label': '内容类型：想法', 'aria-haspopup': 'menu', 'aria-expanded': 'false', 'aria-controls': 'quick-type-menu' }, I('bulb', 17), typeLabel, I('chevronDown', 14));
  const typeMenu = h('div', { class: 'type-menu', id: 'quick-type-menu', role: 'menu', 'aria-label': '内容类型', hidden: true });
  const typePicker = h('div', { class: 'type-picker' }, typeButton, typeMenu);
  const typeOptions = S.CONTENT_TYPES.map((type) => {
    const option = h('button', { type: 'button', role: 'menuitemradio', 'aria-checked': String(type === typeSel.value), tabindex: '-1' }, h('span', { text: type }), I('check', 15));
    option.addEventListener('click', () => {
      typeSel.value = type; typeLabel.textContent = type;
      typeButton.setAttribute('aria-label', '内容类型：' + type);
      typeOptions.forEach((el, i) => el.setAttribute('aria-checked', String(S.CONTENT_TYPES[i] === type)));
      closeTypeMenu(true);
    });
    typeMenu.appendChild(option); return option;
  });
  function closeTypeMenu(restoreFocus) {
    typeMenu.hidden = true; typeButton.setAttribute('aria-expanded', 'false');
    if (restoreFocus) typeButton.focus();
  }
  function openTypeMenu(index) {
    typeMenu.hidden = false; typeButton.setAttribute('aria-expanded', 'true');
    typeOptions[index === undefined ? S.CONTENT_TYPES.indexOf(typeSel.value) : index].focus();
  }
  typeButton.addEventListener('click', () => typeMenu.hidden ? openTypeMenu() : closeTypeMenu(false));
  typeButton.addEventListener('keydown', (e) => {
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') { e.preventDefault(); openTypeMenu(e.key === 'ArrowDown' ? 0 : typeOptions.length - 1); }
  });
  typeMenu.addEventListener('keydown', (e) => {
    const index = typeOptions.indexOf(document.activeElement);
    if (e.key === 'Escape') { e.preventDefault(); closeTypeMenu(true); }
    else if (e.key === 'Tab') closeTypeMenu(false);
    else if (['ArrowDown', 'ArrowUp', 'Home', 'End'].includes(e.key)) {
      e.preventDefault();
      const next = e.key === 'Home' ? 0 : e.key === 'End' ? typeOptions.length - 1 : (index + (e.key === 'ArrowDown' ? 1 : -1) + typeOptions.length) % typeOptions.length;
      typeOptions[next].focus();
    }
  });
  document.addEventListener('pointerdown', (e) => { if (!typePicker.contains(e.target)) closeTypeMenu(false); });
  typePicker.addEventListener('focusout', (e) => { if (!typePicker.contains(e.relatedTarget)) closeTypeMenu(false); });
  const titleIn = h('input', { type: 'text', 'aria-label': '记录标题', placeholder: '给这个想法起个名字…', maxlength: 80 });
  const body = h('textarea', { class: 'quick-body', 'aria-label': '记录正文', placeholder: '从一句话开始，分类可以稍后再做。支持 Markdown。' });
  const saveBtn = h('button', { class: 'primary', type: 'button', text: '保存到收集箱' });
  const recentBox = h('div'); const rail = h('aside', { class: 'continue', 'aria-label': '继续处理' });

  const markDirty = () => U.Guard.set(!!(titleIn.value.trim() || body.value.trim()));
  titleIn.addEventListener('input', markDirty); body.addEventListener('input', markDirty);

  function save() {
    const text = body.value.trim();
    if (!text) { U.toast('先写下一点内容，再保存', 'error'); body.focus(); return; }
    try {
      const firstLine = text.split('\n')[0].replace(/^#+\s*/, '').slice(0, 32);
      S.createContent({ title: titleIn.value.trim() || firstLine, body: body.value, type: typeSel.value }); // 默认进入收集箱并保持私有
      titleIn.value = ''; body.value = ''; U.Guard.set(false);
      U.toast('已保存到收集箱'); L.Shell.renderSidebar(); renderLists(); body.focus();
    } catch (e) { console.error(e); U.toast('保存失败，请重试', 'error'); }
  }
  saveBtn.addEventListener('click', save);
  body.addEventListener('keydown', (e) => { if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') { e.preventDefault(); save(); } });

  function continueItem(c) {
    return h('a', { class: 'continue-item', href: 'editor.html?id=' + encodeURIComponent(c.id) }, I('file', 22),
      h('div', null, h('strong', { text: c.title || '（无标题）' }), h('p', { text: U.stripMd(c.body) }), h('small', { text: '更新于 ' + U.fmtTime(c.updatedAt) })));
  }

  function renderLists() {
    const all = S.sortByUpdated(S.activeContents());
    const cont = all.filter((c) => c.organize === 'organized').slice(0, 3); // 继续处理：已整理的正式内容
    const recent = all.filter((c) => !cont.includes(c)).slice(0, 3); // 最近记录：其余最近更新（含收集箱）
    U.clear(recentBox); U.clear(rail);
    if (!all.length) {
      recentBox.appendChild(h('div', { class: 'onboarding' }, h('h2', { text: '这里还是空的，从第一条记录开始' }),
        h('ol', null, h('li', { text: '在上方写下一句话，保存到收集箱' }), h('li', { text: '到「知识空间」创建属于你的空间和分类' }), h('li', { text: '用「导入中心」把已有资料带进来' }))));
    } else if (recent.length) {
      recentBox.appendChild(h('section', { class: 'recent' }, h('h2', { text: '最近记录' }), recent.map((c) => U.noteRow(c))));
    }
    rail.appendChild(h('h2', { text: '继续上次的思考' }));
    if (cont.length) cont.forEach((c) => rail.appendChild(continueItem(c)));
    else rail.appendChild(h('p', { class: 'hint', text: '还没有可以继续的内容。' }));
    rail.appendChild(h('div', { class: 'rail-block' }, h('h3', { text: '知识空间' }),
      h('div', { class: 'chip-row' }, S.listSpaces().map((s) => h('a', { class: 'chip-link', href: 'space.html?id=' + s.id }, I('folder', 16), s.name, ' ', h('small', { text: String(S.contentsInSpace(s.id).length) }))),
        S.listSpaces().length ? null : h('a', { class: 'chip-link', href: 'spaces.html' }, I('plus', 16), '创建空间'))));
    rail.appendChild(h('div', { class: 'rail-block' }, h('h3', { text: '常用操作' }), h('div', { class: 'chip-row' },
      h('a', { class: 'chip-link', href: 'imports.html' }, I('download', 16), '导入资料'),
      h('a', { class: 'chip-link', href: 'search.html' }, I('search', 16), '搜索'),
      h('a', { class: 'chip-link', href: 'data.html' }, I('database', 16), '导出与备份'))));
    const n = S.inboxCount();
    rail.appendChild(h('a', { class: 'inbox-link', href: 'inbox.html' }, I('inbox', 22), n ? '收集箱还有 ' + n + ' 条待整理' : '收集箱已清空', I('arrowRight', 19)));
  }

  page.appendChild(h('div', { class: 'home' },
    h('section', { class: 'writing' },
      h('h1', { text: '今天，想记住什么？' }), h('p', { class: 'date', text: U.fmtDateLong(new Date()) }),
      h('div', { class: 'quick-title' }, typePicker, titleIn),
      body,
      h('div', { class: 'toolbar' }, L.EditTools.toolbar(body), saveBtn),
      recentBox),
    rail));
  renderLists();
  if (window.location.hash === '#new') body.focus();
  window.addEventListener('hashchange', () => { if (window.location.hash === '#new') body.focus(); });
})();
