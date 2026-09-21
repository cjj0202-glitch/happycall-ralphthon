'use client';

import { useEffect, useId, useRef, useState } from 'react';
import type { CaseData } from '@/lib/types';
import { ApiError } from '@/lib/api';
import fixtures from '../../../data/fixtures/cases.json';
import manifest from '../../../data/demo-media-manifest.json';
import styles from './WmsScene.module.css';

type Row = Record<string, unknown>;
type Props = { caseData: CaseData; onLinkEvidence(id: string): Promise<void> | void; onBack(): void };
type Clip = { id: string; caseId: string; system: string; cameraId: string; eventIds: string[]; occurredAt: string; url: string; startSeconds: number; endSeconds: number; synthetic: true; sha256: string; bytes: number };
const row = (value: unknown): Row => value !== null && typeof value === 'object' && !Array.isArray(value) ? value as Row : {};
const rows = (value: unknown): Row[] => Array.isArray(value) ? value.map(row) : [];
const label = (value: unknown, fallback = '미확인'): string => typeof value === 'string' && value.trim() ? value : typeof value === 'number' && Number.isFinite(value) ? String(value) : fallback;
// Reject timezone-free wall clock values; do not infer the source timezone.
const stamp = (value: unknown): number | null => typeof value === 'string' && /T.*(?:Z|[+-]\d{2}:\d{2})$/i.test(value) && Number.isFinite(Date.parse(value)) ? Date.parse(value) : null;
const visible = (value: unknown, asOf: unknown): boolean => stamp(value) !== null && stamp(asOf) !== null && stamp(value)! <= stamp(asOf)!;
const date = (value: unknown): string => stamp(value) === null ? '시각 미확인' : new Intl.DateTimeFormat('ko-KR', { timeZone: 'Asia/Seoul', year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hour12: false }).format(stamp(value)!) + ' KST';
const scan = (value: Row): string => `${label(value.product)} · ${label(value.quantity, '수량 미확인')} ${label(value.unit, '단위 미확인')}`;
const canonicalCase = (caseData: CaseData) => {
  const direct = fixtures.cases.find(item => item.id === caseData.id);
  if (direct) return direct;
  // A new intake must explicitly reference a source; never infer it from copied rows.
  if (typeof caseData.id !== 'string' || !/^INT-[A-Za-z0-9_-]+$/.test(caseData.id) || caseData.channel !== 'text' || typeof caseData.linkedFixtureId !== 'string') return undefined;
  return fixtures.cases.find(item => item.id === caseData.linkedFixtureId);
};
const sameSource = (left: unknown, right: unknown): boolean => {
  if (left === right) return true;
  if (Array.isArray(left) || Array.isArray(right)) return Array.isArray(left) && Array.isArray(right) && left.length === right.length && left.every((value, index) => sameSource(value, right[index]));
  if (!left || !right || typeof left !== 'object' || typeof right !== 'object') return false;
  const leftRow = row(left), rightRow = row(right), keys = Object.keys(leftRow);
  return keys.length === Object.keys(rightRow).length && keys.every(key => Object.hasOwn(rightRow, key) && sameSource(leftRow[key], rightRow[key]));
};
const stageFor = (caseData: CaseData, event: Row | undefined): number => event ? rows(canonicalCase(caseData)?.wms.events).findIndex(item => item.id === event.id) : -1;

function contextReason(caseData: CaseData): string {
  const baseline = canonicalCase(caseData);
  if (!baseline) return '등록된 합성 사건이 아닙니다. 사건 연결을 확인하세요.';
  const wms = row(caseData.wms), expected = row(baseline.wms);
  if (caseData.store?.id !== baseline.store.id) return '사건과 점포가 일치하지 않습니다.';
  if ((caseData.linkedFixtureId != null && caseData.linkedFixtureId !== baseline.id) || caseData.type !== baseline.type || caseData.asOf !== baseline.asOf) return '원본 사건·문의 유형·기준시각이 일치하지 않습니다.';
  for (const storeId of [caseData.storeId, row(caseData.intake).storeId]) {
    if (storeId != null && storeId !== baseline.store.id) return '접수 점포와 원본 사건의 점포가 일치하지 않습니다.';
  }
  if (caseData.id !== baseline.id && (!sameSource(caseData.wms, baseline.wms) || !sameSource(caseData.evidence, baseline.evidence))) return '신규 접수의 WMS 원본 행·근거가 연결된 사건과 일치하지 않습니다.';
  for (const [section, fields] of [['picking', ['orderId', 'toteId', 'pickedAt']], ['shipping', ['id', 'toteId', 'time']], ['sorting', ['sortedAt']]] as const) {
    for (const field of fields) if ((row(wms[section])[field] ?? null) !== (row(expected[section])[field] ?? null)) return '주문·출고·토트·시각의 등록 관계가 일치하지 않습니다.';
  }
  return '';
}

