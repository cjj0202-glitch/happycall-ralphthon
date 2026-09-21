'use client';

import { useEffect, useId, useRef, useState } from 'react';
import { frameAt, validateClip, validateDescriptor, validateTracks, validateTrackVideo, verifiedBytes } from '../lib/cctv-tracks';
import type { CctvClip, CctvTracks, RegisteredTracks } from '../lib/cctv-tracks';
import styles from './CctvInspector.module.css';

type Row = Record<string, unknown>;
export type CctvInspectorProps = { clip: CctvClip; event: Row; picking: Row; shipping: Row; opener: HTMLElement; onClose(): void } & RegisteredTracks;
const label = (value: unknown, fallback = '미확인') => typeof value === 'string' && value.trim() ? value : typeof value === 'number' && Number.isFinite(value) ? String(value) : fallback;
const elapsed = (value: number) => `${Math.floor(value / 60).toString().padStart(2, '0')}:${(value % 60).toFixed(2).padStart(5, '0')}`;
const recordTime = (value: string) => Number.isFinite(Date.parse(value)) ? new Intl.DateTimeFormat('ko-KR', { timeZone: 'Asia/Seoul', year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false }).format(Date.parse(value)) + ' KST' : '기록시각 미확인';
const scan = (value: Row) => `${label(value.product)} · ${label(value.quantity, '수량 미확인')} ${label(value.unit, '단위 미확인')}`;
function Source({ title, data }: { title: string; data: unknown }) { return <details className={styles.source}><summary>{title}</summary><pre>{JSON.stringify(data, null, 2)}</pre></details>; }

/** A new identity remounts the player, preventing stale video/track responses crossing cases. */
export default function CctvInspector(props: CctvInspectorProps) {
  return <Inspector key={JSON.stringify([props.clip, props.event, props.tracks, props.processAnchor, props.tracksError])} {...props}/>;
}

