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
  // Picking a stage moves the selection with it. The owner reads `active` from the whole
  // list rather than the queue, so 답변 완료 used to sit beside a still-open 접수 대기 case.
  const changeQueue = (next: QueueId) => {
    setNewIntake(false); setQueue(next); setView(roleView[role]);
    const listed = filterCases(cases, role, next, query);
    if (!listed.some(item => item.id === selected)) setSelected(listed[0]?.id || '');
  };
  // An empty first screen reads as "this role has nothing". Open on the role's own queue
  // only while it holds something; the fixture ships no handed_off case, so the center tab
  // would otherwise always greet a judge with an empty rail.
  const firstQueue = (nextRole: WorkRole): QueueId => {
    const preferred: QueueId = nextRole === 'owner' ? 'all' : defaultQueue(nextRole);
    return cases.some(item => inQueue(item, nextRole, preferred)) ? preferred : 'all';
  };
  const changeRole = (nextRole: WorkRole) => {
    // 경영주는 자기 접수 전부를 보는 화면이라 처리 단계로 걸러 두지 않는다.
    setNewIntake(false); setRole(nextRole); setView(roleView[nextRole]); setQueue(firstQueue(nextRole)); setQuery(''); setToast('');
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
        <a className="brand" href="#" onClick={e => { e.preventDefault(); returnToWork(); }} aria-label="AI-GO 무엇이든 물어보살 홈"><span className="brand-mark" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none"><path d="M3 18 8 6l5 12M5 13h6M18 6v12" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/></svg></span><span><strong>AI-GO</strong> 무엇이든 물어보살</span></a>
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
      {loading && !cases.length ? <div className="empty-state" role="status"><div className="spinner"/><h2>접수 건을 불러오고 있습니다</h2><p>서버의 최신 처리 상태를 확인합니다.</p></div> : <div className={`console${logistics ? ' console-wide' : ''}`}>
        {!logistics && <QueueRail role={role} cases={cases} visibleCases={visibleCases} queue={queue} onQueue={changeQueue} query={query} onQuery={setQuery} sort={queueSort} onSort={setQueueSort} activeId={newIntake ? '' : active?.id} onSelect={selectCase} onNewIntake={role === 'counselor' ? () => { setNewIntake(true); setToast(''); } : undefined}/>}
        {newIntake && role === 'counselor'
          ? <Owner counselorEntry cases={cases} selected={selected} onSelect={setSelected} onCreated={created => { update(created); setSelected(created.id); setQueue('attention'); setQuery(''); setNewIntake(false); setToast(`${created.id} 접수 등록 완료 · AI 정리를 진행해 주세요.`); }} onToast={setToast} onDesk={() => setNewIntake(false)} onCancel={() => setNewIntake(false)} fallback={fallback}/>
          : !active ? <section id="selected-work" tabIndex={-1} className="console-pane console-thread" aria-label="선택한 접수 작업 영역"><div className="empty-state"><h2>{logistics ? '선택한 접수를 찾을 수 없습니다' : query.trim() ? '검색 결과가 없습니다' : '이 단계에 처리할 접수가 없습니다'}</h2><p>{logistics ? `접수 ${selected}가 최신 목록에 없습니다. 다른 접수의 근거로 전환하지 않았습니다.` : query.trim() ? '점포명이나 접수번호를 다시 확인해 주세요.' : '왼쪽에서 다른 단계를 선택하거나 최신 접수를 불러올 수 있습니다.'}</p><div className="button-row">{logistics ? <button onClick={returnToWork}>접수 목록으로 돌아가기</button> : <>{query && <button onClick={() => setQuery('')}>검색 지우기</button>}<button onClick={() => { setQueue('all'); setQuery(''); }}>전체 접수 보기</button></>}<button onClick={() => void reload()} disabled={loading}>목록 새로고침</button></div></div></section>
          : view === 'desk' ? <Desk key={active.id} caseData={active} role={role} mode={mode} onMode={setMode} fallback={fallback} playbackRate={playbackRate} onPlaybackRateChange={setPlaybackRate} onUpdate={update} onSave={save} onView={navigate} onToast={setToast}/>
          : view === 'center' ? <Center key={active.id} role={role} mode={mode} fallback={fallback} caseData={active} onUpdate={update} onSave={save} onToast={setToast} onView={navigate}/>
          : view === 'owner' ? <Owner cases={cases} selected={selected} onSelect={setSelected} onCreated={c => { update(c); setSelected(c.id); setToast(`${c.id} 접수가 등록되었습니다.`); }} onToast={setToast} onDesk={() => navigate('desk')} fallback={fallback}/>
          : (view === 'wms' || view === 'tms') ? <section id="selected-work" tabIndex={-1} className="console-pane console-thread console-evidence" data-case-id={active.id} data-work-role={role} data-work-view={view} aria-label={`물류 기록 확인 · ${active.title}`}><div className="console-scroll"><LogisticsScene key={`${view}:${active.id}`} kind={view} caseData={active} backLabel={role === 'center' ? '센터 업무로 돌아가기' : '상담으로 돌아가기'} readOnly={!isEvidenceEditable(active, role)} onBack={returnToWork} onLinkEvidence={async (id: string) => { setToast(''); if (!isEvidenceEditable(active, role)) throw new Error('센터에 전달된 접수 또는 센터 열람 화면에서는 근거를 변경할 수 없습니다.'); const selectedEvidence = Array.from(new Set([...(active.selectedEvidence || []), id])); const saved = await save(active.id, { expectedRevision: active.revision, selectedEvidence }); acceptOwnEvidenceSave(active, saved, selectedEvidence); setToast('확인한 기록을 접수 건에 연결했습니다.'); }}/></div></section> : null}
      </div>}
      <footer className="page-footer"><span>AI-GO 무엇이든 물어보살</span><span>전화·점포·물류 데이터는 시연용 합성 데이터입니다. 실제 고객 통화가 아닙니다.</span></footer>
    </main>
  </div>;
}

type QueueSort = { key: 'store' | 'type' | 'channel' | 'title' | 'status' | 'department'; ascending: boolean };
// 경영주는 처리 단계가 아니라 자기 문의가 어디까지 왔는지를 본다.
const ownerQueueLabels: Partial<Record<QueueId, string>> = { attention: '접수 확인 중', handed_off: '센터 처리 중', closed: '답변 완료', all: '전체' };
const ownerNext = (c: CaseData): string => c.status === 'closed' ? '답변이 도착했습니다' : c.reply ? '중간 답변이 있습니다' : ['handed_off', 'in_progress'].includes(c.status || '') ? '센터에서 확인 중입니다' : '접수를 확인하고 있습니다';

