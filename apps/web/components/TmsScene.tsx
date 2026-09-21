'use client';

import { useEffect, useId, useRef, useState } from 'react';
import type { CaseData, Evidence } from '@/lib/types';
import { ApiError } from '@/lib/api';
import overlay from '../../../data/overlays/pc4-tms.json';
import fixtureData from '../../../data/fixtures/cases.json';
import styles from './TmsScene.module.css';

type Props = {
  caseData: CaseData;
  onLinkEvidence: (id: string) => Promise<void> | void;
  onBack: () => void;
};
type Row = Record<string, unknown>;
type TimeState = 'missing' | 'local' | 'invalid' | 'unbounded' | 'future' | 'recorded';
type TimeValue = { state: TimeState; label: string; epoch: number | null; date: string | null };
type Stop = { key: string; id: string; name: string; sequence: number | null; row: Row; kind: string; index: number };
const rowOf = (value: unknown): Row => value !== null && typeof value === 'object' && !Array.isArray(value) ? value as Row : {};
const text = (value: unknown, fallback = '미등록'): string => typeof value === 'string' && value.trim() ? value : typeof value === 'number' && Number.isFinite(value) ? String(value) : fallback;
const absent = (value: unknown) => value === null || value === undefined || value === '';
const isoDate = /^\d{4}-\d{2}-\d{2}$/;

// Date.parse accepts timezone-less strings and normalizes some invalid dates. Neither is a verified record.
export function tmsTimestamp(value: unknown): number | null {
  if (typeof value !== 'string') return null;
  const match = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})(?::(\d{2})(?:\.\d{1,3})?)?(Z|[+-]\d{2}:\d{2})$/.exec(value);
  if (!match) return null;
  const [, y, m, d, h, minute, second = '0', zone] = match;
  const year = Number(y), month = Number(m), day = Number(d);
  const days = new Date(Date.UTC(year, month, 0)).getUTCDate();
  if (year < 1000 || month < 1 || month > 12 || day < 1 || day > days || Number(h) > 23 || Number(minute) > 59 || Number(second) > 59) return null;
  if (zone !== 'Z' && (Number(zone.slice(1, 3)) > 14 || Number(zone.slice(4)) > 59 || (Number(zone.slice(1, 3)) === 14 && Number(zone.slice(4)) !== 0))) return null;
  const parsed = Date.parse(value);
  return Number.isFinite(parsed) ? parsed : null;
}
function kstDate(epoch: number): string { return new Date(epoch + 9 * 60 * 60 * 1000).toISOString().slice(0, 10); }
function kstClock(epoch: number): string { return new Date(epoch + 9 * 60 * 60 * 1000).toISOString().slice(11, 16); }

