'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import CallReview from '@/components/CallReview';
import NotificationStatus from '@/components/NotificationStatus';
import WmsScene from '@/components/WmsScene';
import TmsScene from '@/components/TmsScene';
import { ApiError, request } from '@/lib/api';
import { acceptOwnEvidenceSave, useHasUnsavedDrafts, useSessionDraft } from '@/lib/drafts';
import { defaultQueue, departmentName, filterCases, inQueue, isEvidenceEditable, nextAction, queueForCase, queues, roleNames, roleView, type QueueId, type WorkRole } from '@/lib/workflow';
import type { Analysis, AnalyzeResult, CaseData, CaseStatus, Intake, Mode, View } from '@/lib/types';

const labels: Record<CaseStatus, string> = { draft: '접수 대기', review: '상담원 확인', handed_off: '센터 전달', in_progress: '처리 중', closed: '처리 완료' };
const tabs: { role: WorkRole; label: string }[] = [{ role: 'counselor', label: '상담원 작업대' }, { role: 'center', label: '센터 작업대' }, { role: 'owner', label: '경영주 화면' }];
const emptyIntake: Intake = { storeId: '', subject: '', quantity: '', unit: '', request: '' };
const normalizeIntake = (input?: Partial<Intake>): Intake => ({ storeId: input?.storeId || '', subject: input?.subject || '', quantity: input?.quantity ?? '', unit: input?.unit || '', request: input?.request || '' });
const errorText = (e: unknown) => e instanceof Error ? e.message : '처리 중 문제가 발생했습니다. 다시 시도해 주세요.';
function Status({ status }: { status?: CaseStatus }) { return <span className={`badge ${status === 'closed' ? 'success' : status && labels[status] ? 'info' : 'warning'}`}>{status && labels[status] ? labels[status] : `상태 확인 필요${status ? ` · ${status}` : ''}`}</span>; }
function Arrow() { return <span aria-hidden="true">↗</span>; }
function FieldSuggestion({ value, current, id }: { value: unknown; current: unknown; id: string }) {
  const text = (item: unknown) => item == null || String(item).trim() === '' ? '미확인' : String(item);
  const changed = text(value).trim() !== text(current).trim();
  return <span id={id} className={`field-suggestion${changed ? ' field-difference' : ''}`}><span>AI 제안: {text(value)}</span>{text(value) === '미확인' || text(current) === '미확인' ? <strong>미확인 포함</strong> : changed && <strong>현재 입력과 다름</strong>}</span>;
}

