'use client';

import { useEffect, useId, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import type { CaseData, Intake, Mode, Transcript } from '@/lib/types';
import styles from './CallReview.module.css';

export type CallReviewProps = {
  caseData: CaseData;
  disabled?: boolean;
  onPlaybackEnded?: () => void;
  /** Tab-scoped preference supplied by Home; completion remains source-scoped. */
  playbackRate?: number;
  onPlaybackRateChange?: (rate: number) => void;
  /** Parent-owned analysis status. This component never calls an API. */
  analysisState?: 'idle' | 'loading' | 'error';
  analysisError?: string;
  onRetryAnalysis?: () => void;
  /** Describe the supplied transcript, not the mode of a future request. */
  transcriptMode?: Mode;
  /** Parent-owned actions/editing slots; no API or persistence is added here. */
  analysisActions?: ReactNode;
  intakeEditor?: ReactNode;
  /** Show the current task without destroying playback/unsaved editor state. */
  workStage?: 'source' | 'review' | 'handoff';
};

type Clip = { start: number; end: number; index: number };
type Playback = 'ready' | 'playing' | 'paused' | 'ended';
const playbackSpeeds = [0.75, 1, 1.25, 1.5, 2];
function safePlaybackRate(value: number | undefined, fallback = 1.25): number {
  return typeof value === 'number' && Number.isFinite(value) && value >= 0.75 && value <= 2 ? value : fallback;
}
const fields: { key: keyof Intake; label: string }[] = [
  { key: 'storeId', label: '점포 ID' },
  { key: 'subject', label: '상품·문의 대상' },
  { key: 'quantity', label: '수령 수량(경영주 진술)' },
  { key: 'unit', label: '수령 단위(경영주 진술)' },
  { key: 'request', label: '요청사항' },
];

function valueText(value: unknown): string {
  if (typeof value === 'number' && Number.isFinite(value)) return String(value);
  return typeof value === 'string' && value.trim() ? value : '미확인';
}

function clock(seconds: number): string {
  const safe = Number.isFinite(seconds) && seconds >= 0 ? Math.floor(seconds) : 0;
  return `${Math.floor(safe / 60)}:${String(safe % 60).padStart(2, '0')}`;
}

function clipClock(seconds: number): string {
  if (Number.isInteger(seconds)) return clock(seconds);
  const milliseconds = Math.round(seconds * 1000);
  return `${clock(Math.floor(milliseconds / 1000))}.${String(milliseconds % 1000).padStart(3, '0')}`;
}

function clipFor(line: Transcript, duration: number | null): { start?: number; end?: number; reason?: string } {
  const { start, end } = line;
  if (start == null || end == null) return { reason: '발화 시각 없음 · 구간을 추정하지 않습니다' };
  if (typeof start !== 'number' || typeof end !== 'number' || !Number.isFinite(start) || !Number.isFinite(end)) {
    return { reason: '발화 시각이 유효한 숫자가 아닙니다' };
  }
  if (start < 0 || end <= start) return { reason: '발화 시작·종료 시각 확인 필요' };
  if (duration === null) return { reason: '음원 길이 확인 후 구간 재생 가능' };
  if (end > duration) return { reason: '발화 구간이 음원 길이를 벗어납니다' };
  return { start, end };
}

/** Native played ranges are evidence of playback; the cursor reaching the end is not. */
function playedWholeAudio(audio: HTMLAudioElement): boolean {
  if (!Number.isFinite(audio.duration) || audio.duration <= 0 || !audio.played.length) return false;
  let covered = 0;
  for (let index = 0; index < audio.played.length; index += 1) {
    if (audio.played.start(index) > covered + 0.05) return false;
    covered = Math.max(covered, audio.played.end(index));
  }
  return covered >= audio.duration - Math.min(0.1, audio.duration * 0.01);
}

export default function CallReview(props: CallReviewProps) {
  // Replacing a case OR its source destroys the old player, callbacks and local gate.
  const sourceKey = JSON.stringify([props.caseData.id, props.caseData.channel, props.caseData.audioUrl ?? null]);
  return <ReviewSession key={sourceKey} {...props} />;
}

function ReviewSession({ caseData, disabled = false, onPlaybackEnded, playbackRate, onPlaybackRateChange, analysisState = 'idle', analysisError, onRetryAnalysis, transcriptMode, analysisActions, intakeEditor, workStage }: CallReviewProps) {
  const id = useId();
  const audioRef = useRef<HTMLAudioElement>(null);
  const alive = useRef(false);
  const completeNotified = useRef(false);
  const fullAttempt = useRef(false);
  const sought = useRef(false);
  const clip = useRef<Clip | null>(null);
  const autoStart = useRef(false);
  const [attempt, setAttempt] = useState(0);
  const [duration, setDuration] = useState<number | null>(null);
  const [position, setPosition] = useState(0);
  const [playback, setPlayback] = useState<Playback>('ready');
  const [mediaError, setMediaError] = useState('');
  const [complete, setComplete] = useState(false);
  const [seekNotice, setSeekNotice] = useState(false);
  const [hiddenClipNotice, setHiddenClipNotice] = useState(false);
  const [segmentIndex, setSegmentIndex] = useState<number | null>(null);
  const [localRate, setLocalRate] = useState(() => safePlaybackRate(playbackRate));
  const rate = safePlaybackRate(playbackRate, localRate);
  const [volume, setVolume] = useState(1);
  const [muted, setMuted] = useState(false);
  const [showTranscript, setShowTranscript] = useState(true);
  const voice = caseData.channel === 'voice';
  const audioUrl = typeof caseData.audioUrl === 'string' && caseData.audioUrl.trim() ? caseData.audioUrl : undefined;
  const transcript = caseData.transcript ?? [];
  const speakers = [...new Set(transcript.map(line => valueText(line.speaker)))];
  const unnamedSpeakers = speakers.filter(speaker => speaker !== '상담원' && speaker !== '경영주');
  const unknownStartsWithOwnerTone = speakers.includes('상담원') && !speakers.includes('경영주');
  const analysis = caseData.analysis;
  const suppliedMode = transcriptMode ?? caseData.analysisMode;
  const mode = suppliedMode === 'replay' || suppliedMode === 'demo-live' ? suppliedMode : undefined;
  const transcriptLabel = mode === 'replay' ? '합성 대화록 · 저장 결과 재생' : mode === 'demo-live' && voice ? '실제 STT 결과 · 인식 오류 확인 필요' : '전사 출처 미확인';
  const canRetryAnalysis = !disabled && analysisState === 'error' && (!voice || (!!caseData.audioUrl && !mediaError));

  useEffect(() => {
    alive.current = true;
    return () => { alive.current = false; };
  }, []);

  useEffect(() => {
    const audio = audioRef.current;
    return () => { audio?.pause(); };
  }, [attempt]);

  useEffect(() => {
    if (!workStage || workStage === 'source') return;
    autoStart.current = false;
    clip.current = null;
    setSegmentIndex(null);
    audioRef.current?.pause();
  }, [workStage]);

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;
    audio.preservesPitch = true;
    if (audio.playbackRate !== rate) audio.playbackRate = rate;
  }, [rate, attempt]);

  useEffect(() => {
    if (!disabled) return;
    fullAttempt.current = false;
    if (audioRef.current && audioRef.current.currentTime > 0) {
      sought.current = true;
      setSeekNotice(true);
    }
    autoStart.current = false;
    clip.current = null;
    setSegmentIndex(null);
    audioRef.current?.pause();
  }, [disabled]);

  useEffect(() => {
    function onVisibilityChange() {
      if (!document.hidden || !clip.current || !alive.current) return;
      fullAttempt.current = false;
      sought.current = true;
      clip.current = null;
      setSegmentIndex(null);
      setHiddenClipNotice(true);
      audioRef.current?.pause();
    }
    document.addEventListener('visibilitychange', onVisibilityChange);
    return () => document.removeEventListener('visibilitychange', onVisibilityChange);
  }, []);

  // Keep segment playback bounded even between the browser's timeupdate events.
  useEffect(() => {
    if (segmentIndex === null) return;
    let frame = 0;
    const tick = () => {
      const audio = audioRef.current;
      const selected = clip.current;
      if (!audio || !selected || !alive.current) return;
      if (stopAtClipEnd(audio)) return;
      frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [segmentIndex]);

  function isCurrent(audio: HTMLAudioElement): boolean {
    return alive.current && audioRef.current === audio;
  }

  function changePlaybackRate(value: number) {
    const next = safePlaybackRate(value, rate);
    setLocalRate(next);
    // Commit before the asynchronous native ratechange, including immediate case navigation.
    onPlaybackRateChange?.(next);
    const audio = audioRef.current;
    if (audio && audio.playbackRate !== next) audio.playbackRate = next;
  }

  function stopAtClipEnd(audio: HTMLAudioElement): boolean {
    const selected = clip.current;
    if (!isCurrent(audio) || !selected || audio.currentTime < selected.end) return false;
    clip.current = null;
    fullAttempt.current = false;
    sought.current = true;
    audio.pause();
    audio.currentTime = selected.end;
    setPosition(selected.end);
    setSegmentIndex(null);
    return true;
  }

  function play(audio: HTMLAudioElement) {
    void audio.play().catch((error: unknown) => {
      // An intentional pause (including a hidden tab) can cancel a pending play().
      if (!isCurrent(audio) || disabled || (error instanceof DOMException && error.name === 'AbortError')) return;
      fullAttempt.current = false;
      clip.current = null;
      setSegmentIndex(null);
      setMediaError('음원을 재생하지 못했습니다. 음원을 다시 불러온 후 재생해 주세요.');
    });
  }

  function restart(startPlaying: boolean) {
    if (disabled || !audioUrl) return;
    audioRef.current?.pause();
    fullAttempt.current = false;
    sought.current = false;
    clip.current = null;
    autoStart.current = startPlaying;
    setDuration(null);
    setPosition(0);
    setPlayback('ready');
    setMediaError('');
    setSeekNotice(false);
    setHiddenClipNotice(false);
    setSegmentIndex(null);
    // A new media element resets played ranges and isolates stale media events.
    setAttempt(current => current + 1);
  }

  function playClip(line: Transcript, index: number) {
    const audio = audioRef.current;
    const range = clipFor(line, duration);
    if (!audio || disabled || document.hidden || mediaError || range.start === undefined || range.end === undefined) return;
    fullAttempt.current = false;
    sought.current = true;
    setSeekNotice(true);
    setHiddenClipNotice(false);
    clip.current = { start: range.start, end: range.end, index };
    setSegmentIndex(index);
    audio.currentTime = range.start;
    play(audio);
  }

  const playbackLabel = disabled ? '재생 일시 중지 · 현재 조작할 수 없습니다' : mediaError ? '음원 오류' : segmentIndex !== null ? '선택 발화 구간 재생' : playback === 'playing' ? `통화 재생 중${complete ? ' · 이전 전체 재생 완료' : ''}` : complete ? '전체 통화 재생 완료' : playback === 'paused' ? '통화 일시정지' : playback === 'ended' ? '재생 종료 · 전체 재생 확인 필요' : '재생 준비';

  const analysisFeedback = <>
          {analysisState === 'loading' && <p className={styles.notice} role="status">AI 분석 중 · 원문과 현재 상담 입력을 보존하고 있습니다.</p>}
          {analysisState === 'error' && <div className={styles.error}><p role="alert">{analysisError || 'AI 분석에 실패했습니다. 원문과 현재 상담 입력은 유지됩니다.'}</p>{onRetryAnalysis ? <button type="button" disabled={!canRetryAnalysis} onClick={() => { if (canRetryAnalysis) onRetryAnalysis(); }}>AI 분석 다시 시도</button> : <p>상위 화면에서 분석을 다시 실행해 주세요.</p>}{voice && !complete && <p>전체 녹음 파일을 기준으로 분석을 다시 시도합니다.</p>}</div>}
  </>;
  const sourceTextContent = <section className={styles.card} aria-labelledby={`${id}-source-title`}>
          <div className={styles.sectionHeading}><h3 id={`${id}-source-title`}>{voice ? '합성 통화 원대본' : '접수 원문'}</h3><span className={styles.badge}>원문 보존</span></div>
          {!workStage && <p className={styles.help}>{voice ? '음성 생성에 사용한 합성 원대본입니다. 실제 STT 결과와 별도로 확인하세요.' : '경영주가 입력한 원문입니다. AI 제안과 상담원 수정 내용이 아닙니다.'}</p>}
          <div className={`${styles.sourceText} ${styles.scrollRegion}`} role="region" tabIndex={0} aria-labelledby={`${id}-source-title`}>{valueText(caseData.sourceText)}</div>
        </section>;
  const sourceContent = <>
        {!voice && sourceTextContent}

        {voice && <section className={styles.card} aria-labelledby={`${id}-transcript-title`}>
          <div className={styles.sectionHeading}><div><h3 id={`${id}-transcript-title`}>화자별 대화록</h3><p className={styles.help}>{transcriptLabel}</p></div><label className={styles.checkbox}><input type="checkbox" checked={showTranscript} disabled={disabled} onChange={event => setShowTranscript(event.target.checked)} aria-label="대화록 표시" />자막 표시</label></div>
          {!workStage && <p className={styles.help}>구간은 제공된 발화 시각 기준입니다. 저장된 합성 대화록의 구간은 음성 생성 파일의 경계이며 STT·단어 정렬 결과가 아닙니다.</p>}
          {showTranscript && (transcript.length ? <div className={styles.scrollRegion} role="region" tabIndex={0} aria-labelledby={`${id}-transcript-title`}><ol className={styles.transcript}>{transcript.map((line, index) => {
            const range = clipFor(line, duration);
            const valid = range.start !== undefined && range.end !== undefined;
            const active = valid && position >= range.start! && position < range.end! && playback === 'playing';
            const speaker = valueText(line.speaker);
            // A/B are source labels, not inferred counselor/owner roles.
            const ownerTone = speaker === '경영주' || (speaker !== '상담원' && (unnamedSpeakers.indexOf(speaker) % 2 === 0) === unknownStartsWithOwnerTone);
            const reason = !voice ? '텍스트 접수 · 음성 구간 없음' : !audioUrl ? '음원 없음 · 구간 재생 불가' : range.reason;
            return <li key={index} className={`${styles.speech} ${active ? styles.activeSpeech : ''}`} aria-current={active ? 'true' : undefined}>
              <div className={styles.speechHeading}><strong className={ownerTone ? styles.ownerSpeaker : styles.agentSpeaker}>{speaker}</strong><span className={styles.help}>발화 {index + 1}{active ? ' · 재생 중' : ''}</span></div>
              <p>{line.text}</p>
              <button type="button" className={styles.clipButton} disabled={disabled || !voice || !audioUrl || !!mediaError || !valid} aria-describedby={reason ? `${id}-range-${index}` : undefined} aria-label={`${speaker} 발화 ${index + 1} 구간 재생${valid ? ` ${clipClock(range.start!)}~${clipClock(range.end!)}` : ''}`} onClick={() => playClip(line, index)}>{valid ? `${clipClock(range.start!)}–${clipClock(range.end!)} 구간 재생` : '구간 재생 불가'}</button>
              {reason && <p id={`${id}-range-${index}`} className={styles.help}>{reason}</p>}
            </li>;
          })}</ol></div> : <p className={styles.empty}>제공된 대화록이 없습니다. 원대본을 전사 결과로 대신 표시하지 않습니다.</p>)}
        </section>}
        {voice && <details className={styles.reviewDetails}><summary>합성 통화 원대본 · 음성 제작 원본, STT 아님</summary>{sourceTextContent}</details>}
  </>;
  const comparisonContent = <>
        <section className={styles.card} aria-labelledby={`${id}-compare-title`} aria-busy={analysisState === 'loading'}>
          <div className={styles.sectionHeading}><h3 id={`${id}-compare-title`}>3. AI 제안과 상담 입력 대조</h3><span className={styles.badge}>사람 확인 필요</span></div>
          {!intakeEditor && analysisFeedback}
          {analysis ? <div className={styles.summary}><strong>{mode === 'replay' ? '저장된 AI 제안 · 재생 자료' : 'AI 요약 · 확인 전 제안'}</strong><p>{analysis.summary}</p></div> : <p className={styles.empty}>분석 전 · AI 제안이 아직 없습니다. 현재 상담 입력은 아래에서 확인할 수 있습니다.</p>}
          <p className={styles.help}>수령 값은 경영주 진술입니다. 주문·출고 수량으로 채우거나 BOX를 EA로 환산하지 않습니다.</p>
          <div className={styles.compareList}>{fields.map(({ key, label }) => {
            const suggested = valueText(analysis?.fields?.[key]);
            const current = valueText(caseData.intake?.[key]);
            const unknown = suggested === '미확인' || current === '미확인';
            const status = !analysis ? 'AI 제안 대기' : unknown ? '미확인 포함' : suggested === current ? '동일' : '차이 확인 필요';
            return <section key={key} className={styles.compareRow} aria-label={`${label} 비교`}>
              <div className={styles.compareHeading}><h4>{label}</h4><span className={`${styles.badge} ${status === '차이 확인 필요' || unknown ? styles.warningBadge : ''}`}>{status}</span></div>
              <dl className={styles.values}><div><dt>AI 제안 · 확인 전</dt><dd>{analysis ? suggested : '제안 없음'}</dd></div><div><dt>현재 상담 입력</dt><dd>{current}</dd></div></dl>
            </section>;
          })}</div>
          <p className={styles.help}>{caseData.reviewConfirmed ? '부모 화면에 상담원 확인 완료로 기록된 접수입니다.' : '현재 상담 입력은 사람의 최종 확인 완료를 뜻하지 않습니다.'} 이 화면은 값을 변경하거나 저장하지 않습니다.</p>
        </section>

        {(caseData.expected || caseData.received) && <section className={styles.card} aria-labelledby={`${id}-quantity-title`}>
          <h3 id={`${id}-quantity-title`}>주문 정보와 수령 진술은 다릅니다</h3>
          <dl className={styles.contextValues}><div><dt>주문 정보 · 합성 사례</dt><dd>{valueText(caseData.expected?.product)} · {valueText(caseData.expected?.quantity)} {valueText(caseData.expected?.unit)}</dd></div><div><dt>수령 진술 · 합성 사례 참고값</dt><dd>{valueText(caseData.received?.product)} · {valueText(caseData.received?.quantity)} {valueText(caseData.received?.unit)}</dd></div></dl>
          <p className={styles.help}>대조용 사례 정보입니다. AI가 식별하지 못한 점포·수량의 자동 보정값이나 실제 물류 확인 결과로 사용하지 않습니다.</p>
        </section>}

        <section className={styles.card} aria-labelledby={`${id}-questions-title`}>
          <h3 id={`${id}-questions-title`}>4. 인용 근거와 추가 확인</h3>
          {!!analysis?.issues?.length && <ul className={styles.issueList}>{analysis.issues.map((issue, index) => <li key={index}><span className={`${styles.badge} ${styles.warningBadge}`}>확인 필요 · {fields.find(field => field.key === issue.field)?.label || issue.field}</span><p>{issue.message}</p>{issue.evidence ? <blockquote><span>AI가 연결한 인용 · 원문 대조 필요</span>{issue.evidence}</blockquote> : <p className={styles.help}>제공된 인용 근거 없음</p>}</li>)}</ul>}
          <h4 className={styles.subheading}>아직 확인되지 않은 내용</h4>
          {analysis?.unknowns?.length ? <ul className={styles.list}>{analysis.unknowns.map((unknown, index) => <li key={index}>{unknown}</li>)}</ul> : <p className={styles.help}>{analysis ? '별도 미확인 목록이 제공되지 않았습니다. 모든 사실이 확인됐다는 뜻은 아닙니다.' : '분석 결과와 원문을 대조한 뒤 확인합니다.'}</p>}
          <h4 className={styles.subheading}>통화 후 확인할 항목</h4>
          {analysis?.questions?.length ? <ol className={styles.list}>{analysis.questions.map((question, index) => <li key={index}>{question}</li>)}</ol> : <p className={styles.help}>제공된 추가 질문 없음</p>}
          {analysis?.department && <div className={styles.department}><strong>AI 추천 부서 · {valueText(analysis.department.name)}</strong><p>{valueText(analysis.department.reason)}</p><span className={styles.help}>상담원 확인 전 제안 · 자동 이관하지 않습니다.</span></div>}
        </section>
  </>;
  return <section className={`${styles.review} ${workStage ? styles.staged : ''}`} data-work-stage={workStage} hidden={workStage === 'handoff'} aria-labelledby={`${id}-title`}>
    <header className={workStage ? styles.taskHeader : styles.header}>
      <h2 id={`${id}-title`}>{voice ? '통화와 원문 대조' : '접수 원문 대조'}</h2>
      <span className={styles.badge}>합성 시연 사례</span>
    </header>

    <div className={styles.columns}>
      <div className={`${styles.stack} ${styles.listenPane}`} hidden={workStage === 'review'}>
        {voice ? <section className={styles.card} aria-labelledby={`${id}-audio-title`}>
          <div className={styles.sectionHeading}><h3 id={`${id}-audio-title`}>통화 녹음</h3><span className={styles.badge}>합성 음성</span></div>
          {audioUrl ? <>
            <div className={styles.buttonRow}><button type="button" className={styles.primaryButton} disabled={disabled} onClick={() => restart(true)}>처음부터 전체 통화 재생</button></div>
            <audio key={attempt} ref={audioRef} className={styles.audio} controls={!disabled} preload="metadata" src={audioUrl}
              aria-label={`합성 상담 통화 ${caseData.id}`} aria-describedby={`${id}-audio-help`} aria-disabled={disabled} tabIndex={disabled ? -1 : 0}
              onLoadedMetadata={event => {
                const audio = event.currentTarget;
                if (!isCurrent(audio)) return;
                if (!Number.isFinite(audio.duration) || audio.duration <= 0) {
                  setMediaError('음원 길이를 확인할 수 없습니다. 유효한 음원인지 확인해 주세요.');
                  fullAttempt.current = false;
                  return;
                }
                setDuration(audio.duration);
                audio.preservesPitch = true;
                audio.playbackRate = rate; audio.volume = volume; audio.muted = muted;
              }}
              onCanPlay={event => {
                if (isCurrent(event.currentTarget) && autoStart.current && !disabled) {
                  autoStart.current = false;
                  play(event.currentTarget);
                }
              }}
              onPlay={event => {
                const audio = event.currentTarget;
                if (!isCurrent(audio)) return;
                if (disabled) { audio.pause(); return; }
                if (!sought.current && !clip.current && audio.currentTime <= 0.05) fullAttempt.current = true;
                setPlayback('playing');
              }}
              onPause={event => { if (isCurrent(event.currentTarget)) setPlayback('paused'); }}
              onTimeUpdate={event => {
                const audio = event.currentTarget;
                if (isCurrent(audio) && !stopAtClipEnd(audio)) setPosition(audio.currentTime);
              }}
              onSeeking={event => {
                const audio = event.currentTarget;
                if (!isCurrent(audio)) return;
                sought.current = true; fullAttempt.current = false;
                setSeekNotice(true);
                const selected = clip.current;
                if (selected && (audio.currentTime < selected.start - 0.05 || audio.currentTime >= selected.end)) {
                  clip.current = null; setSegmentIndex(null); audio.pause();
                }
              }}
              onRateChange={event => { if (isCurrent(event.currentTarget)) changePlaybackRate(event.currentTarget.playbackRate); }}
              onVolumeChange={event => { if (isCurrent(event.currentTarget)) { setVolume(event.currentTarget.volume); setMuted(event.currentTarget.muted); } }}
              onError={event => {
                if (!isCurrent(event.currentTarget)) return;
                fullAttempt.current = false; autoStart.current = false; clip.current = null;
                setSegmentIndex(null);
                setMediaError('음성 파일을 불러오지 못했습니다. 파일 없음·네트워크·음원 형식을 확인해 주세요.');
              }}
              onEnded={event => {
                const audio = event.currentTarget;
                if (!isCurrent(audio)) return;
                setPlayback('ended');
                const selected = clip.current;
                clip.current = null; setSegmentIndex(null);
                if (disabled || selected || sought.current || !fullAttempt.current || mediaError || audio.error || !audio.ended || !event.nativeEvent.isTrusted || !playedWholeAudio(audio)) return;
                setComplete(true);
                if (!completeNotified.current) { completeNotified.current = true; onPlaybackEnded?.(); }
              }} />
            <div className={styles.playbackRow}><strong role="status">{playbackLabel}</strong><span className={styles.time}>{clock(position)} / {duration === null ? '길이 확인 중' : clock(duration)}</span></div>
            <div className={styles.controls}>
              <label>재생 속도<select aria-label="통화 재생 속도" value={rate} disabled={disabled || !!mediaError} onChange={event => changePlaybackRate(Number(event.target.value))}>
                {playbackSpeeds.map(speed => <option value={speed} key={speed}>{speed}배</option>)}
                {!playbackSpeeds.includes(rate) && <option value={rate}>{rate}배</option>}
              </select></label>
              <label className={styles.volume}>볼륨 {Math.round(volume * 100)}%<input aria-label="통화 볼륨" type="range" min="0" max="1" step="0.05" value={volume} disabled={disabled || !!mediaError} onChange={event => { const audio = audioRef.current; if (audio) audio.volume = Number(event.target.value); }} /></label>
              <button type="button" aria-label="통화 음소거" aria-pressed={muted} disabled={disabled || !!mediaError} onClick={() => { const audio = audioRef.current; if (audio) audio.muted = !audio.muted; }}>{muted ? '음소거 해제' : '음소거'}</button>
            </div>
            {(muted || volume === 0) && <p className={styles.warning}>현재 소리가 꺼져 있습니다. 재생 완료는 실제 청취 확인을 뜻하지 않습니다.</p>}
            <p id={`${id}-audio-help`} className={styles.help}>통화 재생은 선택입니다. 상단의 AI 정리 버튼으로 바로 시작할 수 있습니다.</p>
            {hiddenClipNotice && <p className={styles.warning} role="status">탭이 숨겨져 선택 발화 재생을 멈췄습니다. 돌아온 뒤 구간 재생 버튼을 다시 눌러 주세요.</p>}
            {!complete && seekNotice && <p className={styles.warning}>재생 위치를 이동했습니다. AI는 선택 구간이 아닌 전체 녹음을 분석합니다.</p>}
            {mediaError && <p className={styles.error} role="alert">{mediaError}</p>}
            <div className={styles.buttonRow}>
              {mediaError && <button type="button" disabled={disabled} onClick={() => restart(false)}>음원 다시 불러오기</button>}
            </div>
          </> : <p className={styles.warning} role="status">음원 없음 · 이 사건에 연결된 음성 파일이 없습니다. 다른 사건 음원으로 대체하지 않습니다.</p>}
        </section> : <p className={styles.notice}>텍스트 접수 · 음성 전사 없이 입력 원문과 분석 내용을 대조합니다.</p>}

        {!workStage && analysisActions}
        {workStage === 'source' && analysisFeedback}
      </div>

      {intakeEditor ? <details key={workStage || 'all'} open id={`${id}-source-panel`} className={`${styles.sourcePane} ${styles.reviewDetails}`}><summary>{voice ? '원문과 화자별 대화록 확인' : '접수 원문과 입력 내용 확인'}</summary><div className={styles.stack}>
        {sourceContent}
      </div></details> : <div className={`${styles.sourcePane} ${styles.stack}`}>
        {sourceContent}
      </div>}
      <div className={`${styles.stack} ${styles.editorPane}`} hidden={workStage === 'source'}>
        {intakeEditor && analysisFeedback}
        {intakeEditor}
        {intakeEditor ? <details className={styles.reviewDetails}><summary>AI 제안과 현재 입력 상세 대조</summary><div className={styles.stack}>
        {comparisonContent}
        </div></details> : <>
        {comparisonContent}
        </>}
      </div>
    </div>
  </section>;
}
