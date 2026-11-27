/* 灵脑 Studio 原型数据层
   - 仅使用浏览器 localStorage 模拟后端，没有真实服务端、鉴权或同步。
   - 数据对象与 PRD / CORE-DOMAIN-MODEL 的产品职责对齐：
     Content、Space、Category、Tag、ContentRelation、ContentSource、Attachment、ImportJob、Publication。
   - 整理状态（organize）、发布状态（publish.status）相互独立。 */
(function (global) {
  'use strict';
  const L = (global.Luma = global.Luma || {});

  const DATA_KEY = 'luma-studio-proto-data-v2';
  const THEME_KEY = 'luma-studio-proto-theme-v1';
  const OWNER_KEY = 'luma-studio-proto-owner-v1';
  const SESSION_KEY = 'luma-studio-proto-session-v1';
  const LOGIN_GUARD_KEY = 'luma-studio-proto-login-guard-v1';
  const FORMAT_VERSION = 1;

  const CONTENT_TYPES = ['知识', '经历', '记忆记录', '想法']; // Knowledge / Experience / Memory / Thought
  const ORGANIZE_LABEL = { inbox: '待整理', organized: '已整理', archived: '已归档' };
  const PUBLISH_LABEL = { draft: '私有草稿', published: '已发布', withdrawn: '已撤回' };
  const RELATION_TYPES = { related: '相关', prerequisite: '前置知识', application: '实际应用', contrast: '对比' };
  const ACCENTS = { 灰紫: ['#795d8c', '#eee7f1'], 靛蓝: ['#5263c7', '#eef0fa'], 松绿: ['#356c59', '#e8f1ec'], 石墨: ['#49494e', '#e9e9ec'] };
  const BASES = ['暖白', '清白'];
  const DEFAULT_THEME = { base: '暖白', accent: '灰紫' };
  const DEFAULT_OWNER = { account: 'owner', password: 'luma-demo-2026', displayName: '所有者' };
  const MIN_PASSWORD_LENGTH = 8; // 具体密码策略待确认（PRD T-08），原型仅校验长度
  const MAX_LOGIN_FAILURES = 5;
  const LOGIN_LOCK_MS = 30 * 1000;
  const SAVE_LATENCY_MS = 450;

  /* ---------- 工具 ---------- */
  function uid(prefix) {
    const r = (global.crypto && global.crypto.randomUUID) ? global.crypto.randomUUID().slice(0, 8) : Math.random().toString(36).slice(2, 10);
    return (prefix || 'id') + '-' + r;
  }
  function nowIso() { return new Date().toISOString(); }
  function agoIso(minutes) { return new Date(Date.now() - minutes * 60000).toISOString(); }
  function readJson(storage, key, fallback) {
    try { const raw = storage.getItem(key); return raw ? JSON.parse(raw) : fallback; } catch (e) { return fallback; }
  }
  function writeJson(storage, key, value) {
    try { storage.setItem(key, JSON.stringify(value)); return true; } catch (e) { console.error('[luma] 写入本地存储失败', e); return false; }
  }

  /* ---------- 种子数据（真实可读的示例，不含虚假统计） ---------- */
  function buildSeed() {
    const mkSource = (t) => [{ id: uid('src'), kind: 'manual', title: '手动创建', url: '', fileName: '', platform: '', externalId: '', occurredAt: t, importedAt: null }];
    const content = (o) => Object.assign({
      id: uid('c'), title: '', body: '', type: '想法', spaceId: '', categoryId: '', tagIds: [],
      organize: 'organized', publish: { status: 'draft', slug: '', publishedAt: null, updatedAt: null },
      learning: '', sources: [], attachments: [], createdAt: nowIso(), updatedAt: nowIso(), deletedAt: null, trashOrigin: null
    }, o);

    const spaces = [
      { id: 's-tech', name: '技术研究', desc: '探索技术原理与实践方法', order: 1 },
      { id: 's-work', name: '工作项目', desc: '沉淀项目过程、经验与复盘', order: 2 },
      { id: 's-life', name: '生活随记', desc: '收藏日常观察与生活片段', order: 3 }
    ];
    const categories = [
      { id: 'c-python', spaceId: 's-tech', parentId: '', name: 'Python', order: 1 },
      { id: 'c-front', spaceId: 's-tech', parentId: '', name: '前端开发', order: 2 },
      { id: 'c-react', spaceId: 's-tech', parentId: 'c-front', name: 'React', order: 1 },
      { id: 'c-ai', spaceId: 's-tech', parentId: '', name: 'AI / RAG', order: 3 },
      { id: 'c-luma', spaceId: 's-work', parentId: '', name: '灵脑', order: 1 },
      { id: 'c-review', spaceId: 's-work', parentId: '', name: '项目复盘', order: 2 },
      { id: 'c-daily', spaceId: 's-life', parentId: '', name: '日常', order: 1 },
      { id: 'c-read', spaceId: 's-life', parentId: '', name: '阅读', order: 2 }
    ];
    const tags = ['Python', '前端', '复盘', '产品', 'AI'].map((name, i) => ({ id: 't-' + (i + 1), name }));
    const tagId = (n) => tags.find((t) => t.name === n).id;

    const c = {};
    c.python = content({
      id: 'python', title: 'Python 函数与参数', type: '知识', spaceId: 's-tech', categoryId: 'c-python', tagIds: [tagId('Python')], learning: '学习中',
      body: '整理了函数的几种形式，包括位置参数、默认参数、可变参数，以及实际使用场景。\n\n## 函数\n\n函数是组织代码的基本方式。把可以重复使用的逻辑封装起来，让程序更清晰，也更容易维护。\n\n## 参数与返回值\n\n参数是函数接收的输入，返回值是函数执行后的结果。设计函数时，应明确它需要什么、会返回什么。\n\n```python\ndef greet(name, punct="!"):\n    return f"Hello, {name}{punct}"\n```',
      createdAt: agoIso(60 * 30), updatedAt: agoIso(75)
    });
    c.design = content({
      id: 'design', title: '灵脑产品设计思考', type: '想法', spaceId: 's-work', categoryId: 'c-luma', tagIds: [tagId('产品')],
      body: '关于灵脑的核心定位、使用场景和下一步迭代方向的想法：如何更好地帮助用户梳理知识，让记录成为可以再次利用的个人上下文。\n\n相关的阶段安排见 [[下一个阶段的工作重点与节奏]]。',
      createdAt: agoIso(60 * 48), updatedAt: agoIso(60 * 14)
    });
    c.review = content({
      id: 'review', title: '项目故障复盘', type: '经历', spaceId: 's-work', categoryId: 'c-review', tagIds: [tagId('复盘')],
      body: '本次线上故障的时间线、原因分析、处理过程与改进措施，主要涉及服务依赖超时。\n\n- 先记录现场，再分析原因\n- 为关键依赖设置合理的超时和回退方案\n- 复盘后补充监控告警',
      createdAt: agoIso(60 * 40), updatedAt: agoIso(60 * 18)
    });
    c.thought = content({
      id: 'thought', title: '把碎片想法变成可积累的知识', type: '想法', spaceId: 's-life', categoryId: 'c-daily',
      body: '记录的价值不在于完整，而在于让想法有一个落点，之后再慢慢生长、连接。',
      createdAt: agoIso(60 * 6), updatedAt: agoIso(60 * 5)
    });
    c.plan = content({
      id: 'plan', title: '下一个阶段的工作重点与节奏', type: '想法', spaceId: 's-work', categoryId: 'c-luma', tagIds: [tagId('产品')],
      body: '梳理了近期的目标、关键任务和时间安排，重点是保持稳定的推进节奏。',
      createdAt: agoIso(60 * 44), updatedAt: agoIso(60 * 15)
    });
    c.hooks = content({
      id: 'hooks', title: 'React Hooks 的心智模型', type: '知识', spaceId: 's-tech', categoryId: 'c-react', tagIds: [tagId('前端')], learning: '学习中',
      body: 'Hooks 让函数组件拥有状态与副作用能力。理解它们的关键是：**每次渲染都是一次独立的快照**。\n\n## 常用 Hook\n\n- `useState`：保存状态\n- `useEffect`：处理副作用\n- `useMemo`：缓存计算结果\n\n理解 Hooks 之前，建议先掌握 [[JavaScript 闭包]]。',
      publish: { status: 'published', slug: 'react-hooks-mental-model', publishedAt: agoIso(60 * 20), updatedAt: agoIso(60 * 20) },
      createdAt: agoIso(60 * 60), updatedAt: agoIso(60 * 20)
    });
    c.closure = content({
      id: 'closure', title: 'JavaScript 闭包', type: '知识', spaceId: 's-tech', categoryId: 'c-front', tagIds: [tagId('前端')], learning: '已理解',
      body: '闭包是函数与其词法环境的组合。函数可以“记住”并访问它被创建时所在作用域中的变量。\n\n```js\nfunction counter() {\n  let n = 0;\n  return () => ++n;\n}\n```',
      createdAt: agoIso(60 * 70), updatedAt: agoIso(60 * 30)
    });
    c.rag = content({
      id: 'rag', title: 'RAG 检索流程笔记', type: '知识', spaceId: 's-tech', categoryId: 'c-ai', tagIds: [tagId('AI')], learning: '待学习',
      body: '检索增强生成的基本流程：切分文档 → 向量化 → 召回相关片段 → 拼装上下文 → 由模型生成带引用的回答。\n\nV1.0 不要求上线，只作为后续 AI 阶段的预研记录。',
      createdAt: agoIso(60 * 26), updatedAt: agoIso(60 * 26)
    });

    const inboxTitles = ['关于长期学习的几点启发', '团队周会笔记（11 月 16 日）', '好用的 Python 工具清单', '一个新的产品灵感', '收藏的网页资料', '周末的一点生活观察', '待整理的读书摘录', '随手记：下周要确认的事项'];
    const inbox = inboxTitles.map((title, i) => content({
      id: 'inbox-' + i, title, type: i % 2 ? '知识' : '想法', organize: 'inbox',
      body: i === 0 ? '学习需要有真实的问题作为牵引。把看到的知识转化为自己的理解，再通过实践检验。' : '先把值得保存的内容放在这里，之后补充背景与自己的理解。',
      sources: i === 4
        ? [{ id: uid('src'), kind: 'web', title: '收藏的网页资料', url: 'https://example.com/article', fileName: '', platform: '', externalId: '', occurredAt: agoIso(60 * 3), importedAt: agoIso(60 * 3) }]
        : mkSource(agoIso(30 + i * 7)),
      createdAt: agoIso(30 + i * 7), updatedAt: agoIso(30 + i * 7)
    }));
    Object.keys(c).forEach((k) => { c[k].sources = mkSource(c[k].createdAt); });

    const relations = [
      { id: uid('r'), fromId: 'hooks', toId: 'closure', type: 'prerequisite', note: '理解 Hooks 需要先理解闭包' },
      { id: uid('r'), fromId: 'design', toId: 'plan', type: 'related', note: '' }
    ];
    return {
      formatVersion: FORMAT_VERSION,
      spaces, categories, tags,
      contents: Object.values(c).concat(inbox),
      relations, imports: []
    };
  }

  /* ---------- 状态加载 ---------- */
  let state = loadState();
  function loadState() {
    const saved = readJson(global.localStorage, DATA_KEY, null);
    if (saved && saved.formatVersion === FORMAT_VERSION && Array.isArray(saved.contents)) return saved;
    const seed = buildSeed();
    writeJson(global.localStorage, DATA_KEY, seed);
    return seed;
  }
  function persist() { return writeJson(global.localStorage, DATA_KEY, state); }

  const debug = { failSave: false };

  /* ---------- 认证（仅原型：本地模拟，不代表真实安全方案） ---------- */
  const Auth = {
    owner() { return readJson(global.localStorage, OWNER_KEY, DEFAULT_OWNER); },
    isLoggedIn() { return global.sessionStorage.getItem(SESSION_KEY) === '1'; },
    lockRemainingMs() {
      const g = readJson(global.localStorage, LOGIN_GUARD_KEY, { fails: 0, lockUntil: 0 });
      return Math.max(0, g.lockUntil - Date.now());
    },
    /** 失败统一返回通用错误，不泄露账号是否存在。 */
    login(account, password) {
      const guard = readJson(global.localStorage, LOGIN_GUARD_KEY, { fails: 0, lockUntil: 0 });
      if (guard.lockUntil > Date.now()) return { ok: false, code: 'locked', waitMs: guard.lockUntil - Date.now() };
      const owner = Auth.owner();
      if (account === owner.account && password === owner.password) {
        writeJson(global.localStorage, LOGIN_GUARD_KEY, { fails: 0, lockUntil: 0 });
        global.sessionStorage.setItem(SESSION_KEY, '1');
        return { ok: true };
      }
      guard.fails += 1;
      if (guard.fails >= MAX_LOGIN_FAILURES) { guard.fails = 0; guard.lockUntil = Date.now() + LOGIN_LOCK_MS; }
      writeJson(global.localStorage, LOGIN_GUARD_KEY, guard);
      return { ok: false, code: guard.lockUntil > Date.now() ? 'locked' : 'invalid', waitMs: Math.max(0, guard.lockUntil - Date.now()) };
    },
    logout() { global.sessionStorage.removeItem(SESSION_KEY); },
    changePassword(current, next) {
      const owner = Auth.owner();
      if (current !== owner.password) return { ok: false, field: 'current', message: '当前密码不正确' };
      if (next.length < MIN_PASSWORD_LENGTH) return { ok: false, field: 'next', message: '新密码至少 ' + MIN_PASSWORD_LENGTH + ' 位' };
      if (next === current) return { ok: false, field: 'next', message: '新密码不能与当前密码相同' };
      writeJson(global.localStorage, OWNER_KEY, Object.assign({}, owner, { password: next }));
      return { ok: true };
    }
  };

  /* ---------- 主题 ---------- */
  const Theme = {
    get() { const t = readJson(global.localStorage, THEME_KEY, DEFAULT_THEME); return { base: BASES.includes(t.base) ? t.base : DEFAULT_THEME.base, accent: ACCENTS[t.accent] ? t.accent : DEFAULT_THEME.accent }; },
    set(patch) { const next = Object.assign(Theme.get(), patch); writeJson(global.localStorage, THEME_KEY, next); Theme.apply(); return next; },
    reset() { writeJson(global.localStorage, THEME_KEY, DEFAULT_THEME); Theme.apply(); },
    apply() {
      const t = Theme.get(); const root = global.document.documentElement;
      root.dataset.base = t.base;
      root.style.setProperty('--accent', ACCENTS[t.accent][0]);
      root.style.setProperty('--accent-soft', ACCENTS[t.accent][1]);
    }
  };
  Theme.apply(); // 脚本在 <head> 同步加载，避免首屏闪烁

  /* ---------- 查询 ---------- */
  const byOrder = (a, b) => a.order - b.order;
  function activeContents() { return state.contents.filter((c) => !c.deletedAt); }
  function trashedContents() { return state.contents.filter((c) => c.deletedAt); }
  function getContent(id) { return state.contents.find((c) => c.id === id) || null; }
  function getSpace(id) { return state.spaces.find((s) => s.id === id) || null; }
  function getCategory(id) { return state.categories.find((c) => c.id === id) || null; }
  function getTag(id) { return state.tags.find((t) => t.id === id) || null; }
  function listSpaces() { return state.spaces.slice().sort(byOrder); }
  function childCategories(spaceId, parentId) {
    return state.categories.filter((c) => c.spaceId === spaceId && c.parentId === (parentId || '')).sort(byOrder);
  }
  function descendantCategoryIds(id) {
    const out = []; const walk = (pid) => state.categories.filter((c) => c.parentId === pid).forEach((c) => { out.push(c.id); walk(c.id); });
    walk(id); return out;
  }
  function categoryPath(id) {
    const names = []; let cur = getCategory(id); const guard = new Set();
    while (cur && !guard.has(cur.id)) { guard.add(cur.id); names.unshift(cur.name); cur = getCategory(cur.parentId); }
    return names.join(' / ');
  }
  function categoryDepth(id) { return categoryPath(id).split(' / ').length; }
  function contentsInSpace(spaceId) { return activeContents().filter((c) => c.spaceId === spaceId); }
  function contentsInCategory(categoryId, includeChildren) {
    const ids = new Set([categoryId].concat(includeChildren ? descendantCategoryIds(categoryId) : []));
    return activeContents().filter((c) => ids.has(c.categoryId));
  }
  function sortByUpdated(list) { return list.slice().sort((a, b) => b.updatedAt.localeCompare(a.updatedAt)); }

  /* ---------- 内容 CRUD ---------- */
  function createContent(patch) {
    const t = nowIso();
    const c = Object.assign({
      id: uid('c'), title: '', body: '', type: '想法', spaceId: '', categoryId: '', tagIds: [],
      organize: 'inbox', publish: { status: 'draft', slug: '', publishedAt: null, updatedAt: null },
      learning: '', sources: [{ id: uid('src'), kind: 'manual', title: '手动创建', url: '', fileName: '', platform: '', externalId: '', occurredAt: t, importedAt: null }],
      attachments: [], createdAt: t, updatedAt: t, deletedAt: null, trashOrigin: null
    }, patch || {});
    state.contents.unshift(c); persist(); return c;
  }
  /** 同步更新；已发布内容保存后立即视为更新线上内容（PRD 7.12 第 5 条）。 */
  function updateContent(id, patch) {
    const c = getContent(id); if (!c) return null;
    Object.assign(c, patch, { updatedAt: nowIso() });
    if (c.publish.status === 'published') c.publish.updatedAt = c.updatedAt;
    persist(); return c;
  }
  /** 模拟服务端异步保存；仅在成功回调后才可以向用户展示“已保存”。 */
  function saveContentAsync(id, patch) {
    return new Promise((resolve, reject) => {
      setTimeout(() => {
        if (debug.failSave) { reject(new Error('模拟网络异常')); return; }
        const c = updateContent(id, patch);
        c ? resolve(c) : reject(new Error('内容不存在'));
      }, SAVE_LATENCY_MS);
    });
  }
  function moveToTrash(id) {
    const c = getContent(id); if (!c) return;
    c.trashOrigin = { spaceId: c.spaceId, categoryId: c.categoryId, organize: c.organize };
    c.deletedAt = nowIso();
    // 回收站内容不得被公开访问：已发布内容同步撤回
    if (c.publish.status === 'published') c.publish.status = 'withdrawn';
    persist();
  }
  /** 恢复：原空间/分类仍存在则回到原位置，否则进入收集箱。返回 {fallbackToInbox}。 */
  function restoreFromTrash(id) {
    const c = getContent(id); if (!c) return { ok: false };
    const o = c.trashOrigin || {};
    const spaceOk = o.spaceId && getSpace(o.spaceId);
    const catOk = !o.categoryId || (getCategory(o.categoryId) && getCategory(o.categoryId).spaceId === o.spaceId);
    c.deletedAt = null;
    let fallbackToInbox = false;
    if (spaceOk && catOk) { c.spaceId = o.spaceId; c.categoryId = o.categoryId || ''; c.organize = o.organize || 'organized'; }
    else { c.spaceId = ''; c.categoryId = ''; c.organize = 'inbox'; fallbackToInbox = !!(o.spaceId || o.categoryId); }
    c.trashOrigin = null; persist(); return { ok: true, fallbackToInbox };
  }
  function permanentDelete(id) {
    state.contents = state.contents.filter((c) => c.id !== id);
    state.relations = state.relations.filter((r) => r.fromId !== id && r.toId !== id); // 不留悬空关联
    persist();
  }
  function purgeImpact(id) {
    const c = getContent(id);
    return { relations: state.relations.filter((r) => r.fromId === id || r.toId === id).length, attachments: c ? c.attachments.length : 0 };
  }

  /* ---------- 空间 ---------- */
  function validateName(name, siblings, selfId, label) {
    const n = (name || '').trim();
    if (!n) return label + '名称不能为空';
    if (n.length > 30) return label + '名称不能超过 30 个字符';
    if (siblings.some((s) => s.id !== selfId && s.name === n)) return '已存在同名' + label;
    return '';
  }
  function addSpace(name, desc) {
    const err = validateName(name, state.spaces, '', '空间'); if (err) return { ok: false, message: err };
    const s = { id: uid('s'), name: name.trim(), desc: (desc || '').trim(), order: Math.max(0, ...state.spaces.map((x) => x.order)) + 1 };
    state.spaces.push(s); persist(); return { ok: true, space: s };
  }
  function updateSpace(id, patch) {
    const s = getSpace(id); if (!s) return { ok: false, message: '空间不存在' };
    if (patch.name !== undefined) { const err = validateName(patch.name, state.spaces, id, '空间'); if (err) return { ok: false, message: err }; s.name = patch.name.trim(); }
    if (patch.desc !== undefined) s.desc = patch.desc.trim();
    persist(); return { ok: true };
  }
  function moveSpace(id, dir) {
    const list = listSpaces(); const i = list.findIndex((s) => s.id === id); const j = i + dir;
    if (i < 0 || j < 0 || j >= list.length) return false;
    const t = list[i].order; list[i].order = list[j].order; list[j].order = t; persist(); return true;
  }
  /** 非空空间默认阻止直接删除。 */
  function deleteSpace(id) {
    const cats = state.categories.filter((c) => c.spaceId === id).length;
    const contents = state.contents.filter((c) => c.spaceId === id).length; // 含回收站内容
    if (cats || contents) return { ok: false, categories: cats, contents };
    state.spaces = state.spaces.filter((s) => s.id !== id); persist(); return { ok: true };
  }

  /* ---------- 分类 ---------- */
  function addCategory(spaceId, parentId, name) {
    const siblings = childCategories(spaceId, parentId);
    const err = validateName(name, siblings, '', '分类'); if (err) return { ok: false, message: err };
    if (parentId) { const p = getCategory(parentId); if (!p || p.spaceId !== spaceId) return { ok: false, message: '父分类必须属于同一空间' }; }
    const c = { id: uid('cat'), spaceId, parentId: parentId || '', name: name.trim(), order: Math.max(0, ...siblings.map((x) => x.order)) + 1 };
    state.categories.push(c); persist(); return { ok: true, category: c };
  }
  function renameCategory(id, name) {
    const c = getCategory(id); if (!c) return { ok: false, message: '分类不存在' };
    const err = validateName(name, childCategories(c.spaceId, c.parentId), id, '分类'); if (err) return { ok: false, message: err };
    c.name = name.trim(); persist(); return { ok: true };
  }
  /** 禁止移动到自身或后代；父子必须同空间。 */
  function canMoveCategory(id, newParentId) {
    const c = getCategory(id); if (!c) return { ok: false, message: '分类不存在' };
    if (!newParentId) return { ok: true };
    if (newParentId === id) return { ok: false, message: '不能移动到自身' };
    if (descendantCategoryIds(id).includes(newParentId)) return { ok: false, message: '不能移动到自己的子分类下' };
    const p = getCategory(newParentId);
    if (!p || p.spaceId !== c.spaceId) return { ok: false, message: '父分类必须属于同一空间' };
    return { ok: true };
  }
  function moveCategory(id, newParentId) {
    const chk = canMoveCategory(id, newParentId); if (!chk.ok) return chk;
    const c = getCategory(id);
    const siblings = childCategories(c.spaceId, newParentId || '');
    if (siblings.some((s) => s.id !== id && s.name === c.name)) return { ok: false, message: '目标位置已存在同名分类' };
    c.parentId = newParentId || ''; c.order = Math.max(0, ...siblings.map((x) => x.order)) + 1; persist(); return { ok: true };
  }
  function deleteCategory(id) {
    const subs = state.categories.filter((c) => c.parentId === id).length;
    const contents = state.contents.filter((c) => c.categoryId === id).length;
    if (subs || contents) return { ok: false, subs, contents };
    state.categories = state.categories.filter((c) => c.id !== id); persist(); return { ok: true };
  }

  /* ---------- 标签 ---------- */
  function ensureTag(name) {
    const n = (name || '').trim().replace(/^#/, ''); if (!n) return null;
    let t = state.tags.find((x) => x.name.toLowerCase() === n.toLowerCase());
    if (!t) { t = { id: uid('t'), name: n.slice(0, 20) }; state.tags.push(t); persist(); }
    return t;
  }
  function tagUsage(id) { return activeContents().filter((c) => c.tagIds.includes(id)).length; }

  /* ---------- 关联 ---------- */
  function addRelation(fromId, toId, type, note) {
    if (!RELATION_TYPES[type]) return { ok: false, message: '未知的关系类型' };
    if (fromId === toId) return { ok: false, message: '内容不能关联自身' };
    const a = getContent(fromId), b = getContent(toId);
    if (!a || !b || a.deletedAt || b.deletedAt) return { ok: false, message: '目标内容不存在或已在回收站' };
    const dup = state.relations.some((r) => r.type === type && (type === 'related'
      ? ((r.fromId === fromId && r.toId === toId) || (r.fromId === toId && r.toId === fromId))
      : (r.fromId === fromId && r.toId === toId)));
    if (dup) return { ok: false, message: '这两条内容之间已存在相同类型的关系' };
    const r = { id: uid('r'), fromId, toId, type, note: (note || '').trim() };
    state.relations.push(r); persist(); return { ok: true, relation: r };
  }
  function removeRelation(id) { state.relations = state.relations.filter((r) => r.id !== id); persist(); }
  /** 返回 {links, backlinks}；links：从本内容出发的关系 + 双向“相关”；backlinks：指向本内容的全部关系。 */
  function relationsFor(id) {
    const live = (cid) => { const c = getContent(cid); return c && !c.deletedAt ? c : null; };
    const links = [], backlinks = [];
    state.relations.forEach((r) => {
      if (r.fromId === id && live(r.toId)) links.push({ relation: r, other: live(r.toId), arrow: r.type === 'related' ? '↔' : '→' });
      else if (r.toId === id && r.type === 'related' && live(r.fromId)) links.push({ relation: r, other: live(r.fromId), arrow: '↔' });
      if (r.toId === id && live(r.fromId)) backlinks.push({ relation: r, other: live(r.fromId) });
    });
    return { links, backlinks };
  }
  /** 正文里的 [[标题]] 引用（用于预览与公开展示解析）。 */
  function findByTitle(title) { return activeContents().find((c) => c.title === title) || null; }

  /* ---------- 整理 / 发布 ---------- */
  function organize(id, status) { return updateContent(id, { organize: status }); }
  function publishIssues(c) {
    const issues = [];
    if (!c.title.trim()) issues.push('缺少标题');
    if (!c.body.trim()) issues.push('缺少可展示的正文');
    return issues;
  }
  function slugFor(c) { return c.publish.slug || ('k-' + c.id.replace(/[^a-z0-9]/gi, '').slice(0, 6).toLowerCase() + '-' + Math.random().toString(36).slice(2, 6)); }
  /** 发布：创建或更新 Publication；slug 一经生成保持稳定。 */
  function publish(id, opts) {
    const c = getContent(id); if (!c || c.deletedAt) return { ok: false, message: '内容不存在' };
    const issues = publishIssues(c); if (issues.length) return { ok: false, message: issues.join('、') };
    const t = nowIso();
    c.publish = { status: 'published', slug: slugFor(c), publishedAt: c.publish.publishedAt || t, updatedAt: t };
    if (opts && Array.isArray(opts.publicAttachmentIds)) c.attachments.forEach((a) => { a.isPublic = opts.publicAttachmentIds.includes(a.id); });
    persist(); return { ok: true };
  }
  function withdraw(id) {
    const c = getContent(id); if (!c) return;
    c.publish.status = 'withdrawn'; c.attachments.forEach((a) => { a.isPublic = false; }); persist();
  }
  /** 公开视图：关联仅展示两端均已发布的内容。 */
  function publicRelations(id) {
    return relationsFor(id).links.filter((l) => l.other.publish.status === 'published');
  }

  /* ---------- 学习 ---------- */

  /* ---------- 搜索 ---------- */
  const RANGE_MS = { today: 24 * 3600e3, week: 7 * 24 * 3600e3, month: 30 * 24 * 3600e3 };
  function search(opts) {
    const q = (opts.q || '').trim().toLowerCase();
    let list = activeContents();
    if (opts.spaceId) list = list.filter((c) => c.spaceId === opts.spaceId);
    if (opts.categoryId) { const ids = new Set([opts.categoryId].concat(descendantCategoryIds(opts.categoryId))); list = list.filter((c) => ids.has(c.categoryId)); }
    if (opts.type) list = list.filter((c) => c.type === opts.type);
    if (opts.tagId) list = list.filter((c) => c.tagIds.includes(opts.tagId));
    if (opts.range && RANGE_MS[opts.range]) { const since = Date.now() - RANGE_MS[opts.range]; list = list.filter((c) => new Date(c.updatedAt).getTime() >= since); }
    if (q) {
      list = list.map((c) => {
        const inTitle = c.title.toLowerCase().indexOf(q); const inBody = c.body.toLowerCase().indexOf(q);
        return { c, score: (inTitle >= 0 ? 2 : 0) + (inBody >= 0 ? 1 : 0), bodyAt: inBody };
      }).filter((x) => x.score > 0);
      if (opts.sort === 'updated') list.sort((a, b) => b.c.updatedAt.localeCompare(a.c.updatedAt));
      else list.sort((a, b) => b.score - a.score || b.c.updatedAt.localeCompare(a.c.updatedAt));
      return list.map((x) => x.c);
    }
    return sortByUpdated(list);
  }

  /* ---------- 导入记录 ---------- */
  function addImportJob(job) { state.imports.unshift(job); persist(); return job; }
  function updateImportJob(id, patch) { const j = state.imports.find((x) => x.id === id); if (j) { Object.assign(j, patch); persist(); } return j; }
  function findDuplicate(fingerprint) { return state.contents.find((c) => c.sources.some((s) => s.fingerprint && s.fingerprint === fingerprint)) || null; }

  /* ---------- 备份 / 恢复 ---------- */
  function isBlankWorkspace() { return state.contents.length === 0 && state.spaces.length === 0 && state.categories.length === 0 && state.tags.length === 0; }
  function counts(data) {
    return {
      contents: data.contents.length, spaces: data.spaces.length, categories: data.categories.length, tags: data.tags.length,
      relations: data.relations.length, sources: data.contents.reduce((n, c) => n + c.sources.length, 0), attachments: data.contents.reduce((n, c) => n + c.attachments.length, 0)
    };
  }
  function buildBackup() {
    const data = JSON.parse(JSON.stringify({ spaces: state.spaces, categories: state.categories, tags: state.tags, contents: state.contents, relations: state.relations, imports: state.imports }));
    return { manifest: { format: 'luma-backup', formatVersion: FORMAT_VERSION, generatedAt: nowIso(), generator: 'Luma Studio 原型', note: '原型仅保存附件元数据，不含文件二进制内容', counts: counts(data) }, data };
  }
  function validateBackup(obj) {
    const err = (message) => ({ ok: false, message });
    if (!obj || typeof obj !== 'object' || !obj.manifest || !obj.data) return err('不是有效的灵脑备份文件');
    if (obj.manifest.format !== 'luma-backup') return err('文件格式标识不匹配');
    if (obj.manifest.formatVersion !== FORMAT_VERSION) return err('备份格式版本 ' + obj.manifest.formatVersion + ' 与当前原型（版本 ' + FORMAT_VERSION + '）不兼容');
    const d = obj.data;
    for (const k of ['spaces', 'categories', 'tags', 'contents', 'relations']) if (!Array.isArray(d[k])) return err('备份缺少必要数据：' + k);
    const contentIds = new Set(d.contents.map((c) => c.id));
    if (contentIds.size !== d.contents.length) return err('备份中存在重复的内容 ID');
    if (d.relations.some((r) => !contentIds.has(r.fromId) || !contentIds.has(r.toId))) return err('备份中存在指向不存在内容的关联');
    const spaceIds = new Set(d.spaces.map((s) => s.id));
    if (d.categories.some((c) => !spaceIds.has(c.spaceId))) return err('备份中存在不属于任何空间的分类');
    return { ok: true, counts: counts(d), manifest: obj.manifest };
  }
  /** 仅允许恢复到空白工作区；返回恢复后实际数量供校验。 */
  function restoreBackup(obj) {
    const chk = validateBackup(obj); if (!chk.ok) return chk;
    if (!isBlankWorkspace()) return { ok: false, message: 'V1.0 仅支持恢复到空白工作区' };
    const snapshot = JSON.stringify(state);
    try {
      const d = JSON.parse(JSON.stringify(obj.data));
      state = { formatVersion: FORMAT_VERSION, spaces: d.spaces, categories: d.categories, tags: d.tags, contents: d.contents, relations: d.relations, imports: d.imports || [] };
      if (!persist()) throw new Error('写入本地存储失败');
      const after = counts(state);
      const same = Object.keys(chk.counts).every((k) => chk.counts[k] === after[k]);
      if (!same) throw new Error('恢复后的数量与备份清单不一致');
      return { ok: true, expected: chk.counts, actual: after };
    } catch (e) {
      state = JSON.parse(snapshot); persist(); // 失败回滚，不留下半成品
      return { ok: false, message: '恢复失败：' + e.message };
    }
  }
  function resetWorkspace() { state = { formatVersion: FORMAT_VERSION, spaces: [], categories: [], tags: [], contents: [], relations: [], imports: [] }; persist(); }
  function loadDemoData() { state = buildSeed(); persist(); }

  L.Store = {
    CONTENT_TYPES, ORGANIZE_LABEL, PUBLISH_LABEL, RELATION_TYPES, ACCENTS, BASES, MIN_PASSWORD_LENGTH, debug,
    uid, nowIso,
    activeContents, trashedContents, getContent, getSpace, getCategory, getTag, listSpaces, childCategories, descendantCategoryIds,
    categoryPath, categoryDepth, contentsInSpace, contentsInCategory, sortByUpdated, allTags: () => state.tags.slice(), allCategories: () => state.categories.slice(),
    inboxCount: () => activeContents().filter((c) => c.organize === 'inbox').length,
    createContent, updateContent, saveContentAsync, moveToTrash, restoreFromTrash, permanentDelete, purgeImpact,
    addSpace, updateSpace, moveSpace, deleteSpace,
    addCategory, renameCategory, canMoveCategory, moveCategory, deleteCategory,
    ensureTag, tagUsage,
    addRelation, removeRelation, relationsFor, findByTitle,
    organize, publishIssues, publish, withdraw, publicRelations,
    search, addImportJob, updateImportJob, findDuplicate,
    isBlankWorkspace, buildBackup, validateBackup, restoreBackup, resetWorkspace, loadDemoData, counts: () => counts(state),
    state: () => state
  };
  L.Auth = Auth;
  L.Theme = Theme;
})(window);