export default function Home() {
  const [view, setView] = useState<View>('desk');
  const [role, setRole] = useState<WorkRole>('counselor');
  const [queue, setQueue] = useState<QueueId>('attention');
  const [query, setQuery] = useState('');
  const [newIntake, setNewIntake] = useState(false);
  const [queueSort, setQueueSort] = useState<{ key: 'store' | 'type' | 'channel' | 'title' | 'status' | 'department'; ascending: boolean }>({ key: 'title', ascending: true });
  const [cases, setCases] = useState<CaseData[]>([]);
  const [selected, setSelected] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [toast, setToast] = useState('');
  const [fallback, setFallback] = useState(false);
  const [mode, setMode] = useState<Mode>('replay');
  const [playbackRate, setPlaybackRate] = useState(1.25);
  const [lastSync, setLastSync] = useState<string>('');
  const hasDrafts = useHasUnsavedDrafts();
  const reloadInFlight = useRef(false);
  const sortValue = (item: CaseData, key: typeof queueSort.key) => key === 'store' ? item.store?.name || item.store?.id || '' : key === 'type' ? item.type === 'missing' ? '미도착' : '오출고' : key === 'channel' ? item.channel === 'voice' ? '전화' : '웹 접수' : key === 'status' ? labels[item.status || 'draft'] || '' : key === 'department' ? departmentName(item.departmentId, item.analysis?.department) : item.title;
  const visibleCases = filterCases(cases, role, queue, query).sort((a, b) => sortValue(a, queueSort.key).localeCompare(sortValue(b, queueSort.key), 'ko') * (queueSort.ascending ? 1 : -1));
  const logistics = view === 'wms' || view === 'tms';
  // Evidence remains anchored to its case even when a refresh moves it out of the work queue.
  const active = logistics || role === 'owner' ? cases.find(c => c.id === selected) : visibleCases.find(c => c.id === selected) || visibleCases[0];
  const changeRole = (nextRole: WorkRole) => {
    setNewIntake(false); setRole(nextRole); setView(roleView[nextRole]); setQueue(defaultQueue(nextRole)); setQuery(''); setToast('');
  };
  const navigate = (nextView: View) => {
    setNewIntake(false);
    if (nextView === 'wms' || nextView === 'tms') { if (active) { setSelected(active.id); setView(nextView); } return; }
    const nextRole: WorkRole = nextView === 'center' ? 'center' : nextView === 'owner' ? 'owner' : 'counselor';
    if (active) setSelected(active.id);
    setRole(nextRole); setView(nextView); setQuery('');
    setQueue(queueForCase(active, nextRole));
  };
  const returnToWork = () => {
    setNewIntake(false);
    const current = cases.find(item => item.id === selected);
    setQueue(current ? queueForCase(current, role) : 'all'); setQuery(''); setView(roleView[role]);
    if (!current) setSelected('');
  };
  const selectCase = (id: string) => {
    setNewIntake(false); setSelected(id); setView(roleView[role]); setToast('');
    if (!window.matchMedia('(max-width: 768px)').matches) return;
    window.requestAnimationFrame(() => {
      const target = document.getElementById('selected-work');
      // A role, case, or viewport change must not replay an old focus request.
      if (!window.matchMedia('(max-width: 768px)').matches || target?.dataset.caseId !== id || target.dataset.workRole !== role || target.dataset.workView !== roleView[role]) return;
      target.focus({ preventScroll: true });
      target.scrollIntoView({ block: 'start', behavior: 'instant' });
    });
  };

  const reload = useCallback(async () => {
    if (reloadInFlight.current) return;
    reloadInFlight.current = true;
    setLoading(true); setError(''); setToast('');
    try {
      const data = await request<{ cases: CaseData[] }>('/api/cases');
      setCases(data.cases); setFallback(false);
      setLastSync(new Date().toLocaleTimeString('ko-KR', { hour12: false }));
      setSelected(previous => previous || data.cases[0]?.id || '');
    } catch (e) { setError(errorText(e)); } finally { setLoading(false); reloadInFlight.current = false; }
  }, []);
  useEffect(() => { void reload(); }, [reload]);
  useEffect(() => { if (!toast) return; const timer = setTimeout(() => setToast(''), 6000); return () => clearTimeout(timer); }, [toast]);
  useEffect(() => {
    if (!hasDrafts) return;
    const warn = (event: BeforeUnloadEvent) => { event.preventDefault(); event.returnValue = ''; };
    window.addEventListener('beforeunload', warn);
    return () => window.removeEventListener('beforeunload', warn);
  }, [hasDrafts]);
  const update = (updated: CaseData) => setCases(old => old.some(c => c.id === updated.id) ? old.map(c => c.id === updated.id ? { ...c, ...updated } : c) : [updated, ...old]);
  const save = async (id: string, payload: Record<string, unknown>) => {
    setToast('');
    if (role === 'owner') throw new Error('경영주 화면에서는 상담 또는 센터 내용을 수정할 수 없습니다.');
    if (fallback) throw new Error('예시 열람 모드에서는 저장할 수 없습니다. 서버에 다시 연결해 주세요.');
    if (typeof payload.expectedRevision !== 'number') throw new Error('접수 버전을 확인할 수 없습니다. 화면을 새로 연 뒤 변경 내용을 확인해 주세요.');
    const updated = await request<CaseData>(`/api/cases/${id}`, 'PATCH', payload, role === 'center' ? 'center' : 'counselor'); update(updated); return updated;
  };
  const loadExample = async () => {
    setToast('');
    try {
      const response = await fetch('/cases.json');
      if (!response.ok) throw new Error('예시 데이터도 불러오지 못했습니다.');
      const data = await response.json(); const items = Array.isArray(data) ? data : data.cases;
      if (!Array.isArray(items)) throw new Error('예시 데이터 형식을 확인해 주세요.');
      setCases(items); setSelected(items[0]?.id || ''); setFallback(true);
    } catch (e) { setError(errorText(e)); }
  };
  return <div className="app-shell">
    <a className="skip-link" href="#main">본문으로 이동</a>
    <header className="site-header">
      <div className="header-inner">
        <a className="brand" href="#" onClick={e => { e.preventDefault(); returnToWork(); }} aria-label="HappyCall OneFlow 홈"><span className="brand-mark" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none"><path d="M5 6v12M19 6v12M5 12h14M10 6v12" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"/></svg></span><span>HappyCall <strong>OneFlow</strong></span></a>
        <nav className="nav-inner" aria-label="업무 역할">{tabs.map(tab => <button key={tab.role} onClick={() => changeRole(tab.role)} className={role === tab.role ? 'nav-tab selected' : 'nav-tab'} aria-pressed={role === tab.role}>{tab.label}</button>)}</nav>
        <span className="badge neutral demo-label">합성 데이터 시연</span>
      </div>
    </header>
    <main id="main" className="main-content">
      <h1 className="sr-only">{logistics ? view === 'wms' ? 'WMS 작업 근거' : 'TMS 배송 근거' : tabs.find(t => t.role === role)?.label}</h1>
      {error && <div className="notice danger" role="alert"><div><strong>서버 연결 확인이 필요합니다</strong><p>{error}</p>{fallback && <p>현재 예시 열람 중입니다. 변경 사항은 저장되지 않습니다.</p>}</div><div className="button-row"><button onClick={() => void reload()} disabled={loading}>다시 연결</button>{!fallback && <button onClick={() => void loadExample()}>합성 예시 열람</button>}</div></div>}
      {toast && <div className="notice success" role="status">{toast}</div>}
      <div className="workspace-sync">
        <span className="small muted" role="status">최종 서버 확인 {lastSync || '확인 중'}</span>
        {hasDrafts && <details className="draft-notice"><summary>미저장 초안 있음</summary><p>다른 역할·접수의 초안을 포함합니다. 업무와 접수를 이동해도 유지되지만 페이지를 닫거나 새로고침하면 사라질 수 있습니다.</p></details>}
        {role !== 'owner' && !logistics && <div className="mode-control"><label htmlFor="analysis-mode">분석 방식</label><select id="analysis-mode" value={mode} onChange={e => setMode(e.target.value as Mode)}><option value="replay">저장 결과 재생 · API 호출 없음</option><option value="demo-live">실제 AI 분석 · API 사용</option></select></div>}
        <button onClick={() => void reload()} disabled={loading}>{loading ? '최신 내용 확인 중…' : '목록 새로고침'}</button>
      </div>
      {loading && !cases.length ? <div className="empty-state" role="status"><div className="spinner"/><h2>접수 건을 불러오고 있습니다</h2><p>서버의 최신 처리 상태를 확인합니다.</p></div> : role === 'owner' ? <Owner cases={cases} selected={selected} onSelect={setSelected} onCreated={c => { update(c); setSelected(c.id); setToast(`${c.id} 접수가 등록되었습니다.`); }} onToast={setToast} onDesk={() => navigate('desk')} fallback={fallback}/> : <div className={`role-workspace${logistics ? ' logistics-workspace' : ''}`}>
        {!logistics && <aside id="work-queue" tabIndex={-1} className="work-queue" aria-label={`${roleNames[role]} 접수 목록`}>
          <div className="queue-toolbar"><div className="queue-heading"><h2>처리할 접수</h2><span className="small muted">전체 {cases.length}건</span></div>{role === 'counselor' && <button className="primary workflow-new-intake" onClick={() => { setNewIntake(true); setToast(''); }}>＋ 신규 접수</button>}</div>
          <div className="queue-tools"><div className="queue-filters" aria-label="처리 상태">{queues(role).map(item => <button key={item.id} aria-pressed={queue === item.id} onClick={() => { setNewIntake(false); setQueue(item.id); setView(roleView[role]); }} className={queue === item.id ? 'selected' : ''}>{item.label}<span>{cases.filter(c => inQueue(c, role, item.id)).length}</span></button>)}</div><label className="queue-search"><span className="sr-only">접수 검색</span><input type="search" placeholder="점포, 제목, 접수번호 검색" value={query} onChange={e => setQuery(e.target.value)}/></label></div>
          <p className="queue-result" role="status">{queues(role).find(item => item.id === queue)?.label} · {visibleCases.length}건 · 접수를 선택하면 아래에서 처리할 수 있습니다.</p>
          <div className="queue-table-scroll" role="region" aria-label="접수 목록 표" tabIndex={0}><table className="queue-table"><caption className="sr-only">처리할 접수 목록 · 열 제목으로 정렬</caption><thead><tr>{([{ key: 'store', label: '점포' }, { key: 'type', label: '유형' }, { key: 'channel', label: '채널' }, { key: 'title', label: '제목' }, { key: 'status', label: '상태' }, { key: 'department', label: '처리부서' }] as const).map(column => <th key={column.key} scope="col" aria-sort={queueSort.key === column.key ? queueSort.ascending ? 'ascending' : 'descending' : 'none'}><button onClick={() => setQueueSort(old => ({ key: column.key, ascending: old.key === column.key ? !old.ascending : true }))}>{column.label}{queueSort.key === column.key && <span aria-hidden="true">{queueSort.ascending ? ' ↑' : ' ↓'}</span>}</button></th>)}<th scope="col">작업</th></tr></thead><tbody>{visibleCases.map(c => <tr key={c.id} className={active?.id === c.id && !newIntake ? 'selected' : ''} onClick={() => selectCase(c.id)}><td>{c.store?.name || c.store?.id}</td><td>{c.type === 'missing' ? '미도착' : '오출고'}</td><td>{c.channel === 'voice' ? '전화' : '웹 접수'}</td><td className="queue-table-title"><strong>{c.title}</strong><span>{c.id}</span></td><td><Status status={c.status}/></td><td>{departmentName(c.departmentId, c.analysis?.department)}</td><td><button className="queue-open" data-case-id={c.id} aria-label={`${c.title} 접수 열기`} aria-pressed={active?.id === c.id && !newIntake} title={nextAction(c, role)} onClick={event => { event.stopPropagation(); selectCase(c.id); }}>{active?.id === c.id && !newIntake ? '선택됨' : '열기'} →</button></td></tr>)}</tbody></table></div>
          {!visibleCases.length && <p className="queue-empty">{query.trim() ? '검색 조건에 맞는 접수가 없습니다.' : '이 단계에서 처리할 접수가 없습니다.'}</p>}
        </aside>}
        <div id="selected-work" tabIndex={-1} className="work-detail" data-case-id={active?.id} data-work-role={role} data-work-view={view} aria-label={active ? `선택한 접수 작업 영역 · ${active.title}` : '선택한 접수 작업 영역'}>
          {newIntake && role === 'counselor' ? <div className="workflow-intake"><div className="case-heading"><div><span className="small-kicker">NEW REQUEST</span><h2>신규 문의 접수</h2><p className="muted">접수를 등록하면 이 작업대에서 AI 정리와 이관을 이어갑니다.</p></div><button onClick={() => setNewIntake(false)}>기존 접수로 돌아가기</button></div><Owner counselorEntry cases={cases} selected={selected} onSelect={setSelected} onCreated={created => { update(created); setSelected(created.id); setQueue('attention'); setQuery(''); setNewIntake(false); setToast(`${created.id} 접수 등록 완료 · AI 정리를 진행해 주세요.`); }} onToast={setToast} onDesk={() => setNewIntake(false)} fallback={fallback}/></div> : !active ? <div className="empty-state"><h2>{logistics ? '선택한 접수를 찾을 수 없습니다' : query.trim() ? '검색 결과가 없습니다' : '선택한 처리 단계에 접수가 없습니다'}</h2><p>{logistics ? `접수 ${selected}가 최신 목록에 없습니다. 다른 접수의 근거로 전환하지 않았습니다.` : query.trim() ? '점포명이나 접수번호를 다시 확인해 주세요.' : '다른 단계의 목록을 확인하거나 최신 접수를 불러올 수 있습니다.'}</p><div className="button-row">{logistics ? <button onClick={returnToWork}>접수 목록으로 돌아가기</button> : <>{query && <button onClick={() => setQuery('')}>검색 지우기</button>}<button onClick={() => { setQueue('all'); setQuery(''); }}>전체 접수 보기</button></>}<button onClick={() => void reload()} disabled={loading}>목록 새로고침</button></div></div>
            : view === 'desk' ? <Desk key={active.id} caseData={active} mode={mode} fallback={fallback} playbackRate={playbackRate} onPlaybackRateChange={setPlaybackRate} onUpdate={update} onSave={save} onView={navigate} onToast={setToast}/>
            : view === 'center' ? <Center key={active.id} mode={mode} fallback={fallback} caseData={active} onUpdate={update} onSave={save} onToast={setToast} onView={navigate}/>
            : (view === 'wms' || view === 'tms') ? <><div className="logistics-case-context"><span className="badge neutral">{roleNames[role]} 근거 확인</span><strong>{active.title}</strong><span>{active.store?.name} · {active.id}</span>{!isEvidenceEditable(active, role) && <span className="badge info">이관 내용 보존 · 근거 열람</span>}</div><LogisticsScene key={`${view}:${active.id}`} kind={view} caseData={active} backLabel={role === 'center' ? '센터 업무로 돌아가기' : '상담으로 돌아가기'} readOnly={!isEvidenceEditable(active, role)} onBack={returnToWork} onLinkEvidence={async (id: string) => { setToast(''); if (!isEvidenceEditable(active, role)) throw new Error('센터에 전달된 접수 또는 센터 열람 화면에서는 근거를 변경할 수 없습니다.'); const selectedEvidence = Array.from(new Set([...(active.selectedEvidence || []), id])); const saved = await save(active.id, { expectedRevision: active.revision, selectedEvidence }); acceptOwnEvidenceSave(active, saved, selectedEvidence); setToast('물류 근거를 접수 건에 연결했습니다.'); }}/></> : null}
        </div>
      </div>}
      <footer className="page-footer"><span>HappyCall OneFlow</span><span>전화·점포·물류 데이터는 시연용 합성 데이터입니다. 실제 고객 통화가 아닙니다.</span></footer>
    </main>
  </div>;
}

function LogisticsScene({ kind, ...props }: { kind: 'wms' | 'tms'; caseData: CaseData; onBack: () => void; backLabel?: string; readOnly?: boolean; onLinkEvidence: (id: string) => Promise<void> }) {
  return kind === 'wms' ? <WmsScene {...props}/> : <TmsScene {...props}/>;
}

