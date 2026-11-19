/* 用人工选取的示例记录演示思考脉络的阅读顺序。 */
(function () {
  'use strict';
  const { Shell, Store, UI } = window.Luma;
  const { h, fmtDateLong } = UI;
  const topic = '灵脑应该成为怎样的产品？';
  const page = Shell.mount({ nav: 'threads', title: '思考脉络', crumbs: [{ label: '思考脉络' }] });
  if (!page) return;

  const records = ['design', 'plan'].map((id) => Store.getContent(id))
    .filter((record) => record && !record.deletedAt)
    .sort((a, b) => Date.parse(a.createdAt) - Date.parse(b.createdAt));
  const title = (record) => record.title || '（无标题）';
  const source = (record) => h('a', {
    href: 'editor.html?id=' + encodeURIComponent(record.id), text: title(record)
  });
  const summary = h('section', { class: 'thread-section' }, h('h3', { text: '脉络梳理' }));
  if (records.length === 2) {
    summary.appendChild(h('p', null, '这条示例把产品方向与实施节奏放在一起回看：',
      source(Store.getContent('design')), '提出定位和使用场景，',
      source(Store.getContent('plan')), '补充近期目标、任务与时间安排。'));
  } else {
    summary.appendChild(h('p', { text: '部分示例原文已不可用，暂不展示完整梳理。' }));
  }

  const graph = h('section', { class: 'thread-section' }, h('h3', { text: '关联图' }));
  if (records.length) {
    const roles = { design: '梳理产品方向', plan: '补充实施节奏' };
    graph.appendChild(h('div', { class: 'thread-graph' },
      h('div', { class: 'thread-graph-topic', text: topic }),
      h('ul', { class: 'thread-graph-branches' }, records.map((record) =>
        h('li', null, h('span', { text: roles[record.id] }), source(record))))));
    if (Store.relationsFor('design').links.some(({ other }) => other.id === 'plan')) {
      graph.appendChild(h('p', { class: 'thread-graph-note' }, source(Store.getContent('design')),
        ' 与 ', source(Store.getContent('plan')), ' 在原型中也有关联。'));
    }
  } else {
    graph.appendChild(h('p', { text: '暂无可连接的示例记录。' }));
  }

  const timeline = h('section', { class: 'thread-section' }, h('h3', { text: '原始记录时间线' }));
  if (records.length) {
    timeline.appendChild(h('ol', { class: 'thread-timeline' }, records.map((record) =>
      h('li', null, h('time', { datetime: record.createdAt, text: fmtDateLong(new Date(record.createdAt)) }),
        source(record),
        h('p', { text: record.body.split('\n').find((line) => line.trim()) || '暂无正文' })))));
  } else {
    timeline.appendChild(h('p', { text: '暂无可用的示例记录。' }));
  }

  page.appendChild(h('div', { class: 'standard thread-page' },
    h('h1', { text: '思考脉络' }),
    h('details', { class: 'thread-example' },
      h('summary', null, h('span', { class: 'eyebrow', text: '手工整理 · 示例' }),
        h('h2', { text: topic }),
        h('p', { text: records.length + ' 条可查看的原始记录' })),
      summary, graph, timeline)));
})();
