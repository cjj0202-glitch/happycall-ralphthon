'use client';

import { useEffect, useRef, useState } from 'react';
import type { CaseData } from '@/lib/types';
import { ApiError } from '@/lib/api';
import fixtures from '../../../data/fixtures/cases.json';
import manifest from '../../../data/demo-media-manifest.json';
import styles from './WmsScene.module.css';
import CctvInspector from './CctvInspector';
import { registeredTracks } from '../lib/cctv-tracks';
import type { RegisteredTracks } from '../lib/cctv-tracks';

type Row = Record<string, unknown>;
type Props = { caseData: CaseData; onLinkEvidence(id: string): Promise<void> | void; onBack(): void; backLabel?: string; readOnly?: boolean };
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
  for (const [section, fields] of [['picking', ['orderId', 'toteId', 'pickedAt']], ['shipping', ['id', 'toteId', 'time', 'dock']], ['sorting', ['sortedAt', 'rsltChuteNo']]] as const) {
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

/** Fixture identity gates the video; only the build-time manifest can register its coordinates. */
export function validateWmsClip(caseData: CaseData, event: Row, media: unknown = caseData.media): { clip?: Clip; reason: string } & RegisteredTracks {
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
  const clip = { ...Object.fromEntries(keys.map(key => [key, candidate[key]])), eventIds: candidate.eventIds, sha256: asset.sha256, bytes: asset.bytes } as Clip;
  return { clip, reason: '', ...registeredTracks(asset, clip, event, baseline.wms) };
}

function Source({ name, data }: { name: string; data: unknown }) {
  return <details className={styles.sourceInner}><summary>{name}</summary><pre>{JSON.stringify(data, null, 2)}</pre></details>;
}

function registeredEvidence(caseData: CaseData, evidence: Row): boolean {
  const registered = rows(canonicalCase(caseData)?.evidence).find(item => item.id === evidence.id);
  return !!registered && ['system', 'label', 'time', 'value', 'status', 'source'].every(key => evidence[key] === registered[key]);
}

export default function WmsScene(props: Props) {
  // Replacing upstream case contents also invalidates an open clip and pending UI feedback.
  return <Scene key={JSON.stringify([props.caseData.id, props.caseData.linkedFixtureId, props.caseData.type, props.caseData.storeId, row(props.caseData.intake).storeId, props.caseData.store, props.caseData.asOf, props.caseData.revision, props.caseData.status, props.caseData.wms, props.caseData.evidence, props.caseData.media])} {...props}/>;
}

function Scene({ caseData, onBack, onLinkEvidence, backLabel = '상담으로 돌아가기', readOnly: roleReadOnly = false }: Props) {
  const model = inspectWms(caseData), { picking, shipping, sorting, events } = model;
  const [selected, setSelected] = useState(0), [playing, setPlaying] = useState(false), [reduced, setReduced] = useState(false);
  const [active, setActive] = useState<({ clip: Clip; event: Row; opener: HTMLElement } & RegisteredTracks) | null>(null);
  const [pending, setPending] = useState(''), [error, setError] = useState(''), [message, setMessage] = useState(''), [linked, setLinked] = useState<string[]>([]);
  const requestPending = useRef(false), mounted = useRef(true);
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);
  useEffect(() => {
    const query = window.matchMedia('(prefers-reduced-motion: reduce)');
    const update = () => { setReduced(query.matches); if (query.matches) setPlaying(false); };
    update(); query.addEventListener('change', update); return () => query.removeEventListener('change', update);
  }, []);
  const current = events[selected], currentStage = stageFor(caseData, current), clipResult = current ? validateWmsClip(caseData, current) : { reason: '공정 기록 미등록' };
  const registeredVideos = events.map((event, index) => ({ event, index, result: validateWmsClip(caseData, event) })).filter(item => item.result.clip);
  const readOnly = roleReadOnly || (!!caseData.status && !['draft', 'review'].includes(caseData.status));
  const safePicking = model.pickingVisible ? picking : {}, safeShipping = model.shippingVisible ? shipping : {};
  const steps = ['상품 꺼내기', '분류기에 넣기', '분류기 갈림길', '내보내기'];
  const nextActions = ['꺼낸 상품과 수량, 그때 쓴 상자가 맞는지 센터에 확인해 주세요.', '분류기에 넣은 시각과 어느 상자였는지를 센터에 확인해 주세요.', '예정한 출구와 실제 나간 출구가 같은지 확인해 주세요. 출구가 같아도 상품이 같다고는 할 수 없습니다.', '내보낸 기록과 꺼낸 기록을 맞춰 보고, 상자 연결과 상품 처리를 센터에 요청해 주세요.'];
  async function link(id: string) {
    const evidence = (caseData.evidence ?? []).find(item => item.id === id);
    if (requestPending.current || readOnly || model.contextError || !evidence || !registeredEvidence(caseData, evidence)) return;
    requestPending.current = true; setPending(id); setError(''); setMessage('');
    try { await onLinkEvidence(id); if (mounted.current) { setLinked(previous => [...previous, id]); setMessage('상담 근거에 연결했습니다.'); } }
    catch (failure) { if (mounted.current) setError(`${failure instanceof Error ? failure.message : '저장 응답을 확인하지 못했습니다.'} ${failure instanceof ApiError && !failure.uncertain ? '안내 내용을 확인한 뒤 다시 시도해 주세요.' : '상단의 목록 새로고침으로 최신 접수를 조회해 연결 여부를 먼저 확인해 주세요.'}`); }
    finally { requestPending.current = false; if (mounted.current) setPending(''); }
  }
  const featured = registeredVideos[0];
  const featuredActive = featured && current && featured.event.id === current.id ? clipResult.clip : undefined;
  return <section className={styles.scene} aria-label="센터 작업 기록 확인">
    <header className={styles.header}>
      <div><h1>{caseData.store?.name || '점포 미확인'} <span>{caseData.type === 'wrong' ? '다른 상품이 왔어요' : '상품이 안 왔어요'}</span></h1><p>센터에서 상품을 꺼내 내보내기까지의 기록입니다. 기준 {date(caseData.asOf)}</p></div>
      <button className={styles.button} type="button" onClick={onBack}>{backLabel}</button>
    </header>
    {model.contextError && <p className={styles.warning} role="alert">{model.contextError} 영상과 기록 연결을 멈췄습니다.</p>}

    <section className={styles.comparison} aria-label="꺼낸 기록과 내보낸 기록 비교">
      <div><p className={styles.eyebrow}>센터가 꺼낸 상품</p><h2>{scan(safePicking)}</h2><p>상자 {label(safePicking.toteId)}</p><small>{model.pickingVisible ? date(picking.pickedAt) : '기준시각 안에서 꺼낸 시각을 확인할 수 없습니다'}</small></div>
      <div><p className={styles.eyebrow}>센터가 내보낸 상품</p><h2>{scan(safeShipping)}</h2><p>상자 {label(safeShipping.toteId)}</p><small>{model.shippingVisible ? date(shipping.time) : '기준시각 안에서 내보낸 시각을 확인할 수 없습니다'}</small></div>
      <div className={styles.finding}><strong>{model.difference ? '두 기록이 서로 다릅니다' : caseData.type === 'missing' ? '점포는 못 받았다고 합니다' : '아직 확인할 것이 남았습니다'}</strong><p>{caseData.type === 'missing' ? '센터에 내보낸 기록이 있어도 점포에 실제로 도착했는지는 따로 확인해야 합니다.' : '낱개와 박스는 서로 바꿔 계산하지 않습니다. 어느 단계에서 달라졌는지는 아직 모릅니다.'}</p><b>원인·담당자 미확인</b></div>
    </section>

    <section className={styles.panel} aria-labelledby="wms-scene-title">
      <div className={styles.panelHead}><div><h2 id="wms-scene-title">센터에서 무슨 일이 있었나</h2><p>합성으로 만든 센터 장면입니다. 실제 CCTV가 아닙니다.</p></div>{featured && <span className={styles.badge}>{label(featured.event.label)} 구간</span>}</div>

      {featured ? <div className={styles.stagePlayer}>
        <video className={styles.stageVideo} controls preload="metadata" playsInline src={featured.result.clip!.url} aria-label={`${label(featured.event.label)} 합성 장면`}/>
        <div className={styles.stageFoot}>
          <span className={styles.synthetic}>합성 장면 · 실제 CCTV 아님</span>
          <span>{date(featured.result.clip!.occurredAt)} 기록 · 영상은 {featured.result.clip!.endSeconds - featured.result.clip!.startSeconds}초로 줄여 보여 줍니다</span>
          <button className={styles.primary} type="button" data-testid="case-video-shortcut" onClick={event => { setSelected(featured.index); setPlaying(false); setActive({ clip: featured.result.clip!, event: featured.event, opener: event.currentTarget, tracks: featured.result.tracks, processAnchor: featured.result.processAnchor, tracksError: featured.result.tracksError }); }}>프레임별로 자세히 보기</button>
        </div>
      </div> : <p className={styles.empty}>이 문의에는 등록된 장면 영상이 없습니다. 아래 기록으로 확인해 주세요.</p>}

      <ol className={styles.stageList} aria-label="센터 처리 단계">{events.map((event, index) => {
        const stage = stageFor(caseData, event);
        const hasVideo = registeredVideos.some(item => item.index === index);
        return <li key={`${label(event.id)}:${index}`}>
          <button type="button" className={`${styles.stageStep} ${selected === index ? styles.selected : ''}`} aria-pressed={selected === index} data-testid={`event-${label(event.id)}`} onClick={() => { setSelected(index); setPlaying(false); }}>
            <span className={styles.stageNumber}>{index + 1}</span>
            <span className={styles.stageBody}><strong>{steps[stage] || '단계 미확인'}</strong><span>{date(event.time)}</span><span>{label(event.location)}</span></span>
            {hasVideo && <span className={styles.stageTag}>영상 있음</span>}
          </button>
        </li>;
      })}</ol>
      {!events.length && <p className={styles.empty}>센터 처리 기록이 없습니다. 센터에 원본 확인을 요청해 주세요.</p>}
      {model.timeReversal && <p className={styles.warning} role="alert">기록된 시각의 순서가 뒤바뀌어 있습니다. 원본을 그대로 두었고 순서를 임의로 고치지 않았습니다.</p>}
      {events.some(event => !visible(event.time, caseData.asOf)) && <p className={styles.warning}>시각이 없거나 기준시각보다 늦은 기록은 근거로 쓰지 않습니다.</p>}
    </section>

    {current && <section className={styles.panel} aria-label="선택한 단계">
      <div className={styles.panelHead}><div><h2>{steps[currentStage] || '선택한 단계'} · {label(current.label)}</h2><p>{date(current.time)} · {label(current.location)}</p></div>{featuredActive && <span className={styles.badge}>이 단계의 영상이 위에 있습니다</span>}</div>
      <div className={styles.action}><h3>다음에 확인할 것</h3><p>{nextActions[currentStage] || '이 기록과 문의의 연결을 센터에 확인해 주세요.'}</p></div>
      <dl className={styles.facts}>
        <div><dt>꺼낼 때 쓴 상자</dt><dd>{label(safePicking.toteId)}</dd></div>
        <div><dt>내보낼 때 쓴 상자</dt><dd>{label(safeShipping.toteId)}</dd></div>
        <div><dt>예정 / 실제 분류 출구</dt><dd>{visible(sorting.sortedAt, caseData.asOf) ? `${label(sorting.schdChuteNo)} / ${label(sorting.rsltChuteNo)}` : '기준시각 안에서 확인할 수 없습니다'}</dd></div>
        <div><dt>두 상자가 같은 것인지</dt><dd>미확인</dd></div>
      </dl>
      {clipResult.clip ? <div className={styles.videoCard}>
        <div><strong>이 단계의 장면이 있습니다</strong><p>{clipResult.clip.cameraId} · {date(clipResult.clip.occurredAt)}</p></div>
        <button className={styles.primary} type="button" data-testid="open-video" onClick={event => setActive({ clip: clipResult.clip!, event: current, opener: event.currentTarget, tracks: clipResult.tracks, processAnchor: clipResult.processAnchor, tracksError: clipResult.tracksError })}>이 단계 영상 자세히 보기</button>
      </div> : <div className={styles.empty} data-testid="media-unavailable"><strong>이 단계에는 영상이 없습니다</strong><p>{clipResult.reason}</p><p>다른 단계의 영상으로 대신하지 않습니다.</p></div>}
      {clipResult.tracksError && <p className={styles.warning} role="alert">영상 속 물체 좌표를 확인해야 합니다 · {clipResult.tracksError}</p>}
      <details className={styles.source}><summary>원본 기록 보기</summary><Source name="선택 단계" data={current}/><Source name="꺼낸 기록" data={picking}/><Source name="분류 기록" data={sorting}/><Source name="내보낸 기록" data={shipping}/></details>
    </section>}

    <section className={styles.panel} aria-label="상담 근거">
      <div className={styles.panelHead}><div><h2>이 문의에 붙일 기록</h2><p>고른 기록은 상담 화면과 센터에 그대로 전달됩니다.</p></div></div>
      {readOnly && <p className={styles.warning}>지금은 보기만 할 수 있습니다. 센터로 넘어간 접수의 기록은 바꾸지 않습니다.</p>}
      <div className={styles.evidence}>{(caseData.evidence ?? []).filter(item => item.system === 'WMS').map(item => { const registered = registeredEvidence(caseData, item); const temporal = item.status === 'unknown' && !item.time || visible(item.time, caseData.asOf); const done = linked.includes(item.id) || caseData.selectedEvidence?.includes(item.id); return <article key={item.id}><span className={styles.eyebrow}>{item.status === 'unknown' ? '아직 모르는 것' : '센터 기록'}</span><h3>{item.label}</h3><p>{String(item.value ?? '내용 미확인')}</p><small>{item.source} · {item.time ? date(item.time) : '시각 미등록'}</small><button className={styles.button} type="button" data-testid={`link-${item.id}`} disabled={readOnly || !!model.contextError || !registered || !temporal || !!pending || !!done} onClick={() => void link(item.id)}>{!registered ? '기록 확인 필요' : done ? '붙였습니다' : pending === item.id ? '붙이는 중…' : !temporal ? '시각 확인 필요' : '이 문의에 붙이기'}</button></article>; })}</div>
      <p role="status" className={styles.verified}>{message}</p>{error && <p role="alert" className={styles.warning}>{error}</p>}
    </section>

    <details className={styles.disclosure}>
      <summary>이 화면의 자료에 대하여</summary>
      <p>여기 나오는 점포·상품·시각·영상은 모두 시연을 위해 만든 합성 자료입니다. 실제 센터 시스템(WMS)이나 실제 CCTV가 아닙니다.</p>
      <p>기록이 있다는 것과 실제로 그 일이 일어났다는 것은 다릅니다. 영상과 좌표는 무슨 일이 있었는지 설명하기 위한 것이며, 발생 원인이나 담당자 책임을 정하는 데 쓸 수 없습니다.</p>
      <p>현재 접수 {label(caseData.id)} · 원본 사건 {label(canonicalCase(caseData)?.id, '미연결')}{model.contextError ? ' · 연결 확인 필요' : ''}</p>
    </details>
    {active && <CctvInspector {...active} picking={safePicking} shipping={safeShipping} onClose={() => setActive(null)}/>}
  </section>;
}