export function tmsTime(value: unknown, asOf: unknown, bizDate: unknown, planned = false): TimeValue {
  if (absent(value)) return { state: 'missing', label: '미등록', epoch: null, date: null };
  if (typeof value === 'string' && /^(?:[01]\d|2[0-3]):[0-5]\d$/.test(value)) {
    return { state: 'local', label: `${value} · 날짜·시간대 확인 필요`, epoch: null, date: null };
  }
  const epoch = tmsTimestamp(value);
  if (epoch === null) return { state: 'invalid', label: '시각 형식·시간대 확인 필요', epoch: null, date: null };
  const date = kstDate(epoch);
  const time = `${date !== bizDate ? `${date} ` : ''}${kstClock(epoch)} KST`;
  const cutoff = tmsTimestamp(asOf);
  if (cutoff === null) return { state: 'unbounded', label: `${time} · 조회 기준 미확인`, epoch, date };
  if (epoch > cutoff) return { state: 'future', label: planned ? `${time} · 기준 이후 계획` : '조회 기준 이후 · 현재 실적 미채택', epoch, date };
  return { state: 'recorded', label: time, epoch, date };
}
function asOfLabel(value: unknown): string {
  const epoch = tmsTimestamp(value);
  return epoch === null ? '조회 기준 미등록·확인 필요' : `${kstDate(epoch)} ${kstClock(epoch)} KST`;
}
function sourceDetails(label: string, value: unknown) {
  return <details className={styles.source}><summary>{label} · 합성 입력 확인</summary><pre>{JSON.stringify(value, null, 2)}</pre></details>;
}
function stopsFor(tms: Row): Stop[] {
  return (Array.isArray(tms.stops) ? tms.stops : []).map((value, index) => {
    const row = rowOf(value);
    const kind = text(row.visitType ?? row.type, '점포(합성)');
    return { key: `visit-${index}`, id: text(row.id, ''), name: text(row.name, '방문명 미등록'), sequence: typeof row.sequence === 'number' && Number.isInteger(row.sequence) && row.sequence > 0 ? row.sequence : null, row, kind, index };
  }).sort((a, b) => (a.sequence ?? Infinity) - (b.sequence ?? Infinity) || a.index - b.index);
}
function isStore(stop: Stop): boolean { return ['store', '점포', '점포(합성)'].includes(stop.kind); }
function sourceContract(caseData: CaseData) {
  const direct = overlay.cases.find(item => item.caseId === caseData.id);
  if (direct) return absent(caseData.linkedFixtureId) || caseData.linkedFixtureId === direct.caseId ? direct : undefined;
  // CaseService.intake creates exactly this synthetic text shape after validating referenceCaseId.
  if (!/^INT-[0-9A-F]{8}$/.test(caseData.id) || caseData.channel !== 'text' || caseData.synthetic !== true || typeof caseData.linkedFixtureId !== 'string') return undefined;
  return overlay.cases.find(item => item.caseId === caseData.linkedFixtureId);
}
function canonical(value: unknown): string {
  if (Array.isArray(value)) return `[${value.map(canonical).join(',')}]`;
  if (value !== null && typeof value === 'object') return `{${Object.entries(value).sort(([a], [b]) => a.localeCompare(b)).map(([key, entry]) => `${JSON.stringify(key)}:${canonical(entry)}`).join(',')}}`;
  return JSON.stringify(value) ?? 'undefined';
}

/** No implicit join by display name. Only the reviewed synthetic relation can be linked. */
export function tmsRelationIssue(caseData: CaseData): string | null {
  const tms = rowOf(caseData.tms);
  const contract = sourceContract(caseData);
  if (!contract) return '이 사건의 명시적 TMS 연결 계약이 없어 상담 연결을 보류합니다.';
  if (caseData.id !== contract.caseId) {
    const source = fixtureData.cases.find(item => item.id === contract.caseId);
    if (!source || caseData.storeId !== contract.storeId || caseData.intake?.storeId !== contract.storeId || caseData.subject !== source.intake.subject || caseData.title !== source.intake.subject || caseData.asOf !== source.asOf) return '명시적으로 연결한 원본 사례의 점포·문의 대상·조회 기준이 접수와 다릅니다.';
    if (canonical(caseData.tms) !== canonical(source.tms) || canonical(caseData.evidence) !== canonical(source.evidence)) return '명시적으로 연결한 원본 사례와 TMS·근거 내용이 다릅니다. 다른 기록을 섞지 않습니다.';
  }
  if (caseData.store.id !== contract.storeId || caseData.type !== contract.caseType) return '사건의 점포·문의 유형이 등록 계약과 다릅니다.';
  if (caseData.intake?.storeId && caseData.intake.storeId !== contract.storeId) return '접수에서 확인한 점포와 TMS 문의 점포가 다릅니다.';
  for (const [key, expected] of Object.entries({ caseId: contract.caseId, storeId: contract.storeId, relationStatus: 'exact', synthetic: true })) {
    if (tms[key] !== undefined && tms[key] !== expected) return 'TMS의 사건·점포·관계 상태가 검토된 합성 연결과 다릅니다.';
  }
  for (const key of ['bizDate', 'centerId', 'routeId', 'vehicle'] as const) {
    if (tms[key] !== contract[key]) return '업무일·센터·루트·차량이 같은 사건인지 확인해야 합니다.';
  }
  const cutoff = tmsTimestamp(caseData.asOf);
  if (cutoff === null || kstDate(cutoff) !== contract.bizDate) return '조회 기준일과 배송 업무일이 다르거나 미확인입니다. 다른 날 근거를 자동 연결하지 않습니다.';
  const stops = stopsFor(tms);
  const target = stops.filter(stop => stop.id === contract.storeId);
  if (target.length !== 1 || !isStore(target[0]) || target[0].sequence !== contract.sequence) return '문의 점포의 방문키·유형·순번이 일치하지 않거나 중복입니다.';
  const sequences = stops.map(stop => stop.sequence);
  if (sequences.some(value => value === null) || new Set(sequences).size !== sequences.length) return '방문순번 누락·중복이 있어 연결을 보류합니다.';
  const visit = target[0].row;
  for (const [key, expected] of Object.entries({ caseId: contract.caseId, storeId: contract.storeId, bizDate: contract.bizDate, centerId: contract.centerId, routeId: contract.routeId, vehicle: contract.vehicle, relationStatus: 'exact', synthetic: true })) {
    if (visit[key] !== undefined && visit[key] !== expected) return '방문행의 사건·점포·배송키가 상위 사건과 다릅니다.';
  }
  if (visit.planned !== contract.planned || visit.actual !== contract.actual) return '방문 기록과 등록된 근거의 시각이 다릅니다. 관계를 다시 확인해야 합니다.';
  return null;
}