export function inspectWms(caseData: CaseData) {
  const wms = row(caseData.wms), picking = row(wms.picking), shipping = row(wms.shipping), sorting = row(wms.sorting);
  const events = rows(wms.events);
  const knownTimes = events.map(event => stamp(event.time)).filter((time): time is number => time !== null);
  const timeReversal = knownTimes.some((time, index) => index > 0 && time < knownTimes[index - 1]) || (stamp(sorting.sortedAt) !== null && stamp(picking.pickedAt) !== null && stamp(sorting.sortedAt)! < stamp(picking.pickedAt)!);
  const pickingVisible = visible(picking.pickedAt, caseData.asOf), shippingVisible = visible(shipping.time, caseData.asOf);
  const comparisonKnown = pickingVisible && shippingVisible && ['product', 'quantity', 'unit'].every(key => picking[key] !== null && picking[key] !== undefined && shipping[key] !== null && shipping[key] !== undefined);
  return { wms, picking, shipping, sorting, events, timeReversal, pickingVisible, shippingVisible, comparisonKnown, difference: comparisonKnown && ['product', 'quantity', 'unit'].some(key => picking[key] !== shipping[key]), contextError: contextReason(caseData) };
}

/** Only registrations in the shared fixture are playable. Candidate overlays need pc1 integration. */
export function validateWmsClip(caseData: CaseData, event: Row, media: unknown = caseData.media): { clip?: Clip; reason: string } {
  const contextError = contextReason(caseData);
  if (contextError) return { reason: contextError };
  const baseline = canonicalCase(caseData)!;
  if (caseData.id !== baseline.id) return { reason: '신규 접수 영상 미등록 · 원본 사건의 영상을 자동으로 연결하지 않습니다.' };
  const registeredEvent = rows(baseline.wms.events).find(item => item.id === event.id);
  if (!registeredEvent || !['time', 'location', 'source', 'status'].every(key => event[key] === registeredEvent[key])) return { reason: '이벤트의 등록 시각·출처·위치가 일치하지 않습니다.' };
  if (!visible(event.time, caseData.asOf)) return { reason: '이벤트 시각이 미확인이거나 기준시각 이후입니다.' };
  if (inspectWms(caseData).timeReversal) return { reason: '공정 시각 역전을 확인한 뒤 영상을 연결하세요.' };
  const related = rows(media).filter(item => Array.isArray(item.eventIds) && item.eventIds.includes(event.id));
  if (!related.length) return { reason: '영상 미등록 · 이 공정의 별도 영상이 필요합니다.' };
  if (related.length !== 1) return { reason: '중복 영상 등록을 확인하세요. 첫 영상을 임의 선택하지 않습니다.' };
  const candidate = related[0];
  const registered = rows(baseline.media).find(item => item.id === candidate.id && Array.isArray(item.eventIds) && item.eventIds.includes(event.id));
  if (!registered) return { reason: '미등록 영상 후보입니다. 메인의 사건·공정 등록이 필요합니다.' };
  const keys = ['id', 'caseId', 'system', 'cameraId', 'occurredAt', 'url', 'synthetic', 'startSeconds', 'endSeconds'];
  if (keys.some(key => candidate[key] !== registered[key]) || JSON.stringify(candidate.eventIds) !== JSON.stringify(registered.eventIds)) return { reason: '사건·카메라·이벤트·시각·영상 구간의 등록값이 일치하지 않습니다.' };
  if (candidate.caseId !== caseData.id || candidate.system !== 'WMS' || candidate.synthetic !== true || stamp(candidate.occurredAt) !== stamp(event.time)) return { reason: '영상과 선택 이벤트의 사건·시각이 다릅니다.' };
  const wms = row(caseData.wms), stage = stageFor(caseData, event);
  const process = row(stage === 0 ? wms.picking : stage === 3 ? wms.shipping : stage === 2 ? wms.sorting : undefined);
  const optional: Row = { caseId: caseData.id, system: 'WMS', storeId: caseData.store.id, orderId: row(wms.picking).orderId ?? null, pickingToteId: row(wms.picking).toteId ?? null, shippingToteId: row(wms.shipping).toteId ?? null, toteId: process.toteId ?? null, businessDate: row(baseline.tms).bizDate ?? null, asOf: baseline.asOf };
  // Only explicit process records provide a tote. A tote on another stage is not inferred.
  for (const [key, value] of Object.entries(optional)) {
    if ((key in candidate && candidate[key] !== value) || (key in row(candidate.relations) && row(candidate.relations)[key] !== value) || (key in event && event[key] !== value)) return { reason: '점포·주문·토트의 영상 관계가 일치하지 않거나 미확인입니다.' };
  }
  for (const [key, value] of Object.entries(row(registered.relations))) {
    if (row(candidate.relations)[key] !== value) return { reason: '영상 관계 메타데이터가 등록값과 다릅니다.' };
  }
  if ('cameraId' in event && event.cameraId !== candidate.cameraId) return { reason: '선택 이벤트의 카메라가 일치하지 않습니다.' };
  const url = String(candidate.url);
  if (!/^\/demo\/(?:[A-Za-z0-9_-]+\/)*[A-Za-z0-9_-]+\.mp4$/.test(url)) return { reason: '등록된 로컬 영상 경로가 아닙니다.' };
  const asset = manifest.assets.find(item => `/demo/${item.name}` === url);
  if (!asset || !('durationSeconds' in asset) || typeof candidate.startSeconds !== 'number' || typeof candidate.endSeconds !== 'number' || !Number.isFinite(candidate.startSeconds) || !Number.isFinite(candidate.endSeconds) || candidate.startSeconds < 0 || candidate.endSeconds <= candidate.startSeconds || candidate.endSeconds > asset.durationSeconds) return { reason: '영상 구간 또는 자산 정보가 유효하지 않습니다.' };
  if (('sha256' in candidate && candidate.sha256 !== asset.sha256) || ('hash' in candidate && candidate.hash !== asset.sha256) || ('bytes' in candidate && candidate.bytes !== asset.bytes)) return { reason: '영상 해시·크기가 등록 자산과 다릅니다.' };
  return { clip: { ...candidate, sha256: asset.sha256, bytes: asset.bytes } as Clip, reason: '' };
}

