/* 导入中心（PRD 7.7）：文件、网页链接、ChatGPT 对话导出。
   - 以 ImportJob / ImportItem 展示批次与单项状态、失败原因，支持部分成功与重复识别
   - 导入内容默认进入收集箱并保持私有，保留来源
   原型边界：不解析 DOCX / PDF 正文、不抓取网页、不做 OCR；单文件上限与格式白名单待确认（PRD T-01 / T-02 / T-03）。 */
(function () {
  'use strict';
  const L = window.Luma; const S = L.Store; const U = L.UI; const { h, I } = U;
  const MAX_FILE_BYTES = 2 * 1024 * 1024; // 原型限制，正式限制待确认
  const TEXT_EXT = ['md', 'txt']; const BINARY_DOC_EXT = ['docx', 'pdf']; const IMAGE_EXT = ['png', 'jpg', 'jpeg', 'gif', 'webp'];
  const STEP_DELAY_MS = 220;
  const STATUS = { queued: ['排队中', 'mute'], processing: ['处理中', ''], success: ['成功', 'ok'], partial: ['部分成功', 'warn'], failed: ['失败', 'danger'], skipped: ['已跳过', 'mute'] };
  const JOB_LABEL = { file: '文件导入', web: '网页链接', ai: 'ChatGPT 对话' };
  const page = L.Shell.mount({ nav: 'imports', title: '导入中心', crumbs: [{ label: '导入中心' }] }); if (!page) return;
  const expanded = new Set(); let busy = false;
  const box = h('div', { class: 'standard' }); page.appendChild(box);
  const jobsEl = h('div');

  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  const extOf = (name) => (name.split('.').pop() || '').toLowerCase();
  const stripExt = (name) => name.replace(/\.[^.]+$/, '');
  function hash(text) { let x = 5381; for (let i = 0; i < text.length; i += 1) x = ((x << 5) + x + text.charCodeAt(i)) | 0; return (x >>> 0).toString(36); }
  const importedSource = (o) => Object.assign({ id: S.uid('src'), kind: 'other', title: '', url: '', fileName: '', platform: '', externalId: '', occurredAt: null, importedAt: S.nowIso() }, o);
  const attachmentOf = (file) => ({ id: S.uid('att'), name: file.name, size: file.size, mime: file.type || 'application/octet-stream', isPublic: false, role: 'original' });

  /** 以批次方式顺序处理，并实时更新单项状态。tasks: [{name, run: async () => ({status, reason, contentId})}] */
  async function runJob(kind, tasks) {
    if (busy) { U.toast('上一个导入批次还在处理中', 'error'); return; }
    busy = true;
    const job = S.addImportJob({ id: S.uid('job'), kind, createdAt: S.nowIso(), status: 'processing', items: tasks.map((t) => ({ name: t.name, status: 'queued', reason: '', contentId: '' })) });
    expanded.add(job.id); renderJobs();
    for (let i = 0; i < tasks.length; i += 1) {
      job.items[i].status = 'processing'; renderJobs(); await wait(STEP_DELAY_MS);
      try { Object.assign(job.items[i], await tasks[i].run()); } catch (e) { console.error(e); Object.assign(job.items[i], { status: 'failed', reason: '处理时发生错误：' + e.message }); }
      S.updateImportJob(job.id, {}); renderJobs();
    }
    const n = (s) => job.items.filter((x) => x.status === s).length;
    const status = n('failed') === job.items.length ? 'failed' : (n('failed') || n('partial')) ? 'partial' : 'success';
    S.updateImportJob(job.id, { status }); busy = false; renderJobs(); L.Shell.renderSidebar();
    U.toast(status === 'success' ? '导入完成：' + n('success') + ' 项成功，已进入收集箱' : status === 'partial' ? '导入完成，部分项目需要留意' : '导入失败，请查看原因', status === 'failed' ? 'error' : undefined);
  }

  /* ---------- 文件 ---------- */
  function fileTask(file) {
    return { name: file.name, run: async () => {
      const ext = extOf(file.name);
      if (![].concat(TEXT_EXT, BINARY_DOC_EXT, IMAGE_EXT).includes(ext)) return { status: 'failed', reason: '不支持的文件类型（.' + (ext || '无扩展名') + '）。当前支持 md、txt、docx、pdf 与常见图片。' };
      if (file.size === 0) return { status: 'failed', reason: '文件为空' };
      if (file.size > MAX_FILE_BYTES) return { status: 'failed', reason: '文件超过原型限制 ' + U.fmtSize(MAX_FILE_BYTES) + '（正式限制待确认）' };
      let body = ''; let status = 'success'; let reason = ''; let title = stripExt(file.name);
      if (TEXT_EXT.includes(ext)) {
        body = await file.text();
        if (!body.trim()) return { status: 'failed', reason: '文件中没有可导入的文本' };
        if ((body.match(/\uFFFD/g) || []).length > 3) return { status: 'failed', reason: '文本编码无法识别，请另存为 UTF-8 后重试' };
        const heading = /^#\s+(.+)$/m.exec(body); if (heading) title = heading[1].trim().slice(0, 80);
      } else if (BINARY_DOC_EXT.includes(ext)) { body = '（原型未提取正文，已保留原文件。请补充你的摘要。）'; status = 'partial'; reason = '已保留原文件；' + ext.toUpperCase() + ' 正文提取将在正式版本提供'; }
      else { body = '（图片附件。OCR 不在 V1.0 范围内。）'; reason = '作为附件保存'; }
      const fp = 'file:' + file.name + ':' + file.size + ':' + hash(TEXT_EXT.includes(ext) ? body : String(file.lastModified));
      const dup = S.findDuplicate(fp); if (dup) return { status: 'skipped', reason: '与已导入的「' + (dup.title || '无标题') + '」重复，已跳过' };
      const c = S.createContent({ title, body, type: '知识', sources: [importedSource({ kind: 'file', title, fileName: file.name, occurredAt: new Date(file.lastModified).toISOString(), fingerprint: fp })], attachments: [attachmentOf(file)] });
      return { status, reason, contentId: c.id };
    } };
  }
  function onFiles(fileList) { const files = Array.from(fileList || []); if (files.length) runJob('file', files.map(fileTask)); }

  /* ---------- 网页链接 ---------- */
  function onWeb(urlText, summary) {
    let url; try { url = new URL(urlText.trim()); } catch (e) { return '请输入完整的网址，例如 https://example.com/post'; }
    if (!/^https?:$/.test(url.protocol)) return '仅支持 http / https 链接';
    runJob('web', [{ name: url.href, run: async () => {
      const fp = 'url:' + url.href; const dup = S.findDuplicate(fp); if (dup) return { status: 'skipped', reason: '这个链接已保存为「' + (dup.title || '无标题') + '」' };
      const title = url.hostname + (url.pathname.length > 1 ? url.pathname.replace(/\/$/, '') : '');
      const c = S.createContent({ title: title.slice(0, 80), body: summary.trim() || '（原型环境不抓取网页正文。已保存原始链接，可在这里补充你的个人摘要。）', type: '知识',
        sources: [importedSource({ kind: 'web', title, url: url.href, platform: url.hostname, occurredAt: S.nowIso(), fingerprint: fp })] });
      return { status: 'partial', reason: '仅保存了链接与保存时间；正文提取待正式版本（不会绕过登录或付费墙）', contentId: c.id };
    } }]);
    return '';
  }

  /* ---------- ChatGPT 导出 ---------- */
  const isoFromEpoch = (t) => (typeof t === 'number' ? new Date(t * 1000).toISOString() : null);
  function parseChatGpt(text) {
    let data; try { data = JSON.parse(text); } catch (e) { return { ok: false, message: '文件不是有效的 JSON。请选择 ChatGPT 导出包中的 conversations.json。' }; }
    if (!Array.isArray(data) || !data.every((c) => c && typeof c === 'object' && c.mapping && typeof c.mapping === 'object')) return { ok: false, message: '无法识别的导出格式：缺少 conversations 数组或 mapping 字段。目前仅支持 ChatGPT 官方导出的 conversations.json。' };
    const convs = data.map((c, idx) => {
      const chain = []; let node = c.current_node || Object.keys(c.mapping).find((k) => !(c.mapping[k].children || []).length); const seen = new Set();
      while (node && c.mapping[node] && !seen.has(node)) { seen.add(node); chain.unshift(c.mapping[node]); node = c.mapping[node].parent; }
      const messages = chain.map((n) => n.message).filter((m) => m && m.author && ['user', 'assistant'].includes(m.author.role) && m.content && Array.isArray(m.content.parts))
        .map((m) => ({ role: m.author.role, text: m.content.parts.filter((p) => typeof p === 'string').join('\n').trim(), time: isoFromEpoch(m.create_time) })).filter((m) => m.text);
      return { id: String(c.conversation_id || c.id || 'conv-' + idx), title: String(c.title || '未命名对话'), createTime: isoFromEpoch(c.create_time), messages };
    });
    return { ok: true, conversations: convs };
  }
  async function onChatGpt(file) {
    if (!file) return;
    if (file.size > MAX_FILE_BYTES * 5) { U.toast('文件过大，原型暂不处理', 'error'); return; }
    const parsed = parseChatGpt(await file.text());
    if (!parsed.ok) { await U.alertDialog('无法导入这个文件', parsed.message); return; }
    const selected = new Set(parsed.conversations.filter((c) => c.messages.length).map((c) => c.id));
    const list = h('div', { class: 'select-list', role: 'group', 'aria-label': '选择要导入的会话' }, parsed.conversations.map((c) => h('label', null,
      h('input', { type: 'checkbox', checked: selected.has(c.id), disabled: !c.messages.length, onchange: (e) => { e.target.checked ? selected.add(c.id) : selected.delete(c.id); } }),
      h('span', { style: 'flex:1' }, c.title), h('small', { style: 'color:var(--muted)', text: c.messages.length ? c.messages.length + ' 条消息' + (c.createTime ? ' · ' + U.fmtTime(c.createTime) : '') : '无可导入消息' }))));
    const ok = await U.dialog({ title: '选择要导入的会话', desc: '共识别 ' + parsed.conversations.length + ' 个会话。将保留会话标题、消息角色、内容与时间，来源记为 ChatGPT。', content: list, cancelValue: false, actions: [
      { label: '取消', value: false }, { label: '导入所选', value: true, primary: true, validate: () => { if (!selected.size) U.toast('请至少选择一个会话', 'error'); return selected.size > 0; } }] });
    if (!ok) return;
    runJob('ai', parsed.conversations.filter((c) => selected.has(c.id)).map((c) => ({ name: c.title, run: async () => {
      const fp = 'chatgpt:' + c.id; const dup = S.findDuplicate(fp); if (dup) return { status: 'skipped', reason: '该会话已导入为「' + (dup.title || '无标题') + '」' };
      const body = c.messages.map((m) => '### ' + (m.role === 'user' ? '我' : 'ChatGPT') + (m.time ? '　' + U.fmtTime(m.time) : '') + '\n\n' + m.text).join('\n\n');
      const created = S.createContent({ title: c.title.slice(0, 80), body, type: '知识', sources: [importedSource({ kind: 'ai', title: c.title, platform: 'ChatGPT', externalId: c.id, occurredAt: c.createTime, fingerprint: fp })] });
      return { status: 'success', reason: c.messages.length + ' 条消息', contentId: created.id };
    } })));
  }
  function downloadSample() {
    const mk = (id, title, t, pairs) => { const mapping = { root: { id: 'root', parent: null, children: ['n0'], message: null } }; let prev = 'root';
      pairs.forEach(([role, text], i) => { const nid = 'n' + i; mapping[nid] = { id: nid, parent: prev, children: i < pairs.length - 1 ? ['n' + (i + 1)] : [], message: { author: { role }, create_time: t + i * 60, content: { content_type: 'text', parts: [text] } } }; prev = nid; });
      return { id, conversation_id: id, title, create_time: t, current_node: prev, mapping }; };
    const base = Math.floor(Date.now() / 1000) - 86400;
    const sample = [mk('demo-1', 'React Hooks 为什么不能放在条件语句里', base, [['user', 'Hooks 为什么不能写在 if 里？'], ['assistant', '因为 React 依赖调用顺序来对应每个 Hook 的状态。']]),
      mk('demo-2', '周末读书计划', base + 3600, [['user', '帮我安排一个周末读书计划'], ['assistant', '周六上午精读，周日下午整理笔记并写一段总结。']])];
    U.downloadText('conversations-sample.json', JSON.stringify(sample, null, 2), 'application/json;charset=utf-8');
  }

  /* ---------- 渲染 ---------- */
  function renderJobs() {
    U.clear(jobsEl); const jobs = S.state().imports;
    jobsEl.appendChild(h('h2', { style: 'font-size:22px;margin:6px 0 16px', text: '导入记录' }));
    if (!jobs.length) { jobsEl.appendChild(h('p', { class: 'hint', text: '还没有导入记录。导入后，这里会显示每个批次的总数、成功数、失败数和单项原因。' })); return; }
    jobs.forEach((j) => {
      const n = (s) => j.items.filter((x) => x.status === s).length; const open = expanded.has(j.id); const st = j.status === 'processing' ? STATUS.processing : STATUS[j.status];
      jobsEl.appendChild(h('article', { class: 'job' },
        h('button', { class: 'job-head', type: 'button', 'aria-expanded': String(open), onclick: () => { open ? expanded.delete(j.id) : expanded.add(j.id); renderJobs(); } },
          I(open ? 'chevronDown' : 'chevronRight', 17), h('strong', { text: JOB_LABEL[j.kind] || '导入' }), h('span', { class: 'pill ' + st[1], text: st[0] }), h('span', { style: 'font-size:12px;color:var(--muted)', text: U.fmtTime(j.createdAt) }),
          h('span', { class: 'stats', text: '共 ' + j.items.length + ' · 成功 ' + n('success') + ' · 部分 ' + n('partial') + ' · 失败 ' + n('failed') + ' · 跳过 ' + n('skipped') })),
        open ? h('div', { class: 'job-items' }, j.items.map((it) => { const s = STATUS[it.status];
          return h('div', { class: 'job-item' }, h('span', { class: 'pill ' + s[1], text: s[0] }),
            h('div', { class: 'name' }, it.contentId && S.getContent(it.contentId) ? h('a', { href: 'editor.html?id=' + encodeURIComponent(it.contentId), style: 'color:var(--accent)', text: it.name }) : it.name, it.reason ? h('span', { class: 'reason', text: it.reason }) : null)); })) : null));
    });
  }

  function build() {
    const fileIn = h('input', { type: 'file', multiple: true, hidden: true, accept: '.md,.txt,.docx,.pdf,.png,.jpg,.jpeg,.gif,.webp', onchange: (e) => { onFiles(e.target.files); e.target.value = ''; } });
    const drop = h('div', { class: 'dropzone', tabindex: 0, role: 'button', 'aria-label': '拖拽文件到此处，或按回车选择文件', text: '拖拽文件到这里' });
    drop.addEventListener('click', () => fileIn.click()); drop.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); fileIn.click(); } });
    ['dragenter', 'dragover'].forEach((ev) => drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.add('drag'); }));
    ['dragleave', 'drop'].forEach((ev) => drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.remove('drag'); }));
    drop.addEventListener('drop', (e) => onFiles(e.dataTransfer.files));

    const urlIn = h('input', { class: 'field', type: 'url', placeholder: 'https://', 'aria-label': '网页链接' }); const sum = h('textarea', { class: 'field', rows: 2, placeholder: '个人摘要（可选）', 'aria-label': '个人摘要' });
    const urlErr = h('p', { class: 'field-error', role: 'alert' });
    const gptIn = h('input', { type: 'file', accept: '.json,application/json', hidden: true, onchange: (e) => { onChatGpt(e.target.files[0]); e.target.value = ''; } });

    box.appendChild(h('div', { class: 'eyebrow', text: '把分散的内容带回来' })); box.appendChild(h('h1', { text: '导入中心' }));
    box.appendChild(h('p', { class: 'intro', text: '导入的内容默认进入收集箱并保持私有，原始来源会被保留。文件接收成功不等于正文解析成功，会分别反馈。' }));
    box.appendChild(h('div', { class: 'import-grid' },
      h('section', { class: 'import-card' }, I('upload', 30, 'big'), h('h2', { text: '文件' }), h('p', { text: 'Markdown、TXT 解析正文；DOCX、PDF 保留原文件（原型不提取正文）；图片作为附件。单文件不超过 ' + U.fmtSize(MAX_FILE_BYTES) + '。' }), drop, fileIn,
        h('button', { class: 'primary', type: 'button', onclick: () => fileIn.click() }, '选择文件')),
      h('section', { class: 'import-card' }, I('globe', 30, 'big'), h('h2', { text: '网页链接' }), h('p', { text: '保存原始链接与时间。无法获取正文时仍可保存，并补充个人摘要。' }), urlIn, sum, urlErr,
        h('button', { class: 'primary', type: 'button', onclick: () => { urlErr.textContent = onWeb(urlIn.value, sum.value); if (!urlErr.textContent) { urlIn.value = ''; sum.value = ''; } } }, '保存链接')),
      h('section', { class: 'import-card' }, I('chat', 30, 'big'), h('h2', { text: 'ChatGPT 对话' }), h('p', { text: '选择官方导出包中的 conversations.json，预览并勾选要导入的会话。真实导出样本的兼容性待验证。' }), gptIn,
        h('button', { class: 'primary', type: 'button', onclick: () => gptIn.click() }, '选择导出文件'), h('button', { class: 'text-button', type: 'button', onclick: downloadSample, text: '下载示例文件用于试用' }))));
    box.appendChild(jobsEl); renderJobs();
  }
  build();
})();
