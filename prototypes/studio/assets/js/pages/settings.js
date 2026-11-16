/* 账户设置（PRD 4.3 / 7.1）：修改密码、退出登录；忘记密码由服务器管理员重置。 */
(function () {
  'use strict';
  const L = window.Luma; const U = L.UI; const { h, I } = U;
  const page = L.Shell.mount({ nav: 'settings', title: '账户设置', crumbs: [{ label: '设置' }, { label: '账户' }] }); if (!page) return;

  const field = (label, name, autocomplete) => {
    const input = h('input', { class: 'field', type: 'password', name, autocomplete, 'aria-label': label });
    const err = h('p', { class: 'field-error', role: 'alert' });
    return { input, err, node: h('label', { class: 'field-label' }, label, input, err) };
  };
  const cur = field('当前密码', 'current', 'current-password'); const next = field('新密码', 'next', 'new-password'); const again = field('确认新密码', 'again', 'new-password');
  const submit = h('button', { class: 'primary', type: 'submit', text: '修改密码' });

  const form = h('form', { class: 'form-narrow', novalidate: true }, cur.node, next.node, again.node, submit,
    h('p', { class: 'hint', text: '密码策略与会话有效期的具体参数待确认（PRD T-08）；原型仅校验长度不少于 ' + L.Store.MIN_PASSWORD_LENGTH + ' 位。' }));
  form.addEventListener('submit', (e) => {
    e.preventDefault(); [cur, next, again].forEach((f) => { f.err.textContent = ''; });
    if (!cur.input.value) { cur.err.textContent = '请输入当前密码'; return; }
    if (next.input.value !== again.input.value) { again.err.textContent = '两次输入的新密码不一致'; return; }
    submit.disabled = true;
    const r = L.Auth.changePassword(cur.input.value, next.input.value);
    submit.disabled = false;
    if (!r.ok) { (r.field === 'current' ? cur : next).err.textContent = r.message; return; }
    form.reset(); U.toast('密码已修改');
  });

  const owner = L.Auth.owner();
  page.appendChild(h('div', { class: 'standard settings' },
    h('div', { class: 'eyebrow', text: '你的私人工作室' }), h('h1', { text: '设置' }), h('p', { class: 'intro', text: '灵脑 V1.0 只有一个所有者账号，没有公开注册。' }),
    L.Shell.settingsTabs('account'),
    h('section', { class: 'setting-section' }, h('h2', { text: '账户信息' }), h('dl', { class: 'kv' }, h('dt', { text: '账号' }), h('dd', { text: owner.account }), h('dt', { text: '显示名称' }), h('dd', { text: owner.displayName }), h('dt', { text: '角色' }), h('dd', { text: '所有者' }))),
    h('section', { class: 'setting-section' }, h('h2', { text: '修改密码' }), h('p', { text: '忘记密码时，需要由服务器管理员重置，V1.0 不提供公开邮件找回。' }), form),
    h('section', { class: 'setting-section' }, h('h2', { text: '退出登录' }), h('p', { text: '退出后会话失效，需要重新登录才能访问 Studio。' }),
      h('button', { class: 'secondary', type: 'button', onclick: async () => { if (U.Guard.dirty && !(await U.Guard.confirmLeave())) return; L.Auth.logout(); window.location.href = 'login.html'; } }, I('logout', 17), '退出登录'))));
})();