function Source({ name, data }: { name: string; data: unknown }) {
  return <details className={styles.source}><summary>{name} · 원본 보기</summary><pre>{JSON.stringify(data, null, 2)}</pre></details>;
}

function registeredEvidence(caseData: CaseData, evidence: Row): boolean {
  const registered = rows(canonicalCase(caseData)?.evidence).find(item => item.id === evidence.id);
  return !!registered && ['system', 'label', 'time', 'value', 'status', 'source'].every(key => evidence[key] === registered[key]);
}

function VideoDialog({ clip, event, picking, shipping, opener, onClose }: { clip: Clip; event: Row; picking: Row; shipping: Row; opener: HTMLElement; onClose(): void }) {
  const dialog = useRef<HTMLDialogElement>(null), video = useRef<HTMLVideoElement>(null);
  const title = useId();
  const [url, setUrl] = useState(''), [error, setError] = useState(''), [attempt, setAttempt] = useState(0);
  useEffect(() => { const player = video.current; return () => player?.pause(); }, [url, error]);
  useEffect(() => {
    const element = dialog.current;
    element?.showModal();
    return () => { video.current?.pause(); element?.close(); if (opener.isConnected) opener.focus(); };
  }, [opener]);
  useEffect(() => {
    const controller = new AbortController();
    let disposed = false, blobUrl = '';
    const timeout = window.setTimeout(() => controller.abort(), 15000);
    setUrl(''); setError('');
    (async () => {
      try {
        const response = await fetch(clip.url, { signal: controller.signal, credentials: 'same-origin', cache: 'no-store', redirect: 'error' });
        if (!response.ok) throw new Error(`영상 응답 ${response.status}`);
        const data = await response.arrayBuffer();
        if (data.byteLength !== clip.bytes) throw new Error('영상 바이트 수 불일치');
        const digest = await crypto.subtle.digest('SHA-256', data);
        const hash = Array.from(new Uint8Array(digest)).map(value => value.toString(16).padStart(2, '0')).join('');
        if (hash !== clip.sha256) throw new Error('영상 SHA256 불일치');
        if (disposed) return;
        blobUrl = URL.createObjectURL(new Blob([data], { type: 'video/mp4' }));
        setUrl(blobUrl);
      } catch (failure) { if (!disposed) setError(failure instanceof Error ? failure.message : '영상 검증 실패'); }
      finally { window.clearTimeout(timeout); }
    })();
    return () => { disposed = true; controller.abort(); window.clearTimeout(timeout); video.current?.pause(); if (blobUrl) URL.revokeObjectURL(blobUrl); };
  }, [clip, attempt]);
  const close = () => { video.current?.pause(); onClose(); };
  return <dialog ref={dialog} className={styles.dialog} aria-labelledby={title} onCancel={event => { event.preventDefault(); close(); }}>
    <header className={styles.dialogHead}><div><span className={styles.eyebrow}>합성 공정 영상 · 실제 CCTV 아님</span><h2 id={title}>{label(event.label)} 영상</h2></div><button type="button" className={styles.button} onClick={close} autoFocus aria-label="연결 영상 닫기">닫기 ×</button></header>
    <p className={styles.notice}>코드로 만든 공정 설명입니다. 실제 이동 경로·발생 공정·작업자 귀책의 증거가 아닙니다.</p>
    <div className={styles.meta}><span>{clip.caseId}</span><span>{clip.cameraId}</span><span>{label(event.id)}</span><span>{date(clip.occurredAt)}</span><span>{clip.startSeconds}–{clip.endSeconds}초</span></div>
    <div className={styles.videoGrid}><div>
      {error ? <div role="alert" className={styles.empty}><strong>영상 재생 차단</strong><p>{error}. 원본 기록을 확인하거나 다시 불러오세요.</p><button className={styles.button} type="button" onClick={() => setAttempt(value => value + 1)}>영상 다시 불러오기</button></div> : !url ? <div className={styles.empty} role="status">영상 바이트·SHA256 확인 중…</div> : <><video ref={video} src={url} className={styles.video} controls playsInline preload="metadata" aria-label="합성 공정 영상" onError={() => { video.current?.pause(); setError('영상 디코딩 실패'); }} onLoadedMetadata={event => { const player = event.currentTarget; if (!Number.isFinite(player.duration) || clip.endSeconds > player.duration + 0.05 || clip.startSeconds >= player.duration) { player.pause(); setError('등록 구간이 실제 영상 길이를 초과합니다'); return; } player.currentTime = clip.startSeconds; }} onTimeUpdate={event => { const player = event.currentTarget; if (player.currentTime >= clip.endSeconds) { player.pause(); if (player.currentTime > clip.endSeconds) player.currentTime = clip.endSeconds; } }} onSeeking={event => { const player = event.currentTarget; if (player.currentTime < clip.startSeconds) player.currentTime = clip.startSeconds; if (player.currentTime > clip.endSeconds) { player.pause(); player.currentTime = clip.endSeconds; } }} onPlay={event => { if (event.currentTarget.currentTime >= clip.endSeconds) event.currentTarget.currentTime = clip.startSeconds; }}>영상 재생을 지원하는 브라우저가 필요합니다.</video><p className={styles.verified}>등록 자산 SHA256·크기 확인 · 사용자가 재생할 때 시작합니다.</p></>}
      <p className={styles.caption}>카메라·이벤트 연결은 합성 시나리오의 등록 관계입니다. 실물 토트의 연속 이동은 미확인입니다.</p>
    </div><aside><h3>원본 스캔과 비교</h3><p>피킹: {scan(picking)}</p><p>출고: {scan(shipping)}</p><p className={styles.warning}>상품·단위를 대조하세요. 원인과 귀책은 미확인입니다.</p><Source name="선택 이벤트" data={event}/><Source name="피킹 기록" data={picking}/><Source name="출고 기록" data={shipping}/><Source name="영상 등록·해시" data={clip}/></aside></div>
  </dialog>;
}

