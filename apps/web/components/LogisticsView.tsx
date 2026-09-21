'use client';

import { useEffect, useId, useRef, useState } from 'react';
import type { CaseData, Evidence } from '@/lib/types';
import styles from './LogisticsView.module.css';

type Props = {
  kind: 'wms' | 'tms';
  caseData: CaseData;
  onBack: () => void;
  onLinkEvidence: (id: string) => void | Promise<void>;
};
type Row = Record<string, unknown>;
type Point = { x: number; y: number };
type MediaClip = { id: string; caseId: string; system: string; cameraId: string; eventIds: string[]; url: string; synthetic: true; startSeconds: number; endSeconds: number; occurredAt: string };
type Stop = { id: string; name: string; sequence: number; planned: unknown; actual: unknown; mobileEntry: unknown; mobileExit: unknown; lat: number | null; lng: number | null; status: unknown };
type SortKey = 'sequence' | 'name' | 'planned' | 'actual' | 'mobileEntry' | 'mobileExit';
const object = (value: unknown): Row => value !== null && typeof value === 'object' && !Array.isArray(value) ? value as Row : {};
const rows = (value: unknown): Row[] => Array.isArray(value) ? value.map(object) : [];
const text = (value: unknown, fallback = '미등록'): string => typeof value === 'string' && value.trim() ? value : typeof value === 'number' && Number.isFinite(value) ? String(value) : fallback;
const number = (value: unknown): number | null => typeof value === 'number' && Number.isFinite(value) ? value : null;
const stamp = (value: unknown): number | null => typeof value === 'string' && Number.isFinite(Date.parse(value)) ? Date.parse(value) : null;
function atOrBefore(value: unknown, asOf: unknown): boolean {
  if (value === null || value === undefined || value === '') return true;
  const time = stamp(value); const cutoff = stamp(asOf);
  return time !== null && cutoff !== null && time <= cutoff;
}
function timeLabel(value: unknown, asOf?: unknown): string {
  if (value === null || value === undefined || value === '') return '미등록';
  if (asOf !== undefined && !atOrBefore(value, asOf)) return '기준시각 이후 / 미표시';
  const time = stamp(value);
  return time === null ? '시각 확인 필요' : new Intl.DateTimeFormat('ko-KR', { timeZone: 'Asia/Seoul', hour: '2-digit', minute: '2-digit', hour12: false }).format(time);
}
function dateLabel(value: unknown): string {
  const time = stamp(value);
  return time === null ? '기준시각 미등록' : new Intl.DateTimeFormat('ko-KR', { timeZone: 'Asia/Seoul', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hour12: false }).format(time) + ' KST';
}
function Source({ label, value }: { label: string; value: unknown }) {
  return <details className={styles.sourceDetails}><summary>{label} · 원본 행 보기</summary><pre className={styles.sourceCode}>{JSON.stringify(value, null, 2)}</pre></details>;
}
function Badge({ unknown = false }: { unknown?: boolean }) {
  return <span className={`${styles.badge} ${unknown ? styles.statusUnknown : styles.statusFact}`}>{unknown ? '원인 미확인' : '기록 확인'}</span>;
}
function position(points: Point[], progress: number): Point {
  if (!points.length) return { x: 90, y: 155 };
  if (points.length === 1) return points[0];
  const index = Math.min(Math.floor(progress * (points.length - 1)), points.length - 2);
  const fraction = progress * (points.length - 1) - index;
  return { x: points[index].x + (points[index + 1].x - points[index].x) * fraction, y: points[index].y + (points[index + 1].y - points[index].y) * fraction };
}

function clipForEvent(media: unknown, caseData: CaseData, kind: string, eventId: unknown): MediaClip | undefined {
  if (typeof eventId !== 'string' || !eventId) return;
  return rows(media).find(row => row.caseId === caseData.id && row.system === kind.toUpperCase() && row.synthetic === true &&
    Array.isArray(row.eventIds) && row.eventIds.includes(eventId) && typeof row.id === 'string' && typeof row.cameraId === 'string' &&
    typeof row.url === 'string' && row.url.startsWith('/') && !row.url.startsWith('//') &&
    number(row.startSeconds) !== null && number(row.endSeconds) !== null && Number(row.startSeconds) >= 0 && Number(row.endSeconds) > Number(row.startSeconds) &&
    stamp(row.occurredAt) !== null && atOrBefore(row.occurredAt, caseData.asOf)) as MediaClip | undefined;
}