type DeskDraft = { analysis?: Analysis; transcript: CaseData['transcript']; resultMode?: Mode; form: Intake; formRevision?: number; department: string; edited: boolean; confirmed: boolean; question: string; uncertain?: Record<string, unknown>; operation?: string; workStage?: 'source' | 'review' | 'handoff' };
const deskDraft = (c: CaseData): DeskDraft => ({ analysis: c.analysis, transcript: c.transcript || [], resultMode: c.analysis && (c.analysisMode === 'demo-live' || c.analysisMode === 'replay') ? c.analysisMode : undefined, form: normalizeIntake(c.intake || { ...emptyIntake, storeId: c.store?.id || '' }), formRevision: c.revision, department: c.departmentId || '', edited: c.reviewConfirmed === true, confirmed: c.reviewConfirmed || false, question: '' });
const deskContent = (d: DeskDraft) => ({ form: normalizeIntake(d.form), department: d.department, confirmed: d.confirmed, question: d.question, uncertain: d.uncertain });
function sameMutation(current: CaseData, payload: Record<string, unknown>) {
  return Object.entries(payload).filter(([key]) => key !== 'expectedRevision').every(([key, value]) => {
    if (key === 'intake') return JSON.stringify(normalizeIntake(current.intake)) === JSON.stringify(normalizeIntake(value as Intake));
    return JSON.stringify(current[key] ?? null) === JSON.stringify(value ?? null);
  });
}
function Recovery({ current, rows, busy, onUseServer, onKeepDraft }: { current: CaseData; rows: { label: string; local: string; server: string }[]; busy: boolean; onUseServer: () => void; onKeepDraft: () => void }) {
  return <section className="panel recovery-panel" aria-label="최신 서버 내용과 초안 대조"><h3>다른 저장 내용이 있습니다</h3><p className="muted">최신 내용과 현재 초안을 확인한 뒤 사용할 내용을 선택해 주세요. 선택 전에는 덮어쓰지 않습니다.</p><Status status={current.status}/><div className="recovery-comparison">{rows.map(row => <div key={row.label}><h4>{row.label}</h4><div><strong>현재 초안</strong><p>{row.local || '비어 있음'}</p></div><div><strong>서버에 저장된 내용</strong><p>{row.server || '비어 있음'}</p></div></div>)}</div><div className="button-row"><button disabled={busy} onClick={onUseServer}>서버 내용 사용</button><button disabled={busy} onClick={onKeepDraft}>내 초안 유지 · 다시 확인</button></div><p className="small muted">초안을 유지하면 다시 대조·확인한 후 저장할 수 있습니다. 서버에 저장된 내용은 이 선택만으로 바뀌지 않습니다.</p></section>;
}

