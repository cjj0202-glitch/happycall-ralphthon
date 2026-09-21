'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import CallReview from '@/components/CallReview';
import WmsScene from '@/components/WmsScene';
import TmsScene from '@/components/TmsScene';
import { ApiError, request } from '@/lib/api';
import { useHasUnsavedDrafts, useSessionDraft } from '@/lib/drafts';
import type { Analysis, AnalyzeResult, CaseData, CaseStatus, Intake, Mode, View } from '@/lib/types';

const labels: Record<CaseStatus, string> = { draft: '접수 대기', review: '상담원 확인', handed_off: '센터 전달', in_progress: '처리 중', closed: '처리 완료' };
const tabs: { id: View; label: string }[] = [{ id: 'desk', label: '상담 작업대' }, { id: 'owner', label: '경영주 접수' }, { id: 'center', label: '센터 회신' }, { id: 'wms', label: 'WMS 작업 확인' }, { id: 'tms', label: 'TMS 배송 확인' }];
const emptyIntake: Intake = { storeId: '', subject: '', quantity: '', unit: '', request: '' };
const normalizeIntake = (input?: Partial<Intake>): Intake => ({ storeId: input?.storeId || '', subject: input?.subject || '', quantity: input?.quantity ?? '', unit: input?.unit || '', request: input?.request || '' });
const errorText = (e: unknown) => e instanceof Error ? e.message : '처리 중 문제가 발생했습니다. 다시 시도해 주세요.';
function Status({ status = 'draft' }: { status?: CaseStatus }) { return <span className={`badge ${status === 'closed' ? 'success' : status === 'draft' ? 'neutral' : 'info'}`}>{labels[status] || status}</span>; }
function Arrow() { return <span aria-hidden="true">↗</span>; }