/** 좌측 큐 레일: 표 7열을 접기 쉬운 카드로 바꿔 목록과 작업을 한 화면에 둔다. */
function QueueRail({ role, cases, visibleCases, queue, onQueue, query, onQuery, sort, onSort, activeId, onSelect, onNewIntake }: {
  role: WorkRole; cases: CaseData[]; visibleCases: CaseData[]; queue: QueueId; onQueue: (id: QueueId) => void;
  query: string; onQuery: (value: string) => void; sort: QueueSort; onSort: (next: QueueSort) => void;
  activeId?: string; onSelect: (id: string) => void; onNewIntake?: () => void;
}) {
  const owner = role === 'owner';
  const label = (id: QueueId, fallback: string) => owner ? ownerQueueLabels[id] || fallback : fallback;
  return <aside id="work-queue" tabIndex={-1} className="console-pane console-queue" aria-label={owner ? '내 문의 목록' : `${roleNames[role]} 접수 목록`}>
    <header><h2>{owner ? '내 문의' : '처리할 접수'}</h2>{onNewIntake ? <button className="primary" onClick={onNewIntake}>새 접수</button> : <span className="small muted">{cases.length}건</span>}</header>
    <div className="queue-rail-tools">
      <div className="queue-filters" aria-label={owner ? '진행 상태' : '처리 상태'}>{queues(role).map(item => <button key={item.id} type="button" aria-pressed={queue === item.id} onClick={() => onQueue(item.id)} className={queue === item.id ? 'selected' : ''}>{label(item.id, item.label)}<span>{cases.filter(c => inQueue(c, role, item.id)).length}</span></button>)}</div>
      <label className="queue-search"><span className="sr-only">접수 검색</span><input type="search" placeholder="점포 이름이나 제목으로 찾기" value={query} onChange={e => onQuery(e.target.value)}/></label>
      <label className="queue-rail-sort">정렬<select value={sort.key} onChange={e => onSort({ key: e.target.value as QueueSort['key'], ascending: sort.ascending })}><option value="title">제목</option><option value="store">점포</option><option value="type">문의 유형</option><option value="status">상태</option>{!owner && <option value="department">담당 부서</option>}</select><button type="button" className="text-button" aria-label={sort.ascending ? '내림차순으로 바꾸기' : '오름차순으로 바꾸기'} onClick={() => onSort({ key: sort.key, ascending: !sort.ascending })}>{sort.ascending ? '↑' : '↓'}</button></label>
    </div>
    <p className="queue-rail-count" role="status">{label(queue, queues(role).find(item => item.id === queue)?.label || '전체')} {visibleCases.length}건</p>
    <div className="console-scroll">
      {visibleCases.length ? <div className="queue-rail">{visibleCases.map(c => <button key={c.id} type="button" className="queue-card" data-case-id={c.id} aria-pressed={activeId === c.id} aria-label={`${c.title} 접수 열기`} onClick={() => onSelect(c.id)}>
        <span className="queue-card-top"><span className="badge neutral">{c.type === 'missing' ? '안 왔어요' : '다르게 왔어요'}</span><span className="queue-card-store">{c.store?.name || c.store?.id}</span><span>{c.channel === 'voice' ? '전화' : '웹'}</span></span>
        <strong className="queue-card-title">{c.title}</strong>
        <span className="queue-card-foot"><Status status={c.status}/><span className="queue-card-next">{owner ? ownerNext(c) : nextAction(c, role)}</span></span>
      </button>)}</div> : <p className="queue-rail-empty">{query.trim() ? '찾는 접수가 없습니다.' : '이 단계에 접수가 없습니다.'}</p>}
    </div>
  </aside>;
}

function LogisticsScene({ kind, ...props }: { kind: 'wms' | 'tms'; caseData: CaseData; onBack: () => void; backLabel?: string; readOnly?: boolean; onLinkEvidence: (id: string) => Promise<void> }) {
  return kind === 'wms' ? <WmsScene {...props}/> : <TmsScene {...props}/>;
}

type DeskDraft = { analysis?: Analysis; transcript: CaseData['transcript']; resultMode?: Mode; form: Intake; formRevision?: number; department: string; edited: boolean; confirmed: boolean; question: string; uncertain?: Record<string, unknown>; operation?: string };
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

