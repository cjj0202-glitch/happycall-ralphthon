import type { CaseData, View } from './types';

export type WorkRole = 'counselor' | 'center' | 'owner';
export type QueueId = 'attention' | 'handed_off' | 'in_progress' | 'closed' | 'all';
export const roleView: Record<WorkRole, View> = { counselor: 'desk', center: 'center', owner: 'owner' };
export const roleNames: Record<WorkRole, string> = { counselor: '상담원', center: '센터 담당자', owner: '경영주' };
const departmentNames: Record<string, string> = { delivery: '배송 운영', warehouse: '출고 운영', cs: '고객 지원' };
export function departmentName(id?: string | null, recommendation?: { id: string; name: string } | null): string {
  if (!id) return '미선택';
  return Object.hasOwn(departmentNames, id) ? departmentNames[id] : recommendation?.id === id && recommendation.name ? recommendation.name : id;
}
export const queues = (role: WorkRole): { id: QueueId; label: string }[] => role === 'center'
  ? [{ id: 'handed_off', label: '새 이관' }, { id: 'in_progress', label: '처리 중' }, { id: 'closed', label: '완료' }, { id: 'all', label: '전체' }]
  : [{ id: 'attention', label: '접수·확인 대기' }, { id: 'handed_off', label: '센터 전달' }, { id: 'closed', label: '완료' }, { id: 'all', label: '전체' }];
export const defaultQueue = (role: WorkRole): QueueId => role === 'center' ? 'handed_off' : 'attention';
/** Follow an explicit case across roles or back from evidence, using its current status. */
export function queueForCase(item: CaseData | undefined, role: WorkRole): QueueId {
  if (!item) return defaultQueue(role);
  if (item.status === 'closed') return 'closed';
  if (item.status === 'handed_off') return 'handed_off';
  if (item.status === 'in_progress') return role === 'center' ? 'in_progress' : 'handed_off';
  if (item.status === 'draft' || item.status === 'review') return role === 'center' ? 'all' : 'attention';
  return 'all';
}
export function inQueue(item: CaseData, role: WorkRole, queue: QueueId): boolean {
  if (queue === 'all') return true;
  const status = item.status;
  if (queue === 'attention') return status === 'draft' || status === 'review';
  // Only the center splits handed_off from in_progress. The counselor and the owner
  // share one bucket, and queueForCase routes both statuses into it, so the filter
  // has to accept both or that bucket counts 0 while holding the selected case.
  if (queue === 'handed_off' && role !== 'center') return status === 'handed_off' || status === 'in_progress';
  return status === queue;
}
export function filterCases(cases: CaseData[], role: WorkRole, queue: QueueId, query: string): CaseData[] {
  const search = query.trim().toLocaleLowerCase('ko-KR');
  return cases.filter(item => inQueue(item, role, queue) && (!search || [item.id, item.title, item.store?.name, item.store?.id].some(value => String(value ?? '').toLocaleLowerCase('ko-KR').includes(search))));
}
export function nextAction(item: CaseData, role: WorkRole): string {
  if (item.status === 'closed') return '최종 회신 확인';
  if (item.status === 'handed_off') return role === 'center' ? '근거 확인 후 조치 기록' : '센터 확인 대기';
  if (item.status === 'in_progress') return role === 'center' ? '남은 조치 확인 후 회신' : '센터 처리 현황 확인';
  if (item.status === 'review') return role === 'center' ? '상담원 이관 전 · 열람' : '접수 대조 후 센터 전달';
  if (item.status === 'draft') return role === 'center' ? '상담원 이관 전 · 열람' : item.channel === 'voice' ? '통화 확인 후 AI 정제' : '접수 원문 확인 후 AI 정제';
  return '처리 상태 확인 필요';
}
export function isEvidenceEditable(item: CaseData, role: WorkRole): boolean {
  return role === 'counselor' && (item.status === 'draft' || item.status === 'review');
}
export function deskStep(item: CaseData, hasAnalysis: boolean, confirmed: boolean): 1 | 2 | 3 {
  if (['handed_off', 'in_progress', 'closed'].includes(item.status || '') || confirmed) return 3;
  return hasAnalysis ? 2 : 1;
}
