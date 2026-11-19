/* Studio 控制台（PRD 7.2 / 7.3）：快速记录、最近内容、收集箱入口、空间入口、空状态引导。 */
(function () {
  'use strict';
  const L = window.Luma; const S = L.Store; const U = L.UI; const { h, I, t } = U;
  const page = L.Shell.mount({ nav: 'home', title: t('此刻', 'Now'), crumbs: [{ label: t('此刻', 'Now') }] }); if (!page) return;

  const displayType = (type) => ({ 知识: t('知识', 'Knowledge'), 经历: t('经历', 'Experience'), 记忆记录: t('记忆记录', 'Memory'), 想法: t('想法', 'Thought') })[type] || type;
  const typeSel = { value: '想法' };
  const typeLabel = h('span', { text: displayType(typeSel.value) });
  const typeButton = h('button', { class: 'type-trigger', type: 'button', 'aria-label': '内容类型：想法', 'aria-haspopup': 'menu', 'aria-expanded': 'false', 'aria-controls': 'quick-type-menu' }, I('bulb', 17), typeLabel, I('chevronDown', 14));
  const typeMenu = h('div', { class: 'type-menu', id: 'quick-type-menu', role: 'menu', 'aria-label': '内容类型', hidden: true });
  const typePicker = h('div', { class: 'type-picker' }, typeButton, typeMenu);
  const typeOptions = S.CONTENT_TYPES.map((type) => {
    const option = h('button', { type: 'button', role: 'menuitemradio', 'aria-checked': String(type === typeSel.value), tabindex: '-1' }, h('span', { text: displayType(type) }), I('check', 15));
    option.addEventListener('click', () => {
      typeSel.value = type; typeLabel.textContent = displayType(type);
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
  const titleIn = h('input', { type: 'text', 'aria-label': t('记录标题', 'Note title'), placeholder: t('给这个想法起个名字…', 'Give this note a title…'), maxlength: 80 });
  const body = h('textarea', { class: 'quick-body', 'aria-label': t('记录正文', 'Note body'), placeholder: t('从一句话开始，分类可以稍后再做。支持 Markdown。', 'Start with a sentence. Markdown supported.') });
  const saveBtn = h('button', { class: 'primary min-h-[36px]! rounded-lg! px-3! text-sm!', type: 'button', text: t('保存到收集箱', 'Save to inbox') });
  const recentBox = h('section', { class: 'home-records', 'aria-label': t('最近记录', 'Recent notes') });
  let richEditor, richLoading;
  const richBody = h('div', { class: 'rich-note capture-rich', hidden: true });
  const plainTools = L.EditTools.toolbar(body);
  const richTools = h('div', { class: 'format-tools', role: 'group', 'aria-label': '正文格式', hidden: true });
  const composerPanel = h('div', { id: 'home-composer-panel', hidden: true },
    h('div', { class: 'quick-title' }, typePicker, titleIn), body, richBody,
    h('div', { class: 'toolbar' }, plainTools, richTools, saveBtn));
  const composerToggle = h('button', { class: 'capture-trigger min-h-12 px-4! py-3! hover:bg-[var(--side)]!', type: 'button', 'aria-expanded': 'false', 'aria-controls': 'home-composer-panel' }, I('plus', 18), h('span', { text: t('记录此刻', 'Capture a thought') }), h('small', { text: t('有什么想留下？', 'What would you like to remember?') }));
  const collapseBtn = h('button', { class: 'text-button', type: 'button', text: t('收起', 'Collapse'), onclick: () => setExpanded(false) });
  const composer = h('section', { class: 'home-capture mb-8! rounded-lg!', 'aria-label': t('记录此刻', 'Capture a thought') }, composerToggle, composerPanel, collapseBtn);
  function setExpanded(expanded) {
    composerPanel.hidden = !expanded; collapseBtn.hidden = !expanded; composerToggle.hidden = expanded;
    composerToggle.setAttribute('aria-expanded', String(expanded));
    if (expanded) {
      focusBody();
      richLoading ??= loadRichEditor();
      richLoading.then(showRichWhenReady);
    } else composerToggle.focus();
  }
  composerToggle.addEventListener('click', () => setExpanded(true));
  collapseBtn.hidden = true;

  function focusBody() {
    if (richBody.hidden) body.focus();
    else richEditor.commands.focus();
  }

  function showRichWhenReady() {
    if (!richEditor || composerPanel.hidden || !richBody.hidden || body.value) return;
    const restoreFocus = document.activeElement === body;
    body.hidden = true; plainTools.hidden = true;
    richBody.hidden = false; richTools.hidden = false;
    if (restoreFocus) focusBody();
  }

  async function loadRichEditor() {
    try {
      const [{ Editor }, { default: StarterKit }, { Markdown }] = await Promise.all([
        import('https://cdn.jsdelivr.net/npm/@tiptap/core@3.31.3/+esm'),
        import('https://cdn.jsdelivr.net/npm/@tiptap/starter-kit@3.31.3/+esm'),
        import('https://cdn.jsdelivr.net/npm/@tiptap/markdown@3.31.3/+esm')
      ]);
      const formats = [
        ['H2', '二级标题', 'toggleHeading', 'heading', { level: 2 }],
        ['B', '加粗', 'toggleBold', 'bold'],
        ['I', '斜体', 'toggleItalic', 'italic'],
        ['列表', '项目列表', 'toggleBulletList', 'bulletList'],
        ['引用', '引用', 'toggleBlockquote', 'blockquote'],
        ['代码', '代码块', 'toggleCodeBlock', 'codeBlock']
      ];
      const buttons = formats.map(([text, label, command, , attrs]) =>
        h('button', { type: 'button', text, title: label, 'aria-label': label, 'aria-pressed': 'false',
          onclick: () => richEditor.chain().focus()[command](attrs).run() }));
      const syncFormats = ({ editor }) => formats.forEach(([, , , mark, attrs], index) =>
        buttons[index].setAttribute('aria-pressed', String(editor.isActive(mark, attrs))));
      richEditor = new Editor({
        element: richBody, extensions: [StarterKit.configure({ link: { openOnClick: false } }), Markdown],
        editorProps: { attributes: { role: 'textbox', 'aria-label': t('记录正文', 'Note body'), 'aria-multiline': 'true' } },
        onUpdate: (event) => {
          body.value = event.editor.getMarkdown();
          markDirty();
          syncFormats(event);
        },
        onSelectionUpdate: syncFormats
      });
      richTools.append(...buttons);
    } catch (error) {
      console.warn('首页可视化快记加载失败', error);
    }
  }

  const markDirty = () => U.Guard.set(!!(titleIn.value.trim() || body.value.trim()));
  titleIn.addEventListener('input', markDirty); body.addEventListener('input', markDirty);

  function save() {
    const text = body.value.trim();
    if (!text) { U.toast(t('先写下一点内容，再保存', 'Write something before saving.'), 'error'); focusBody(); return; }
    try {
      const firstLine = text.split('\n')[0].replace(/^#+\s*/, '').slice(0, 32);
      S.createContent({ title: titleIn.value.trim() || firstLine, body: body.value, type: typeSel.value }); // 默认进入收集箱并保持私有
      titleIn.value = ''; body.value = '';
      if (!richBody.hidden) {
        richEditor.destroy();
        richEditor = richLoading = undefined;
        richTools.replaceChildren();
        richBody.hidden = richTools.hidden = true;
        body.hidden = plainTools.hidden = false;
      }
      U.Guard.set(false);
      U.toast(t('已保存到收集箱', 'Saved to inbox')); L.Shell.renderSidebar(); renderLists(); setExpanded(false);
    } catch (e) { console.error(e); U.toast(t('保存失败，请重试', 'Could not save. Try again.'), 'error'); }
  }
  saveBtn.addEventListener('click', save);
  composerPanel.addEventListener('keydown', (e) => { if ((e.target === body || richBody.contains(e.target)) && (e.ctrlKey || e.metaKey) && e.key === 'Enter') { e.preventDefault(); save(); } });

  function renderLists() {
    const all = S.sortByUpdated(S.activeContents());
    U.clear(recentBox);
    recentBox.appendChild(h('div', { class: 'home-section-heading' }, h('h2', { class: 'text-lg!', text: t('最近记录', 'Recent notes') }), h('a', { href: 'search.html', text: t('查找记录', 'Find notes') }, I('arrowRight', 14))));
    if (!all.length) {
      recentBox.appendChild(h('div', { class: 'home-empty' }, h('p', { text: t('从此刻开始，留下一点自己的痕迹。', 'Your notes will appear here.') }), h('span', { text: t('一句想法、一段经历，或一个还没有答案的问题。', 'Capture a thought, an experience, or an open question.') })));
      return;
    }
    const recordList = h('div', { class: 'home-record-list' });
    recentBox.appendChild(recordList);
    all.slice(0, 6).forEach((c) => {
      const excerpt = U.stripMd(c.body).replace(/\s+/g, ' ').trim();
      recordList.appendChild(h('a', { class: 'home-record', href: 'editor.html?id=' + encodeURIComponent(c.id) },
        h('div', { class: 'home-record-meta text-xs!' }, h('span', { text: displayType(c.type) }), h('span', { text: t('更新于 ', 'Updated ') + U.fmtTime(c.updatedAt) })),
        h('h3', { text: c.title || t('（无标题）', 'Untitled') }),
        excerpt ? h('p', { text: excerpt }) : null));
    });
  }

  page.appendChild(h('div', { class: 'home home-personal' },
    h('header', { class: 'home-intro mb-6!' }, h('p', { class: 'home-date', text: U.fmtDateLong(new Date()) }),
      h('h1', { text: t('此刻', 'Now') })),
    composer, recentBox));
  renderLists();
  if (window.location.hash === '#new') setExpanded(true);
  window.addEventListener('hashchange', () => { if (window.location.hash === '#new') setExpanded(true); });
})();