function Desk({ caseData: c, mode, fallback, playbackRate, onPlaybackRateChange, onUpdate, onSave, onView, onToast }: { caseData: CaseData; mode: Mode; fallback: boolean; playbackRate: number; onPlaybackRateChange: (rate: number) => void; onUpdate: (c: CaseData) => void; onSave: (id: string, p: Record<string, unknown>) => Promise<CaseData>; onView: (v: View) => void; onToast: (s: string) => void }) {
  const draft = useSessionDraft<DeskDraft>(`desk:${c.id}`, deskDraft(c), deskContent);
  const { analysis, transcript, resultMode, form, formRevision, department, edited, confirmed, question, uncertain } = draft.value;
  const setForm = (value: Intake | ((old: Intake) => Intake)) => draft.set('form', value);
  const setDepartment = (value: string) => draft.set('department', value);
  const setEdited = (value: boolean) => draft.set('edited', value);
  const setConfirmed = (value: boolean) => draft.set('confirmed', value);
  const setQuestion = (value: string) => { draft.set('question', value); draft.set('confirmed', false); };
  const audioSource = JSON.stringify([c.id, c.channel, c.audioUrl ?? null]);
  const [completedAudioSource, setCompletedAudioSource] = useState<string | null>(null);
  const audioEnded = completedAudioSource === audioSource;
  const busy = draft.value.operation || '';
  const setBusy = (value: string) => draft.set('operation', value);
  const [error, setError] = useState('');
  const [analysisFailure, setAnalysisFailure] = useState('');
  const [recovery, setRecovery] = useState<CaseData | null>(null);
  const stale = formRevision !== c.revision;
  const analysisInFlight = useRef(false);
  const mounted = useRef(false);
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);
  const intakeLocked = ['handed_off', 'in_progress', 'closed'].includes(c.status || '');
  const workStage = draft.value.workStage || (intakeLocked ? 'handoff' : analysis ? 'review' : 'source');
  const showStage = (stage: 'source' | 'review' | 'handoff') => {
    draft.set('workStage', stage);
    window.requestAnimationFrame(() => document.getElementById('desk-workflow')?.scrollIntoView({ block: 'start', behavior: 'instant' }));
  };
  const analyzeBlocked = intakeLocked || !!busy || fallback || stale || !!uncertain || !!recovery || (c.channel === 'voice' && !c.audioUrl);
  const canTransfer = !intakeLocked && !stale && !uncertain && !recovery && confirmed && !!(form.storeId || '').trim() && !!(form.subject || '').trim() && !!department && !busy && !fallback;
  // Cards only read the saved selection. Opening a record must not refresh formRevision.
  const evidenceText = (value: unknown, empty = '미등록') => typeof value === 'string' && value.trim() ? value : typeof value === 'number' && Number.isFinite(value) ? String(value) : empty;
  const evidenceStamp = (value: unknown) => {
    if (typeof value !== 'string') return null;
    const parts = value.match(/^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})(?::(\d{2})(?:\.\d+)?)?(?:Z|[+-]\d{2}:\d{2})$/i);
    if (!parts) return null;
    const [year, month, day, hour, minute, second] = parts.slice(1, 7).map(part => part === undefined ? 0 : Number(part));
    const calendar = new Date(0);
    calendar.setUTCFullYear(year, month - 1, day); calendar.setUTCHours(hour, minute, second, 0);
    if (calendar.getUTCFullYear() !== year || calendar.getUTCMonth() !== month - 1 || calendar.getUTCDate() !== day || calendar.getUTCHours() !== hour || calendar.getUTCMinutes() !== minute || calendar.getUTCSeconds() !== second) return null;
    const stamp = Date.parse(value);
    return Number.isFinite(stamp) ? stamp : null;
  };
  const evidenceDate = (value: unknown) => {
    const stamp = evidenceStamp(value);
    return stamp === null ? (value == null || value === '' ? '미등록' : '시각·시간대 확인 필요') : new Intl.DateTimeFormat('ko-KR', { timeZone: 'Asia/Seoul', year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false }).format(new Date(stamp)) + ' KST';
  };
  const selectedEvidence = Array.from(new Set(c.selectedEvidence || [])).map(id => {
    const matches = (c.evidence || []).filter(record => record.id === id);
    const record = matches.length === 1 ? matches[0] : undefined;
    const metadata = (record || {}) as Record<string, unknown>;
    const observedAt = 'observedAt' in metadata ? metadata.observedAt : record?.time;
    const sourceAsOf = 'sourceAsOf' in metadata ? metadata.sourceAsOf : c.asOf;
    const observedStamp = evidenceStamp(observedAt);
    const asOfStamp = evidenceStamp(c.asOf);
    const sourceStamp = evidenceStamp(sourceAsOf);
    const suppliedTimes = [record?.time, observedAt].filter(value => value != null && value !== '');
    const suppliedStamps = suppliedTimes.map(evidenceStamp);
    let withheld = !record ? (matches.length ? '같은 ID의 원본이 여러 개입니다. 연결 대상을 확인해 주세요.' : '현재 접수 건에서 원본을 찾을 수 없습니다.') : '';
    if (!withheld && metadata.caseId != null && ![c.id, c.linkedFixtureId].includes(metadata.caseId)) withheld = '원본 사건과 현재 접수의 연결 관계를 확인해 주세요.';
    if (!withheld && metadata.storeId != null && metadata.storeId !== c.store?.id) withheld = '원본 점포와 현재 접수 점포가 다릅니다.';
    if (!withheld && metadata.relationStatus != null && metadata.relationStatus !== 'exact') withheld = '원본과 접수의 연결 관계가 확인되지 않았습니다.';
    if (!withheld && ['unknown', 'unverified'].includes(String(metadata.timezoneStatus))) withheld = '원본 기록의 시간대를 확인해 주세요.';
    if (!withheld && suppliedStamps.some(stamp => stamp === null)) withheld = '원본 기록의 시각·시간대를 확인해 주세요.';
    if (!withheld && suppliedStamps.length > 0 && asOfStamp === null) withheld = '접수 기준시각이 없어 기록 시점을 대조할 수 없습니다.';
    if (!withheld && asOfStamp !== null && suppliedStamps.some(stamp => stamp !== null && stamp > asOfStamp)) withheld = '접수 기준시각 이후의 기록입니다.';
    if (!withheld && 'observedAt' in metadata && record?.time != null && record.time !== '' && observedStamp !== evidenceStamp(record.time)) withheld = '원본의 두 기록 시각이 서로 다릅니다. 시각 정보를 확인해 주세요.';
    if (!withheld && 'sourceAsOf' in metadata && (sourceStamp === null || asOfStamp === null || sourceStamp > asOfStamp)) withheld = '원본 조회 기준시각과 접수 기준시각을 대조해 주세요.';
    const synthetic = metadata.synthetic === true || (metadata.synthetic !== false && (c.synthetic === true || /합성/.test(evidenceText(record?.source, '')) || /합성/.test(evidenceText(c.provenance, ''))));
    return { id, record, metadata, observedAt, sourceAsOf, withheld, synthetic };
  });
  const visibleEvidenceCount = selectedEvidence.filter(item => !item.withheld).length;
  const field = (key: keyof Intake, value: string) => { setForm(old => ({ ...old, [key]: value })); setEdited(true); setConfirmed(false); };
  const analyze = async () => {
    if (intakeLocked || busy || analysisInFlight.current || stale || uncertain || recovery) return;
    onToast('');
    if (fallback) { setAnalysisFailure('분석은 서버에 연결한 후 사용할 수 있습니다.'); return; }
    if (c.channel === 'voice' && !c.audioUrl) { setAnalysisFailure('통화를 처음부터 끝까지 재생한 뒤 분석해 주세요.'); return; }
    analysisInFlight.current = true;
    setBusy('analyze'); setAnalysisFailure('');
    try {
      const data = await request<AnalyzeResult>(`/api/cases/${c.id}/analyze`, 'POST', { mode });
      if (!mounted.current) return;
      draft.replace({ analysis: data.analysis, transcript: data.transcript || [], resultMode: data.mode, form: normalizeIntake(data.analysis.fields), formRevision: data.revision, department: data.analysis.department?.id || '', edited: false, confirmed: false, question: '', workStage: 'review' }, true);
      onUpdate({ ...c, revision: data.revision, status: 'review', reviewConfirmed: false, intake: normalizeIntake(data.analysis.fields), departmentId: data.analysis.department?.id || '', analysis: data.analysis, transcript: data.transcript, analysisMode: data.mode });
      onToast(data.mode === 'demo-live' ? '실제 AI 전사·정제가 완료되었습니다. 접수 정보를 확인해 주세요.' : '저장된 분석 결과를 불러왔습니다. 실제 AI 호출은 하지 않았습니다.');
    } catch (e) { if (mounted.current) setAnalysisFailure(errorText(e)); } finally { analysisInFlight.current = false; setBusy(''); }
  };
  const persist = async (transfer = false) => {
    if (busy || stale || uncertain || recovery || intakeLocked || fallback) return;
    if (transfer && !canTransfer) return;
    setBusy(transfer ? 'transfer' : 'save'); setError('');
    const nextRequest = question.trim() ? `${form.request}\n\n추가 확인 질문: ${question.trim()}` : form.request;
    const payload = { expectedRevision: formRevision, intake: { ...form, request: nextRequest, quantity: form.quantity === '' || form.quantity === null ? null : Number(form.quantity) }, departmentId: department || null, reviewConfirmed: confirmed, status: transfer ? 'handed_off' : 'review' };
    try {
      const saved = await onSave(c.id, payload);
      draft.replace({ ...deskDraft(saved), edited, workStage }, true);
      onToast(transfer ? '확인한 접수 내용과 근거를 센터에 전달했습니다.' : '상담원이 편집한 접수 정보를 저장했습니다.');
      if (transfer && mounted.current) onView('center');
    } catch (e) { setError(errorText(e)); if (e instanceof ApiError && e.uncertain) draft.set('uncertain', payload); if (e instanceof ApiError && e.status === 409) await inspectLatest(); } finally { setBusy(''); }
  };
  const inspectLatest = async () => {
    setBusy('verify'); setError(''); onToast('');
    try {
      const latest = await request<CaseData>(`/api/cases/${c.id}`);
      onUpdate(latest);
      if (uncertain && sameMutation(latest, uncertain)) { draft.replace(deskDraft(latest), true); setRecovery(null); onToast('서버에 요청한 접수 내용이 저장되어 있음을 확인했습니다.'); }
      else setRecovery(latest);
    } catch (e) { setError(errorText(e)); } finally { setBusy(''); }
  };
  const transferBlockers = [
    intakeLocked && '이미 센터로 전달된 접수입니다.',
    fallback && '서버에 다시 연결해 주세요.',
    !!busy && '진행 중인 작업이 끝날 때까지 기다려 주세요.',
    !!uncertain && '저장 여부를 먼저 확인해 주세요.',
    (!!recovery || stale) && '최신 서버 내용과 현재 초안을 대조해 주세요.',
    !(form.storeId || '').trim() && '점포코드를 확인해 주세요.',
    !(form.subject || '').trim() && '상품·문의 대상을 확인해 주세요.',
    !department && '전달 부서를 선택해 주세요.',
    !confirmed && '원문 대조·확인 체크를 해 주세요.',
  ].filter((item): item is string => typeof item === 'string');
  const stepHint = intakeLocked ? '센터에 전달한 접수입니다. 처리 현황을 확인하세요.' : workStage === 'source' ? (c.channel === 'voice' ? (c.audioUrl ? '저장된 통화 녹음을 AI가 대화록과 접수서로 정리합니다.' : '통화 녹음 파일이 필요합니다.') : '원문을 확인한 뒤 AI로 접수 내용을 정리하세요.') : workStage === 'review' ? '필수 정보를 대조하고 원문 확인에 체크해 주세요.' : canTransfer ? '확인한 접수와 근거를 담당 센터에 전달합니다.' : transferBlockers[0];
  return <div className="desk">
    <div className="case-heading"><div><div className="button-row"><span className="badge neutral">{c.type === 'missing' ? '미도착 문의' : '오출고 문의'}</span><span className="muted small">{c.id}</span></div><h2>{c.title}</h2></div><div className="case-heading-meta"><Status status={c.status}/><span className="muted small">{c.asOf ? `기준 ${c.asOf.replace('T', ' ').slice(0, 16)}` : '시연 기준 데이터'}</span></div></div>
    <div id="desk-workflow" className="workflow-command" tabIndex={-1}>
      <nav className="workflow-steps" aria-label="상담 처리 흐름">
        <a className="workflow-queue-return" href="#work-queue">← 접수 목록으로</a>
        {([{ id: 'source', label: '통화 · 텍스트 접수', detail: '녹음 / 원문 확인' }, { id: 'review', label: 'AI 정리 · 확인', detail: '접수서 대조' }, { id: 'handoff', label: '부서 이관', detail: '근거와 함께 전달' }] as const).map((item, index) => <button key={item.id} onClick={() => showStage(item.id)} aria-pressed={workStage === item.id} aria-controls={item.id === 'handoff' ? 'desk-handoff' : item.id === 'review' ? 'intake-editor' : 'desk-source'}><b>{index + 1}</b><span><strong>{item.label}</strong><small>{item.detail}</small></span></button>)}
      </nav>
      <div className="workflow-primary"><div><span className="small-kicker">지금 할 일</span><strong>{stepHint}</strong>{workStage === 'source' && <small>{mode === 'demo-live' ? '실제 AI API 사용' : '저장 결과 재생 · API 호출 없음'}</small>}</div>
        {intakeLocked ? <button className="primary" onClick={() => onView('center')}>센터 처리 현황 보기 →</button> : workStage === 'source' ? <button className="primary" disabled={analyzeBlocked} onClick={() => void analyze()}>{busy === 'analyze' ? 'AI 정리 중…' : c.channel === 'voice' ? '대화록 변환 · AI 접수 정리' : '텍스트 문의 · AI 접수 정리'} →</button> : workStage === 'review' ? <button className="primary" onClick={() => showStage('handoff')}>이관 내용 확인 →</button> : <button className="primary" disabled={!canTransfer} onClick={() => void persist(true)}>{busy === 'transfer' ? '이관 중…' : '확인하고 센터로 이관'} →</button>}
      </div>
    </div>
    {workStage !== 'review' && !intakeLocked && !canTransfer && workStage === 'handoff' && <div className="notice warning compact"><span>{transferBlockers.join(' ')}</span><button onClick={() => showStage('review')}>② 접수 내용 확인 · 수정</button></div>}
    {workStage !== 'handoff' && (!!analysis?.unknowns?.length || selectedEvidence.some(item => item.withheld)) && <div className="workflow-attention" role="status"><span>추가 확인 {analysis?.unknowns?.length || 0}건 · 근거 보류 {selectedEvidence.filter(item => item.withheld).length}건</span><button className="text-button" onClick={() => showStage('handoff')}>미확인 사항 보기 →</button></div>}
    {analysisFailure && <div className="notice danger" role="alert">{analysisFailure}<button onClick={() => showStage('source')}>통화·분석 확인</button></div>}
    {error && <div className="notice danger" role="alert">{error}<button className="text-button" onClick={() => setError('')}>닫기</button></div>}
    {(uncertain || stale) && <div className="notice warning" role="status"><div><strong>{uncertain ? '저장 여부 확인이 필요합니다' : '서버의 접수 내용이 변경되었습니다'}</strong><p>{uncertain ? '응답을 받지 못했어도 저장되었을 수 있습니다. 초안은 보존하고, 먼저 서버 내용을 확인합니다.' : '현재 초안은 유지했습니다. 최신 내용과 대조한 후 다시 저장해 주세요.'}</p></div><button disabled={!!busy || fallback} onClick={() => void inspectLatest()}>{uncertain ? '저장 여부 확인' : '최신 내용 대조'}</button></div>}
    {recovery && <Recovery current={recovery} busy={!!busy} rows={[{ label: '접수 정보', local: [form.storeId, form.subject, `${form.quantity ?? ''} ${form.unit || ''}`, form.request, question].filter(Boolean).join('\n'), server: [recovery.intake?.storeId, recovery.intake?.subject, `${recovery.intake?.quantity ?? ''} ${recovery.intake?.unit || ''}`, recovery.intake?.request].filter(Boolean).join('\n') }, { label: '전달 부서 · 확인', local: `${departmentName(department, analysis?.department)} · ${confirmed ? '확인함' : '확인 전'}`, server: `${departmentName(recovery.departmentId, recovery.analysis?.department)} · ${recovery.reviewConfirmed ? '확인함' : '확인 전'}` }]} onUseServer={() => { draft.replace(deskDraft(recovery), true); setRecovery(null); setError(''); }} onKeepDraft={() => { draft.replace({ ...draft.value, formRevision: recovery.revision, confirmed: false, edited: true, uncertain: undefined }); setRecovery(null); setError(''); }}/>}
    {intakeLocked && <div className="notice info compact">센터로 전달된 접수입니다. 상담원이 확인한 내용은 보존되며 이후 회신은 센터 회신에서 등록합니다.<button onClick={() => onView('center')}>센터 회신 보기</button></div>}
    <div id="desk-source" className="integrated-review task-anchor" tabIndex={-1}>
      <CallReview
        workStage={workStage}
        caseData={{ ...c, transcript, analysis, intake: form, reviewConfirmed: confirmed, analysisMode: resultMode }}
        disabled={intakeLocked || !!busy}
        playbackRate={playbackRate}
        onPlaybackRateChange={onPlaybackRateChange}
        onPlaybackEnded={() => setCompletedAudioSource(audioSource)}
        transcriptMode={resultMode ?? (!analysis ? 'replay' : undefined)}
        analysisState={busy === 'analyze' ? 'loading' : analysisFailure ? 'error' : 'idle'}
        analysisError={analysisFailure}
        onRetryAnalysis={() => void analyze()}
        analysisActions={<div className="analysis-action integrated-analysis-action">
        <div><strong>{audioEnded || c.channel !== 'voice' ? '접수 내용을 정리할 준비가 되었습니다' : '통화를 먼저 끝까지 재생해 주세요'}</strong><p className="small muted">{mode === 'demo-live' ? '실제 AI API를 사용합니다. 결과를 확인한 뒤 아래 접수 정보를 편집해 주세요.' : '저장된 결과를 불러옵니다. 실제 AI API 비용은 발생하지 않습니다.'}</p></div>
        <button className={!analysis ? "primary" : undefined} disabled={analyzeBlocked} onClick={() => void analyze()}>{busy === 'analyze' ? 'AI가 전사·정제하고 있습니다…' : mode === 'demo-live' ? 'AI 전사·정제 실행' : '저장된 분석 결과 재생'} <span aria-hidden="true">→</span></button>
        <button className="text-button" onClick={() => showStage('review')}>접수 편집으로 이동 →</button>
      </div>}
        intakeEditor={<section id="intake-editor" tabIndex={-1} className="panel refinement-panel"><div className="panel-heading"><div><span className="small-kicker">02 / REFINE & REVIEW</span><h3>AI 정제와 접수 확인</h3></div>{resultMode && <span className={`badge ${resultMode === 'demo-live' ? 'success' : 'info'}`}>{resultMode === 'demo-live' ? '실제 AI 분석' : '저장 결과 재생'}</span>}</div>
        <fieldset disabled={!!busy || !!uncertain || intakeLocked}>
        <label className="review-check"><input type="checkbox" checked={confirmed} onChange={e => setConfirmed(e.target.checked)}/><span>점포·상품·전달 부서를 원문과 대조하고, 접수 내용을 확인했습니다. 수정할 내용이 없으면 그대로 확인하셔도 됩니다.</span></label>
<div className="form-grid"><label>점포코드 <span className="required">필수</span><input value={form.storeId || ''} aria-label="점포코드 필수" aria-describedby={analysis ? "proposal-storeId" : undefined} onChange={e => field('storeId', e.target.value)} placeholder="점포코드 확인"/>{analysis && <FieldSuggestion id="proposal-storeId" value={analysis.fields?.storeId} current={form.storeId}/>}</label><label>상품·문의 대상 <span className="required">필수</span><input value={form.subject || ''} aria-label="상품·문의 대상 필수" aria-describedby={analysis ? "proposal-subject" : undefined} onChange={e => field('subject', e.target.value)} placeholder="상품명 또는 문의 대상"/>{analysis && <FieldSuggestion id="proposal-subject" value={analysis.fields?.subject} current={form.subject}/>}</label><label>수령 수량(경영주 진술)<input type="number" min="0" value={form.quantity ?? ''} aria-label="수령 수량(경영주 진술)" aria-describedby={analysis ? "proposal-quantity" : undefined} onChange={e => field('quantity', e.target.value)} placeholder="미확인"/>{analysis && <FieldSuggestion id="proposal-quantity" value={analysis.fields?.quantity} current={form.quantity}/>}</label><label>수령 단위<input value={form.unit || ''} aria-label="수령 단위" aria-describedby={analysis ? "proposal-unit" : undefined} onChange={e => field('unit', e.target.value)} placeholder="개 / 박스 · 미확인"/>{analysis && <FieldSuggestion id="proposal-unit" value={analysis.fields?.unit} current={form.unit}/>}</label><label className="full">요청사항<textarea value={form.request || ''} aria-label="요청사항" aria-describedby={analysis ? "proposal-request" : undefined} onChange={e => field('request', e.target.value)} placeholder="경영주가 요청한 내용을 확인해 주세요." rows={3}/>{analysis && <FieldSuggestion id="proposal-request" value={analysis.fields?.request} current={form.request}/>}</label></div>
        <details className="quantity-context"><summary>수량·단위 대조 기준</summary><p>수령 값은 경영주 진술입니다. 주문·출고 수량으로 채우거나 BOX를 EA로 환산하지 않습니다.</p>{(c.expected || c.received) && <><p>주문: {c.expected?.product || '미확인'} · {c.expected?.quantity ?? '미확인'} {c.expected?.unit || ''}<br/>수령 진술: {c.received?.product || '미확인'} · {c.received?.quantity ?? '미확인'} {c.received?.unit || ''}</p><span className="small muted">합성 사례 참고값 · 실제 확인 결과나 자동 보정값이 아닙니다.</span></>}</details>
        {analysis ? <><div className="ai-summary"><span className="small-kicker">AI 요약 · 확인 전 초안</span><p>{analysis.summary}</p></div>{!!analysis.issues?.length && <div className="issue-list">{analysis.issues.map((issue, i) => <div className="issue" key={i}><span className="badge warning">확인 필요</span><div><strong>{issue.message}</strong>{issue.evidence && <p>원문 근거: {issue.evidence}</p>}</div></div>)}</div>}
          <div className="compare-strip"><span>원문 보존</span><span aria-hidden="true">→</span><span>AI 초안</span><span aria-hidden="true">→</span><strong>상담원 편집·확인</strong></div>
          <details className="ai-fields"><summary>AI가 제안한 접수 정보 원본</summary><dl className="details-list"><div><dt>점포</dt><dd>{analysis.fields.storeId || '미확인'}</dd></div><div><dt>상품·대상</dt><dd>{analysis.fields.subject || '미확인'}</dd></div><div><dt>수령 수량·단위(진술)</dt><dd>{analysis.fields.quantity ?? '미확인'} {analysis.fields.unit || '단위 미확인'}</dd></div><div><dt>요청</dt><dd>{analysis.fields.request || '미확인'}</dd></div></dl></details>
        </> : <div className="analysis-empty"><svg viewBox="0 0 32 32" fill="none" aria-hidden="true"><path d="m16 3 3.5 9.5L29 16l-9.5 3.5L16 29l-3.5-9.5L3 16l9.5-3.5L16 3Z" stroke="currentColor" strokeWidth="1.5"/></svg><strong>문의의 핵심을 접수 정보로</strong><p>전사·정제를 실행하면 상품, 수량, 요청사항과<br/>추가로 확인할 질문을 정리합니다.</p></div>}
        {analysis && <div className="questions"><h4>확인할 항목 <span className="count">{analysis.questions?.length || 0}</span></h4>{analysis.questions?.map((q, i) => <button key={i} className="question" onClick={() => setQuestion(q)}><span>{String(i + 1).padStart(2, '0')}</span>{q}<span aria-hidden="true">＋</span></button>)}<label className="full">추가 확인 메모<textarea rows={2} value={question} onChange={e => setQuestion(e.target.value)} placeholder="확인할 항목을 선택하거나 직접 적어 주세요."/></label></div>}
        <div className="department-card"><div><h4>전달 부서</h4>{analysis?.department && <p>{analysis.department.reason}</p>}</div><label><span className="sr-only">전달 부서</span><select value={department} onChange={e => { setDepartment(e.target.value); setEdited(true); setConfirmed(false); }}><option value="">부서 선택</option>{analysis?.department?.id && !['delivery', 'warehouse', 'cs'].includes(analysis.department.id) && <option value={analysis.department.id}>{analysis.department.name} · AI 추천</option>}<option value="warehouse">출고 운영</option><option value="delivery">배송 운영</option><option value="cs">고객 지원</option></select></label></div>
        {!edited && <p className="small muted">접수 정보를 한 번 편집한 뒤 확인 체크를 해 주세요. 미확인 정보는 비워 둘 수 있습니다.</p>}
        </fieldset>

      </section>}
      />
    </div>
    <div hidden={workStage !== 'handoff'} className="workflow-stage-content">
    <section id="desk-evidence" tabIndex={-1} className="panel evidence-panel task-anchor">
      <div className="panel-heading"><div><span className="small-kicker">03 / CONNECTED EVIDENCE</span><h3>물류 근거와 남은 질문</h3></div><div className="button-row"><button onClick={() => onView('wms')}>WMS 작업 확인 <Arrow/></button><button onClick={() => onView('tms')}>TMS 배송 확인 <Arrow/></button></div></div>
      <div className="facts-grid"><details className="workflow-facts"><summary>AI가 정리한 사실 · 확인 전 초안</summary>{analysis?.facts?.length ? <ul className="clean-list">{analysis.facts.map((x, i) => <li key={i}>{x}</li>)}</ul> : <p className="muted">분석 결과를 불러오면 원문과 대조할 초안을 표시합니다.</p>}</details><div><h4><span className="status-dot warning"/>AI가 정리한 추가 확인 사항</h4>{analysis?.unknowns?.length ? <ul className="clean-list">{analysis.unknowns.map((x, i) => <li key={i}>{x}</li>)}</ul> : <p className="muted">확인되지 않은 내용은 단정하지 않습니다.</p>}</div></div>
      <section className="desk-evidence-section" aria-label="연결한 물류 근거" data-case-id={c.id}>
        <div className="desk-evidence-heading"><h4>연결한 물류 근거</h4><span className="small muted">선택 {selectedEvidence.length}건 · 표시 {visibleEvidenceCount}건{selectedEvidence.length > visibleEvidenceCount ? ` · 보류 ${selectedEvidence.length - visibleEvidenceCount}건` : ''}</span></div>
        <div className="desk-evidence-context"><span>접수 {c.id}</span>{typeof c.linkedFixtureId === 'string' && <span>연결 원본 {c.linkedFixtureId}</span>}<span>접수 기준 {evidenceDate(c.asOf)}</span></div>
        {selectedEvidence.length ? <ul className="desk-evidence-grid">{selectedEvidence.map(({ id, record, metadata, observedAt, sourceAsOf, withheld, synthetic }) => <li key={id}>
          <article className={`desk-evidence-card${withheld ? ' desk-evidence-blocked' : ''}`} data-evidence-id={id} data-evidence-state={withheld ? 'withheld' : 'ready'}>
            {withheld || !record ? <><div className="desk-evidence-card-header"><h4>{id}</h4><span className="badge warning">내용 표시 보류</span></div><p className="desk-evidence-note">{withheld}</p><p className="desk-evidence-summary">연결된 ID는 유지됩니다. 원본을 확인한 뒤 접수에 사용할 수 있습니다.</p></> : <>
              <div className="desk-evidence-card-header"><h4>{evidenceText(record.label, id)}</h4><div className="desk-evidence-badges"><span className="badge neutral">{evidenceText(metadata.sourceSystem ?? record.system, '출처 시스템 미등록')}</span><span className={`badge ${(metadata.recordStatus ?? record.status) === 'fact' ? 'info' : 'warning'}`}>{(metadata.recordStatus ?? record.status) === 'fact' ? '기록 확인' : (metadata.recordStatus ?? record.status) === 'unknown' ? '미확인' : '기록 상태 미등록'}</span><span className="badge neutral">{synthetic ? '합성 자료' : '합성 여부 확인 필요'}</span></div></div>
              <p className="desk-evidence-value">{evidenceText(record.value, '관측 내용 미등록')}</p>
              <dl className="desk-evidence-meta"><div><dt>원본 출처</dt><dd>{evidenceText(record.source, '출처 미등록')}</dd></div><div><dt>기록 시각</dt><dd>{evidenceDate(observedAt)}</dd></div><div><dt>조회 기준시각</dt><dd>{evidenceDate(sourceAsOf)}</dd></div><div><dt>근거 ID</dt><dd>{id}</dd></div></dl>
              {(observedAt == null || observedAt === '') && <p className="desk-evidence-note">기록 시각 미등록 · 접수 기준시각과 대조할 수 없습니다.</p>}
              <details className="desk-evidence-detail"><summary>원본 기록과 연결 정보</summary><dl className="desk-evidence-meta"><div><dt>원본 레코드 키</dt><dd>{evidenceText(metadata.sourceRecordKey)}</dd></div><div><dt>시각 정밀도 / 시간대 상태</dt><dd>{evidenceText(metadata.observedAtPrecision)} / {evidenceText(metadata.timezoneStatus)}</dd></div><div><dt>원본 연결 상태</dt><dd>{evidenceText(metadata.relationStatus)}</dd></div></dl><pre>{JSON.stringify(record, null, 2)}</pre></details>
            </>}
          </article>
        </li>)}</ul> : <p className="desk-evidence-empty">연결한 근거가 없습니다. WMS 작업 확인 또는 TMS 배송 확인에서 현재 접수에 필요한 근거를 연결해 주세요.</p>}
        <p className="desk-evidence-summary">기록 상태와 합성 여부를 구분합니다. 기록 확인만으로 실제 도착·발생 원인·작업자 귀책을 확정할 수 없습니다.</p>
      </section>
    </section>
    <section id="desk-handoff" tabIndex={-1} className="panel handoff-panel task-anchor" aria-label="접수 저장 및 센터 전달"><div><h3>{intakeLocked ? '센터로 전달한 접수입니다' : '확인한 접수를 센터로 전달'}</h3><p className="muted">{intakeLocked ? '이관한 내용은 보존됩니다. 센터의 조치와 회신을 확인하세요.' : '점포·문의 대상·부서와 원문 대조를 확인하세요. 미확인 사항은 남긴 채 전달할 수 있습니다.'}</p></div><div className="transfer-readiness" role="status">{intakeLocked ? <p>센터 전달 완료 · 등록된 조치와 회신을 확인하세요.</p> : canTransfer ? <p>확인한 내용을 센터로 전달할 준비가 됐습니다.</p> : <><strong>전달 전 확인할 내용</strong><ul>{transferBlockers.map(reason => <li key={reason}>{reason}</li>)}</ul></>}</div><div className="panel-actions"><button disabled={intakeLocked || !!busy || fallback || stale || !!uncertain || !!recovery} onClick={() => void persist()}>접수 내용 저장</button><button className="primary" disabled={!canTransfer} onClick={() => void persist(true)}>{busy === 'transfer' ? '전달 중…' : '확인 후 센터 전달'} <span aria-hidden="true">→</span></button></div></section>
    </div>
    {workStage === 'handoff' && <NotificationStatus caseData={c} audience="workforce"/>}
  </div>;
}

