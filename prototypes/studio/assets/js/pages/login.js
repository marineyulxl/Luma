/* 登录页（PRD 7.1）：账号、密码、提交中状态、密码显隐、通用错误提示、基础限流。 */
(function () {
  'use strict';
  const L = window.Luma; const { h, I } = L.UI; const root = document.getElementById('app');

  function safeNext() {
    const n = L.UI.qs('next');
    return /^[a-z-]+\.html(\?[\w=&%-]*)?$/i.test(n) && n !== 'login.html' ? n : 'index.html';
  }
  if (L.Auth.isLoggedIn()) { window.location.replace(safeNext()); return; }

  const account = h('input', { class: 'field', type: 'text', id: 'account', autocomplete: 'username', 'aria-label': '账号', placeholder: '账号' });
  const password = h('input', { class: 'field', type: 'password', id: 'password', autocomplete: 'current-password', 'aria-label': '密码', placeholder: '密码' });
  const eye = h('button', { class: 'icon-button', type: 'button', 'aria-label': '显示密码', title: '显示/隐藏密码' }, I('eye', 19));
  const error = h('p', { class: 'field-error', role: 'alert' });
  const submit = h('button', { class: 'primary full', type: 'submit', text: '登录' });
  let timer = null;

  eye.addEventListener('click', () => {
    const show = password.type === 'password'; password.type = show ? 'text' : 'password';
    eye.setAttribute('aria-label', show ? '隐藏密码' : '显示密码'); eye.replaceChildren(I(show ? 'eyeOff' : 'eye', 19));
  });

  function showLock() {
    const left = L.Auth.lockRemainingMs();
    if (left <= 0) { clearInterval(timer); timer = null; error.textContent = ''; submit.disabled = false; return; }
    submit.disabled = true; error.textContent = '尝试次数过多，请 ' + Math.ceil(left / 1000) + ' 秒后再试';
  }

  const form = h('form', { class: 'login-card', novalidate: true },
    h('div', { class: 'brand' }, h('img', { src: 'assets/img/luma-mark.png', alt: '' }), h('span', null, 'Luma 灵脑 ', h('em', { text: 'Studio' }))),
    h('h1', { text: '登录你的私人工作室' }),
    h('p', { class: 'intro', style: 'margin-bottom:24px', text: '让知识成为记忆，让记忆产生联系，让联系辅助思考。' }),
    h('label', { class: 'field-label' }, '账号', account),
    h('label', { class: 'field-label' }, '密码', h('div', { class: 'pw-wrap' }, password, eye)),
    error, submit,
    h('p', { class: 'hint', text: '没有公开注册入口。忘记密码请联系服务器管理员重置。' }),
    h('div', { class: 'demo-hint' }, h('strong', { text: '原型演示账号' }), h('br'), '账号：owner　密码：luma-demo-2026', h('br'), '真实认证、会话与限流由正式后端实现（待技术设计）。'));

  form.addEventListener('submit', (e) => {
    e.preventDefault();
    if (!account.value.trim() || !password.value) { error.textContent = '请输入账号和密码'; return; }
    submit.disabled = true; submit.textContent = '登录中…'; error.textContent = '';
    setTimeout(() => {
      const r = L.Auth.login(account.value.trim(), password.value);
      submit.textContent = '登录';
      if (r.ok) { window.location.replace(safeNext()); return; }
      if (r.code === 'locked') { showLock(); timer = setInterval(showLock, 1000); return; }
      submit.disabled = false; error.textContent = '账号或密码不正确'; // 通用错误，不泄露账号是否存在
      password.value = ''; password.focus();
    }, 500);
  });

  root.appendChild(h('div', { class: 'login-page' }, form));
  document.title = '登录 · 灵脑 Studio';
  if (L.Auth.lockRemainingMs() > 0) { showLock(); timer = setInterval(showLock, 1000); }
  account.focus();
})();