export function tmsEvidenceIssue(caseData: CaseData, evidence: Evidence): string | null {
  const relation = tmsRelationIssue(caseData);
  if (relation) return relation;
  const contract = sourceContract(caseData)!;
  const expected = contract.evidence.find(item => item.id === evidence.id);
  if (!expected) return '이 사건의 허용 근거가 아닙니다. 다른 점포·사건의 근거는 연결하지 않습니다.';
  if ((caseData.evidence ?? []).filter(item => item.id === evidence.id).length !== 1) return '근거 ID가 중복되어 연결할 수 없습니다.';
  for (const key of ['system', 'label', 'time', 'value', 'status', 'source'] as const) {
    if ((evidence[key] ?? null) !== (expected[key] ?? null)) return '근거 내용·출처·시각이 검토된 합성 입력과 달라 재확인이 필요합니다.';
  }
  const extra = evidence as unknown as Row;
  for (const [key, expectedValue] of Object.entries({ caseId: contract.caseId, storeId: contract.storeId, bizDate: contract.bizDate, centerId: contract.centerId, routeId: contract.routeId, vehicle: contract.vehicle, sequence: contract.sequence, relationStatus: 'exact', synthetic: true })) {
    if (extra[key] !== undefined && extra[key] !== expectedValue) return '근거의 명시적 관계키가 현재 사건과 다릅니다.';
  }
  const time = tmsTime(evidence.time, caseData.asOf, contract.bizDate);
  if (!['missing', 'recorded'].includes(time.state) || (time.date !== null && time.date !== contract.bizDate)) return '조회 기준 이후 또는 다른 업무일 근거는 연결할 수 없습니다.';
  return null;
}

export default function TmsScene(props: Props) {
  // Remount on relevant context changes, including same-ID replacement and late async callbacks.
  const contextKey = JSON.stringify([props.caseData.id, props.caseData.revision, props.caseData.selectedEvidence, props.caseData.store, props.caseData.type, props.caseData.asOf, props.caseData.tms, props.caseData.evidence, props.caseData.linkedFixtureId, props.caseData.channel, props.caseData.synthetic, props.caseData.intake?.storeId, props.caseData.storeId, props.caseData.subject, props.caseData.title]);
  return <TmsContent key={contextKey} {...props}/>;
}

