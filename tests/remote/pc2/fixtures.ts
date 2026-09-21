import input from '../../../data/fixtures/cases.json';
import storedVoice from '../../../reports/e2e/normalized-voice-live.json';
import type { CaseData, Analysis } from '../../../apps/web/lib/types';

// All inputs below are synthetic, isolated copies. No API, shared fixture or
// application state is modified. Added timestamps test the player clock only;
// they are not asserted to be STT-derived word alignment for the real v2 WAVs.
export function makeCase(name: string): CaseData {
  const source = input.cases[name === 'real-2' || name === 'stored-live' ? 1 : 0];
  const c = JSON.parse(JSON.stringify(source)) as CaseData;
  if (name.startsWith('real-')) return c;
  if (name === 'stored-live') {
    // Previously authorized synthetic CASE-0002 STT/analysis response, read only.
    // This does not call an API or claim a new live run.
    c.transcript = JSON.parse(JSON.stringify(storedVoice.result.transcript));
    c.analysis = JSON.parse(JSON.stringify(storedVoice.result.analysis));
    c.analysisMode = 'demo-live';
    return c;
  }
  c.id = 'SYN-N02-PLAYER';
  c.title = 'N02 독립 합성 통화 검토';
  c.audioUrl = '/test-audio/short.wav';
  c.sourceText = '경영주: 주문은 18 EA였지만 받은 것은 1 BOX입니다. 상담원: 1 EA가 아니라 1 BOX로 확인하겠습니다.';
  c.expected = { product: '합성 테스트 상품', quantity: 18, unit: 'EA' };
  c.received = { product: '합성 테스트 상품', quantity: 1, unit: 'BOX' };
  c.intake = { storeId: 'SYN-OPERATOR', subject: '합성 테스트 상품', quantity: 1, unit: 'EA', request: '단위 정정과 출고 확인' };
  c.transcript = [
    { speaker: '경영주', text: '주문은 18 EA였지만 받은 것은 1 BOX입니다.', start: 0.15, end: 0.8 },
    { speaker: '상담원', text: '1 EA가 아니라 1 BOX로 확인하겠습니다.', start: 1, end: 1.7 },
  ];
  c.analysis = {
    summary: '경영주 진술은 수령 1 BOX이며 상담원 입력 1 EA와 단위가 다릅니다.',
    fields: { storeId: null, subject: '합성 테스트 상품', quantity: 1, unit: 'BOX', request: '단위 정정과 출고 확인' },
    issues: [{ field: 'unit', message: '수령 단위 1 BOX / 상담 입력 1 EA 불일치', evidence: '1 EA가 아니라 1 BOX' }],
    questions: ['점포를 다시 확인해 주세요.', '수령 단위가 BOX인지 확인해 주세요.'],
    department: { id: 'warehouse', name: '센터 확인 담당', reason: '합성 출고 문의' },
    facts: ['경영주가 1 BOX 수령이라고 진술함'], unknowns: ['점포와 실제 물류 수량 미확인'],
    replyDraft: '단위와 출고 내용을 담당자에게 확인하겠습니다.',
  } as Analysis;
  if (name === 'missing') delete c.audioUrl;
  if (name === '404') c.audioUrl = '/test-audio/not-found.wav';
  if (name === 'damaged') c.audioUrl = '/test-audio/damaged.wav';
  if (name === 'silent') c.audioUrl = '/test-audio/silent.wav';
  if (name === 'zero') c.audioUrl = '/test-audio/zero.wav';
  if (name === 'text') {
    c.channel = 'text';
    delete c.audioUrl;
    c.transcript = [];
    c.sourceText = '합성 텍스트 접수: 주문 18 EA, 수령 1 BOX의 단위를 확인해 주세요.';
  }
  if (name === 'null-zero') {
    c.intake = { ...c.intake!, storeId: null, quantity: 0, unit: null };
    c.analysis!.fields = { ...c.analysis!.fields, quantity: null, unit: null };
  }
  if (name === 'invalid-timestamps') {
    c.transcript = [
      { speaker: '경영주', text: '시각 없음' },
      { speaker: '경영주', text: '음수 시각', start: -1, end: 1 },
      { speaker: '경영주', text: '역전 시각', start: 2, end: 1 },
      { speaker: '경영주', text: '같은 시각', start: 1, end: 1 },
      { speaker: '경영주', text: 'NaN 시각', start: Number.NaN, end: 1 },
      { speaker: '경영주', text: '무한 시각', start: 1, end: Number.POSITIVE_INFINITY },
      { speaker: '경영주', text: '음원보다 긴 시각', start: 2, end: 9 },
      { speaker: '경영주', text: '끝 시각 없음', start: 1 },
    ];
  }
  if (name === 'long') {
    c.title = '긴합성문자'.repeat(40);
    c.transcript![0].text = 'SYNTHETIC_LONG_TOKEN_'.repeat(45);
    c.sourceText = c.transcript![0].text;
    c.analysis!.questions.push('긴추가확인문장'.repeat(45));
    c.analysis!.issues[0].evidence = '긴인용문'.repeat(80);
    c.analysis!.fields.subject = 'LONG_FIELD_'.repeat(30);
  }
  return c;
}

export function freezeDeep<T>(value: T): T {
  if (value && typeof value === 'object' && !Object.isFrozen(value)) {
    Object.freeze(value);
    Object.values(value).forEach(freezeDeep);
  }
  return value;
}