function scanLabel(row: Row): string { return `${text(row.product)} ${text(row.quantity, '수량 미등록')} ${text(row.unit, '단위 미등록')}`; }

function EventVideo({ event, clip, picking, shipping, onClose, opener }: { event: Row; clip: MediaClip; picking: Row; shipping: Row; onClose: () => void; opener: HTMLElement | null }) {
  const dialog = useRef<HTMLDialogElement>(null);
  const video = useRef<HTMLVideoElement>(null);
  const titleId = useId();
  const [failed, setFailed] = useState(false);
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    const element = dialog.current; element?.showModal();
    return () => { element?.close(); if (opener?.isConnected) opener.focus(); };
  }, [opener]);
  return <dialog ref={dialog} className={styles.mediaDialog} aria-labelledby={titleId} onCancel={event => { event.preventDefault(); onClose(); }} onClick={event => {
    if (event.target !== event.currentTarget) return;
    const bounds = event.currentTarget.getBoundingClientRect();
    if (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom) onClose();
  }}>
    <div className={styles.panelHeader}><div><p className={styles.eyebrow}>AI SYNTHETIC CCTV · REFERENCE ONLY</p><h2 id={titleId} className={styles.panelTitle}>{text(event.label)} · 연결 영상</h2></div><button type="button" className={styles.button} onClick={onClose} autoFocus aria-label="연결 영상 닫기">닫기 ×</button></div>
    <div className={styles.mediaMetadata}><span className={styles.badge}>AI 합성 · 실제 CCTV 아님</span><span>{clip.caseId}</span><span>카메라 {clip.cameraId}</span><span>이벤트 {text(event.id)}</span><span>근거 시각 {dateLabel(event.time)}</span><span>영상 기준 {dateLabel(clip.occurredAt)}</span><span>구간 {clip.startSeconds}–{clip.endSeconds}초</span></div>
    <div className={styles.mediaGrid}><div>{failed ? <div className={styles.empty} role="alert"><p>연결 영상 또는 등록 구간을 재생할 수 없습니다. 원본 스캔은 오른쪽에서 계속 확인할 수 있습니다.</p><button type="button" className={styles.button} onClick={() => { setFailed(false); setRetry(value => value + 1); }}>영상 다시 불러오기</button></div> : <video key={retry} ref={video} className={styles.video} controls preload="metadata" playsInline aria-label={`${text(event.label)} AI 합성 CCTV 등록 구간`} onError={() => setFailed(true)} onLoadedMetadata={event => { const player = event.currentTarget; if (!Number.isFinite(player.duration) || clip.startSeconds >= player.duration || clip.endSeconds > player.duration + 0.25) { setFailed(true); return; } player.currentTime = clip.startSeconds; }} onTimeUpdate={event => { if (event.currentTarget.currentTime >= clip.endSeconds) { event.currentTarget.pause(); } }} onSeeking={event => { const player = event.currentTarget; if (player.currentTime < clip.startSeconds) player.currentTime = clip.startSeconds; else if (player.currentTime > clip.endSeconds) { player.pause(); player.currentTime = clip.endSeconds; } }} onPlay={event => { if (event.currentTarget.currentTime >= clip.endSeconds) event.currentTarget.currentTime = clip.startSeconds; }}><source src={clip.url} type="video/mp4" onError={() => setFailed(true)}/>브라우저에서 영상 재생을 지원하지 않습니다.</video>}<p className={styles.videoCaption}>AI 합성 공정 설명 영상입니다. 실제 이동·설비 위치나 오출 발생 지점을 입증하지 않으며, 영상만으로 휴먼에러 또는 작업자 귀책을 확정하지 않습니다.</p></div>
      <div><h3 className={styles.panelTitle}>원본 스캔과 비교</h3><div className={styles.observation}><strong>관측값 대조</strong><p>피킹: {scanLabel(picking)}</p><p>출고: {scanLabel(shipping)}</p><p>상품·수량·단위를 각각 확인합니다. 차이가 발생한 공정은 추가 확인이 필요합니다.</p></div><Source label="선택 이벤트" value={event}/><Source label="피킹 스캔" value={picking}/><Source label="출고 스캔" value={shipping}/><Source label="영상 연결 정보" value={clip}/></div></div>
  </dialog>;
}