export default function Home() {
  const [view, setView] = useState<View>('desk');
  const [cases, setCases] = useState<CaseData[]>([]);
  const [selected, setSelected] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [toast, setToast] = useState('');
  const [fallback, setFallback] = useState(false);
  const [mode, setMode] = useState<Mode>('replay');
  const [lastSync, setLastSync] = useState<string>('');
  const hasDrafts = useHasUnsavedDrafts();
  const reloadInFlight = useRef(false);
  const active = cases.find(c => c.id === selected) || cases[0];

  const reload = useCallback(async () => {
    if (reloadInFlight.current) return;
    reloadInFlight.current = true;
    setLoading(true); setError('');
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
    if (fallback) throw new Error('예시 열람 모드에서는 저장할 수 없습니다. 서버에 다시 연결해 주세요.');
    if (typeof payload.expectedRevision !== 'number') throw new Error('접수 버전을 확인할 수 없습니다. 화면을 새로 연 뒤 변경 내용을 확인해 주세요.');
    const updated = await request<CaseData>(`/api/cases/${id}`, 'PATCH', payload, view === 'center' ? 'center' : 'counselor'); update(updated); return updated;
  };
  const loadExample = async () => {
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
      <div className="header-inner"><a className="brand" href="#" onClick={e => { e.preventDefault(); setView('desk'); }} aria-label="HappyCall OneFlow 홈"><span className="brand-mark" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none"><path d="M5 6v12M19 6v12M5 12h14M10 6v12" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"/></svg></span><span>HappyCall <strong>OneFlow</strong></span></a><div className="header-meta"><span className="badge neutral">합성 데이터 시연</span><span className="user-avatar" aria-label="상담원 김하나">김</span><span className="user-name">김하나 상담원</span></div></div>
      <nav className="nav-inner" aria-label="주 메뉴">{tabs.map(tab => <button key={tab.id} onClick={() => setView(tab.id)} className={view === tab.id ? 'nav-tab selected' : 'nav-tab'} aria-current={view === tab.id ? 'page' : undefined}>{tab.label}</button>)}<span className="nav-note">접수부터 회신까지, 한 흐름으로</span></nav>
    </header>
    <main id="main" className="main-content">
      <div className="page-heading"><div><p className="eyebrow">HAPPYCALL WORKSPACE</p><h1>{tabs.find(t => t.id === view)?.label}</h1><p className="muted">{view === 'desk' ? '흩어진 문의와 물류 근거를 모아, 정확한 접수로 연결합니다.' : view === 'owner' ? '불편 사항을 접수하고 센터의 회신을 확인하세요.' : view === 'center' ? '상담원이 확인한 내용과 근거를 이어받아 회신합니다.' : '선택한 문의와 연결된 합성 물류 기록을 확인합니다.'}</p></div><div className="mode-control"><label htmlFor="analysis-mode">분석 방식</label><select id="analysis-mode" value={mode} onChange={e => setMode(e.target.value as Mode)}><option value="replay">저장 결과 재생 · API 호출 없음</option><option value="demo-live">실제 AI 분석 · API 사용</option></select></div></div>
      {error && <div className="notice danger" role="alert"><div><strong>서버 연결 확인이 필요합니다</strong><p>{error}</p>{fallback && <p>현재 예시 열람 중입니다. 변경 사항은 저장되지 않습니다.</p>}</div><div className="button-row"><button onClick={() => void reload()} disabled={loading}>다시 연결</button>{!fallback && <button onClick={() => void loadExample()}>합성 예시 열람</button>}</div></div>}
      {toast && <div className="notice success" role="status">{toast}</div>}
      <div className="workspace-sync"><div><strong>{hasDrafts ? '저장하지 않은 초안이 있습니다' : '접수 현황'}</strong><p className="small muted">{hasDrafts ? '메뉴를 이동해도 초안을 유지합니다. 이 페이지를 닫거나 새로고침하면 사라질 수 있습니다.' : '다른 담당자가 등록한 내용은 목록 새로고침으로 확인하세요.'}</p><span className="small muted" role="status">최종 서버 확인 {lastSync || '확인 중'}</span></div><button onClick={() => void reload()} disabled={loading}>{loading ? '최신 내용 확인 중…' : '목록 새로고침'}</button></div>
      {loading && !cases.length ? <div className="empty-state" role="status"><div className="spinner"/><h2>접수 건을 불러오고 있습니다</h2><p>서버의 최신 처리 상태를 확인합니다.</p></div> : <>
        {view !== 'owner' && cases.length > 0 && <section className="case-selector" aria-label="문의 선택"><div className="section-label"><span className="small-kicker">TODAY&apos;S CASES</span><strong>접수 목록 <span className="count">{cases.length}</span></strong></div><div className="case-buttons">{cases.map(c => <button key={c.id} className={`case-button ${active?.id === c.id ? 'active' : ''}`} onClick={() => setSelected(c.id)} aria-pressed={active?.id === c.id}><span className="case-icon" aria-hidden="true">{c.channel === 'voice' ? <svg viewBox="0 0 24 24" fill="none"><path d="M7 3h3l1 5-2 1c1 3 3 5 6 6l1-2 5 1v3c0 3-3 4-6 3C8 18 3 13 3 6c0-2 2-3 4-3Z" stroke="currentColor" strokeWidth="1.6"/></svg> : <svg viewBox="0 0 24 24" fill="none"><path d="M4 4h16v12H9l-5 4V4Z" stroke="currentColor" strokeWidth="1.6"/></svg>}</span><span className="case-copy"><strong>{c.title}</strong><span>{c.store?.name || c.store?.id} · {c.id}</span></span><Status status={c.status}/></button>)}</div></section>}
        {view === 'owner' ? <Owner cases={cases} selected={selected} onSelect={setSelected} onCreated={c => { update(c); setSelected(c.id); setToast(`${c.id} 접수가 등록되었습니다.`); }} onDesk={() => setView('desk')} fallback={fallback}/> : !active ? <div className="empty-state"><h2>접수된 문의가 없습니다</h2><p>경영주 접수에서 첫 문의를 등록해 주세요.</p><button className="primary" onClick={() => setView('owner')}>문의 접수하기</button></div> : view === 'desk' ? <Desk key={active.id} caseData={active} mode={mode} fallback={fallback} onUpdate={update} onSave={save} onView={setView} onToast={setToast}/> : view === 'center' ? <Center key={active.id} caseData={active} onUpdate={update} onSave={save} onToast={setToast} onView={setView}/> : <LogisticsScene key={`${view}:${active.id}`} kind={view} caseData={active} onBack={() => setView('desk')} onLinkEvidence={async (id: string) => { await save(active.id, { expectedRevision: active.revision, selectedEvidence: Array.from(new Set([...(active.selectedEvidence || []), id])) }); setToast('물류 근거를 접수 건에 연결했습니다.'); }}/>}
      </>}
      <footer className="page-footer"><span>HappyCall OneFlow</span><span>전화·점포·물류 데이터는 시연용 합성 데이터입니다. 실제 고객 통화가 아닙니다.</span></footer>
    </main>
  </div>;
}

function LogisticsScene({ kind, ...props }: { kind: 'wms' | 'tms'; caseData: CaseData; onBack: () => void; onLinkEvidence: (id: string) => Promise<void> }) {
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

function Desk({ caseData: c, mode, fallback, onUpdate, onSave, onView, onToast }: { caseData: CaseData; mode: Mode; fallback: boolean; onUpdate: (c: CaseData) => void; onSave: (id: string, p: Record<string, unknown>) => Promise<CaseData>; onView: (v: View) => void; onToast: (s: string) => void }) {
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
  const canTransfer = !intakeLocked && !stale && !uncertain && !recovery && edited && confirmed && !!(form.storeId || '').trim() && !!(form.subject || '').trim() && !!department && !busy && !fallback;
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
    if (fallback) { setAnalysisFailure('분석은 서버에 연결한 후 사용할 수 있습니다.'); return; }
    if (c.channel === 'voice' && !audioEnded) { setAnalysisFailure('통화를 처음부터 끝까지 재생한 뒤 분석해 주세요.'); return; }
    analysisInFlight.current = true;
    setBusy('analyze'); setAnalysisFailure('');
    try {
      const data = await request<AnalyzeResult>(`/api/cases/${c.id}/analyze`, 'POST', { mode });
      if (!mounted.current) return;
      draft.replace({ analysis: data.analysis, transcript: data.transcript || [], resultMode: data.mode, form: normalizeIntake(data.analysis.fields), formRevision: data.revision, department: data.analysis.department?.id || '', edited: false, confirmed: false, question: '' }, true);
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
      draft.replace({ ...deskDraft(saved), edited }, true);
      onToast(transfer ? '확인한 접수 내용과 근거를 센터에 전달했습니다.' : '상담원이 편집한 접수 정보를 저장했습니다.');
      if (transfer && mounted.current) onView('center');
    } catch (e) { setError(errorText(e)); if (e instanceof ApiError && e.uncertain) draft.set('uncertain', payload); if (e instanceof ApiError && e.status === 409) await inspectLatest(); } finally { setBusy(''); }
  };
  const inspectLatest = async () => {
    setBusy('verify'); setError('');
    try {
      const latest = await request<CaseData>(`/api/cases/${c.id}`);
      onUpdate(latest);
      if (uncertain && sameMutation(latest, uncertain)) { draft.replace(deskDraft(latest), true); setRecovery(null); onToast('서버에 요청한 접수 내용이 저장되어 있음을 확인했습니다.'); }
      else setRecovery(latest);
    } catch (e) { setError(errorText(e)); } finally { setBusy(''); }
  };
  return <div className="desk">
    <div className="case-heading"><div><div className="button-row"><span className="badge neutral">{c.type === 'missing' ? '미도착 문의' : '오출고 문의'}</span><span className="muted small">{c.id}</span></div><h2>{c.title}</h2></div><div className="case-heading-meta"><Status status={c.status}/><span className="muted small">{c.asOf ? `기준 ${c.asOf.replace('T', ' ').slice(0, 16)}` : '시연 기준 데이터'}</span></div></div>
    <div className="workflow" aria-label="처리 흐름"><span className="current"><b>1</b> 문의 듣기</span><span className={analysis ? 'current' : ''}><b>2</b> AI 정제·사람 확인</span><span className={['handed_off', 'in_progress', 'closed'].includes(c.status || '') ? 'current' : ''}><b>3</b> 센터 전달·회신</span></div>
    {error && <div className="notice danger" role="alert">{error}<button className="text-button" onClick={() => setError('')}>닫기</button></div>}
    {(uncertain || stale) && <div className="notice warning" role="status"><div><strong>{uncertain ? '저장 여부 확인이 필요합니다' : '서버의 접수 내용이 변경되었습니다'}</strong><p>{uncertain ? '응답을 받지 못했어도 저장되었을 수 있습니다. 초안은 보존하고, 먼저 서버 내용을 확인합니다.' : '현재 초안은 유지했습니다. 최신 내용과 대조한 후 다시 저장해 주세요.'}</p></div><button disabled={!!busy || fallback} onClick={() => void inspectLatest()}>{uncertain ? '저장 여부 확인' : '최신 내용 대조'}</button></div>}
    {recovery && <Recovery current={recovery} busy={!!busy} rows={[{ label: '접수 정보', local: [form.storeId, form.subject, `${form.quantity ?? ''} ${form.unit || ''}`, form.request, question].filter(Boolean).join('\n'), server: [recovery.intake?.storeId, recovery.intake?.subject, `${recovery.intake?.quantity ?? ''} ${recovery.intake?.unit || ''}`, recovery.intake?.request].filter(Boolean).join('\n') }, { label: '전달 부서 · 확인', local: `${department || '미선택'} · ${confirmed ? '확인함' : '확인 전'}`, server: `${recovery.departmentId || '미선택'} · ${recovery.reviewConfirmed ? '확인함' : '확인 전'}` }]} onUseServer={() => { draft.replace(deskDraft(recovery), true); setRecovery(null); setError(''); }} onKeepDraft={() => { draft.replace({ ...draft.value, formRevision: recovery.revision, confirmed: false, edited: true, uncertain: undefined }); setRecovery(null); setError(''); }}/>}
    {intakeLocked && <div className="notice info compact">센터로 전달된 접수입니다. 상담원이 확인한 내용은 보존되며 이후 회신은 센터 회신에서 등록합니다.<button onClick={() => onView('center')}>센터 회신 보기</button></div>}
    <div className="integrated-review">
      <CallReview
        caseData={{ ...c, transcript, analysis, intake: form, reviewConfirmed: confirmed, analysisMode: resultMode }}
        disabled={intakeLocked || !!busy}
        onPlaybackEnded={() => setCompletedAudioSource(audioSource)}
        transcriptMode={resultMode ?? (!analysis ? 'replay' : undefined)}
        analysisState={busy === 'analyze' ? 'loading' : analysisFailure ? 'error' : 'idle'}
        analysisError={analysisFailure}
        onRetryAnalysis={() => void analyze()}
        analysisActions={<div className="analysis-action integrated-analysis-action">
        <div><strong>{audioEnded || c.channel !== 'voice' ? '접수 내용을 정리할 준비가 되었습니다' : '통화를 먼저 끝까지 재생해 주세요'}</strong><p className="small muted">{mode === 'demo-live' ? '실제 AI API를 사용합니다. 결과를 확인한 뒤 아래 접수 정보를 편집해 주세요.' : '저장된 결과를 불러옵니다. 실제 AI API 비용은 발생하지 않습니다.'}</p></div>
        <button className="primary" disabled={intakeLocked || !!busy || fallback || stale || !!uncertain || !!recovery || (c.channel === 'voice' && !audioEnded)} onClick={() => void analyze()}>{busy === 'analyze' ? 'AI가 전사·정제하고 있습니다…' : mode === 'demo-live' ? 'AI 전사·정제 실행' : '저장된 분석 결과 재생'} <span aria-hidden="true">→</span></button>
        <a className="text-button" href="#intake-editor">접수 편집으로 이동 ↓</a>
      </div>}
        intakeEditor={<section id="intake-editor" className="panel refinement-panel"><div className="panel-heading"><div><span className="small-kicker">02 / REFINE & REVIEW</span><h3>AI 정제와 접수 확인</h3></div>{resultMode && <span className={`badge ${resultMode === 'demo-live' ? 'success' : 'info'}`}>{resultMode === 'demo-live' ? '실제 AI 분석' : '저장 결과 재생'}</span>}</div>
        {analysis ? <><div className="ai-summary"><span className="small-kicker">AI 요약 · 확인 전 초안</span><p>{analysis.summary}</p></div>{!!analysis.issues?.length && <div className="issue-list">{analysis.issues.map((issue, i) => <div className="issue" key={i}><span className="badge warning">확인 필요</span><div><strong>{issue.message}</strong>{issue.evidence && <p>원문 근거: {issue.evidence}</p>}</div></div>)}</div>}
          <div className="compare-strip"><span>원문 보존</span><span aria-hidden="true">→</span><span>AI 초안</span><span aria-hidden="true">→</span><strong>상담원 편집·확인</strong></div>
          <details className="ai-fields"><summary>AI가 제안한 접수 정보 원본</summary><dl className="details-list"><div><dt>점포</dt><dd>{analysis.fields.storeId || '미확인'}</dd></div><div><dt>상품·대상</dt><dd>{analysis.fields.subject || '미확인'}</dd></div><div><dt>수령 수량·단위(진술)</dt><dd>{analysis.fields.quantity ?? '미확인'} {analysis.fields.unit || '단위 미확인'}</dd></div><div><dt>요청</dt><dd>{analysis.fields.request || '미확인'}</dd></div></dl></details>
        </> : <div className="analysis-empty"><svg viewBox="0 0 32 32" fill="none" aria-hidden="true"><path d="m16 3 3.5 9.5L29 16l-9.5 3.5L16 29l-3.5-9.5L3 16l9.5-3.5L16 3Z" stroke="currentColor" strokeWidth="1.5"/></svg><strong>문의의 핵심을 접수 정보로</strong><p>전사·정제를 실행하면 상품, 수량, 요청사항과<br/>추가로 확인할 질문을 정리합니다.</p></div>}
        <fieldset disabled={!!busy || !!uncertain || intakeLocked}><div className="form-grid"><label>점포코드 <span className="required">필수</span><input value={form.storeId || ''} onChange={e => field('storeId', e.target.value)} placeholder="점포코드 확인"/></label><label>상품·문의 대상 <span className="required">필수</span><input value={form.subject || ''} onChange={e => field('subject', e.target.value)} placeholder="상품명 또는 문의 대상"/></label><label>수령 수량(경영주 진술)<input type="number" min="0" value={form.quantity ?? ''} onChange={e => field('quantity', e.target.value)} placeholder="미확인"/></label><label>수령 단위<input value={form.unit || ''} onChange={e => field('unit', e.target.value)} placeholder="개 / 박스 · 미확인"/></label><label className="full">요청사항<textarea value={form.request || ''} onChange={e => field('request', e.target.value)} placeholder="경영주가 요청한 내용을 확인해 주세요." rows={3}/></label></div>
        {analysis && <div className="questions"><h4>추가 확인 질문 <span className="count">{analysis.questions?.length || 0}</span></h4>{analysis.questions?.map((q, i) => <button key={i} className="question" onClick={() => setQuestion(q)}><span>{String(i + 1).padStart(2, '0')}</span>{q}<span aria-hidden="true">＋</span></button>)}<label className="full">추가 질문 메모<textarea rows={2} value={question} onChange={e => setQuestion(e.target.value)} placeholder="추천 질문을 선택하거나 직접 적어 주세요."/></label></div>}
        <div className="department-card"><div><h4>전달 부서</h4>{analysis?.department && <p>{analysis.department.reason}</p>}</div><label><span className="sr-only">전달 부서</span><select value={department} onChange={e => { setDepartment(e.target.value); setEdited(true); setConfirmed(false); }}><option value="">부서 선택</option>{analysis?.department?.id && !['delivery', 'warehouse', 'cs'].includes(analysis.department.id) && <option value={analysis.department.id}>{analysis.department.name} · AI 추천</option>}<option value="warehouse">출고 운영</option><option value="delivery">배송 운영</option><option value="cs">고객 지원</option></select></label></div>
        <label className="review-check"><input type="checkbox" checked={confirmed} onChange={e => setConfirmed(e.target.checked)}/><span>점포·상품·전달 부서를 원문과 대조하고, 접수 정보를 편집·확인했습니다.</span></label>
        {!edited && <p className="small muted">접수 정보를 한 번 편집한 뒤 확인 체크를 해 주세요. 미확인 정보는 비워 둘 수 있습니다.</p>}
        </fieldset>
        <div className="panel-actions"><button disabled={intakeLocked || !!busy || fallback || stale || !!uncertain || !!recovery} onClick={() => void persist()}>접수 내용 저장</button><button className="primary" disabled={!canTransfer} onClick={() => void persist(true)}>{busy === 'transfer' ? '전달 중…' : '확인 후 센터 전달'} <span aria-hidden="true">→</span></button></div>
      </section>}
      />
    </div>
    <section className="panel evidence-panel">
      <div className="panel-heading"><div><span className="small-kicker">03 / CONNECTED EVIDENCE</span><h3>물류 근거와 남은 질문</h3></div><div className="button-row"><button onClick={() => onView('wms')}>WMS 작업 확인 <Arrow/></button><button onClick={() => onView('tms')}>TMS 배송 확인 <Arrow/></button></div></div>
      <div className="facts-grid"><div><h4>AI가 정리한 사실 · 확인 전 초안</h4>{analysis?.facts?.length ? <ul className="clean-list">{analysis.facts.map((x, i) => <li key={i}>{x}</li>)}</ul> : <p className="muted">분석 결과를 불러오면 원문과 대조할 초안을 표시합니다.</p>}</div><div><h4><span className="status-dot warning"/>AI가 정리한 추가 확인 사항</h4>{analysis?.unknowns?.length ? <ul className="clean-list">{analysis.unknowns.map((x, i) => <li key={i}>{x}</li>)}</ul> : <p className="muted">확인되지 않은 내용은 단정하지 않습니다.</p>}</div></div>
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
  </div>;
}

function Owner({ cases, selected, onSelect, onCreated, onDesk, fallback }: { cases: CaseData[]; selected: string; onSelect: (s: string) => void; onCreated: (c: CaseData) => void; onDesk: () => void; fallback: boolean }) {
  type Attempt = { key: string; payload: { storeId: string; subject: string; text: string; type: 'missing' | 'wrong'; referenceCaseId?: string }; retryAllowed?: boolean };
  const draft = useSessionDraft<{ storeId: string; subject: string; text: string; type: 'missing' | 'wrong'; referenceCaseId: string | null; attempt: Attempt | null }>('owner:new', { storeId: '', subject: '', text: '', type: 'missing', referenceCaseId: null, attempt: null });
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
    setBusy(true); setError('');
    try { finish(await request<CaseData>(`/api/intake-attempts/${attempt.key}`, 'GET', undefined, 'owner')); }
    catch (err) {
      if (err instanceof ApiError && err.status === 404) { draft.set('attempt', { ...attempt, retryAllowed: true }); setError('아직 등록된 접수를 찾지 못했습니다. 첫 요청이 처리 중일 수 있어 입력을 유지합니다. 같은 내용으로 확인·재시도하면 중복 접수를 방지합니다.'); }
      else setError(errorText(err));
    } finally { setBusy(false); }
  };
  return <div className="owner-grid"><section className="panel"><div className="panel-heading"><div><span className="small-kicker">STORE REQUEST</span><h2>어떤 도움이 필요하신가요?</h2><p className="muted">매장 상황을 편하게 적어 주세요.</p></div></div><form onSubmit={e => void submit(e)} className="owner-form"><fieldset className="owner-entry" disabled={busy || !!attempt}><label>관련 기존 접수 연결(선택)<select value={referenceCaseId || ''} onChange={e => chooseReference(e.target.value)} disabled={busy} aria-describedby="reference-case-help"><option value="">연결하지 않음 · 새 문의</option>{referenceCases.map(item => <option key={item.id} value={item.id}>{item.id} · {referenceDate(item.asOf)} · {item.title}</option>)}</select></label><p id="reference-case-help" className="muted">{referenceCaseId ? '선택한 사건과 동일한 날짜·배송 건인지 확인해 주세요. 점포·문의 유형·제목이 달라지면 연결이 해제됩니다.' : '선택하지 않으면 입력한 원문을 기반으로 새 문의를 접수하며 기존 물류 근거는 연결되지 않습니다.'}</p>{linkNotice && <p className="notice info compact" role="status">{linkNotice}</p>}<fieldset><legend>문의 유형</legend><div className="type-choices"><label className={type === 'missing' ? 'chosen' : ''}><input type="radio" name="type" checked={type === 'missing'} onChange={() => editContext('type', 'missing')}/><strong>상품 미도착</strong><span>예정된 상품이 오지 않았어요</span></label><label className={type === 'wrong' ? 'chosen' : ''}><input type="radio" name="type" checked={type === 'wrong'} onChange={() => editContext('type', 'wrong')}/><strong>다른 상품 도착</strong><span>주문한 것과 다르게 왔어요</span></label></div></fieldset><label>점포코드<input required value={storeId} onChange={e => editContext('storeId', e.target.value)} placeholder="예: GS0001"/></label><label>문의 제목<input required value={subject} onChange={e => editContext('subject', e.target.value)} placeholder="어떤 상품에 문제가 있나요?"/></label><label>상세 내용<textarea required rows={7} value={text} onChange={e => setText(e.target.value)} placeholder="상품명, 수량, 도착 시간과 원하시는 조치를 적어 주세요. 모르는 내용은 비워 두셔도 괜찮습니다."/></label><div className="notice info compact">작성하신 내용은 상담원이 확인한 후 담당 센터에 전달합니다.</div></fieldset>{error && <p className="notice danger" role="alert">{error}</p>}{attempt && <div className="notice warning recovery-attempt" role="status"><strong>접수 결과를 확인하고 있습니다</strong><p>입력 내용은 보존했습니다. 저장 여부 확인이 끝날 때까지 내용을 바꾸거나 새 문의를 보내지 않습니다.</p><div className="button-row"><button type="button" disabled={busy || fallback} onClick={() => void verifyAttempt()}>접수 저장 여부 확인</button>{attempt.retryAllowed && <button type="button" disabled={busy || fallback} onClick={() => void submit()}>같은 내용으로 접수 확인·재시도</button>}</div></div>}<button className="primary wide" disabled={busy || fallback || !!attempt}>{busy ? '접수 중…' : '문의 접수하기'} <span aria-hidden="true">→</span></button></form></section><section className="panel"><div className="panel-heading"><div><span className="small-kicker">MY REQUEST</span><h2>접수 진행 상황</h2></div><span className="badge neutral">시연용 전체 목록</span></div><label>접수 건 선택<select value={c?.id || ''} onChange={e => onSelect(e.target.value)}>{cases.map(item => <option key={item.id} value={item.id}>{item.id} · {item.title}</option>)}</select></label>{c ? <div className="receipt"><div className="receipt-top"><div><span className="muted small">{c.id}</span><h3>{c.title}</h3><p>{c.store.name}</p></div><Status status={c.status}/></div><div className="receipt-steps"><div className="done">문의 접수</div><div className={['handed_off', 'in_progress', 'closed'].includes(c.status || '') ? 'done' : ''}>담당 센터 확인</div><div className={c.reply ? 'done' : ''}>센터 회신</div></div><h4>센터에서 보낸 회신</h4>{c.reply ? <div className="registered-reply"><span className="badge success">등록된 회신</span><p>{c.reply}</p></div> : <div className="empty-reply"><p>아직 등록된 센터 회신이 없습니다.</p><span>확인이 끝나는 대로 이곳에서 안내해 드립니다.</span></div>}{!!c.pendingActions?.length && <div className="pending-list"><h4>진행 중인 조치</h4><ul>{c.pendingActions.map((a, i) => <li key={i}>{a}</li>)}</ul></div>}<details><summary>내가 접수한 내용</summary><p className="source-text">{c.sourceText}</p></details><button className="text-button" onClick={onDesk}>시연: 상담 작업대로 이동 <Arrow/></button></div> : <div className="empty-state"><p>접수 후 진행 상황을 확인할 수 있습니다.</p></div>}</section></div>;
}

function Center({ caseData: c, onSave, onToast, onView, onUpdate }: { caseData: CaseData; onSave: (id: string, p: Record<string, unknown>) => Promise<CaseData>; onToast: (s: string) => void; onView: (v: View) => void; onUpdate: (c: CaseData) => void }) {
  type CenterDraft = { formRevision?: number; reply: string; pending: string[]; action: string; uncertain?: Record<string, unknown>; operation?: boolean };
  const initial = (item: CaseData): CenterDraft => ({ formRevision: item.revision, reply: item.reply || '', pending: item.pendingActions || [], action: '' });
  const draft = useSessionDraft<CenterDraft>(`center:${c.id}`, initial(c), value => ({ reply: value.reply, pending: value.pending, action: value.action, uncertain: value.uncertain }));
  const { formRevision, reply, pending, action, uncertain } = draft.value;
  const setReply = (value: string) => draft.set('reply', value);
  const setPending = (value: string[] | ((old: string[]) => string[])) => draft.set('pending', value);
  const setAction = (value: string) => draft.set('action', value);
  const [error, setError] = useState(''); const busy = draft.value.operation || false;
  const setBusy = (value: boolean) => draft.set('operation', value);
  const [recovery, setRecovery] = useState<CaseData | null>(null);
  const stale = formRevision !== c.revision;
  const received = ['handed_off', 'in_progress', 'closed'].includes(c.status || '');
  const blocked = !received || c.status === 'closed' || busy || stale || !!uncertain || !!recovery;
  const submit = async (close: boolean) => {
    if (blocked || !reply.trim() || (close && pending.length) || action.trim()) return;
    setBusy(true); setError('');
    const payload = { expectedRevision: formRevision, reply: reply.trim(), pendingActions: pending, status: close ? 'closed' : 'in_progress' };
    try {
      const saved = await onSave(c.id, payload);
      draft.replace(initial(saved), true);
      onToast(close ? '회신을 등록하고 처리를 완료했습니다. 경영주 화면에도 반영되었습니다.' : '중간 회신을 등록했습니다. 남은 조치는 계속 진행됩니다.');
    } catch (e) { setError(errorText(e)); if (e instanceof ApiError && e.uncertain) draft.set('uncertain', payload); if (e instanceof ApiError && e.status === 409) await inspectLatest(); } finally { setBusy(false); }
  };
  const inspectLatest = async () => {
    setBusy(true); setError('');
    try {
      const latest = await request<CaseData>(`/api/cases/${c.id}`, 'GET', undefined, 'center'); onUpdate(latest);
      if (uncertain && sameMutation(latest, uncertain)) { draft.replace(initial(latest), true); setRecovery(null); onToast('서버에 요청한 회신이 저장되어 있음을 확인했습니다.'); }
      else setRecovery(latest);
    } catch (e) { setError(errorText(e)); } finally { setBusy(false); }
  };
  return <><div>{(uncertain || stale) && <div className="notice warning" role="status"><div><strong>{uncertain ? '회신 저장 여부 확인이 필요합니다' : '서버의 접수 내용이 변경되었습니다'}</strong><p>현재 회신 초안과 남은 조치는 보존했습니다. 최신 내용을 확인한 뒤 계속해 주세요.</p></div><button disabled={busy} onClick={() => void inspectLatest()}>{uncertain ? '회신 저장 여부 확인' : '최신 내용 대조'}</button></div>}{recovery && <Recovery current={recovery} busy={busy} rows={[{ label: '회신', local: reply, server: recovery.reply || '' }, { label: '남은 조치', local: [...pending, ...(action ? [action + ' (추가 전)'] : [])].join('\n'), server: (recovery.pendingActions || []).join('\n') }]} onUseServer={() => { draft.replace(initial(recovery), true); setRecovery(null); setError(''); }} onKeepDraft={() => { draft.replace({ ...draft.value, formRevision: recovery.revision, uncertain: undefined }); setRecovery(null); setError(''); }}/>}</div><div className="center-grid"><section className="panel"><div className="panel-heading"><div><span className="small-kicker">HANDOFF SUMMARY</span><h2>센터 전달 내용</h2></div><Status status={c.status}/></div>{!received && <div className="notice warning compact">상담원의 확인과 센터 전달이 먼저 필요합니다.</div>}<h3>{c.title}</h3><dl className="details-list"><div><dt>접수 번호</dt><dd>{c.id}</dd></div><div><dt>점포</dt><dd>{c.store.name} · {c.intake?.storeId || c.store.id}</dd></div><div><dt>상품·문의 대상</dt><dd>{c.intake?.subject || '상담원 확인 전'}</dd></div><div><dt>수량</dt><dd>{c.intake?.quantity ?? '미확인'} {c.intake?.unit}</dd></div><div><dt>요청사항</dt><dd>{c.intake?.request || '상담원 확인 전'}</dd></div><div><dt>전달 부서</dt><dd>{c.analysis?.department?.id === c.departmentId ? c.analysis?.department?.name : c.departmentId || '미선택'}</dd></div><div><dt>사람 확인</dt><dd>{c.reviewConfirmed ? '상담원 대조·확인 완료' : '확인 전'}</dd></div></dl><div className="button-row"><button onClick={() => onView('wms')}>WMS 근거 <Arrow/></button><button onClick={() => onView('tms')}>TMS 근거 <Arrow/></button></div><div className="divider"/><h4>연결된 근거</h4>{c.selectedEvidence?.length ? <ul className="clean-list">{c.selectedEvidence.map(id => <li key={id}>{c.evidence?.find(e => e.id === id)?.label || id}</li>)}</ul> : <p className="muted">연결된 근거가 없습니다. 물류 기록을 확인해 주세요.</p>}<details><summary>원문 확인</summary><p className="source-text">{c.sourceText}</p></details></section><section className="panel"><div className="panel-heading"><div><span className="small-kicker">REPLY & FOLLOW-UP</span><h2>확인 결과 회신</h2></div><span className="badge neutral">센터 담당자</span></div><fieldset disabled={busy || !!uncertain || c.status === 'closed'}>{c.analysis?.replyDraft && <div className="draft-reply"><div className="subheading"><strong>AI 회신 초안</strong><span className="badge warning">아직 발송되지 않음</span></div><p>{c.analysis.replyDraft}</p><button onClick={() => setReply(c.analysis!.replyDraft)}>초안을 편집창에 가져오기</button></div>}<label>경영주에게 등록할 회신 <span className="required">필수</span><textarea rows={8} value={reply} onChange={e => setReply(e.target.value)} placeholder="확인한 사실, 처리 내용과 후속 안내를 적어 주세요. 확인되지 않은 배송 시각이나 원인은 단정하지 않습니다."/></label><div className="pending-editor"><div className="subheading"><h4>남은 조치 <span className="count">{pending.length}</span></h4><span className="small muted">남은 조치가 있으면 처리 중으로 유지</span></div>{pending.map((p, i) => <div className="pending-item" key={`${p}-${i}`}><span>{p}</span><button aria-label={`${p} 조치 완료`} onClick={() => setPending(old => old.filter((_, n) => n !== i))}>완료</button></div>)}<div className="inline-form"><input aria-label="남은 조치 내용" value={action} onChange={e => setAction(e.target.value)} placeholder="예: 기사 확인 후 도착 예정 시각 안내"/><button disabled={!action.trim()} onClick={() => { setPending(old => [...old, action.trim()]); setAction(''); }}>조치 추가</button></div></div></fieldset>{action.trim() && <p className="notice warning compact">작성 중인 조치가 있습니다. 조치 추가를 누르거나 입력을 비운 뒤 회신을 등록해 주세요.</p>}{error && <div className="notice danger" role="alert">{error}</div>}<div className="panel-actions"><button disabled={blocked || !reply.trim() || !!action.trim()} onClick={() => void submit(false)}>중간 회신 등록</button><button className="primary" disabled={blocked || !reply.trim() || !!pending.length || !!action.trim()} onClick={() => void submit(true)}>{busy ? '등록 중…' : '최종 회신·처리 완료'}</button></div><p className="small muted">등록한 회신만 경영주 화면에 보입니다. 모든 조치를 완료해야 문의를 종결할 수 있습니다.</p><button className="text-button" onClick={() => onView('owner')}>경영주 수신 화면 확인 <Arrow/></button></section></div></>;
}