function Owner({ cases, selected, onSelect, onCreated, onToast, onDesk, fallback, counselorEntry = false }: { counselorEntry?: boolean; cases: CaseData[]; selected: string; onSelect: (s: string) => void; onCreated: (c: CaseData) => void; onToast: (s: string) => void; onDesk: () => void; fallback: boolean }) {
  type Attempt = { key: string; payload: { storeId: string; subject: string; text: string; type: 'missing' | 'wrong'; referenceCaseId?: string }; retryAllowed?: boolean };
  const draft = useSessionDraft<{ storeId: string; subject: string; text: string; type: 'missing' | 'wrong'; referenceCaseId: string | null; attempt: Attempt | null }>(counselorEntry ? 'counselor:new' : 'owner:new', { storeId: '', subject: '', text: '', type: 'missing', referenceCaseId: null, attempt: null });
  const { storeId, subject, text, type, referenceCaseId, attempt } = draft.value;
  const setStoreId = (value: string) => draft.set('storeId', value);
  const setSubject = (value: string) => draft.set('subject', value);
  const setText = (value: string) => draft.set('text', value);
  const setType = (value: 'missing' | 'wrong') => draft.set('type', value);
  const setReferenceCaseId = (value: string | null) => draft.set('referenceCaseId', value);
  const [busy, setBusy] = useState(false); const [error, setError] = useState('');
  const [linkNotice, setLinkNotice] = useState('');
  const [referenceSources, setReferenceSources] = useState<CaseData[]>([]);
  useEffect(() => {
    let mounted = true;
    void fetch('/cases.json', { cache: 'no-store' }).then(async response => {
      if (!response.ok) throw new Error('reference load failed');
      const data = await response.json();
      if (!Array.isArray(data.cases)) throw new Error('reference shape invalid');
      if (mounted) setReferenceSources(data.cases);
    }).catch(() => { if (mounted) setLinkNotice('연결 기준 사건을 불러오지 못했습니다. 연결 없이 새 문의를 접수할 수 있습니다.'); });
    return () => { mounted = false; };
  }, []);
  const referenceKeys = (item: CaseData) => ({
    storeId: item.intake && 'storeId' in item.intake ? item.intake.storeId : item.storeId,
    subject: item.intake && 'subject' in item.intake ? item.intake.subject : item.subject,
    type: item.type,
  });
  const referenceCases = referenceSources.filter(item => { const keys = referenceKeys(item); return /^CASE-/.test(item.id) && typeof keys.storeId === 'string' && !!keys.storeId.trim() && typeof keys.subject === 'string' && !!keys.subject.trim(); });
  const referenceDate = (value?: string) => value && Number.isFinite(Date.parse(value)) ? new Intl.DateTimeFormat('ko-KR', { timeZone: 'Asia/Seoul', year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hour12: false }).format(new Date(value)) + ' KST' : '기준시각 미등록';
  const chooseReference = (id: string) => {
    const item = referenceCases.find(row => row.id === id);
    if (!item) { setReferenceCaseId(null); setLinkNotice(''); return; }
    const keys = referenceKeys(item);
    setReferenceCaseId(item.id); setStoreId(String(keys.storeId)); setSubject(String(keys.subject)); setType(keys.type);
    setLinkNotice('선택한 사건의 점포·문의 유형·제목을 채웠습니다. 상세 내용은 유지됩니다. 동일 날짜의 문의인지 확인해 주세요.');
  };
  const editContext = (field: 'storeId' | 'subject' | 'type', value: string) => {
    if (field === 'storeId') setStoreId(value); else if (field === 'subject') setSubject(value); else setType(value as 'missing' | 'wrong');
    const item = referenceCases.find(row => row.id === referenceCaseId);
    if (referenceCaseId && (!item || referenceKeys(item)[field] !== value)) { setReferenceCaseId(null); setLinkNotice('점포·문의 유형·제목이 변경되어 기존 접수 연결을 해제했습니다.'); }
  };
  const c = cases.find(item => item.id === selected) || cases[0];
  const finish = (result: CaseData) => { onCreated(result); draft.replace({ storeId, subject: '', text: '', type, referenceCaseId: null, attempt: null }, true); setLinkNotice(''); setError(''); };
  const submit = async (e?: React.FormEvent) => {
    e?.preventDefault();
    if (busy || fallback || (attempt && !attempt.retryAllowed)) return;
    onToast('');
    const current = attempt || { key: crypto.randomUUID(), payload: { storeId, subject, text, type, ...(referenceCaseId ? { referenceCaseId } : {}) } };
    draft.set('attempt', { ...current, retryAllowed: false }); setBusy(true); setError('');
    try { finish(await request<CaseData>('/api/intake', 'POST', current.payload, 'owner', { idempotencyKey: current.key })); }
    catch (err) {
      setError(errorText(err));
      if (err instanceof ApiError && !err.uncertain && err.status !== 409) draft.set('attempt', null);
    } finally { setBusy(false); }
  };
  const verifyAttempt = async () => {
    if (!attempt || busy) return;
    setBusy(true); setError(''); onToast('');
    try { finish(await request<CaseData>(`/api/intake-attempts/${attempt.key}`, 'GET', undefined, 'owner')); }
    catch (err) {
      if (err instanceof ApiError && err.status === 404) { draft.set('attempt', { ...attempt, retryAllowed: true }); setError('아직 등록된 접수를 찾지 못했습니다. 첫 요청이 처리 중일 수 있어 입력을 유지합니다. 같은 내용으로 확인·재시도하면 중복 접수를 방지합니다.'); }
      else setError(errorText(err));
    } finally { setBusy(false); }
  };
  return <div className={`owner-grid${counselorEntry ? ' workflow-counselor-entry' : ''}`}><section className="panel"><div className="panel-heading"><div><span className="small-kicker">STORE REQUEST</span><h2>{counselorEntry ? '접수 원문 작성' : '어떤 도움이 필요하신가요?'}</h2><p className="muted">{counselorEntry ? '점포가 전달한 문의를 그대로 입력해 주세요.' : '매장 상황을 편하게 적어 주세요.'}</p></div></div><form onSubmit={e => void submit(e)} className="owner-form"><fieldset className="owner-entry" disabled={busy || !!attempt}><label>관련 기존 접수 연결(선택)<select value={referenceCaseId || ''} onChange={e => chooseReference(e.target.value)} disabled={busy} aria-describedby="reference-case-help"><option value="">연결하지 않음 · 새 문의</option>{referenceCases.map(item => <option key={item.id} value={item.id}>{item.id} · {referenceDate(item.asOf)} · {item.title}</option>)}</select></label><p id="reference-case-help" className="muted">{referenceCaseId ? '선택한 사건과 동일한 날짜·배송 건인지 확인해 주세요. 점포·문의 유형·제목이 달라지면 연결이 해제됩니다.' : '선택하지 않으면 입력한 원문을 기반으로 새 문의를 접수하며 기존 물류 근거는 연결되지 않습니다.'}</p>{linkNotice && <p className="notice info compact" role="status">{linkNotice}</p>}<fieldset><legend>문의 유형</legend><div className="type-choices"><label className={type === 'missing' ? 'chosen' : ''}><input type="radio" name="type" checked={type === 'missing'} onChange={() => editContext('type', 'missing')}/><strong>상품 미도착</strong><span>예정된 상품이 오지 않았어요</span></label><label className={type === 'wrong' ? 'chosen' : ''}><input type="radio" name="type" checked={type === 'wrong'} onChange={() => editContext('type', 'wrong')}/><strong>다른 상품 도착</strong><span>주문한 것과 다르게 왔어요</span></label></div></fieldset><label>점포코드<input required value={storeId} onChange={e => editContext('storeId', e.target.value)} placeholder="예: GS0001"/></label><label>문의 제목<input required value={subject} onChange={e => editContext('subject', e.target.value)} placeholder="어떤 상품에 문제가 있나요?"/></label><label>상세 내용<textarea required rows={7} value={text} onChange={e => setText(e.target.value)} placeholder="상품명, 수량, 도착 시간과 원하시는 조치를 적어 주세요. 모르는 내용은 비워 두셔도 괜찮습니다."/></label><div className="notice info compact">작성하신 내용은 상담원이 확인한 후 담당 센터에 전달합니다.</div></fieldset>{error && <p className="notice danger" role="alert">{error}</p>}{attempt && <div className="notice warning recovery-attempt" role="status"><strong>접수 결과를 확인하고 있습니다</strong><p>입력 내용은 보존했습니다. 저장 여부 확인이 끝날 때까지 내용을 바꾸거나 새 문의를 보내지 않습니다.</p><div className="button-row"><button type="button" disabled={busy || fallback} onClick={() => void verifyAttempt()}>접수 저장 여부 확인</button>{attempt.retryAllowed && <button type="button" disabled={busy || fallback} onClick={() => void submit()}>같은 내용으로 접수 확인·재시도</button>}</div></div>}<button className="primary wide" disabled={busy || fallback || !!attempt}>{busy ? '접수 중…' : counselorEntry ? '등록하고 AI 정리로 이동' : '문의 접수하기'} <span aria-hidden="true">→</span></button></form></section><section hidden={counselorEntry} className="panel"><div className="panel-heading"><div><span className="small-kicker">MY REQUEST</span><h2>접수 진행 상황</h2></div><span className="badge neutral">시연용 전체 목록</span></div><label>접수 건 선택<select value={c?.id || ''} onChange={e => onSelect(e.target.value)}>{cases.map(item => <option key={item.id} value={item.id}>{item.id} · {item.title}</option>)}</select></label>{c ? <div className="receipt"><div className="receipt-top"><div><span className="muted small">{c.id}</span><h3>{c.title}</h3><p>{c.store.name}</p></div><Status status={c.status}/></div><div className="receipt-steps"><div className="done">문의 접수</div><div className={['handed_off', 'in_progress', 'closed'].includes(c.status || '') ? 'done' : ''}>담당 센터 확인</div><div className={c.reply ? 'done' : ''}>센터 회신</div></div><h4>센터에서 보낸 회신</h4>{c.reply ? <div className="registered-reply"><span className="badge success">등록된 회신</span>{c.replyTitle && <h3>{c.replyTitle}</h3>}<p>{c.reply}</p></div> : <div className="empty-reply"><p>아직 등록된 센터 회신이 없습니다.</p><span>확인이 끝나는 대로 이곳에서 안내해 드립니다.</span></div>}{!!c.pendingActions?.length && <div className="pending-list"><h4>진행 중인 조치</h4><ul>{c.pendingActions.map((a, i) => <li key={i}>{a}</li>)}</ul></div>}<NotificationStatus caseData={c} audience="owner"/><details><summary>내가 접수한 내용</summary><p className="source-text">{c.sourceText}</p></details><button className="text-button" onClick={onDesk}>시연: 상담 작업대로 이동 <Arrow/></button></div> : <div className="empty-state"><p>접수 후 진행 상황을 확인할 수 있습니다.</p></div>}</section></div>;
}