function Inspector({ clip, event, picking, shipping, opener, onClose, tracks: descriptor, processAnchor, tracksError: registrationError }: CctvInspectorProps) {
  const dialog = useRef<HTMLDialogElement>(null), video = useRef<HTMLVideoElement>(null), surface = useRef<HTMLDivElement>(null);
  const title = useId(), help = useId();
  const [url, setUrl] = useState(''), [error, setError] = useState(''), [attempt, setAttempt] = useState(0);
  const [trackData, setTrackData] = useState<CctvTracks | null>(null), [trackError, setTrackError] = useState(''), [trackAttempt, setTrackAttempt] = useState(0), [trackLoading, setTrackLoading] = useState(!!descriptor && !registrationError);
  const [metadata, setMetadata] = useState<{ width: number; height: number; duration: number } | null>(null);
  const [time, setTime] = useState(clip.startSeconds), [playing, setPlaying] = useState(false), [speed, setSpeed] = useState(1), [loop, setLoop] = useState(false), [overlay, setOverlay] = useState(true), [selected, setSelected] = useState(false), [full, setFull] = useState(false), [controlError, setControlError] = useState('');
  const loopRef = useRef(loop); loopRef.current = loop;
  const trackRef = useRef(trackData); trackRef.current = trackData;

  useEffect(() => {
    const element = dialog.current;
    element?.showModal();
    return () => { video.current?.pause(); element?.close(); if (opener.isConnected) opener.focus(); };
  }, [opener]);

  useEffect(() => {
    const controller = new AbortController(); let disposed = false, blobUrl = '';
    const timeout = window.setTimeout(() => controller.abort(), 15000);
    setUrl(''); setError(''); setMetadata(null); setPlaying(false); setTime(clip.startSeconds);
    (async () => {
      try {
        validateClip(clip, event);
        const bytes = await verifiedBytes(clip.url, clip.bytes, clip.sha256, controller.signal);
        if (disposed) return;
        blobUrl = URL.createObjectURL(new Blob([bytes], { type: 'video/mp4' })); setUrl(blobUrl);
      } catch (failure) { if (!disposed) setError(failure instanceof Error ? failure.message : '영상 검증 실패'); }
      finally { window.clearTimeout(timeout); }
    })();
    return () => { disposed = true; controller.abort(); window.clearTimeout(timeout); video.current?.pause(); if (blobUrl) URL.revokeObjectURL(blobUrl); };
  }, [clip, event, attempt]);

  useEffect(() => {
    setTrackData(null); setSelected(false); setTrackError(''); setTrackLoading(!!descriptor && !registrationError);
    if (!descriptor || registrationError) return;
    const controller = new AbortController(); let disposed = false;
    const timeout = window.setTimeout(() => controller.abort(), 15000);
    (async () => {
      try {
        validateDescriptor(descriptor, clip);
        const bytes = await verifiedBytes(descriptor.url, descriptor.bytes, descriptor.sha256, controller.signal);
        const parsed = validateTracks(JSON.parse(new TextDecoder('utf-8', { fatal: true }).decode(bytes)), descriptor, clip, event, processAnchor);
        if (!disposed) setTrackData(parsed);
      } catch (failure) { if (!disposed) setTrackError(failure instanceof Error ? failure.message : '객체 좌표 검증 실패'); }
      finally { window.clearTimeout(timeout); if (!disposed) setTrackLoading(false); }
    })();
    return () => { disposed = true; controller.abort(); window.clearTimeout(timeout); };
  }, [descriptor, clip, event, processAnchor, registrationError, trackAttempt]);

  let alignmentError = '';
  if (trackData && metadata) { try { validateTrackVideo(trackData, metadata.width, metadata.height, metadata.duration); } catch (failure) { alignmentError = failure instanceof Error ? failure.message : '영상·좌표 정합 실패'; } }
  const validatedTracks = trackData && metadata && !registrationError && !alignmentError && !error ? trackData : null;
  const issue = registrationError || trackError || alignmentError;
  // A partial clip's end is still a real frame in the asset; only the asset end is exclusive.
  const current = validatedTracks ? frameAt(validatedTracks, Math.min(time, validatedTracks.frameCount / validatedTracks.fps - 1e-7)) : null;

  useEffect(() => {
    const player = video.current; if (!player || !url) return;
    let disposed = false, callback = 0, fallback = 0;
    const update = (mediaTime: number) => {
      if (disposed) return;
      if (player.currentTime < clip.startSeconds) player.currentTime = clip.startSeconds;
      if (mediaTime >= clip.endSeconds || player.currentTime >= clip.endSeconds) {
        if (loopRef.current && !player.paused) { player.currentTime = clip.startSeconds; setTime(clip.startSeconds); }
        else { player.pause(); if (Math.abs(player.currentTime - clip.endSeconds) > 1e-6) player.currentTime = clip.endSeconds; setTime(clip.endSeconds); }
      } else setTime(Math.max(clip.startSeconds, mediaTime));
    };
    const hasFrameCallback = typeof player.requestVideoFrameCallback === 'function';
    const seeked = () => update(player.currentTime);
    // A queued pre-seek frame must not rewind the paused frame readout after a user step.
    const onFrame = (_: number, info: VideoFrameCallbackMetadata) => { if (!player.seeking && (!player.paused || Math.abs(info.mediaTime - player.currentTime) <= .5 / (trackRef.current?.fps ?? 24))) update(info.mediaTime); if (!disposed) callback = player.requestVideoFrameCallback(onFrame); };
    const timeupdate = () => { if (!hasFrameCallback || player.paused || player.currentTime >= clip.endSeconds || player.currentTime < clip.startSeconds) update(player.currentTime); };
    const tick = () => { update(player.currentTime); if (!disposed) fallback = requestAnimationFrame(tick); };
    player.addEventListener('seeked', seeked); player.addEventListener('timeupdate', timeupdate);
    if (hasFrameCallback) callback = player.requestVideoFrameCallback(onFrame); else fallback = requestAnimationFrame(tick);
    return () => { disposed = true; player.removeEventListener('seeked', seeked); player.removeEventListener('timeupdate', timeupdate); if (callback) player.cancelVideoFrameCallback(callback); if (fallback) cancelAnimationFrame(fallback); };
  }, [url, clip.startSeconds, clip.endSeconds]);

  useEffect(() => { const changed = () => setFull(document.fullscreenElement === surface.current); document.addEventListener('fullscreenchange', changed); return () => document.removeEventListener('fullscreenchange', changed); }, []);
  function close() { video.current?.pause(); if (document.fullscreenElement === surface.current) void document.exitFullscreen().catch(() => {}); onClose(); }
  async function togglePlay() { const player = video.current; if (!player) return; setControlError(''); if (!player.paused) { player.pause(); return; } if (player.currentTime >= clip.endSeconds) player.currentTime = clip.startSeconds; try { await player.play(); } catch { setControlError('브라우저가 재생을 시작하지 못했습니다. 재생 버튼을 다시 눌러 주세요.'); } }
  function seek(value: number) { const player = video.current; if (!player) return; player.currentTime = Math.max(clip.startSeconds, Math.min(clip.endSeconds, value)); setTime(player.currentTime); }
  function step(direction: number) { const player = video.current; if (!player || !validatedTracks) return; player.pause(); const fps = validatedTracks.fps; const index = Math.min(validatedTracks.frameCount - 1, Math.floor(player.currentTime * fps + 1e-6)); const lastIndex = Math.min(validatedTracks.frameCount - 1, Math.floor(clip.endSeconds * fps + 1e-6)); seek(Math.min(lastIndex, Math.max(Math.floor(clip.startSeconds * fps), index + direction)) / fps); }
  async function fullscreen() { setControlError(''); try { if (document.fullscreenElement === surface.current) await document.exitFullscreen(); else if (surface.current?.requestFullscreen) await surface.current.requestFullscreen(); else throw new Error(); } catch { setControlError('이 브라우저에서는 전체 화면을 사용할 수 없습니다. 현재 창에서 조사할 수 있습니다.'); } }
  const phase = current ? ({ approach: '접근', branch: '분기', chute: '슈트 이동', settle: '정지' }[current.phase]) : '좌표 없음';

  return <dialog ref={dialog} className={styles.dialog} aria-labelledby={title} aria-describedby={help} onCancel={e => { e.preventDefault(); close(); }} onClick={e => { if (e.target === e.currentTarget) { const box = e.currentTarget.getBoundingClientRect(); if (e.clientX < box.left || e.clientX > box.right || e.clientY < box.top || e.clientY > box.bottom) close(); } }} onKeyDown={e => {
    if (e.key !== 'Tab') return;
    const focusScope = document.fullscreenElement === surface.current ? surface.current : dialog.current;
    const focusable = [...(focusScope?.querySelectorAll<HTMLElement>('button:not(:disabled),select:not(:disabled),input:not(:disabled),summary,[tabindex="0"]') ?? [])].filter(item => item.getClientRects().length > 0);
    const first = focusable[0], last = focusable[focusable.length - 1];
    if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last?.focus(); } else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first?.focus(); }
  }}>
    <header className={styles.header}><div><p className={styles.eyebrow}>WMS · 공정 영상 조사</p><h2 id={title}>{label(event.label)} <span>연결 영상</span></h2></div><button type="button" onClick={close} autoFocus aria-label="연결 영상 닫기">닫기 ×</button></header>
    <p id={help} className={styles.notice}>합성 공정 설명입니다. 실제 CCTV·AI 검출 결과가 아니며, 발생 공정이나 작업자 귀책을 확정할 수 없습니다.</p>
    <dl className={styles.context}><div><dt>원본 사건 / 이벤트</dt><dd>{clip.caseId} / {label(event.id)}</dd></div><div><dt>등록 카메라</dt><dd>{clip.cameraId}</dd></div><div><dt>고정 기록시각</dt><dd data-testid="cctv-record-time">{recordTime(clip.occurredAt)}</dd></div></dl>
    <div className={styles.workspace}><section className={styles.main} aria-label="합성 영상과 재생 조작">
      {error ? <div role="alert" className={styles.empty}><strong>영상 재생 차단</strong><p>{error}</p><p>등록 자산을 확인한 뒤 다시 불러오세요.</p><button type="button" onClick={() => setAttempt(value => value + 1)}>영상 다시 불러오기</button></div> : !url ? <div role="status" className={styles.empty}>영상 바이트·SHA256 확인 중…</div> : <div ref={surface} className={styles.surface} data-testid="cctv-surface">
        <div className={styles.stage}><video ref={video} src={url} className={styles.video} playsInline preload="metadata" disablePictureInPicture controlsList="nofullscreen nodownload noremoteplayback" aria-label="합성 공정 영상" onLoadedMetadata={e => { const player = e.currentTarget; if (!Number.isFinite(player.duration) || clip.endSeconds > player.duration + 0.05 || clip.startSeconds >= player.duration) { player.pause(); setError('등록 구간이 실제 영상 길이를 초과합니다'); return; } setMetadata({ width: player.videoWidth, height: player.videoHeight, duration: player.duration }); player.currentTime = clip.startSeconds; player.playbackRate = speed; }} onError={() => { video.current?.pause(); setError('영상 디코딩 실패'); }} onSeeking={e => { const p = e.currentTarget; if (p.currentTime < clip.startSeconds) p.currentTime = clip.startSeconds; if (p.currentTime > clip.endSeconds) { p.pause(); p.currentTime = clip.endSeconds; } }} onPlay={() => setPlaying(true)} onPause={() => setPlaying(false)} onEnded={() => { if (loopRef.current) { seek(clip.startSeconds); void video.current?.play().catch(() => setControlError('구간 반복 재생을 시작하지 못했습니다.')); } }}>영상 재생을 지원하는 브라우저가 필요합니다.</video>
          <span className={styles.watermark}>합성 시연 · 실제 CCTV 아님</span>
          {overlay && current && <button type="button" className={`${styles.box} ${selected ? styles.boxSelected : ''}`} style={{ left: `${current.bboxNormalizedXYXY[0] * 100}%`, top: `${current.bboxNormalizedXYXY[1] * 100}%`, width: `${(current.bboxNormalizedXYXY[2] - current.bboxNormalizedXYXY[0]) * 100}%`, height: `${(current.bboxNormalizedXYXY[3] - current.bboxNormalizedXYXY[1]) * 100}%` }} aria-label={`시각 객체 ${current.visualObjectId} 선택`} aria-pressed={selected} onClick={() => setSelected(value => !value)} data-testid="cctv-bbox"><span>시각 객체 · {phase}</span></button>}
        </div>
        <div className={styles.transport}><div className={styles.time}><strong>시연 경과 <output data-testid="cctv-time">{elapsed(time)}</output></strong><span>{validatedTracks && current ? `${current.frame} / ${validatedTracks.frameCount} 프레임 · ${validatedTracks.fps} fps` : '프레임 좌표 미연결'}</span></div><input type="range" min={clip.startSeconds} max={clip.endSeconds} step={validatedTracks ? 1 / validatedTracks.fps : 0.01} value={time} aria-label="영상 구간 탐색" aria-valuetext={`${elapsed(time)} / ${elapsed(clip.endSeconds)}`} onChange={e => seek(Number(e.target.value))}/><div className={styles.controls}><button type="button" className={styles.primary} disabled={!metadata} onClick={() => void togglePlay()} aria-label={playing ? '영상 일시정지' : '영상 재생'}>{playing ? '일시정지' : '재생'}</button><button type="button" disabled={!validatedTracks} onClick={() => step(-1)} aria-label="이전 한 프레임">−1 프레임</button><button type="button" disabled={!validatedTracks} onClick={() => step(1)} aria-label="다음 한 프레임">+1 프레임</button><label className={styles.speed}>속도<select aria-label="영상 재생 속도" value={speed} onChange={e => { const value = Number(e.target.value); setSpeed(value); if (video.current) video.current.playbackRate = value; }}><option value="0.5">0.5×</option><option value="1">1×</option><option value="2">2×</option></select></label><button type="button" aria-pressed={loop} onClick={() => setLoop(value => !value)}>구간 반복 {loop ? '켜짐' : '꺼짐'}</button><button type="button" onClick={() => void fullscreen()}>{full ? '전체 화면 나가기' : '전체 화면'}</button></div><p className={styles.caption}>등록 구간 {elapsed(clip.startSeconds)}–{elapsed(clip.endSeconds)} · 고정 기록시각과 별개의 시연 시간입니다.</p>{controlError && <p role="alert" className={styles.warning}>{controlError}</p>}</div>
      </div>}
      {url && !error && <p className={styles.verified}>등록 자산 SHA256·크기 확인 · 사용자가 재생할 때 시작합니다.</p>}
      <div className={styles.viewbar}><strong>영상 보기</strong><div role="group" aria-label="객체 표시 보기"><button type="button" aria-pressed={!overlay} onClick={() => setOverlay(false)}>원본 영상</button><button type="button" aria-pressed={overlay} disabled={!validatedTracks} onClick={() => setOverlay(true)}>객체 표시</button></div></div>
      {trackLoading ? <p role="status" className={styles.caption}>객체 좌표 해시·사건 관계 확인 중…</p> : issue ? <div role="alert" className={styles.warning}><strong>객체 좌표 표시 중지</strong><p>{issue}</p><p>검증된 영상만 사용할 수 있습니다. 다른 장면의 좌표로 대체하지 않습니다.</p>{registrationError ? <p>배포 자산 등록을 확인한 뒤 화면을 새로 열어 주세요.</p> : <button type="button" onClick={() => setTrackAttempt(value => value + 1)}>객체 좌표 다시 불러오기</button>}</div> : !descriptor ? <p className={styles.caption}>객체 좌표 미등록 · 영상과 원본 기록만 제공합니다.</p> : validatedTracks ? <p className={styles.caption}>3D 투영 경계 · 실제 AI 검출 아님 · 가림 검증 안 됨</p> : <p className={styles.caption}>영상 메타데이터 확인 후 객체 좌표를 표시합니다.</p>}
    </section><aside className={styles.details} aria-label="객체와 원본 기록 비교">
      <section className={styles.objectPanel}><p className={styles.eyebrow}>선택한 시각 객체</p><h3>{selected && current ? current.visualObjectId : '객체를 선택하세요'}</h3><p>{selected && current ? `${phase} · 프레임 ${current.frame}` : validatedTracks ? '영상의 경계 상자나 아래 버튼으로 선택할 수 있습니다.' : '검증된 영상과 좌표가 연결되면 선택할 수 있습니다.'}</p><button type="button" disabled={!current} aria-pressed={selected} onClick={() => { setSelected(value => !value); setOverlay(true); }}>시각 객체 {selected ? '선택 해제' : '선택'}</button><dl className={styles.facts}><div><dt>업무 토트 연결</dt><dd>미확인 (null)</dd></div><div><dt>슈트 / 도크</dt><dd>{validatedTracks ? `${validatedTracks.eventAnchor.chuteId} / ${validatedTracks.eventAnchor.dockId}` : '좌표 등록 미확인'}</dd></div><div><dt>가림 검증</dt><dd>미실시</dd></div></dl><p className={styles.caption}>시각 객체 ID는 업무 토트 ID가 아닙니다. 화면에 보이는 경계는 실제 검출·연속 추적을 증명하지 않습니다.</p></section>
      <section className={styles.comparison}><h3>원본 스캔과 비교</h3><div><span>피킹 기록</span><strong>{scan(picking)}</strong><small>토트 {label(picking.toteId)}</small></div><div><span>출고 기록</span><strong>{scan(shipping)}</strong><small>토트 {label(shipping.toteId)}</small></div><p className={styles.warning}>상품·수량·단위를 대조하세요. 발생 공정·실물 동일성·작업자 귀책은 미확인입니다.</p></section>
      <Source title="선택 이벤트 · 원본" data={event}/>{processAnchor && <Source title="등록 공정의 슈트·도크 · 원본 대조" data={processAnchor}/>}<Source title="피킹 기록 · 원본" data={picking}/><Source title="출고 기록 · 원본" data={shipping}/><Source title="영상 등록 · 해시" data={clip}/>{descriptor && <Source title="객체 좌표 등록 · 해시" data={descriptor}/>}
    </aside></div>
  </dialog>;
}