function Desk({ caseData: c, role, mode, onMode, fallback, playbackRate, onPlaybackRateChange, onUpdate, onSave, onView, onToast }: { caseData: CaseData; role: WorkRole; mode: Mode; onMode: (value: Mode) => void; fallback: boolean; playbackRate: number; onPlaybackRateChange: (rate: number) => void; onUpdate: (c: CaseData) => void; onSave: (id: string, p: Record<string, unknown>) => Promise<CaseData>; onView: (v: View) => void; onToast: (s: string) => void }) {
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
  const [analysisFailureCode, setAnalysisFailureCode] = useState('');
  const [recovery, setRecovery] = useState<CaseData | null>(null);
  const stale = formRevision !== c.revision;
  const analysisInFlight = useRef(false);
  const mounted = useRef(false);
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);
  const intakeLocked = ['handed_off', 'in_progress', 'closed'].includes(c.status || '');
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
    setBusy('analyze'); setAnalysisFailure(''); setAnalysisFailureCode('');
    try {
      const data = await request<AnalyzeResult>(`/api/cases/${c.id}/analyze`, 'POST', { mode });
      // The draft store and the case list live outside this component. A counselor who
      // opens a logistics record while the analysis runs unmounts the desk, so guarding
      // on mount here dropped a result the server had already saved.
      draft.replace({ analysis: data.analysis, transcript: data.transcript || [], resultMode: data.mode, form: normalizeIntake(data.analysis.fields), formRevision: data.revision, department: data.analysis.department?.id || '', edited: false, confirmed: false, question: '' }, true);
      onUpdate({ ...c, revision: data.revision, status: 'review', reviewConfirmed: false, intake: normalizeIntake(data.analysis.fields), departmentId: data.analysis.department?.id || '', analysis: data.analysis, transcript: data.transcript, analysisMode: data.mode });
      onToast(data.mode === 'demo-live' ? '실제 AI 전사·정제가 완료되었습니다. 접수 정보를 확인해 주세요.' : '저장된 분석 결과를 불러왔습니다. 실제 AI 호출은 하지 않았습니다.');
    } catch (e) { if (mounted.current) { setAnalysisFailure(errorText(e)); setAnalysisFailureCode(e instanceof ApiError && e.code ? e.code : ''); } } finally { analysisInFlight.current = false; setBusy(''); }
  };
  const persist = async (transfer = false) => {
    if (busy || stale || uncertain || recovery || intakeLocked || fallback) return;
    if (transfer && !canTransfer) return;
    setBusy(transfer ? 'transfer' : 'save'); setError('');
    const nextRequest = question.trim() ? `${form.request}\n\n추가 확인 질문: ${question.trim()}` : form.request;
    const payload = { expectedRevision: formRevision, intake: { ...form, request: nextRequest, quantity: form.quantity === '' || form.quantity === null ? null : Number(form.quantity) }, departmentId: department || null, reviewConfirmed: confirmed, status: transfer ? 'handed_off' : 'review' };
    try {
      const saved = await onSave(c.id, payload);
      draft.replace({ ...deskDraft(saved), edited }, true);
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
  const withheldCount = selectedEvidence.length - visibleEvidenceCount;
  const channelLabel = c.channel === 'voice' ? '전화로 접수' : '웹으로 접수';
  return <>
    <section id="selected-work" tabIndex={-1} className="console-pane console-thread" data-case-id={c.id} data-work-role={role} data-work-view="desk" aria-label={`접수 처리 · ${c.title}`}>
      <div className="thread-head">
        <div className="thread-head-top"><span className="badge neutral">{c.type === 'missing' ? '상품이 안 왔어요' : '다른 상품이 왔어요'}</span><Status status={c.status}/><span>{c.store?.name || c.store?.id}</span><span>{channelLabel}</span></div>
        <h2>{c.title}</h2>
      </div>
      <div className="console-scroll"><div className="thread-body">
        {error && <div className="notice danger" role="alert"><span>{error}</span><button className="text-button" onClick={() => setError('')}>닫기</button></div>}
        {(uncertain || stale) && <div className="notice warning" role="status"><div><strong>{uncertain ? '저장됐는지 확인이 필요합니다' : '서버의 접수 내용이 바뀌었습니다'}</strong><p>{uncertain ? '응답을 받지 못했어도 저장됐을 수 있습니다. 지금 쓴 내용은 그대로 두고 서버부터 확인합니다.' : '지금 쓴 내용은 그대로 있습니다. 서버 내용과 맞춰 본 뒤 다시 저장해 주세요.'}</p></div><button disabled={!!busy || fallback} onClick={() => void inspectLatest()}>{uncertain ? '저장 여부 확인' : '서버 내용 보기'}</button></div>}
        {recovery && <Recovery current={recovery} busy={!!busy} rows={[{ label: '접수 정보', local: [form.storeId, form.subject, `${form.quantity ?? ''} ${form.unit || ''}`, form.request, question].filter(Boolean).join('\n'), server: [recovery.intake?.storeId, recovery.intake?.subject, `${recovery.intake?.quantity ?? ''} ${recovery.intake?.unit || ''}`, recovery.intake?.request].filter(Boolean).join('\n') }, { label: '전달 부서 · 확인', local: `${departmentName(department, analysis?.department)} · ${confirmed ? '확인함' : '확인 전'}`, server: `${departmentName(recovery.departmentId, recovery.analysis?.department)} · ${recovery.reviewConfirmed ? '확인함' : '확인 전'}` }]} onUseServer={() => { draft.replace(deskDraft(recovery), true); setRecovery(null); setError(''); }} onKeepDraft={() => { draft.replace({ ...draft.value, formRevision: recovery.revision, confirmed: false, edited: true, uncertain: undefined }); setRecovery(null); setError(''); }}/>}

        <article className="thread-entry from-owner">
          <span className="thread-avatar" aria-hidden="true">점</span>
          <div className="thread-main">
            <div className="thread-meta"><strong>{c.store?.name || '경영주'}</strong><span>{channelLabel}</span>{c.asOf && <span>{c.asOf.replace('T', ' ').slice(0, 16)}</span>}</div>
            <CallReview
              workStage="source"
              caseData={{ ...c, transcript, analysis, intake: form, reviewConfirmed: confirmed, analysisMode: resultMode }}
              disabled={intakeLocked || !!busy}
              playbackRate={playbackRate}
              onPlaybackRateChange={onPlaybackRateChange}
              onPlaybackEnded={() => setCompletedAudioSource(audioSource)}
              transcriptMode={resultMode ?? (!analysis ? 'replay' : undefined)}
              analysisState={busy === 'analyze' ? 'loading' : 'idle'}
            />
          </div>
        </article>

        <article className="thread-entry from-ai">
          <span className="thread-avatar" aria-hidden="true">AI</span>
          <div className="thread-main">
            <div className="thread-meta"><strong>AI가 정리한 접수</strong>{resultMode && <span className={`badge ${resultMode === 'demo-live' ? 'success' : 'info'}`}>{resultMode === 'demo-live' ? '실제 AI' : '저장 결과 재생'}</span>}</div>
            {analysisFailure && <div className="notice danger" role="alert">
              <div><strong>정리하지 못했습니다</strong><p>{analysisFailure}</p></div>
              {analysisFailureCode === 'REPLAY_NOT_AVAILABLE' && mode === 'replay'
                ? <button onClick={() => { onMode('demo-live'); setAnalysisFailure(''); setAnalysisFailureCode(''); }}>실제 AI 분석으로 바꾸기</button>
                : <button disabled={analyzeBlocked} onClick={() => void analyze()}>다시 시도</button>}
            </div>}
            <div className="thread-card">
              <div className="thread-actions"><button className={analysis ? undefined : 'primary'} disabled={analyzeBlocked} onClick={() => void analyze()}>{busy === 'analyze' ? '정리하는 중…' : analysis ? '다시 정리하기' : 'AI로 정리하기'}</button><span className="small muted">{mode === 'demo-live' ? '실제 AI를 호출합니다. 사용료가 듭니다.' : '미리 만들어 둔 사례만 불러옵니다. 새로 접수한 문의는 실제 AI 분석이 필요합니다.'}</span></div>
              {analysis ? <p className="thread-quote">{analysis.summary}</p>
                : <p className="thread-note">{c.channel === 'voice' ? '통화 내용을 듣고 점포·상품·수량·요청사항으로 정리합니다. 통화를 끝까지 듣지 않아도 되고, 아래에서 직접 적으셔도 됩니다.' : '문의 원문을 점포·상품·수량·요청사항으로 정리합니다. 아래에서 직접 적으셔도 됩니다.'}</p>}
            </div>
            <div id="intake-editor" tabIndex={-1} className="thread-card">
              <fieldset disabled={!!busy || !!uncertain || intakeLocked}>
                <div className="form-grid">
                  <label>점포 코드 <span className="required">필수</span><input value={form.storeId || ''} aria-label="점포 코드 필수" aria-describedby={analysis ? 'proposal-storeId' : undefined} onChange={e => field('storeId', e.target.value)} placeholder="예: GS0001"/>{analysis && <FieldSuggestion id="proposal-storeId" value={analysis.fields?.storeId} current={form.storeId}/>}</label>
                  <label>어떤 상품인가요 <span className="required">필수</span><input value={form.subject || ''} aria-label="어떤 상품인가요 필수" aria-describedby={analysis ? 'proposal-subject' : undefined} onChange={e => field('subject', e.target.value)} placeholder="상품 이름이나 문의 대상"/>{analysis && <FieldSuggestion id="proposal-subject" value={analysis.fields?.subject} current={form.subject}/>}</label>
                  <label>받은 수량<input type="number" min="0" value={form.quantity ?? ''} aria-label="받은 수량" aria-describedby={analysis ? 'proposal-quantity' : undefined} onChange={e => field('quantity', e.target.value)} placeholder="모르면 비워 두세요"/>{analysis && <FieldSuggestion id="proposal-quantity" value={analysis.fields?.quantity} current={form.quantity}/>}</label>
                  <label>단위<input value={form.unit || ''} aria-label="단위" aria-describedby={analysis ? 'proposal-unit' : undefined} onChange={e => field('unit', e.target.value)} placeholder="개 / 박스"/>{analysis && <FieldSuggestion id="proposal-unit" value={analysis.fields?.unit} current={form.unit}/>}</label>
                  <label className="full">점포가 바라는 것<textarea value={form.request || ''} aria-label="점포가 바라는 것" aria-describedby={analysis ? 'proposal-request' : undefined} onChange={e => field('request', e.target.value)} placeholder="점포가 요청한 내용" rows={3}/>{analysis && <FieldSuggestion id="proposal-request" value={analysis.fields?.request} current={form.request}/>}</label>
                </div>
                <p className="thread-note">받은 수량은 점포가 말한 값입니다. 주문·출고 수량으로 채우거나 박스를 낱개로 바꾸지 않습니다.</p>
                {!!analysis?.issues?.length && <div className="issue-list">{analysis.issues.map((issue, i) => <div className="issue" key={i}><span className="badge warning">확인 필요</span><div><strong>{issue.message}</strong>{issue.evidence && <p>원문: {issue.evidence}</p>}</div></div>)}</div>}
                <label className="review-check"><input type="checkbox" checked={confirmed} onChange={e => setConfirmed(e.target.checked)}/><span>원문과 맞는지 확인했습니다. 고칠 내용이 없으면 그대로 체크하셔도 됩니다.</span></label>
                {!edited && <p className="thread-note">한 번 확인하거나 고친 뒤 체크해 주세요. 모르는 값은 비워 두셔도 됩니다.</p>}
              </fieldset>
            </div>
            {!!analysis?.questions?.length && <div className="thread-card">
              <div className="thread-meta"><strong>점포에 더 물어볼 것</strong><span>{analysis.questions.length}개</span></div>
              <div className="questions">{analysis.questions.map((q, i) => <button key={i} className="question" onClick={() => setQuestion(q)}><span>{String(i + 1).padStart(2, '0')}</span>{q}<span aria-hidden="true">＋</span></button>)}<label className="full">직접 적기<textarea rows={2} value={question} onChange={e => setQuestion(e.target.value)} placeholder="눌러서 넣거나 직접 적어 주세요."/></label></div>
            </div>}
          </div>
        </article>

        <article className="thread-entry">
          <span className="thread-avatar" aria-hidden="true">기</span>
          <div className="thread-main">
            <div className="thread-meta"><strong>확인한 기록</strong><span>{visibleEvidenceCount}건 연결{withheldCount > 0 ? ` · ${withheldCount}건 보류` : ''}</span></div>
            <div className="thread-card">
              {selectedEvidence.length ? <ul className="evidence-chips">{selectedEvidence.map(({ id, record, withheld }) => <li key={id}><span className={`evidence-chip ${withheld ? 'withheld' : 'confirmed'}`}>{withheld ? `${id} · 확인 필요` : evidenceText(record?.label, id)}</span></li>)}</ul>
                : <p className="thread-note">아직 연결한 기록이 없습니다. 아래에서 센터 작업이나 배송 기록을 열어 이 문의에 필요한 기록을 연결해 주세요.</p>}
              <div className="thread-actions"><button onClick={() => onView('wms')}>센터 작업 기록 보기 <Arrow/></button><button onClick={() => onView('tms')}>배송 기록 보기 <Arrow/></button></div>
              {!!selectedEvidence.length && <details className="evidence-detail"><summary>연결한 기록 자세히</summary>
                <p className="thread-note">접수 {c.id} · 접수 기준 {evidenceDate(c.asOf)}</p>
                <ul className="desk-evidence-grid">{selectedEvidence.map(({ id, record, metadata, observedAt, sourceAsOf, withheld, synthetic }) => <li key={id}>
                  <article className={`desk-evidence-card${withheld ? ' desk-evidence-blocked' : ''}`} data-evidence-id={id} data-evidence-state={withheld ? 'withheld' : 'ready'}>
                    {withheld || !record ? <><div className="desk-evidence-card-header"><h4>{id}</h4><span className="badge warning">내용 표시 보류</span></div><p className="desk-evidence-note">{withheld}</p></> : <>
                      <div className="desk-evidence-card-header"><h4>{evidenceText(record.label, id)}</h4><div className="desk-evidence-badges"><span className="badge neutral">{evidenceText(metadata.sourceSystem ?? record.system, '출처 미등록')}</span><span className={`badge ${(metadata.recordStatus ?? record.status) === 'fact' ? 'info' : 'warning'}`}>{(metadata.recordStatus ?? record.status) === 'fact' ? '기록 확인' : '미확인'}</span>{synthetic && <span className="badge neutral">합성 자료</span>}</div></div>
                      <p className="desk-evidence-value">{evidenceText(record.value, '내용 미등록')}</p>
                      <dl className="desk-evidence-meta"><div><dt>어디서</dt><dd>{evidenceText(record.source, '출처 미등록')}</dd></div><div><dt>기록 시각</dt><dd>{evidenceDate(observedAt)}</dd></div><div><dt>조회 기준</dt><dd>{evidenceDate(sourceAsOf)}</dd></div></dl>
                    </>}
                  </article>
                </li>)}</ul>
              </details>}
            </div>
            {!!analysis?.unknowns?.length && <div className="thread-card">
              <div className="thread-meta"><strong>아직 모르는 것</strong><span>{analysis.unknowns.length}개</span></div>
              <ul className="clean-list">{analysis.unknowns.map((x, i) => <li key={i}>{x}</li>)}</ul>
              <p className="thread-note">기록이 있다고 해서 실제 도착이나 원인이 확정되지는 않습니다. 모르는 것은 모르는 채로 센터에 넘깁니다.</p>
            </div>}
          </div>
        </article>

        <article className="thread-entry from-center">
          <span className="thread-avatar" aria-hidden="true">센</span>
          <div className="thread-main">
            <div className="thread-meta"><strong>{intakeLocked ? '센터로 넘겼습니다' : '어느 부서로 넘길까요'}</strong></div>
            {intakeLocked ? <div className="thread-card">
              <p className="thread-note">{departmentName(c.departmentId, c.analysis?.department)}에서 확인하고 있습니다. 상담원이 확인한 내용은 그대로 보존됩니다.</p>
              <div className="thread-actions"><button className="primary" onClick={() => onView('center')}>센터 처리 현황 보기 <Arrow/></button></div>
              <NotificationStatus caseData={c} audience="workforce"/>
            </div> : <div className="thread-card accent">
              <label><span className="sr-only">전달 부서</span><select value={department} onChange={e => { setDepartment(e.target.value); setEdited(true); setConfirmed(false); }}><option value="">부서를 골라 주세요</option>{analysis?.department?.id && !['delivery', 'warehouse', 'cs'].includes(analysis.department.id) && <option value={analysis.department.id}>{analysis.department.name} · AI 추천</option>}<option value="warehouse">출고 운영</option><option value="delivery">배송 운영</option><option value="cs">고객 지원</option></select></label>
              {analysis?.department && <p className="thread-note">AI 추천 · {analysis.department.name}: {analysis.department.reason}</p>}
              {!canTransfer && <ul className="thread-blockers">{transferBlockers.map(reason => <li key={reason}>{reason}</li>)}</ul>}
              <div className="thread-actions">
                <button disabled={intakeLocked || !!busy || fallback || stale || !!uncertain || !!recovery} onClick={() => void persist()}>{busy === 'save' ? '저장 중…' : '여기까지 저장'}</button>
                <span className="spacer"/>
                <button className="primary" disabled={!canTransfer} onClick={() => void persist(true)}>{busy === 'transfer' ? '넘기는 중…' : '센터로 넘기기'} <span aria-hidden="true">→</span></button>
              </div>
            </div>}
          </div>
        </article>
      </div></div>
    </section>

    <aside className="console-pane console-context" aria-label="접수 정보">
      <header><h2>접수 정보</h2><Status status={c.status}/></header>
      <div className="console-scroll">
        <dl className="context-list">
          <div><dt>접수 번호</dt><dd>{c.id}</dd></div>
          <div><dt>점포</dt><dd>{c.store?.name} · {c.intake?.storeId || c.store?.id}</dd></div>
          <div><dt>문의 유형</dt><dd>{c.type === 'missing' ? '상품이 안 왔어요' : '다른 상품이 왔어요'}</dd></div>
          <div><dt>접수 방법</dt><dd>{c.channel === 'voice' ? '전화' : '웹'}</dd></div>
          <div><dt>접수 기준 시각</dt><dd>{c.asOf ? c.asOf.replace('T', ' ').slice(0, 16) : '시연 기준 데이터'}</dd></div>
          <div><dt>담당 부서</dt><dd>{departmentName(department || c.departmentId, analysis?.department)}</dd></div>
          <div><dt>사람 확인</dt><dd>{confirmed ? '확인함' : '아직'}</dd></div>
          <div><dt>연결한 기록</dt><dd>{visibleEvidenceCount}건{withheldCount > 0 ? ` (보류 ${withheldCount})` : ''}</dd></div>
        </dl>
        <div className="context-block">
          <h3>지금 할 일</h3>
          <p>{intakeLocked ? '센터 처리 현황을 확인하세요.' : !analysis ? 'AI로 접수 내용을 정리하세요.' : !canTransfer ? transferBlockers[0] : '센터로 넘길 준비가 됐습니다.'}</p>
        </div>
        <div className="context-block">
          <h3>기록 열어 보기</h3>
          <div className="context-actions"><button onClick={() => onView('wms')}>센터 작업 기록 (WMS)</button><button onClick={() => onView('tms')}>배송 기록 (TMS)</button></div>
        </div>
        <div className="context-block">
          <h3>이 화면의 자료</h3>
          <p className="thread-note">통화·점포·물류 기록은 모두 시연용으로 만든 합성 자료입니다. 실제 고객 통화나 실제 CCTV가 아니며, 기록을 확인했다는 것이 실제 도착이나 원인·책임을 확정한다는 뜻은 아닙니다.</p>
        </div>
      </div>
    </aside>
  </>;
}

function Owner({ cases, selected, onSelect, onCreated, onToast, onDesk, onCancel, fallback, counselorEntry = false }: { counselorEntry?: boolean; cases: CaseData[]; selected: string; onSelect: (s: string) => void; onCreated: (c: CaseData) => void; onToast: (s: string) => void; onDesk: () => void; onCancel?: () => void; fallback: boolean }) {
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
  const intakeForm = <form onSubmit={e => void submit(e)} className="owner-form">
    <fieldset className="owner-entry" disabled={busy || !!attempt}>
      <fieldset><legend>어떤 일인가요</legend><div className="type-choices">
        <label className={type === 'missing' ? 'chosen' : ''}><input type="radio" name="type" checked={type === 'missing'} onChange={() => editContext('type', 'missing')}/><strong>상품이 안 왔어요</strong><span>오기로 한 상품이 도착하지 않았어요</span></label>
        <label className={type === 'wrong' ? 'chosen' : ''}><input type="radio" name="type" checked={type === 'wrong'} onChange={() => editContext('type', 'wrong')}/><strong>다른 상품이 왔어요</strong><span>주문한 것과 다른 상품이 왔어요</span></label>
      </div></fieldset>
      <label>점포 코드<input required value={storeId} onChange={e => editContext('storeId', e.target.value)} placeholder="예: GS0001"/></label>
      <label>어떤 상품인가요<input required value={subject} onChange={e => editContext('subject', e.target.value)} placeholder="상품 이름을 적어 주세요"/></label>
      <label>자세한 내용<textarea required rows={5} value={text} onChange={e => setText(e.target.value)} placeholder="상품 이름, 수량, 도착 시간과 바라시는 것을 적어 주세요. 모르는 것은 비워 두셔도 됩니다."/></label>
      <details><summary>같은 건으로 이미 문의한 적이 있나요</summary>
        <label>이어서 볼 문의 고르기<select value={referenceCaseId || ''} onChange={e => chooseReference(e.target.value)} disabled={busy} aria-describedby="reference-case-help"><option value="">고르지 않음 · 새 문의</option>{referenceCases.map(item => <option key={item.id} value={item.id}>{item.id} · {referenceDate(item.asOf)} · {item.title}</option>)}</select></label>
        <p id="reference-case-help" className="thread-note">{referenceCaseId ? '같은 날짜·같은 배송 건인지 확인해 주세요. 점포나 상품을 바꾸면 연결이 풀립니다.' : '고르지 않으면 새 문의로 접수되고 지난 기록은 함께 가지 않습니다.'}</p>
      </details>
      {linkNotice && <p className="notice info compact" role="status">{linkNotice}</p>}
      <p className="thread-note">보내 주시면 상담원이 확인한 뒤 담당 센터로 전달합니다.</p>
    </fieldset>
    {error && <p className="notice danger" role="alert">{error}</p>}
    {attempt && <div className="notice warning recovery-attempt" role="status"><strong>보내진 건지 확인하고 있습니다</strong><p>쓰신 내용은 그대로 두었습니다. 확인이 끝날 때까지 같은 문의를 다시 보내지 않습니다.</p><div className="button-row"><button type="button" disabled={busy || fallback} onClick={() => void verifyAttempt()}>보내졌는지 확인</button>{attempt.retryAllowed && <button type="button" disabled={busy || fallback} onClick={() => void submit()}>같은 내용으로 다시 보내기</button>}</div></div>}
    <button className="primary wide" disabled={busy || fallback || !!attempt}>{busy ? '보내는 중…' : counselorEntry ? '등록하고 AI 정리로 가기' : '문의 보내기'} <span aria-hidden="true">→</span></button>
  </form>;

  if (counselorEntry) return <section id="selected-work" tabIndex={-1} className="console-pane console-thread" aria-label="새 접수 등록">
    <div className="thread-head"><div className="thread-head-top"><span className="badge neutral">새 접수</span></div><h2>점포 문의를 대신 등록합니다</h2></div>
    <div className="console-scroll"><div className="thread-body">
      <p className="thread-note">점포가 전화나 메신저로 알려준 내용을 그대로 적어 주세요. 등록하면 이 작업대에서 AI 정리와 이관을 이어서 할 수 있습니다.</p>
      <div className="thread-card">{intakeForm}</div>
      {onCancel && <div className="thread-actions"><button onClick={onCancel}>기존 접수로 돌아가기</button></div>}
    </div></div>
  </section>;

  const steps: { label: string; done: boolean }[] = [
    { label: '문의 접수', done: true },
    { label: '담당 센터 확인', done: ['handed_off', 'in_progress', 'closed'].includes(c?.status || '') },
    { label: '센터 답변', done: !!c?.reply },
  ];
  return <>
    <section id="selected-work" tabIndex={-1} className="console-pane console-thread" data-case-id={c?.id} data-work-role="owner" data-work-view="owner" aria-label={c ? `내 문의 · ${c.title}` : '내 문의'}>
      {c ? <>
        <div className="thread-head">
          <div className="thread-head-top"><span className="badge neutral">{c.type === 'missing' ? '상품이 안 왔어요' : '다른 상품이 왔어요'}</span><Status status={c.status}/><span>{c.store.name}</span></div>
          <h2>{c.title}</h2>
        </div>
        <div className="console-scroll"><div className="thread-body">
          <div className="owner-steps">{steps.map(step => <span key={step.label} className={step.done ? 'done' : ''}>{step.label}</span>)}</div>

          <article className="thread-entry from-owner">
            <span className="thread-avatar" aria-hidden="true">나</span>
            <div className="thread-main">
              <div className="thread-meta"><strong>내가 보낸 문의</strong><span>{c.channel === 'voice' ? '전화' : '웹'}</span></div>
              <p className="thread-quote">{c.sourceText}</p>
            </div>
          </article>

          <article className="thread-entry from-center">
            <span className="thread-avatar" aria-hidden="true">센</span>
            <div className="thread-main">
              <div className="thread-meta"><strong>센터 답변</strong>{c.reply && <span className="badge success">등록됨</span>}</div>
              {c.reply ? <div className="thread-card registered-reply">{c.replyTitle && <h3>{c.replyTitle}</h3>}<p>{c.reply}</p></div>
                : <div className="thread-card"><p className="thread-note">아직 답변이 등록되지 않았습니다. 확인이 끝나는 대로 이곳에 보여 드립니다.</p></div>}
            </div>
          </article>

          {!!c.pendingActions?.length && <article className="thread-entry">
            <span className="thread-avatar" aria-hidden="true">조</span>
            <div className="thread-main">
              <div className="thread-meta"><strong>진행 중인 일</strong><span>{c.pendingActions.length}건</span></div>
              <div className="thread-card"><ul className="clean-list">{c.pendingActions.map((a, i) => <li key={i}>{a}</li>)}</ul></div>
            </div>
          </article>}

          <NotificationStatus caseData={c} audience="owner"/>
          <div className="thread-actions"><button className="text-button" onClick={onDesk}>시연: 상담 작업대로 이동 <Arrow/></button></div>
        </div></div>
      </> : <div className="console-scroll"><div className="empty-state"><h2>아직 접수한 문의가 없습니다</h2><p>오른쪽에서 문의를 보내면 진행 상황을 여기서 확인할 수 있습니다.</p></div></div>}
    </section>

    <aside className="console-pane console-context" aria-label="새 문의 보내기">
      <header><h2>문의 보내기</h2></header>
      <div className="console-scroll"><div className="context-block">{intakeForm}</div></div>
    </aside>
  </>;
}

function Center({ caseData: c, role, onSave, onToast, onView, onUpdate, fallback, mode }: { role: WorkRole; mode: Mode; fallback: boolean; caseData: CaseData; onSave: (id: string, p: Record<string, unknown>) => Promise<CaseData>; onToast: (s: string) => void; onView: (v: View) => void; onUpdate: (c: CaseData) => void }) {
  type CenterDraft = { formRevision?: number; replyTitle?: string; reply: string; pending: string[]; action: string; uncertain?: Record<string, unknown>; operation?: boolean };
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
  // The center draft lives in a module-level store, so it keeps the revision it first saw.
  // A counselor who hands the case over afterwards would turn an untouched draft into a
  // false conflict and lock both reply buttons. Nothing was typed, so follow the server.
  useEffect(() => {
    if (formRevision !== c.revision && !draft.dirty && !recovery && !uncertain) draft.replace(initial(c), true);
  }, [c.revision]); // eslint-disable-line react-hooks/exhaustive-deps
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
      setGeneratedTitle(result.replyTitle); setGeneratedReply(result.replyDraft);
      onToast(result.mode === 'demo-live' ? 'AI 답변 초안을 생성했습니다. 검토 후 적용해 주세요.' : '저장된 답변 초안을 불러왔습니다. API 호출은 하지 않았습니다.');
    } catch (failure) { if (alive.current) setError(errorText(failure)); }
    finally { generatingRef.current = false; setBusy(false); if (alive.current) setGenerating(false); }
  };
  const replyReadiness = c.status === 'closed' ? '최종 회신이 등록되어 처리 완료된 접수입니다.' : fallback ? '예시 열람 중입니다. 서버에 연결한 뒤 회신을 저장할 수 있습니다.' : !received ? '상담원이 확인 후 센터로 전달해야 회신할 수 있습니다.' : busy ? '저장 처리 중입니다.' : uncertain ? '회신 저장 여부를 먼저 확인해 주세요.' : stale || recovery ? '최신 서버 내용과 회신 초안을 대조해 주세요.' : action.trim() ? '작성 중인 조치를 추가하거나 입력을 비워 주세요.' : !replyTitle.trim() ? '회신 제목을 입력해 주세요.' : !reply.trim() ? '경영주에게 안내할 회신을 작성해 주세요.' : pending.length ? `남은 조치 ${pending.length}건 · 중간 회신만 등록할 수 있습니다.` : '모든 조치가 끝났다면 최종 회신으로 처리 완료할 수 있습니다.';
  const submit = async (close: boolean) => {
    if (blocked || !replyTitle.trim() || !reply.trim() || (close && pending.length) || action.trim()) return;
    setBusy(true); setError('');
    const payload = { expectedRevision: formRevision, replyTitle: replyTitle.trim(), reply: reply.trim(), pendingActions: pending, status: close ? 'closed' : 'in_progress' };
    try {
      const saved = await onSave(c.id, payload);
      draft.replace(initial(saved), true);
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
  const linkedEvidence = (c.selectedEvidence || []).map(id => ({ id, label: c.evidence?.find(e => e.id === id)?.label || id }));
  return <>
    <section id="selected-work" tabIndex={-1} className="console-pane console-thread" data-case-id={c.id} data-work-role={role} data-work-view="center" aria-label={`센터 처리 · ${c.title}`}>
      <div className="thread-head">
        <div className="thread-head-top"><span className="badge neutral">{c.type === 'missing' ? '상품이 안 왔어요' : '다른 상품이 왔어요'}</span><Status status={c.status}/><span>{c.store.name}</span><span>{departmentName(c.departmentId, c.analysis?.department)}</span></div>
        <h2>{c.title}</h2>
      </div>
      <div className="console-scroll"><div className="thread-body">
        {!received && <div className="notice warning compact">아직 상담원이 확인 중인 접수입니다. 센터로 넘어와야 회신할 수 있습니다.</div>}
        {error && <div className="notice danger" role="alert">{error}</div>}
        {(uncertain || stale) && <div className="notice warning" role="status"><div><strong>{uncertain ? '회신이 저장됐는지 확인이 필요합니다' : '서버의 접수 내용이 바뀌었습니다'}</strong><p>지금 쓴 회신과 남은 조치는 그대로 있습니다. 서버 내용을 확인한 뒤 이어서 작성해 주세요.</p></div><button disabled={busy} onClick={() => void inspectLatest()}>{uncertain ? '저장 여부 확인' : '서버 내용 보기'}</button></div>}
        {recovery && <Recovery current={recovery} busy={busy} rows={[{ label: '회신 제목', local: replyTitle, server: recovery.replyTitle || '' }, { label: '회신', local: reply, server: recovery.reply || '' }, { label: '남은 조치', local: [...pending, ...(action ? [action + ' (추가 전)'] : [])].join('\n'), server: (recovery.pendingActions || []).join('\n') }]} onUseServer={() => { draft.replace(initial(recovery), true); setRecovery(null); setError(''); }} onKeepDraft={() => { draft.replace({ ...draft.value, formRevision: recovery.revision, uncertain: undefined }); setRecovery(null); setError(''); }}/>}

        <article className="thread-entry from-owner">
          <span className="thread-avatar" aria-hidden="true">점</span>
          <div className="thread-main">
            <div className="thread-meta"><strong>{c.store.name}</strong><span>{c.channel === 'voice' ? '전화로 접수' : '웹으로 접수'}</span></div>
            <p className="thread-quote">{c.sourceText}</p>
          </div>
        </article>

        <article className="thread-entry">
          <span className="thread-avatar" aria-hidden="true">상</span>
          <div className="thread-main">
            <div className="thread-meta"><strong>상담원이 정리해 넘긴 내용</strong>{c.reviewConfirmed && <span className="badge success">사람이 확인함</span>}</div>
            <div className="thread-card">
              <dl className="context-list">
                <div><dt>어떤 상품</dt><dd>{c.intake?.subject || '상담원 확인 전'}</dd></div>
                <div><dt>받은 수량</dt><dd>{c.intake?.quantity ?? '미확인'} {c.intake?.unit || ''}</dd></div>
                <div><dt>점포가 바라는 것</dt><dd>{c.intake?.request || '상담원 확인 전'}</dd></div>
              </dl>
              <div className="thread-meta"><strong>함께 넘어온 기록</strong><span>{linkedEvidence.length}건</span></div>
              {linkedEvidence.length ? <ul className="evidence-chips">{linkedEvidence.map(item => <li key={item.id}><span className="evidence-chip confirmed">{item.label}</span></li>)}</ul> : <p className="thread-note">연결된 기록이 없습니다. 아래에서 직접 확인해 주세요.</p>}
              <div className="thread-actions"><button onClick={() => onView('wms')}>센터 작업 기록 보기 <Arrow/></button><button onClick={() => onView('tms')}>배송 기록 보기 <Arrow/></button></div>
            </div>
          </div>
        </article>

        <article className="thread-entry from-ai">
          <span className="thread-avatar" aria-hidden="true">AI</span>
          <div className="thread-main">
            <div className="thread-meta"><strong>AI 답변 초안</strong><span className="badge warning">보내지 않음</span></div>
            <div className="thread-card">
              {generatedReply ? <div className="draft-reply">
                <h3>{generatedTitle}</h3>
                <p>{generatedReply}</p>
                <button onClick={() => { setReplyTitle(generatedTitle); setReply(generatedReply); setGeneratedReply(''); }}>제목·본문을 답변에 적용</button>
              </div> : <p className="thread-note">초안을 만들어도 저절로 보내지 않습니다. 담당자가 읽고 고친 뒤 아래에서 등록해야 경영주에게 보입니다.</p>}
              <div className="thread-actions">
                <button className="primary" disabled={blocked || generating} onClick={() => void generateReply()}>{generating ? 'AI 답변 생성 중…' : generatedReply ? '다시 생성' : 'AI 답변 초안 생성'}</button>
                <span className="small muted">{mode === 'demo-live' ? '실제 AI를 호출합니다' : '저장된 결과를 불러옵니다'}</span>
              </div>
              {c.analysis?.replyDraft && <details><summary>접수 때 만든 참고 초안</summary><p>{c.analysis.replyDraft}</p><button onClick={() => { setReplyTitle(suggestedTitle); setReply(c.analysis!.replyDraft); }}>이 초안 가져오기</button></details>}
            </div>
          </div>
        </article>

        <article className="thread-entry">
          <span className="thread-avatar" aria-hidden="true">조</span>
          <div className="thread-main">
            <div className="thread-meta"><strong>아직 진행 중인 조치</strong><span>{pending.length}건</span></div>
            <div id="center-actions" tabIndex={-1} className="thread-card">
              {pending.length ? pending.map((p, i) => <div className="pending-item" key={`${p}-${i}`}><span>{p}</span><button aria-label={`${p} 조치 완료`} onClick={() => setPending(old => old.filter((_, n) => n !== i))}>완료</button></div>) : <p className="thread-note">남은 조치가 없습니다. 조치를 남기면 문의는 처리 중으로 유지되고, 모두 끝내야 완료할 수 있습니다.</p>}
              <div className="inline-form"><input aria-label="남은 조치 내용" value={action} onChange={e => setAction(e.target.value)} placeholder="예: 기사 확인 후 도착 예정 시각 안내"/><button disabled={!action.trim()} onClick={() => { setPending(old => [...old, action.trim()]); setAction(''); }}>조치 추가</button></div>
            </div>
          </div>
        </article>

        <div id="center-save-result" aria-live="polite">{savedNotice && <div className="notice success"><strong>{savedNotice}</strong><p>{c.replyTitle || replyTitle}</p><button onClick={() => onView('owner')}>경영주 화면에서 보기 <Arrow/></button></div>}</div>
      </div></div>

      <div id="center-response" className="thread-dock">
        <fieldset disabled={!received || busy || !!uncertain || c.status === 'closed'}>
          <label className="reply-title-field">경영주에게 보낼 제목 <span className="required">필수</span><input aria-label="회신 제목" maxLength={160} value={replyTitle} onChange={e => setReplyTitle(e.target.value)} placeholder="예: 아침 배송 미도착 확인 안내"/></label>
          <label id="center-reply" tabIndex={-1}>답변 내용 <span className="required">필수</span><textarea rows={4} aria-label="경영주에게 등록할 회신" value={reply} onChange={e => setReply(e.target.value)} placeholder="확인한 내용과 앞으로 할 일을 적어 주세요. 확인되지 않은 도착 시각이나 원인은 단정하지 않습니다."/></label>
        </fieldset>
        <div className="thread-dock-row">
          <span className="small muted" role="status">{replyReadiness}</span>
          <span className="spacer"/>
          <button className={pending.length ? 'primary' : undefined} disabled={blocked || !replyTitle.trim() || !reply.trim() || !!action.trim()} onClick={() => void submit(false)}>중간 회신 등록</button>
          <button className={!pending.length ? 'primary' : undefined} disabled={blocked || !replyTitle.trim() || !reply.trim() || !!pending.length || !!action.trim()} onClick={() => void submit(true)}>{busy ? '등록 중…' : '최종 회신·처리 완료'}</button>
        </div>
      </div>
    </section>

    <aside className="console-pane console-context" aria-label="접수 정보">
      <header><h2>접수 정보</h2><Status status={c.status}/></header>
      <div className="console-scroll">
        <dl className="context-list">
          <div><dt>접수 번호</dt><dd>{c.id}</dd></div>
          <div><dt>점포</dt><dd>{c.store.name} · {c.intake?.storeId || c.store.id}</dd></div>
          <div><dt>문의 유형</dt><dd>{c.type === 'missing' ? '상품이 안 왔어요' : '다른 상품이 왔어요'}</dd></div>
          <div><dt>담당 부서</dt><dd>{departmentName(c.departmentId, c.analysis?.department)}</dd></div>
          <div><dt>상담원 확인</dt><dd>{c.reviewConfirmed ? '확인함' : '확인 전'}</dd></div>
          <div><dt>함께 온 기록</dt><dd>{linkedEvidence.length}건</dd></div>
          <div><dt>남은 조치</dt><dd>{pending.length}건</dd></div>
        </dl>
        <div className="context-block">
          <h3>지금 할 일</h3>
          <p>{replyReadiness}</p>
        </div>
        <div className="context-block">
          <h3>기록 열어 보기</h3>
          <div className="context-actions"><button onClick={() => onView('wms')}>센터 작업 기록 (WMS)</button><button onClick={() => onView('tms')}>배송 기록 (TMS)</button><button className="text-button" onClick={() => onView('owner')}>경영주 화면 보기</button></div>
        </div>
        <div className="context-block">
          <NotificationStatus caseData={c} audience="workforce"/>
        </div>
        <div className="context-block">
          <h3>이 화면의 자료</h3>
          <p className="thread-note">등록한 답변만 경영주에게 보입니다. AI 초안은 저절로 보내지지 않습니다. 물류 기록은 시연용 합성 자료이며, 기록 확인이 실제 도착이나 원인·책임을 확정하지는 않습니다.</p>
        </div>
      </div>
    </aside>
  </>;
}
