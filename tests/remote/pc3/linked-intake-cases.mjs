// Synthetic, offline input shaped after CaseService.intake (server/service.py).
// Expected source records are copied from the tracked fixture, not from WmsScene's resolver.
export function makeLinkedIntake(source, id = source.id === 'CASE-0001' ? 'INT-A1B2C3D4' : 'INT-1020ABCD') {
  const text = `독립 회귀 입력: ${source.store.name} 배송 내용을 다시 확인해 주세요.`;
  const intake = {
    id, type: source.type, channel: 'text', synthetic: true,
    title: source.intake.subject, storeId: source.store.id, subject: source.intake.subject,
    store: structuredClone(source.store), storeName: source.store.name, sourceText: text, text,
    status: 'draft', createdAt: '2026-09-21T10:00:00+09:00', updatedAt: '2026-09-21T10:00:00+09:00',
    intake: { storeId: source.store.id, subject: source.intake.subject, quantity: null, unit: null, request: text },
    departmentId: null, reviewConfirmed: false, reply: null, pendingActions: [], selectedEvidence: [],
    evidence: structuredClone(source.evidence || []), linkedFixtureId: source.id,
    history: [{ at: '2026-09-21T10:00:00+09:00', actor: 'owner', action: 'text_intake', message: '합성 문의 접수' }],
    transcript: [{ speaker: '점주', text, start: 0, end: 0 }], analysis: null, revision: 0,
  };
  for (const field of ['wms', 'tms', 'asOf', 'expected', 'received', 'provenance']) {
    if (Object.hasOwn(source, field)) intake[field] = structuredClone(source[field]);
  }
  return intake;
}

export const linkedIntakeMutations = [
  { name: 'missing-source', edit: data => { delete data.linkedFixtureId; } },
  { name: 'unregistered-source', edit: data => { data.linkedFixtureId = 'CASE-UNREGISTERED'; } },
  { name: 'foreign-source', edit: data => { data.linkedFixtureId = 'CASE-0001'; } },
  { name: 'voice-channel', edit: data => { data.channel = 'voice'; } },
  { name: 'foreign-store', edit: data => { data.store.id = 'SYN-ST01'; } },
  { name: 'foreign-intake-store', edit: data => { data.intake.storeId = 'SYN-ST01'; } },
  { name: 'foreign-type', edit: data => { data.type = 'missing'; } },
  { name: 'foreign-asof', edit: data => { data.asOf = '2026-09-19T07:00:00+09:00'; } },
  { name: 'foreign-order', edit: data => { data.wms.picking.orderId = 'SYN-ORDER01'; } },
  { name: 'foreign-picking-tote', edit: data => { data.wms.picking.toteId = 'SYN-TOTE02-B'; } },
  { name: 'foreign-shipping-tote', edit: data => { data.wms.shipping.toteId = 'SYN-TOTE02-A'; } },
  { name: 'raw-event-modified', edit: data => { data.wms.events[2].location = '다른 분기'; } },
  { name: 'raw-event-reordered', edit: data => { data.wms.events.reverse(); } },
  { name: 'process-row-modified', edit: data => { data.wms.picking.product = '다른 상품'; } },
  { name: 'process-row-extra-field', edit: data => { data.wms.shipping.unverified = '임의 연결'; } },
  { name: 'evidence-modified', edit: data => { data.evidence[0].value = '변조된 주문값'; } },
  { name: 'evidence-reordered', edit: data => { data.evidence.reverse(); } },
  { name: 'malformed-id-null', edit: data => { data.id = null; } },
  { name: 'malformed-id-number', edit: data => { data.id = 23; } },
  { name: 'malformed-id-empty', edit: data => { data.id = ''; } },
  { name: 'malformed-id-empty-suffix', edit: data => { data.id = 'INT-'; } },
  { name: 'malformed-id-wrong-prefix', edit: data => { data.id = 'NEW-1020ABCD'; } },
  { name: 'malformed-id-whitespace', edit: data => { data.id = 'INT- 1020ABCD'; } },
];

export function reorderObjectKeys(value) {
  if (Array.isArray(value)) return value.map(reorderObjectKeys);
  if (value && typeof value === 'object') return Object.fromEntries(Object.entries(value).reverse().map(([key, item]) => [key, reorderObjectKeys(item)]));
  return value;
}
