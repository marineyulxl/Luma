/* 文本编辑辅助：为 textarea 提供 Markdown 快捷格式按钮。
   原型使用 textarea + Markdown 源码模拟编辑体验；正式版本使用 Tiptap（PRD 7.4），行为以 PRD 为准。 */
(function (global) {
  'use strict';
  const L = (global.Luma = global.Luma || {});

  function emit(ta) { ta.dispatchEvent(new global.Event('input', { bubbles: true })); ta.focus(); }

  /** 用 before/after 包裹选中文字；无选区时插入占位文字并选中。 */
  function wrap(ta, before, after, placeholder) {
    const s = ta.selectionStart, e = ta.selectionEnd; const sel = ta.value.slice(s, e) || placeholder;
    ta.value = ta.value.slice(0, s) + before + sel + after + ta.value.slice(e);
    ta.selectionStart = s + before.length; ta.selectionEnd = s + before.length + sel.length; emit(ta);
  }
  /** 为选区覆盖的每一行添加前缀（列表 / 引用）。 */
  function prefixLines(ta, makePrefix) {
    const s = ta.selectionStart, e = ta.selectionEnd;
    const start = ta.value.lastIndexOf('\n', s - 1) + 1; let end = ta.value.indexOf('\n', e); if (end < 0) end = ta.value.length;
    const lines = ta.value.slice(start, end).split('\n').map((line, i) => makePrefix(i) + line);
    ta.value = ta.value.slice(0, start) + lines.join('\n') + ta.value.slice(end);
    ta.selectionStart = start; ta.selectionEnd = start + lines.join('\n').length; emit(ta);
  }

  /** 返回格式工具条节点。opts.onImage 为图片按钮回调（原型不实现上传）。 */
  L.EditTools = {
    wrap, prefixLines,
    toolbar(ta, opts) {
      const U = L.UI, h = U.h, I = U.I; const o = opts || {};
      const btn = (icon, label, fn) => h('button', { type: 'button', title: label, 'aria-label': label, onmousedown: (e) => e.preventDefault(), onclick: fn }, I(icon, 19));
      return h('div', { class: 'format-tools', role: 'toolbar', 'aria-label': '格式工具' },
        btn('bold', '加粗', () => wrap(ta, '**', '**', '加粗文字')),
        btn('italic', '斜体', () => wrap(ta, '*', '*', '斜体文字')),
        btn('strike', '删除线', () => wrap(ta, '~~', '~~', '删除线文字')),
        btn('list', '项目列表', () => prefixLines(ta, () => '- ')),
        btn('listOrdered', '编号列表', () => prefixLines(ta, (i) => (i + 1) + '. ')),
        btn('quote', '引用', () => prefixLines(ta, () => '> ')),
        btn('code', '代码块', () => wrap(ta, '```\n', '\n```', '代码')),
        h('span', { class: 'tool-sep' }),
        btn('link', '插入链接', () => wrap(ta, '[', '](https://)', '链接文字')),
        btn('image', '添加图片', () => (o.onImage ? o.onImage() : U.toast('图片上传将在正式编辑器中提供'))));
    }
  };
})(window);
