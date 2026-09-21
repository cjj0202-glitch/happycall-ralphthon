import type { CaseData, NotificationIntent } from '@/lib/types';

type Props = { caseData: CaseData; audience: 'workforce' | 'owner' };
const fields = ['schemaVersion', 'id', 'caseId', 'caseRevision', 'kind', 'channel', 'recipientRole', 'recipientRef', 'createdAt', 'status', 'reason'];
const kinds = { handoff: '센터 전달', interim_reply: '중간 회신', final_reply: '최종 회신' };
const channels = { teams: 'Teams', kakao: '카카오톡' };
const roles = { center: '담당 센터', counselor: '담당 상담원', owner: '경영주' };
const combinations = new Set(['handoff:teams:center', 'interim_reply:teams:counselor', 'final_reply:teams:counselor', 'final_reply:kakao:owner']);
const timestamp = new Intl.DateTimeFormat('ko-KR', { timeZone: 'Asia/Seoul', year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false });

function validTime(value: unknown): value is string {
  if (typeof value !== 'string') return false;
  const match = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.\d{1,6})?(Z|[+-](\d{2}):(\d{2}))$/.exec(value);
  if (!match) return false;
  const [, year, month, day, hour, minute, second, , zoneHour = '0', zoneMinute = '0'] = match;
  return +month >= 1 && +month <= 12 && +day >= 1 && +day <= new Date(Date.UTC(+year, +month, 0)).getUTCDate()
    && +hour < 24 && +minute < 60 && +second < 60 && +zoneHour < 24 && +zoneMinute < 60 && Number.isFinite(Date.parse(value));
}

function validRecord(value: unknown, caseData: CaseData): value is NotificationIntent {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return false;
  const row = value as Record<string, unknown>;
  if (Object.keys(row).length !== fields.length || !fields.every(field => Object.hasOwn(row, field))) return false;
  if (row.schemaVersion !== 1 || typeof row.id !== 'string' || !/^[a-f0-9]{64}$/.test(row.id)
    || typeof caseData.id !== 'string' || !caseData.id.trim() || row.caseId !== caseData.id
    || !Number.isSafeInteger(row.caseRevision) || (row.caseRevision as number) < 1
    || !Number.isSafeInteger(caseData.revision) || (row.caseRevision as number) > (caseData.revision as number)
    || typeof row.kind !== 'string' || typeof row.channel !== 'string' || typeof row.recipientRole !== 'string'
    || !combinations.has(`${row.kind}:${row.channel}:${row.recipientRole}`)
    || row.status !== 'not_connected' || !validTime(row.createdAt)) return false;
  if (row.reason === 'missing_recipient') return row.recipientRole === 'owner' && row.recipientRef === null;
  return row.reason === 'delivery_not_configured' && typeof row.recipientRef === 'string'
    && new RegExp(`^${row.recipientRole}:[a-f0-9]{64}$`).test(row.recipientRef);
}

export default function NotificationStatus({ caseData, audience }: Props) {
  // Read only the saved case. Never derive notification events from a form or reply draft.
  const raw: unknown = caseData.notificationOutbox;
  let needsReview = (raw !== undefined && !Array.isArray(raw)) || !['workforce', 'owner'].includes(audience);
  const records: NotificationIntent[] = [];
  const seen = new Set<string>();
  if (Array.isArray(raw)) for (const row of raw) {
    if (!validRecord(row, caseData) || seen.has(row.id)) { needsReview = true; continue; }
    seen.add(row.id);
    if (audience === 'workforce' || (audience === 'owner' && row.channel === 'kakao' && row.recipientRole === 'owner')) records.push(row);
  }
  return <details className="panel" aria-label="외부 알림">
    <summary>외부 알림 <span className="badge neutral">연결 안 됨</span>{needsReview && <> <span className="badge warning">기록 확인 필요</span></>}</summary>
    <p className="small muted">알림 공급자 미설정 · 현재 외부 메시지를 전송할 수 없습니다. 접수·회신 저장과 외부 알림 전달은 별개입니다.</p>
    {needsReview && <p className="small muted">기록 확인 필요 · 확인되지 않은 알림 기록의 표시는 보류했습니다.</p>}
    {!records.length && !needsReview && <p className="muted">저장된 알림 기록 없음</p>}
    {!!records.length && <p className="small muted">아래 기록은 실제 외부 메시지로 전송되지 않았습니다.</p>}
    {records.map(row => <dl className="details-list" key={row.id}>
      <div><dt>알림 종류</dt><dd>{kinds[row.kind]}</dd></div>
      <div><dt>채널 · 수신 역할</dt><dd>{channels[row.channel]} · {roles[row.recipientRole]}</dd></div>
      <div><dt>기록 시각</dt><dd><time dateTime={new Date(row.createdAt).toISOString()}>{timestamp.format(new Date(row.createdAt))} KST</time></dd></div>
      <div><dt>전달 상태</dt><dd>연결 안 됨 · {row.reason === 'missing_recipient' ? '수신 대상 확인 필요' : '공급자 미설정'}</dd></div>
    </dl>)}
  </details>;
}