function Center({ caseData: c, onSave, onToast, onView, onUpdate, fallback, mode }: { mode: Mode; fallback: boolean; caseData: CaseData; onSave: (id: string, p: Record<string, unknown>) => Promise<CaseData>; onToast: (s: string) => void; onView: (v: View) => void; onUpdate: (c: CaseData) => void }) {
  type CenterDraft = { formRevision?: number; replyTitle?: string; reply: string; pending: string[]; action: string; uncertain?: Record<string, unknown>; operation?: boolean; workStage?: 'evidence' | 'reply' };
  const suggestedTitle = `${c.intake?.subject || c.title} 확인 안내`.slice(0, 160);
  const initial = (item: CaseData): CenterDraft => ({ formRevision: item.revision, replyTitle: item.replyTitle || suggestedTitle, reply: item.reply || '', pending: item.pendingActions || [], action: '' });
  const draft = useSessionDraft<CenterDraft>(`center:${c.id}`, initial(c), value => ({ replyTitle: value.replyTitle, reply: value.reply, pending: value.pending, action: value.action, uncertain: value.uncertain }));
  const { formRevision, reply, pending, action, uncertain } = draft.value;
  const replyTitle = draft.value.replyTitle ?? suggestedTitle;
  const setReplyTitle = (value: string) => draft.set('replyTitle', value);
  const [savedNotice, setSavedNotice] = useState('');
  const setReply = (value: string) => draft.set('reply', value);
  const setPending = (value: string[] | ((old: string[]) => string[])) => draft.set('pending', value);
  const setAction = (value: string) => draft.set('action', value);
  const [error, setError] = useState(''); const busy = draft.value.operation || false;
  const setBusy = (value: boolean) => draft.set('operation', value);
  const [recovery, setRecovery] = useState<CaseData | null>(null);
  const stale = formRevision !== c.revision;
  const received = ['handed_off', 'in_progress', 'closed'].includes(c.status || '');
  const blocked = fallback || !received || c.status === 'closed' || busy || stale || !!uncertain || !!recovery;
  const [generatedReply, setGeneratedReply] = useState('');
  const [generatedTitle, setGeneratedTitle] = useState('');
  const [generating, setGenerating] = useState(false);
  const generatingRef = useRef(false);
  const alive = useRef(false);
  useEffect(() => { alive.current = true; return () => { alive.current = false; }; }, []);
  const generateReply = async () => {
    if (blocked || generatingRef.current) return;
    generatingRef.current = true; setGenerating(true); setBusy(true); setError('');
    try {
      const result = await request<{ replyTitle: string; replyDraft: string; mode: Mode; revision: number }>(`/api/cases/${c.id}/reply-draft`, 'POST', { mode, expectedRevision: formRevision, centerContext: { pendingActions: pending, reply, replyTitle } }, 'center');
      if (!alive.current) return;
      setGeneratedTitle(result.replyTitle); setGeneratedReply(result.replyDraft); draft.set('workStage', 'reply');
      onToast(result.mode === 'demo-live' ? 'AI 답변 초안을 생성했습니다. 검토 후 적용해 주세요.' : '저장된 답변 초안을 불러왔습니다. API 호출은 하지 않았습니다.');
    } catch (failure) { if (alive.current) setError(errorText(failure)); }
    finally { generatingRef.current = false; setBusy(false); if (alive.current) setGenerating(false); }
  };
  const workStage = draft.value.workStage || (c.status === 'closed' ? 'reply' : 'evidence');
  const showStage = (stage: 'evidence' | 'reply') => { draft.set('workStage', stage); window.requestAnimationFrame(() => document.getElementById('center-workflow')?.scrollIntoView({ block: 'start', behavior: 'instant' })); };
  const replyReadiness = c.status === 'closed' ? '최종 회신이 등록되어 처리 완료된 접수입니다.' : fallback ? '예시 열람 중입니다. 서버에 연결한 뒤 회신을 저장할 수 있습니다.' : !received ? '상담원이 확인 후 센터로 전달해야 회신할 수 있습니다.' : busy ? '저장 처리 중입니다.' : uncertain ? '회신 저장 여부를 먼저 확인해 주세요.' : stale || recovery ? '최신 서버 내용과 회신 초안을 대조해 주세요.' : action.trim() ? '작성 중인 조치를 추가하거나 입력을 비워 주세요.' : !replyTitle.trim() ? '회신 제목을 입력해 주세요.' : !reply.trim() ? '경영주에게 안내할 회신을 작성해 주세요.' : pending.length ? `남은 조치 ${pending.length}건 · 중간 회신만 등록할 수 있습니다.` : '모든 조치가 끝났다면 최종 회신으로 처리 완료할 수 있습니다.';
  const submit = async (close: boolean) => {
    if (blocked || !replyTitle.trim() || !reply.trim() || (close && pending.length) || action.trim()) return;
    setBusy(true); setError('');
    const payload = { expectedRevision: formRevision, replyTitle: replyTitle.trim(), reply: reply.trim(), pendingActions: pending, status: close ? 'closed' : 'in_progress' };
    try {
      const saved = await onSave(c.id, payload);
      draft.replace({ ...initial(saved), workStage }, true);
      setSavedNotice(close ? '최종 회신 등록 완료' : '중간 회신 등록 완료');
      window.requestAnimationFrame(() => document.getElementById('center-save-result')?.scrollIntoView({ block: 'center', behavior: 'smooth' }));
      onToast(close ? '회신을 등록하고 처리를 완료했습니다. 경영주 화면에도 반영되었습니다.' : '중간 회신을 등록했습니다. 남은 조치는 계속 진행됩니다.');
    } catch (e) { setError(errorText(e)); if (e instanceof ApiError && e.uncertain) draft.set('uncertain', payload); if (e instanceof ApiError && e.status === 409) await inspectLatest(); } finally { setBusy(false); }
  };
  const inspectLatest = async () => {
    setBusy(true); setError(''); onToast('');
    try {
      const latest = await request<CaseData>(`/api/cases/${c.id}`, 'GET', undefined, 'center'); onUpdate(latest);
      if (uncertain && sameMutation(latest, uncertain)) { draft.replace(initial(latest), true); setRecovery(null); onToast('서버에 요청한 회신이 저장되어 있음을 확인했습니다.'); }
      else setRecovery(latest);
    } catch (e) { setError(errorText(e)); } finally { setBusy(false); }
  };
  return <><div className="case-heading"><div><span className="small muted">{c.store.name} · {c.id}</span><h2>{c.title}</h2></div><Status status={c.status}/></div><div id="center-workflow" className="workflow-command" tabIndex={-1}><nav className="workflow-steps workflow-center-steps" aria-label="센터 처리 흐름"><a className="workflow-queue-return" href="#work-queue">← 접수 목록으로</a><button aria-pressed={workStage === 'evidence'} aria-controls="center-evidence" onClick={() => showStage('evidence')}><b>1</b><span><strong>이관 · 근거 확인</strong><small>접수와 물류 기록</small></span></button><button aria-pressed={workStage === 'reply'} aria-controls="center-response" onClick={() => showStage('reply')}><b>2</b><span><strong>처리 · 최종 회신</strong><small>조치 기록과 경영주 안내</small></span></button></nav><div className="workflow-primary"><div><span className="small-kicker">지금 할 일</span><strong>{workStage === 'evidence' ? '이관한 접수와 근거를 확인한 뒤 처리 내용을 작성하세요.' : replyReadiness}</strong></div>{workStage === 'evidence' ? <button className="primary" onClick={() => showStage('reply')}>처리·회신 작성 →</button> : c.status === 'closed' ? <button className="primary" onClick={() => onView('owner')}>경영주 회신 확인 →</button> : <button className="primary" disabled={blocked || !replyTitle.trim() || !reply.trim() || !!action.trim()} onClick={() => void submit(!pending.length)}>{busy ? '등록 중…' : pending.length ? '중간 회신 등록' : '최종 회신·처리 완료'} →</button>}</div></div>{workStage === "evidence" && received && c.status !== "closed" && <div className="reply-ai-action"><button className="primary" disabled={blocked || generating} onClick={() => void generateReply()}>{generating ? "AI 답변 생성 중…" : "AI 답변 초안 생성"}</button><span className="small muted">{mode === "demo-live" ? "실제 ChatGPT API" : "저장 결과 재생 · API 호출 없음"}</span></div>}{!received && <div className="notice warning compact">상담원의 원문 확인과 센터 이관이 먼저 필요합니다.</div>}{error && <div className="notice danger" role="alert">{error}</div>}{workStage === 'evidence' && (!!pending.length || !!action.trim()) && <p className="notice warning compact" role="status">남은 조치 {pending.length}건{action.trim() ? ' · 추가하지 않은 조치 초안 있음' : ''} · 처리·회신 단계에서 확인해 주세요.</p>}<div>{(uncertain || stale) && <div className="notice warning" role="status"><div><strong>{uncertain ? '회신 저장 여부 확인이 필요합니다' : '서버의 접수 내용이 변경되었습니다'}</strong><p>현재 회신 초안과 남은 조치는 보존했습니다. 최신 내용을 확인한 뒤 계속해 주세요.</p></div><button disabled={busy} onClick={() => void inspectLatest()}>{uncertain ? '회신 저장 여부 확인' : '최신 내용 대조'}</button></div>}{recovery && <Recovery current={recovery} busy={busy} rows={[{ label: '회신 제목', local: replyTitle, server: recovery.replyTitle || '' }, { label: '회신', local: reply, server: recovery.reply || '' }, { label: '남은 조치', local: [...pending, ...(action ? [action + ' (추가 전)'] : [])].join('\n'), server: (recovery.pendingActions || []).join('\n') }]} onUseServer={() => { draft.replace(initial(recovery), true); setRecovery(null); setError(''); }} onKeepDraft={() => { draft.replace({ ...draft.value, formRevision: recovery.revision, uncertain: undefined }); setRecovery(null); setError(''); }}/>}</div><div className="center-grid"><section hidden={workStage !== 'evidence'} id="center-evidence" tabIndex={-1} className="panel center-context task-anchor"><div className="panel-heading"><div><h2>이관 내용과 근거 확인</h2></div><Status status={c.status}/></div>{!received && <div className="notice warning compact">상담원의 확인과 센터 전달이 먼저 필요합니다.</div>}<h3>{c.title}</h3><dl className="details-list"><div><dt>접수 번호</dt><dd>{c.id}</dd></div><div><dt>점포</dt><dd>{c.store.name} · {c.intake?.storeId || c.store.id}</dd></div><div><dt>상품·문의 대상</dt><dd>{c.intake?.subject || '상담원 확인 전'}</dd></div><div><dt>수량</dt><dd>{c.intake?.quantity ?? '미확인'} {c.intake?.unit}</dd></div><div><dt>요청사항</dt><dd>{c.intake?.request || '상담원 확인 전'}</dd></div><div><dt>전달 부서</dt><dd>{departmentName(c.departmentId, c.analysis?.department)}</dd></div><div><dt>사람 확인</dt><dd>{c.reviewConfirmed ? '상담원 대조·확인 완료' : '확인 전'}</dd></div></dl><div className="button-row"><button onClick={() => onView('wms')}>WMS 근거 <Arrow/></button><button onClick={() => onView('tms')}>TMS 근거 <Arrow/></button></div><div className="divider"/><h4>연결된 근거</h4>{c.selectedEvidence?.length ? <ul className="clean-list">{c.selectedEvidence.map(id => <li key={id}>{c.evidence?.find(e => e.id === id)?.label || id}</li>)}</ul> : <p className="muted">연결된 근거가 없습니다. 물류 기록을 확인해 주세요.</p>}<details><summary>원문 확인</summary><p className="source-text">{c.sourceText}</p></details></section><section hidden={workStage !== 'reply'} id="center-response" className="panel center-response"><div className="panel-heading"><div><h2>조치 기록과 경영주 회신</h2></div><span className="badge neutral">센터 담당자</span></div><fieldset disabled={!received || busy || !!uncertain || c.status === 'closed'}><div className="reply-ai-action"><button className="primary" disabled={blocked || generating} onClick={() => void generateReply()}>{generating ? "AI 답변 생성 중…" : "AI 답변 초안 생성"}</button><span className="small muted">{mode === "demo-live" ? "실제 ChatGPT API · 생성 후 검토" : "저장 결과 재생 · API 호출 없음"}</span></div>{generatedReply && <div className="draft-reply"><div className="subheading"><strong>생성된 답변 초안</strong><span className="badge warning">미발송</span></div><h3>{generatedTitle}</h3><p>{generatedReply}</p><button onClick={() => { setReplyTitle(generatedTitle); setReply(generatedReply); setGeneratedReply(""); }}>제목·본문을 답변에 적용</button></div>}{c.analysis?.replyDraft && <details><summary>접수 때 작성된 참고 초안</summary><p>{c.analysis.replyDraft}</p><button onClick={() => { setReplyTitle(suggestedTitle); setReply(c.analysis!.replyDraft); }}>초안을 편집창에 가져오기</button></details>}<div id="center-actions" tabIndex={-1} className="pending-editor task-anchor"><div className="subheading"><h4>진행 중인 조치 <span className="count">{pending.length}</span></h4><span className="small muted">남은 조치가 있으면 처리 중으로 유지</span></div>{pending.map((p, i) => <div className="pending-item" key={`${p}-${i}`}><span>{p}</span><button aria-label={`${p} 조치 완료`} onClick={() => setPending(old => old.filter((_, n) => n !== i))}>완료</button></div>)}<div className="inline-form"><input aria-label="남은 조치 내용" value={action} onChange={e => setAction(e.target.value)} placeholder="예: 기사 확인 후 도착 예정 시각 안내"/><button disabled={!action.trim()} onClick={() => { setPending(old => [...old, action.trim()]); setAction(''); }}>조치 추가</button></div></div><label className="reply-title-field">회신 제목 <span className="required">필수</span><input aria-label="회신 제목" maxLength={160} value={replyTitle} onChange={e => setReplyTitle(e.target.value)} placeholder="예: 아침 배송 미도착 확인 안내"/></label><label id="center-reply" tabIndex={-1} className="task-anchor">경영주에게 등록할 회신 <span className="required">필수</span><textarea rows={8} value={reply} onChange={e => setReply(e.target.value)} placeholder="확인한 사실, 처리 내용과 후속 안내를 적어 주세요. 확인되지 않은 배송 시각이나 원인은 단정하지 않습니다."/></label></fieldset>{action.trim() && <p className="notice warning compact">작성 중인 조치가 있습니다. 조치 추가를 누르거나 입력을 비운 뒤 회신을 등록해 주세요.</p>}<div id="center-save-result" aria-live="polite">{savedNotice && <div className="notice success"><strong>{savedNotice}</strong><p>{c.replyTitle || replyTitle}</p><p>등록된 회신을 경영주 화면에서 확인할 수 있습니다.</p><button onClick={() => onView("owner")}>등록된 회신 보기 →</button></div>}{error && <p className="notice danger" role="alert">{error}</p>}</div><p className="reply-readiness" role="status">{replyReadiness}</p><div className="panel-actions"><button className={pending.length ? "primary" : undefined} disabled={blocked || !replyTitle.trim() || !reply.trim() || !!action.trim()} onClick={() => void submit(false)}>중간 회신 등록</button><button className={!pending.length ? "primary" : undefined} disabled={blocked || !replyTitle.trim() || !reply.trim() || !!pending.length || !!action.trim()} onClick={() => void submit(true)}>{busy ? '등록 중…' : '최종 회신·처리 완료'}</button></div><p className="small muted">등록한 회신만 경영주 화면에 보입니다. 모든 조치를 완료해야 문의를 종결할 수 있습니다.</p><button className="text-button" onClick={() => onView('owner')}>경영주 수신 화면 확인 <Arrow/></button><NotificationStatus caseData={c} audience="workforce"/></section></div></>;
}