export default function WmsScene(props: Props) {
  // Replacing upstream case contents also invalidates an open clip and pending UI feedback.
  return <Scene key={JSON.stringify([props.caseData.id, props.caseData.linkedFixtureId, props.caseData.type, props.caseData.storeId, row(props.caseData.intake).storeId, props.caseData.store, props.caseData.asOf, props.caseData.revision, props.caseData.status, props.caseData.wms, props.caseData.evidence, props.caseData.media])} {...props}/>;
}

function Scene({ caseData, onBack, onLinkEvidence }: Props) {
  const model = inspectWms(caseData), { picking, shipping, sorting, events } = model;
  const [selected, setSelected] = useState(0), [playing, setPlaying] = useState(false), [reduced, setReduced] = useState(false);
  const [active, setActive] = useState<{ clip: Clip; event: Row; opener: HTMLElement } | null>(null);
  const [pending, setPending] = useState(''), [error, setError] = useState(''), [message, setMessage] = useState(''), [linked, setLinked] = useState<string[]>([]);
  const requestPending = useRef(false), mounted = useRef(true);
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);
  useEffect(() => {
    const query = window.matchMedia('(prefers-reduced-motion: reduce)');
    const update = () => { setReduced(query.matches); if (query.matches) setPlaying(false); };
    update(); query.addEventListener('change', update); return () => query.removeEventListener('change', update);
  }, []);
  const current = events[selected], currentStage = stageFor(caseData, current), clipResult = current ? validateWmsClip(caseData, current) : { reason: '공정 기록 미등록' };
  const readOnly = !!caseData.status && !['draft', 'review'].includes(caseData.status);
  const safePicking = model.pickingVisible ? picking : {}, safeShipping = model.shippingVisible ? shipping : {};
  const steps = ['피킹', '소터 투입', '분기 / 슈트', '출고'];
  const nextActions = ['상품·수량·단위와 피킹 토트 원본을 확인하세요.', '투입 시각과 토트 연결 기록을 센터에 확인하세요.', '계획·실적 슈트와 분기 전후 연결을 확인하세요. 슈트 일치만으로 상품 일치를 확정할 수 없습니다.', '출고 스캔과 피킹 기록을 대조하고 센터에 토트 연결·상품 처리를 요청하세요.'];
  async function link(id: string) {
    const evidence = (caseData.evidence ?? []).find(item => item.id === id);
    if (requestPending.current || readOnly || model.contextError || !evidence || !registeredEvidence(caseData, evidence)) return;
    requestPending.current = true; setPending(id); setError(''); setMessage('');
    try { await onLinkEvidence(id); if (mounted.current) { setLinked(previous => [...previous, id]); setMessage('상담 근거에 연결했습니다.'); } }
    catch (failure) { if (mounted.current) setError(`${failure instanceof Error ? failure.message : '저장 응답을 확인하지 못했습니다.'} ${failure instanceof ApiError && !failure.uncertain ? '안내 내용을 확인한 뒤 다시 시도해 주세요.' : '상단의 목록 새로고침으로 최신 접수를 조회해 연결 여부를 먼저 확인해 주세요.'}`); }
    finally { requestPending.current = false; if (mounted.current) setPending(''); }
  }
  return <section className={styles.scene} aria-label="WMS 공정 확인">
    <header className={styles.header}><div><p className={styles.eyebrow}>WMS · 물류 기록 확인</p><h1>{caseData.store?.name || '점포 미확인'} <span>{caseData.type === 'wrong' ? '오출고 문의' : '미도착 문의'}</span></h1><p>{caseData.id} · 기준 {date(caseData.asOf)}</p></div><button className={styles.button} type="button" onClick={onBack}>상담으로 돌아가기</button></header>
    <p className={styles.caption} data-testid="source-reference">현재 접수 {label(caseData.id)} · 원본 사건 {label(canonicalCase(caseData)?.id, '미연결')}{model.contextError ? ' · 연결 검증 필요' : ''}</p>
    <p className={styles.notice}>독립 합성 시연 · 실제 WMS/CCTV 아님. 기록과 경영주 진술, 원인 미확인을 구분합니다.</p>
    {model.contextError && <p className={styles.warning} role="alert">{model.contextError} 영상·근거 연결이 차단되었습니다.</p>}
    <section className={styles.comparison} aria-label="피킹과 출고 기록 비교"><div><p className={styles.eyebrow}>피킹 기록</p><h2>{scan(safePicking)}</h2><p>토트 {label(safePicking.toteId)} · {model.pickingVisible ? date(picking.pickedAt) : '기준시각 내 피킹 시각 미확인'}</p><small>주문 {label(picking.orderId)} · 작업방식 {label(picking.workType)}</small></div><div><p className={styles.eyebrow}>출고 기록</p><h2>{scan(safeShipping)}</h2><p>토트 {label(safeShipping.toteId)} · {model.shippingVisible ? date(shipping.time) : '기준시각 내 출고 시각 미확인'}</p><small>출고 {label(shipping.id)} · 도크 {label(shipping.dock)}</small></div><div className={styles.finding}><strong>{model.difference ? '상품·수량·단위 기록 차이' : caseData.type === 'missing' ? '미수령 진술과 출고 기록을 구분' : '관측값과 미확인을 대조'}</strong><p>{caseData.type === 'missing' ? '경영주는 미수령을 진술했습니다. 센터 출고 기록만으로 점포 도착·인도를 확정할 수 없습니다.' : 'EA와 BOX는 환산하거나 차감하지 않습니다. 피킹·출고 토트의 연결과 차이가 발생한 공정은 추가 확인이 필요합니다.'}</p><b>발생 공정·작업자 귀책 미확인</b></div></section>
    <section className={styles.panel} aria-labelledby="pc3-process-title"><div className={styles.panelHead}><div><h2 id="pc3-process-title">공정별 기록</h2><p>원본 이벤트 순서를 유지합니다. 연속 위치 추적·snapshot 누계 재구성이 아닙니다.</p></div><button className={styles.button} type="button" disabled={reduced} aria-pressed={playing} data-testid="motion-toggle" onClick={() => setPlaying(value => !value)}>{reduced ? '모션 감소 · 정지' : playing ? '설명 이동 일시정지' : '설명 이동 시작'}</button></div>
      <div className={styles.diagram} aria-label="피킹, 소터 투입, 분기, 출고 개념도" data-testid="process-diagram" data-playing={playing && !reduced}><svg viewBox="0 0 800 84" role="img" aria-label="실제 좌표가 아닌 공정 설명"><path d="M65 42H735" stroke="#c5d3e1" strokeWidth="5" strokeDasharray="7 7"/>{[65, 290, 515, 735].map((x, i) => <g key={x}><circle cx={x} cy="42" r="25" fill={i === currentStage ? '#005ba8' : '#eef3f8'}/><text x={x} y="48" textAnchor="middle" fill={i === currentStage ? 'white' : '#334155'} fontSize="18">{i + 1}</text></g>)}<circle className={playing && !reduced ? styles.moving : undefined} cx="65" cy="42" r="7" fill="#b54708"/></svg></div>
      <div className={styles.events}>{events.map((event, index) => <button key={`${label(event.id)}:${index}`} type="button" className={`${styles.event} ${selected === index ? styles.selected : ''}`} aria-pressed={selected === index} data-testid={`event-${label(event.id)}`} onClick={() => { setSelected(index); setPlaying(false); }}><small>{String(index + 1).padStart(2, '0')} · {steps[stageFor(caseData, event)] || '공정 미확인'}</small><strong>{label(event.label)}</strong><span>{date(event.time)}</span><span>{label(event.location)}</span><em>{visible(event.time, caseData.asOf) ? '합성 기록' : '시각 확인 필요'}</em></button>)}</div>
      {!events.length && <p className={styles.empty}>공정 기록 미등록 · 센터 원본 확인이 필요합니다.</p>}
      {model.timeReversal && <p className={styles.warning} role="alert">공정 시각 역전이 있습니다. 원본을 보존했으며 발생 순서를 임의로 고치지 않았습니다.</p>}
      {events.some(event => !visible(event.time, caseData.asOf)) && <p className={styles.warning}>미등록·불명확·기준시각 이후 이벤트는 확정 근거로 사용할 수 없습니다.</p>}
    </section>
    {current && <section className={styles.detailGrid}><div className={styles.panel}><p className={styles.eyebrow}>선택 공정 · {label(current.id)}</p><h2>{label(current.label)}</h2><p>{date(current.time)} · {label(current.location)}</p><div className={styles.action}><h3>다음 확인 행동</h3><p>{nextActions[currentStage] || '사건 관계와 원본을 센터에 확인하세요.'}</p></div><dl className={styles.facts}><div><dt>피킹 토트</dt><dd>{label(safePicking.toteId)}</dd></div><div><dt>출고 토트</dt><dd>{label(safeShipping.toteId)}</dd></div><div><dt>계획 / 실적 슈트</dt><dd>{visible(sorting.sortedAt, caseData.asOf) ? `${label(sorting.schdChuteNo)} / ${label(sorting.rsltChuteNo)}` : '기준시각 내 분류 실적 미확인'}</dd></div><div><dt>토트 연속 연결</dt><dd>미확인 · 동일 이동으로 가정하지 않음</dd></div></dl><Source name="선택 이벤트" data={current}/><Source name="피킹 스캔" data={picking}/><Source name="분류 기록" data={sorting}/><Source name="출고 스캔" data={shipping}/></div>
      <div className={styles.panel}><p className={styles.eyebrow}>선택 공정의 합성 영상</p><h2>기록과 함께 확인</h2><p className={styles.caption}>영상은 설명용이며 원인·귀책 판정에 사용할 수 없습니다.</p>{clipResult.clip ? <><div className={styles.videoCard}><span className={styles.synthetic}>합성 · 실제 CCTV 아님</span><strong>{clipResult.clip.cameraId}</strong><p>{date(clipResult.clip.occurredAt)} · {clipResult.clip.startSeconds}–{clipResult.clip.endSeconds}초</p><button className={styles.primary} type="button" data-testid="open-video" onClick={event => setActive({ clip: clipResult.clip!, event: current, opener: event.currentTarget })}>등록된 합성 영상 열기</button></div><p className={styles.caption}>재생 전 등록 파일의 크기·SHA256을 확인합니다. 카메라 관계는 합성 시나리오에 한정됩니다.</p></> : <div className={styles.empty} data-testid="media-unavailable"><strong>연결 영상 없음</strong><p>{clipResult.reason}</p><p>원본 기록을 먼저 확인하세요. 다른 공정의 영상으로 대체하지 않습니다.</p></div>}<p className={styles.caption}>선택한 사건과 공정에 등록된 영상만 제공합니다. 영상이 없으면 원본 기록을 확인하고 센터에 추가 자료를 요청하세요.</p></div>
    </section>}
    <section className={styles.panel} aria-label="상담 근거"><h2>상담에 연결할 근거</h2><p>합성 기록·미확인 항목의 출처를 유지합니다. 연결 완료는 저장 응답 후 표시합니다.</p>{readOnly && <p className={styles.warning}>이관 이후 읽기 전용 · 상담 근거를 변경할 수 없습니다.</p>}<div className={styles.evidence}>{(caseData.evidence ?? []).filter(item => item.system === 'WMS').map(item => { const registered = registeredEvidence(caseData, item); const temporal = item.status === 'unknown' && !item.time || visible(item.time, caseData.asOf); const done = linked.includes(item.id) || caseData.selectedEvidence?.includes(item.id); return <article key={item.id}><span className={styles.eyebrow}>{item.status === 'unknown' ? '미확인 항목' : '합성 기록'} · {item.id}</span><h3>{item.label}</h3><p>{String(item.value ?? '값 미확인')}</p><small>{item.source} · {item.time ? date(item.time) : '시각 미등록'}</small><button className={styles.button} type="button" data-testid={`link-${item.id}`} disabled={readOnly || !!model.contextError || !registered || !temporal || !!pending || !!done} onClick={() => void link(item.id)}>{!registered ? '사건 근거 불일치' : done ? '연결됨' : pending === item.id ? '연결 중…' : !temporal ? '시각 확인 필요' : '상담 근거에 연결'}</button></article>; })}</div><p role="status" className={styles.verified}>{message}</p>{error && <p role="alert" className={styles.warning}>근거 연결 확인: {error}</p>}</section>
    {active && <VideoDialog {...active} picking={safePicking} shipping={safeShipping} onClose={() => setActive(null)}/>}
  </section>;
}