function TmsContent({ caseData, onLinkEvidence, onBack }: Props) {
  const tms = rowOf(caseData.tms);
  const stops = stopsFor(tms);
  const target = stops.find(stop => stop.id === caseData.store.id && isStore(stop));
  const [selectedKey, setSelectedKey] = useState(target?.key ?? stops[0]?.key ?? '');
  const [order, setOrder] = useState<'sequence' | 'actual'>('sequence');
  const [playing, setPlaying] = useState(false);
  const [reduced, setReduced] = useState(false);
  const [frame, setFrame] = useState(0);
  const [pending, setPending] = useState<string | null>(null);
  const [linked, setLinked] = useState<string[]>([]);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const busy = useRef(false);
  const mounted = useRef(true);
  const mapTitle = useId();
  const selectId = useId();
  const selectedIndex = stops.findIndex(stop => stop.key === selectedKey);
  const selected = stops[selectedIndex];
  const selectedIsTarget = selected?.key === target?.key && target !== undefined;
  const relationIssue = tmsRelationIssue(caseData);
  const evidence = (caseData.evidence ?? []).filter(item => item.system?.toUpperCase() === 'TMS');
  const selectedEvidence = new Set([...(caseData.selectedEvidence ?? []), ...linked]);
  const businessDate = typeof tms.bizDate === 'string' && isoDate.test(tms.bizDate) ? tms.bizDate : '업무일 미등록';
  const timeOf = (value: unknown, planned = false) => tmsTime(value, caseData.asOf, businessDate, planned);

  useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);
  useEffect(() => {
    const media = window.matchMedia('(prefers-reduced-motion: reduce)');
    const update = () => { setReduced(media.matches); if (media.matches) setPlaying(false); };
    update(); media.addEventListener('change', update);
    return () => media.removeEventListener('change', update);
  }, []);
  useEffect(() => {
    if (!playing || reduced || stops.length < 2) return;
    const timer = window.setInterval(() => setFrame(value => (value + 0.06) % (stops.length * 3)), 60);
    return () => window.clearInterval(timer);
  }, [playing, reduced, stops.length]);

  function choose(stop: Stop) { setSelectedKey(stop.key); setPlaying(false); setFrame(stops.indexOf(stop) * 3); setError(''); setMessage(''); }
  async function link(item: Evidence) {
    if (busy.current || selectedEvidence.has(item.id)) return;
    const reason = tmsEvidenceIssue(caseData, item);
    if (!selectedIsTarget || reason) { setError(reason ?? '문의 점포를 선택한 뒤 근거를 연결해 주세요.'); return; }
    busy.current = true; setPending(item.id); setError(''); setMessage('');
    try {
      await onLinkEvidence(item.id);
      if (mounted.current) { setLinked(current => [...current, item.id]); setMessage(`${item.label} 근거를 ${caseData.id} 상담에 연결했습니다.`); }
    } catch (cause) {
      if (mounted.current) setError(`${cause instanceof Error ? cause.message : '저장 응답을 확인하지 못했습니다.'} ${cause instanceof ApiError && !cause.uncertain ? '안내 내용을 확인한 뒤 다시 시도해 주세요.' : '상단의 목록 새로고침으로 최신 접수를 조회해 연결 여부를 먼저 확인해 주세요.'}`);
    } finally { busy.current = false; if (mounted.current) setPending(null); }
  }

  const recorded = stops.map(stop => ({ stop, time: timeOf(stop.row.actual) })).filter(item => item.time.state === 'recorded');
  const reversal = recorded.some((item, index) => index > 0 && item.time.epoch! < recorded[index - 1].time.epoch!);
  const duplicateSequence = new Set(stops.map(stop => stop.sequence)).size !== stops.length || stops.some(stop => stop.sequence === null);
  const sortedStops = order === 'sequence' ? stops : [...stops].sort((a, b) => {
    const at = timeOf(a.row.actual), bt = timeOf(b.row.actual);
    return (at.state === 'recorded' ? at.epoch! : Infinity) - (bt.state === 'recorded' ? bt.epoch! : Infinity) || a.index - b.index;
  });
  const points = stops.map((_, index) => ({ x: stops.length < 2 ? 380 : 80 + index / (stops.length - 1) * 600, y: index % 2 ? 165 : 100 }));
  const segment = Math.min(Math.floor(frame / 3), Math.max(stops.length - 1, 0));
  const phase = frame % 3;
  const progress = Math.min(Math.max((phase - 1) / 2, 0), 1);
  const start = points[segment] ?? { x: 80, y: 100 };
  const end = points[Math.min(segment + 1, points.length - 1)] ?? start;
  const truck = { x: start.x + (end.x - start.x) * progress, y: start.y + (end.y - start.y) * progress };
  const selectedActual = timeOf(selected?.row.actual);
  const entry = timeOf(selected?.row.mobileEntry), exit = timeOf(selected?.row.mobileExit);
  const gpsReversed = entry.state === 'recorded' && exit.state === 'recorded' && exit.epoch! < entry.epoch!;
  const completedWithoutTime = selected && ['fact', 'completed', '완료'].includes(text(selected.row.status, '')) && selectedActual.state === 'missing';

  return <section className={styles.root} aria-label="TMS 방문 기록" data-testid="tms-scene">
    <header className={styles.header}>
      <div><p className={styles.eyebrow}>TMS · VISIT RECORDS</p><h1>배송 기록, 어디까지 확인됐나요?</h1><p className={styles.subtitle}>{caseData.store.name} · {caseData.id} · 문의 점포의 기록과 확인할 내용을 살펴보세요.</p></div>
      <button type="button" className={styles.back} onClick={onBack}>← 상담으로 돌아가기</button>
    </header>
    <div className={styles.context}><span className={styles.badge}>독립 합성 사례</span><span>업무일 <strong>{businessDate}</strong></span><span>센터 <strong>{text(tms.centerId)}</strong></span><span>루트 <strong>{text(tms.routeId)}</strong></span><span>차량 <strong>{text(tms.vehicle)}</strong></span><span>조회 기준 <strong>{asOfLabel(caseData.asOf)}</strong></span></div>
    <p className={styles.notice}>계획은 예정 시각, 배송완료는 시스템 등록, GPS 진출입은 접근 기록입니다. <strong>정확한 상품의 실물 인도 여부는 별도 확인이 필요합니다.</strong></p>
    {relationIssue && <p className={styles.warning} role="status">연결 보류 · {relationIssue}</p>}

    {!stops.length ? <div className={styles.empty}>등록된 TMS 방문행이 없습니다. 0회 방문이나 배송완료로 판단하지 않습니다.</div> : <>
      <div className={styles.workspace}>
        <section className={styles.panel} aria-label="방문순번 개념 지도">
          <div className={styles.panelHeader}><div><p className={styles.eyebrow}>ROUTE OVERVIEW</p><h2>방문순번 개념 지도</h2></div><span className={styles.badge}>실제 GPS 궤적 아님</span></div>
          <p className={styles.muted}>순번을 잇는 설명용 경로입니다. 차량 움직임은 실제 위치·도착 여부를 나타내지 않습니다.</p>
          <svg viewBox="0 0 760 250" className={styles.map} role="img" aria-labelledby={mapTitle} data-playing={playing}>
            <title id={mapTitle}>{`합성 방문순번 경로. 문의 점포 ${caseData.store.name}. 실제 도로·GPS 궤적이 아닙니다.`}</title>
            <path d="M 15 220 Q 180 145 380 225 T 750 210" className={styles.land}/>
            <polyline points={points.map(point => `${point.x},${point.y}`).join(' ')} className={styles.road}/>
            <polyline points={points.map(point => `${point.x},${point.y}`).join(' ')} className={styles.route}/>
            {stops.map((stop, index) => <g key={stop.key}><circle cx={points[index].x} cy={points[index].y} r={stop.key === selectedKey ? 22 : 17} className={stop.key === selectedKey ? styles.selectedNode : styles.node}/><text x={points[index].x} y={points[index].y + 5} textAnchor="middle" className={stop.key === selectedKey ? styles.selectedNumber : styles.nodeNumber}>{stop.sequence ?? '?'}</text></g>)}
            <g transform={`translate(${truck.x},${truck.y - 35})`} data-testid="tms-truck" aria-hidden="true"><rect x="-15" y="-10" width="23" height="16" rx="3" className={styles.truck}/><path d="M8 -5 H15 L20 1 V6 H8 Z" className={styles.truck}/><circle cx="-8" cy="8" r="4" className={styles.wheel}/><circle cx="13" cy="8" r="4" className={styles.wheel}/></g>
          </svg>
          <div className={styles.controls}><button type="button" onClick={() => setPlaying(value => !value)} disabled={reduced || stops.length < 2} aria-pressed={playing}>{playing ? '설명 재생 일시정지' : '설명 재생'}</button><button type="button" onClick={() => { setPlaying(false); setFrame(0); }}>처음으로</button><span className={styles.muted}>{reduced ? '동작 줄이기 적용 · 정지 화면' : '각 방문에서 1초 정지 · 설명용'}</span></div>
          <ol className={styles.visits} aria-label="방문 선택">{stops.map(stop => <li key={stop.key}><button type="button" onClick={() => choose(stop)} aria-pressed={stop.key === selectedKey}><span className={styles.visitNumber}>{stop.sequence ?? '?'}</span><span>{stop.name}<small>{stop.id === caseData.store.id ? '문의 점포' : stop.kind}</small></span></button></li>)}</ol>
        </section>

        <section className={styles.panel} aria-label="선택 방문 상세">
          <div className={styles.panelHeader}><div><p className={styles.eyebrow}>SELECTED VISIT</p><h2>{selected?.name ?? '방문 미선택'}</h2></div><span className={selectedIsTarget ? styles.badge : styles.compareBadge}>{selectedIsTarget ? '문의 점포' : '비교 방문'}</span></div>
          <div className={styles.controls}><button type="button" disabled={selectedIndex <= 0} onClick={() => choose(stops[selectedIndex - 1])}>← 이전 방문</button><button type="button" disabled={selectedIndex < 0 || selectedIndex >= stops.length - 1} onClick={() => choose(stops[selectedIndex + 1])}>다음 방문 →</button>{target && !selectedIsTarget && <button type="button" onClick={() => choose(target)}>문의 점포로</button>}</div>
          {!target && <p className={styles.warning}>문의 점포ID와 일치하는 점포 방문행이 없습니다.</p>}
          <dl className={styles.facts}>
            <div><dt>계획 도착</dt><dd>{timeOf(selected?.row.planned, true).label}</dd><small>예정 · 실제 도착과 구분</small></div>
            <div><dt>배송완료 등록</dt><dd data-testid="tms-actual">{selectedActual.label}</dd><small>{selectedActual.state === 'recorded' ? '시스템 등록 · 상품 인도 확인과 구분' : '기록 부재만으로 미도착 확정 불가'}</small></div>
            <div><dt>모바일 GPS 진입</dt><dd>{entry.label}</dd><small>현장 접근 기록</small></div>
            <div><dt>모바일 GPS 이탈</dt><dd>{exit.label}</dd><small>이동 기록 · 실물 인도 증거 아님</small></div>
          </dl>
          {completedWithoutTime && <p className={styles.warning}>상태는 완료이나 완료시각은 미등록입니다. 시각을 만들어 보충하지 않습니다.</p>}
          {gpsReversed && <p className={styles.warning}>GPS 이탈이 진입보다 이릅니다. 기록 충돌을 확인해야 합니다.</p>}
          <div className={styles.nextAction}><h3>아직 확인할 내용</h3><p>{selectedActual.state === 'recorded' ? '완료 등록 방법과 정확한 상품 인도 여부를 센터에 확인해 주세요.' : '배송 기록의 미등록 원인과 실제 도착·인도 여부를 센터에 확인해 주세요.'}</p><p>실물 인도: <strong>미확인</strong> · TMS 이벤트 영상: <strong>미등록</strong></p></div>
          <p className={styles.muted}>등록 방법: {text(selected?.row.registrationMethod, '미등록·센터 확인 필요')} · 방문유형: {selected?.kind ?? '미등록'}</p>
          {selected && sourceDetails('선택 방문', { caseId: caseData.id, bizDate: tms.bizDate, centerId: tms.centerId, routeId: tms.routeId, vehicle: tms.vehicle, ...selected.row })}
        </section>
      </div>

      <section className={styles.panel} aria-label="방문 기록 전체">
        <div className={styles.panelHeader}><div><p className={styles.eyebrow}>VISIT LEDGER</p><h2>방문 기록 전체</h2></div><label className={styles.sort} htmlFor={selectId}>표 정렬<select id={selectId} value={order} onChange={event => setOrder(event.target.value as 'sequence' | 'actual')}><option value="sequence">원천 방문순번</option><option value="actual">확인 가능한 완료시각</option></select></label></div>
        <p className={styles.muted}>원천 순번과 실제 방문순서는 같다고 확정할 수 없습니다. 시각 정렬은 표에만 적용하며 개념 경로의 순번을 바꾸지 않습니다.</p>
        {reversal && <p className={styles.warning}>방문순번과 완료시각 순서가 다릅니다. 원본 기록의 역전을 보존했습니다.</p>}
        {duplicateSequence && <p className={styles.warning}>방문순번 누락·중복이 있습니다. 방문키를 확인해야 합니다.</p>}
        <div className={styles.tableWrap} tabIndex={0} role="region" aria-label="방문 시각 표 · 좁은 화면에서 가로 스크롤"><table className={styles.table}><thead><tr><th scope="col">순번</th><th scope="col">방문지·유형</th><th scope="col">계획 도착</th><th scope="col">배송완료 등록</th><th scope="col">GPS 진입</th><th scope="col">GPS 이탈</th></tr></thead><tbody>{sortedStops.map(stop => <tr key={stop.key} className={stop.key === selectedKey ? styles.selectedRow : undefined}><td>{stop.sequence ?? '미등록'}</td><th scope="row"><button type="button" aria-pressed={stop.key === selectedKey} onClick={() => choose(stop)}>{stop.name}</button><small>{stop.id === caseData.store.id ? '문의 점포 · ' : ''}{stop.kind}</small></th><td>{timeOf(stop.row.planned, true).label}</td><td>{timeOf(stop.row.actual).label}</td><td>{timeOf(stop.row.mobileEntry).label}</td><td>{timeOf(stop.row.mobileExit).label}</td></tr>)}</tbody></table></div>
      </section>
    </>}

    <section className={styles.panel} aria-label="TMS 상담 근거 연결">
      <div className={styles.panelHeader}><div><p className={styles.eyebrow}>EVIDENCE FOR THIS CASE</p><h2>{caseData.store.name} 상담에 연결할 근거</h2></div><span className={styles.muted}>{caseData.id} · {evidence.length}건</span></div>
      {!selectedIsTarget && stops.length > 0 && <p className={styles.warning}>다른 방문의 근거는 이 문의에 연결하지 않습니다. 문의 점포를 선택해 주세요.</p>}
      {!evidence.length && <p className={styles.empty}>이 사건에 등록된 TMS 근거가 없습니다.</p>}
      <div className={styles.evidenceList}>{evidence.map((item, index) => {
        const reason = tmsEvidenceIssue(caseData, item);
        const connected = selectedEvidence.has(item.id) && reason === null;
        return <article className={styles.evidence} key={`${item.id}-${index}`}><div className={styles.evidenceTitle}><h3>{item.label}</h3><span className={reason ? styles.compareBadge : item.status === 'fact' ? styles.badge : styles.compareBadge}>{reason ? '관계 확인 필요' : item.status === 'fact' ? '시스템 기록' : '미확인 사항'}</span></div><p>{text(item.value)}</p><p className={styles.muted}>{timeOf(item.time).label} · {text(item.source)}</p>{reason && <p className={styles.warning}>{reason}</p>}<div className={styles.evidenceFooter}><span className={styles.muted}>{item.id} · {businessDate}</span><button type="button" className={connected ? styles.connected : styles.primary} disabled={pending !== null || connected || reason !== null || !selectedIsTarget} onClick={() => void link(item)}>{connected ? '연결됨' : pending === item.id ? '연결 중…' : '이 근거 연결'}</button></div>{sourceDetails('근거', item)}</article>;
      })}</div>
      {error && <p className={styles.error} role="alert">{error}</p>}<p className={styles.feedback} role="status" aria-live="polite">{message}</p>
    </section>
  </section>;
}