export default function LogisticsView(props: Props) {
  return <LogisticsContent key={`${props.kind}:${props.caseData.id}:${props.caseData.asOf}`} {...props} />;
}

function LogisticsContent({ kind, caseData, onBack, onLinkEvidence }: Props) {
  const isWms = kind === 'wms';
  const svgTitle = useId();
  const [playing, setPlaying] = useState(false);
  const [reduced, setReduced] = useState(false);
  const [progress, setProgress] = useState(0);
  const [selectedStop, setSelectedStop] = useState(caseData.store.id);
  const [sort, setSort] = useState<{ key: SortKey; direction: 1 | -1 }>({ key: 'sequence', direction: 1 });
  const [pending, setPending] = useState<string | null>(null);
  const [linked, setLinked] = useState<string[]>([]);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [activeMedia, setActiveMedia] = useState<{ event: Row; clip: MediaClip; opener: HTMLElement | null } | null>(null);

  useEffect(() => {
    const media = window.matchMedia('(prefers-reduced-motion: reduce)');
    const update = () => { setReduced(media.matches); if (media.matches) setPlaying(false); };
    update(); media.addEventListener('change', update);
    return () => media.removeEventListener('change', update);
  }, []);
  useEffect(() => {
    if (!playing || reduced) return;
    const timer = window.setInterval(() => setProgress(current => (current + 0.008) % 1), 80);
    return () => window.clearInterval(timer);
  }, [playing, reduced]);

  const wms = object(caseData.wms);
  const tms = object(caseData.tms);
  const events = rows(wms.events).filter(row => atOrBefore(row.time, caseData.asOf)).sort((a, b) => (stamp(a.time) ?? Infinity) - (stamp(b.time) ?? Infinity));
  const allEvents = rows(wms.events);
  const picking = object(wms.picking);
  const shippingSource = object(wms.shipping);
  const shipping = atOrBefore(shippingSource.time, caseData.asOf) ? shippingSource : {};
  const sortingSource = object(wms.sorting);
  const sorting = atOrBefore(sortingSource.sortedAt, caseData.asOf) ? sortingSource : {};
  const pickingVisible = events.some(event => text(event.label, '').includes('피킹'));
  const scanDifference = pickingVisible && typeof picking.product === 'string' && typeof shipping.product === 'string' && (picking.product !== shipping.product || picking.unit !== shipping.unit || picking.quantity !== shipping.quantity);
  const eventMedia = events.map(event => ({ event, clip: clipForEvent(caseData.media, caseData, kind, event.id) })).filter((item): item is { event: Row; clip: MediaClip } => item.clip !== undefined);
  const evidence = (caseData.evidence ?? []).filter(row => row.system.toUpperCase() === kind.toUpperCase() && atOrBefore(row.time, caseData.asOf));
  const expected = object(caseData.expected);
  const received = object(caseData.received);
  const stops: Stop[] = rows(tms.stops).map((row, index) => ({ id: text(row.id, `stop-${index}`), name: text(row.name), sequence: number(row.sequence) ?? index + 1, planned: row.planned, actual: atOrBefore(row.actual, caseData.asOf) ? row.actual : null, mobileEntry: atOrBefore(row.mobileEntry, caseData.asOf) ? row.mobileEntry : null, mobileExit: atOrBefore(row.mobileExit, caseData.asOf) ? row.mobileExit : null, lat: number(row.lat), lng: number(row.lng), status: row.status })).sort((a, b) => a.sequence - b.sequence);
  const mappedStops = stops.filter((stop): stop is Stop & { lat: number; lng: number } => stop.lat !== null && stop.lng !== null);
  const latitudes = mappedStops.map(stop => stop.lat); const longitudes = mappedStops.map(stop => stop.lng);
  const minLat = Math.min(...latitudes); const maxLat = Math.max(...latitudes); const minLng = Math.min(...longitudes); const maxLng = Math.max(...longitudes);
  const mapPoints = mappedStops.map(stop => ({ ...stop, x: minLng === maxLng ? 380 : 130 + ((stop.lng - minLng) / (maxLng - minLng)) * 490, y: minLat === maxLat ? 155 : 235 - ((stop.lat - minLat) / (maxLat - minLat)) * 160 }));
  const truck = position(mapPoints, progress);
  const parcel = position([{ x: 100, y: 155 }, { x: 280, y: 155 }, { x: 460, y: 155 }, { x: 645, y: 235 }], progress);
  const sortedStops = [...stops].sort((a, b) => {
    const left = a[sort.key]; const right = b[sort.key];
    if (left == null && right == null) return a.sequence - b.sequence;
    if (left == null) return 1; if (right == null) return -1;
    return (typeof left === 'number' && typeof right === 'number' ? left - right : String(left).localeCompare(String(right), 'ko')) * sort.direction;
  });
  const selected = stops.find(stop => stop.id === selectedStop);
  const selectedEvidence = new Set([...(caseData.selectedEvidence ?? []), ...linked]);

  async function linkEvidence(row: Evidence) {
    if (pending || selectedEvidence.has(row.id)) return;
    setPending(row.id); setError(''); setMessage('');
    try { await onLinkEvidence(row.id); setLinked(current => [...current, row.id]); setMessage(`${row.label} 근거를 ${caseData.id}에 연결했습니다.`); }
    catch (cause) { setError(cause instanceof Error ? cause.message : '근거를 연결하지 못했습니다. 다시 시도해 주세요.'); }
    finally { setPending(null); }
  }
  function sortBy(key: SortKey) { setSort(current => ({ key, direction: current.key === key && current.direction === 1 ? -1 : 1 })); }
  const playback = <div className={styles.controls}><button type="button" className={styles.button} onClick={() => setPlaying(value => !value)} disabled={reduced || (!isWms && mapPoints.length < 2)} aria-pressed={playing}>{playing ? '설명 재생 일시정지' : '설명 재생'}</button><button type="button" className={styles.button} onClick={() => { setPlaying(false); setProgress(0); }}>처음으로</button><span className={styles.muted}>{reduced ? '동작 줄이기 설정 적용' : '설명용 이동 · 실제 상태와 무관'}</span></div>;

  return <section className={styles.root} aria-label={`${kind.toUpperCase()} 물류 확인`}>
    <header className={styles.header}>
      <div className={styles.heading}><p className={styles.eyebrow}>{kind.toUpperCase()} / {isWms ? 'WAREHOUSE OPERATIONS' : 'TRANSPORT OPERATIONS'}</p><h1>{isWms ? '센터 작업 흐름 확인' : '배송 방문 기록 확인'}</h1><p className={styles.subtitle}>{isWms ? '주문부터 피킹·분류·출고까지, 같은 사례의 기록을 대조합니다.' : '규정 시각과 배송·모바일 기록을 나란히 확인합니다.'}</p></div>
      <button type="button" className={styles.back} onClick={onBack}>← 같은 사례로 돌아가기</button>
    </header>
    <div className={styles.context}><strong>{caseData.store.name}</strong><span>{caseData.id}</span><span>{caseData.title}</span><span>조회 기준 {dateLabel(caseData.asOf)}</span><span className={styles.badge}>독립 합성 시연</span></div>
    <p className={styles.notice}>{isWms ? '소터·도크 이동은 합성 공정 설명입니다. 기록 차이만으로 발생 공정이나 작업자 귀책을 확정하지 않습니다.' : '지도는 가상 좌표의 방문순서 연결선이며 실제 GPS 궤적이 아닙니다. 배송완료 미등록은 실제 미도착 확정을 뜻하지 않습니다.'}</p>
    {stamp(caseData.asOf) === null && <p className={styles.warning}>조회 기준시각을 확인할 수 없어 시각이 있는 근거와 이벤트를 표시하지 않았습니다.</p>}

    {isWms ? <>
      <div className={styles.comparison}>
        {[{ label: '주문 내역', data: expected, caption: '주문 상품 · 수량 · 단위' }, { label: '점포 수령 내용', data: received, caption: '접수 진술 · 실물 대조 필요' }, { label: '출고 스캔', data: shipping, caption: '센터 기록 · 점포 인도 완료와 구분' }].map(item => <article key={item.label} className={styles.compareCard}><h2 className={styles.compareTitle}>{item.label}</h2><strong>{text(item.data.product)}</strong><p className={styles.quantity}>{text(item.data.quantity, '수량 미등록')} <span className={styles.unit}>{text(item.data.unit, '단위 미등록')}</span></p><p className={styles.muted}>{item.caption}</p></article>)}
      </div>
      {text(expected.unit, '') && text(received.unit, '') && expected.unit !== received.unit && <p className={styles.warning}>주문과 수령의 단위가 다릅니다. EA(개)와 BOX(박스)를 그대로 빼거나 동일 수량으로 환산하지 않습니다.</p>}
      <div className={styles.workspace}>
        <section className={styles.panel}><div className={styles.panelHeader}><div><p className={styles.eyebrow}>PROCESS REPLAY</p><h2 className={styles.panelTitle}>피킹 → 소터 → 출고</h2></div><span className={styles.badge}>합성 공정 설명</span></div>
          <svg className={styles.processSvg} viewBox="0 0 760 310" role="img" aria-labelledby={svgTitle} data-playing={playing && !reduced}>
            <title id={svgTitle}>피킹과 소터 분기, 출고 도크의 설명용 공정도. 실제 설비 위치나 이동 실적이 아닙니다.</title>
            <path className={styles.conveyor} d="M70 155 H470 L660 235 M470 155 L660 75" fill="none" strokeWidth="42" strokeLinecap="round" />
            <path className={styles.conveyorMark} d="M70 155 H470 L660 235 M470 155 L660 75" fill="none" strokeWidth="3" strokeDasharray="4 15" />
            {[{ x: 100, y: 155, title: '피킹', sub: pickingVisible ? text(picking.cell) : '기록 확인 필요' }, { x: 280, y: 155, title: '소터 투입', sub: '합성 투입 이벤트' }, { x: 460, y: 155, title: '분기', sub: '합성 분기 이벤트' }, { x: 650, y: 235, title: '출고 도크', sub: text(shipping.dock) }].map(station => <g key={station.title}><rect className={styles.station} x={station.x - 42} y={station.y - 23} width="84" height="46" rx="4"/><text className={styles.svgLabel} textAnchor="middle" x={station.x} y={station.y + 5}>{station.title}</text><text className={styles.svgMuted} textAnchor="middle" x={station.x} y={station.y + 48}>{station.sub}</text></g>)}
            <text className={styles.svgMuted} textAnchor="middle" x="655" y="44">다른 분기 · 설명용</text>
            <g className={styles.parcel} transform={`translate(${parcel.x}, ${parcel.y - 40})`}><rect x="-13" y="-12" width="26" height="24" rx="3"/><path d="M-13 -5H13 M0 -12V-5" fill="none"/></g>
          </svg>
          {playback}
          <div className={styles.facts}><div className={styles.fact}><span className={styles.factLabel}>피킹 위치</span><strong className={styles.factValue}>{pickingVisible ? `${text(picking.zone)} / ${text(picking.cell)}` : '기록 미확인'}</strong></div><div className={styles.fact}><span className={styles.factLabel}>피킹 토트</span><strong className={styles.factValue}>{pickingVisible ? text(picking.toteId) : '기록 미확인'}</strong></div><div className={styles.fact}><span className={styles.factLabel}>출고 기록 시각</span><strong className={styles.factValue}>{timeLabel(shipping.time, caseData.asOf)}</strong></div></div>
          <div className={styles.facts}><div className={styles.fact}><span className={styles.factLabel}>분류 실적 시각</span><strong className={styles.factValue}>{timeLabel(sorting.sortedAt, caseData.asOf)}</strong></div><div className={styles.fact}><span className={styles.factLabel}>예정 슈트</span><strong className={styles.factValue}>{text(sorting.schdChuteNo)}</strong></div><div className={styles.fact}><span className={styles.factLabel}>실적 슈트</span><strong className={styles.factValue}>{text(sorting.rsltChuteNo)}</strong></div></div>
          <p className={styles.muted}>슈트 번호의 일치 여부는 상품·토트 일치와 별도로 확인합니다.</p>
          <Source label="피킹 기록" value={pickingVisible ? picking : { status: '조회 기준 내 피킹 스캔 미확인' }}/><Source label="분류 기록" value={sorting}/><Source label="출고 기록" value={shipping}/>
        </section>
        <section className={styles.panel}><div className={styles.panelHeader}><div><p className={styles.eyebrow}>EVENT HISTORY</p><h2 className={styles.panelTitle}>작업 이벤트</h2></div><span className={styles.muted}>{events.length}개 기록</span></div>
          <ol className={styles.timeline}>{events.map((event, index) => {
            const clip = clipForEvent(caseData.media, caseData, kind, event.id);
            const observedDifference = scanDifference && text(event.label, '').includes('출고');
            return <li className={`${styles.timelineItem} ${observedDifference || activeMedia?.event.id === event.id ? styles.eventSelected : ''}`} key={text(event.id, String(index))}><time className={styles.timelineTime}>{timeLabel(event.time)}</time><div className={styles.timelineBody}><strong>{text(event.label)}</strong><p>{text(event.location)}</p>{observedDifference && <p className={styles.observation}>관측 차이: 피킹 {scanLabel(picking)} → 출고 {scanLabel(shipping)}. 발생 공정·귀책은 미확인입니다.</p>}<span className={styles.source}>{text(event.source)}</span>{clip ? <button type="button" className={styles.eventCta} onClick={click => setActiveMedia({ event, clip, opener: click.currentTarget })}><strong>AI 합성 CCTV 구간 보기</strong><span>{clip.cameraId} · {text(event.id)} · {timeLabel(event.time)} · {clip.startSeconds}–{clip.endSeconds}초</span></button> : <p className={styles.muted}>연결 영상 미등록</p>}<Source label="이벤트" value={event}/></div></li>;
          })}</ol>
          {!events.length && <p className={styles.empty}>조회 기준 내 작업 이벤트가 없습니다. 수량만으로 작업 완료를 판단하지 않습니다.</p>}
          {events.length < allEvents.length && <p className={styles.muted}>기준시각 이후이거나 시각을 확인할 수 없는 이벤트 {allEvents.length - events.length}건은 숨겼습니다.</p>}
        </section>
      </div>
      <section className={styles.panel}><div className={styles.panelHeader}><div><p className={styles.eyebrow}>EVENT LINKED CCTV</p><h2 className={styles.panelTitle}>이벤트에 연결된 AI 합성 영상</h2></div><span className={styles.badge}>AI 합성 · 실제 CCTV 아님</span></div>{eventMedia.length ? <><p className={styles.muted}>위 작업 이벤트의 CCTV 버튼으로 등록된 구간과 원본 스캔을 함께 확인하세요.</p><div className={styles.controls}>{eventMedia.map(({ event, clip }) => <button key={`${text(event.id)}:${clip.id}`} type="button" className={styles.eventCta} onClick={click => setActiveMedia({ event, clip, opener: click.currentTarget })}>{text(event.label)} · {clip.cameraId} · {timeLabel(event.time)} · AI 합성 구간 열기</button>)}</div></> : <p className={styles.empty}>이 사례의 WMS 이벤트에 연결된 영상이 미등록입니다.</p>}</section>
    </> : <>
      <div className={styles.facts}><div className={styles.fact}><span className={styles.factLabel}>센터 / 노선</span><strong className={styles.factValue}>{text(tms.centerId)} / {text(tms.routeId)}</strong></div><div className={styles.fact}><span className={styles.factLabel}>차량</span><strong className={styles.factValue}>{text(tms.vehicle)}</strong></div><div className={styles.fact}><span className={styles.factLabel}>방문 예정 점포</span><strong className={styles.factValue}>{stops.length}개</strong></div><div className={styles.fact}><span className={styles.factLabel}>완료 시각 등록</span><strong className={styles.factValue}>{stops.filter(stop => stamp(stop.actual) !== null).length} / {stops.length}개</strong></div></div>
      <section className={styles.panel}><div className={styles.panelHeader}><div><p className={styles.eyebrow}>ROUTE OVERVIEW</p><h2 className={styles.panelTitle}>가상 지역 · 방문순서 개념도</h2></div><span className={styles.badge}>GPS 아님</span></div>
        <svg className={styles.processSvg} viewBox="0 0 760 310" role="group" aria-labelledby={svgTitle}>
          <title id={svgTitle}>가상 좌표에 방문순서를 연결한 개념도. 트럭은 설명용이며 현재 위치를 나타내지 않습니다.</title>
          <rect className={styles.svgLand} width="760" height="310" rx="8"/><path className={styles.svgWater} d="M0 215 C160 265 230 175 400 215 S610 285 760 240 V275 C580 320 530 280 390 250 S160 310 0 250Z"/>
          <g className={styles.svgRoad} fill="none" strokeWidth="13"><path d="M0 90 L210 90 L295 165 L760 165"/><path d="M100 0 L100 310 M340 0L420 310 M655 0 L600 310"/><path d="M0 280L760 45"/></g>
          <text className={styles.svgMuted} x="24" y="30">가상 물류 권역</text><text className={styles.svgMuted} x="24" y="294">좌표·도로·트럭 이동은 합성 설명</text>
          {mapPoints.length > 1 && <polyline className={styles.svgRoute} points={mapPoints.map(point => `${point.x},${point.y}`).join(' ')} fill="none" strokeWidth="4" strokeDasharray="9 7"/>}
          {mapPoints.map(point => <g key={point.id} role="button" tabIndex={0} aria-label={`${point.sequence}번째 ${point.name} 방문 기록 선택`} aria-pressed={point.id === selectedStop} onClick={() => setSelectedStop(point.id)} onKeyDown={event => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); setSelectedStop(point.id); } }}><circle className={point.id === selectedStop ? styles.svgSelected : styles.svgNode} cx={point.x} cy={point.y} r="19"/><text className={styles.svgLabel} x={point.x} y={point.y + 5} textAnchor="middle">{point.sequence}</text><text className={styles.svgLabel} x={point.x} y={point.y - 31} textAnchor="middle">{point.name}</text><text className={styles.svgMuted} x={point.x} y={point.y + 42} textAnchor="middle">규정 {timeLabel(point.planned, caseData.asOf)}</text></g>)}
          {mapPoints.length > 0 && <g className={styles.truck} transform={`translate(${truck.x}, ${truck.y - 5})`} aria-hidden="true"><rect x="-16" y="-12" width="23" height="17" rx="2"/><path d="M7 -7H15L20 0V5H7Z"/><circle cx="-9" cy="7" r="4"/><circle cx="13" cy="7" r="4"/></g>}
        </svg>
        {playback}<p className={styles.legend}>번호는 방문순서입니다. 점포를 선택하면 아래 원본 방문행을 확인할 수 있습니다. {stops.length - mappedStops.length > 0 && `좌표 미등록 ${stops.length - mappedStops.length}개 점포는 표에서 확인하세요.`}</p>
        {!stops.length && <p className={styles.empty}>등록된 방문순서가 없습니다.</p>}
        {selected && <Source label={`${selected.name} 방문 기록`} value={{ ...selected, planned: atOrBefore(selected.planned, caseData.asOf) ? selected.planned : null, status: stamp(selected.actual) === null ? '배송완료 시각 미등록 · 원인 미확인' : '배송완료 시각 등록', source: `합성 TMS 방문행 ${text(tms.routeId)}/${selected.sequence}`, mapNote: '가상 좌표·방문순서 연결선. 실제 GPS 궤적 아님.' }}/>}</section>
      <section className={styles.panel}><div className={styles.panelHeader}><h2 className={styles.panelTitle}>방문별 시각 대조</h2><span className={styles.muted}>KST · 빈 기록은 미등록</span></div><div className={styles.tableWrap}><table className={styles.table}><caption className={styles.srOnly}>배송 방문 기록: 규정, 배송완료, 모바일 진입과 이탈 시각 비교</caption><thead><tr>{([{ key: 'sequence', label: '방문순번' }, { key: 'name', label: '점포' }, { key: 'planned', label: '규정 도착' }, { key: 'actual', label: '배송완료' }, { key: 'mobileEntry', label: '모바일 진입' }, { key: 'mobileExit', label: '모바일 이탈' }] as { key: SortKey; label: string }[]).map(column => <th scope="col" key={column.key} aria-sort={sort.key === column.key ? sort.direction === 1 ? 'ascending' : 'descending' : 'none'}><button type="button" className={styles.sortButton} onClick={() => sortBy(column.key)}>{column.label} {sort.key === column.key ? sort.direction === 1 ? '▲' : '▼' : '↕'}</button></th>)}</tr></thead><tbody>{sortedStops.map(stop => <tr key={stop.id} className={stop.id === selectedStop ? styles.selectedRow : undefined}><td className={styles.numeric}>{stop.sequence}</td><td><button type="button" className={styles.button} onClick={() => setSelectedStop(stop.id)} aria-pressed={stop.id === selectedStop}>{stop.name}{stop.id === caseData.store.id ? ' · 문의 점포' : ''}</button></td><td className={styles.numeric}>{timeLabel(stop.planned, caseData.asOf)}</td><td className={styles.numeric}>{timeLabel(stop.actual, caseData.asOf)}</td><td className={styles.numeric}>{timeLabel(stop.mobileEntry, caseData.asOf)}</td><td className={styles.numeric}>{timeLabel(stop.mobileExit, caseData.asOf)}</td></tr>)}</tbody></table></div><p className={styles.muted}>모바일 진입·이탈은 배송완료와 별개의 기록입니다. 미등록 원인과 실제 인도 여부는 센터 확인이 필요합니다.</p></section>
    </>}

    {!isWms && <p className={styles.empty}>이 사례의 TMS 이벤트에 연결된 영상이 미등록입니다.</p>}
    <section className={styles.panel}><div className={styles.panelHeader}><div><p className={styles.eyebrow}>LINKED EVIDENCE</p><h2 className={styles.panelTitle}>상담에 연결할 {kind.toUpperCase()} 근거</h2></div><span className={styles.muted}>{evidence.length}건 · {caseData.id}</span></div><div className={styles.evidenceList}>{evidence.map(row => <article className={styles.evidenceCard} key={row.id}><div className={styles.evidenceTop}><strong>{row.label}</strong><Badge unknown={row.status !== 'fact'}/></div><p className={styles.evidenceValue}>{text(row.value)}</p><div className={styles.evidenceFooter}><span className={styles.source}>{timeLabel(row.time)} · {text(row.source)}</span><button type="button" className={selectedEvidence.has(row.id) ? styles.linked : styles.primary} disabled={pending !== null || selectedEvidence.has(row.id)} onClick={() => void linkEvidence(row)}>{selectedEvidence.has(row.id) ? '연결됨' : pending === row.id ? '연결 중…' : '이 근거 연결'}</button></div><Source label={row.id} value={row}/></article>)}</div>{!evidence.length && <p className={styles.empty}>조회 기준 내 연결 가능한 근거가 없습니다.</p>}<p role="status" className={styles.muted}>{message}</p>{error && <p className={styles.error} role="alert">{error}</p>}</section>
    {activeMedia && <EventVideo key={`${activeMedia.clip.id}:${text(activeMedia.event.id)}`} {...activeMedia} picking={pickingVisible ? picking : {}} shipping={shipping} onClose={() => setActiveMedia(null)}/>}
  </section>;
}
