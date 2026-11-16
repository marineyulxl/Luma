/* Studio 外观设置（PRD 7.15）：两种底色 × 四种强调色，独立选择、即时生效、保存在当前浏览器。
   仅影响 Studio 界面，不影响正文内容颜色、Explore 公开样式、权限与发布状态。 */
(function () {
  'use strict';
  const L = window.Luma; const S = L.Store; const U = L.UI; const { h, I } = U;
  const page = L.Shell.mount({ nav: 'settings', title: '外观设置', crumbs: [{ label: '设置', href: 'settings.html' }, { label: '外观' }] }); if (!page) return;
  const box = h('div', { class: 'standard settings' }); page.appendChild(box);
  const BASE_DESC = { 暖白: '柔和温润，像一张纸', 清白: '干净清晰，专注内容' };

  function render() {
    const theme = L.Theme.get(); U.clear(box);
    box.appendChild(h('div', { class: 'eyebrow', text: '让工作室更像你' })); box.appendChild(h('h1', { text: '外观设置' }));
    box.appendChild(h('p', { class: 'intro', text: '选择舒服的底色与强调色，让记录自然发生。选择后即时生效。' }));
    box.appendChild(L.Shell.settingsTabs('appearance'));
    box.appendChild(h('section', { class: 'setting-section' }, h('h2', { text: '界面底色' }), h('p', { text: '为侧栏、画布和文字选择一套基础搭配。' }),
      h('div', { class: 'base-options', role: 'radiogroup', 'aria-label': '界面底色' }, S.BASES.map((b) => h('button', { type: 'button', role: 'radio', 'aria-checked': String(theme.base === b), class: 'base-option' + (theme.base === b ? ' selected' : ''),
        onclick: () => { L.Theme.set({ base: b }); render(); } },
        h('div', { class: 'mini-preview ' + (b === '暖白' ? '' : 'cool-preview') }, h('div'), h('section', null, h('span'), h('span'), h('span'))),
        h('strong', { text: b }), h('small', { text: BASE_DESC[b] }), theme.base === b ? I('check', 20) : null)))));
    box.appendChild(h('section', { class: 'setting-section' }, h('h2', { text: '主题强调色' }), h('p', { text: '用于主按钮、链接、选中状态和输入焦点。' }),
      h('div', { class: 'accent-options', role: 'radiogroup', 'aria-label': '主题强调色' }, Object.keys(S.ACCENTS).map((name) => h('button', { type: 'button', role: 'radio', 'aria-checked': String(theme.accent === name), class: theme.accent === name ? 'selected' : '',
        onclick: () => { L.Theme.set({ accent: name }); render(); } },
        h('span', { class: 'color-dot', style: 'background:' + S.ACCENTS[name][0] }, theme.accent === name ? I('check', 16) : null), name)))));
    box.appendChild(h('div', { class: 'theme-sample' }, h('span', { class: 'pill', text: '预览' }),
      h('div', null, h('strong', { text: '让知识成为记忆，让记忆产生联系。' }), h('p', { text: '你的内容保持原样，主题只改变工作台外观。' })),
      h('a', { class: 'primary', href: 'index.html' }, '返回工作台', I('arrowRight', 17))));
    box.appendChild(h('p', { class: 'saved-preference' }, I('check', 15), '偏好自动保存在当前浏览器，不影响 Explore 公开页面；暂不提供跨设备同步、深色模式与自定义色号。'));
    box.appendChild(h('button', { class: 'text-button', type: 'button', text: '恢复默认外观（暖白 + 灰紫）', onclick: () => { L.Theme.reset(); render(); U.toast('已恢复默认主题'); } }));
  }
  render();
})();
