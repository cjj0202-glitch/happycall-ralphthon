'use client';

import { useCallback, useSyncExternalStore } from 'react';
import type { CaseData } from './types';

// Deliberately memory-only: customer text is not copied into browser storage.
type Entry = { value: unknown; baseline: string; project: (value: unknown) => unknown };
const entries = new Map<string, Entry>();
const listeners = new Set<() => void>();
const publish = () => listeners.forEach(listener => listener());
const subscribe = (listener: () => void) => { listeners.add(listener); return () => { listeners.delete(listener); }; };
const serial = (value: unknown) => JSON.stringify(value);

export function useSessionDraft<T extends object>(key: string, initial: T, project: (value: T) => unknown = value => value) {
  if (!entries.has(key)) entries.set(key, { value: initial, baseline: serial(project(initial)), project: project as (value: unknown) => unknown });
  const value = useSyncExternalStore(subscribe, () => entries.get(key)!.value as T, () => initial);
  const replace = useCallback((next: T, clean = false) => {
    const entry = entries.get(key)!;
    entry.value = next;
    if (clean) entry.baseline = serial(entry.project(next));
    publish();
  }, [key]);
  const set = useCallback(<K extends keyof T>(field: K, next: T[K] | ((previous: T[K]) => T[K])) => {
    const entry = entries.get(key)!;
    const previous = entry.value as T;
    const nextValue = typeof next === 'function' ? (next as (previous: T[K]) => T[K])(previous[field]) : next;
    replace({ ...previous, [field]: nextValue });
  }, [key, replace]);
  const dirty = serial(entries.get(key)!.project(value)) !== entries.get(key)!.baseline;
  return { value, set, replace, dirty };
}

const hasUnsaved = () => Array.from(entries.values()).some(entry => serial(entry.project(entry.value)) !== entry.baseline);
export function useHasUnsavedDrafts() { return useSyncExternalStore(subscribe, hasUnsaved, () => false); }

// Only the acknowledged evidence-only PATCH may advance an unmounted Desk's
// baseline revision. A list refresh or an already stale draft must not do this.
export function acceptOwnEvidenceSave(previous: CaseData, saved: CaseData, selectedEvidence: string[]) {
  const entry = entries.get(`desk:${previous.id}`);
  if (!entry || previous.id !== saved.id || typeof previous.revision !== 'number' || !Number.isSafeInteger(previous.revision) || !Number.isSafeInteger(saved.revision) || saved.revision !== previous.revision + 1) return false;
  if (previous.status !== 'draft' && previous.status !== 'review') return false;
  const draft = entry.value as { formRevision?: number; confirmed: boolean; uncertain?: unknown; operation?: unknown };
  if (draft.formRevision !== previous.revision || draft.uncertain || draft.operation) return false;
  if (serial(saved.selectedEvidence) !== serial(selectedEvidence)) return false;
  const evidenceChanged = serial(previous.selectedEvidence || []) !== serial(selectedEvidence);
  if (saved.reviewConfirmed !== (evidenceChanged ? false : previous.reviewConfirmed)) return false;
  // AnalyzeResult omits audit metadata, while Home normalizes nullable fields.
  // Compare the actual editable values; CAS already proves the saved predecessor.
  const intake = (value: CaseData['intake']) => ({ storeId: value?.storeId || '', subject: value?.subject || '', quantity: value?.quantity ?? '', unit: value?.unit || '', request: value?.request || '' });
  if (serial(intake(previous.intake)) !== serial(intake(saved.intake)) || (previous.departmentId || '') !== (saved.departmentId || '')) return false;
  const allowed = new Set(['revision', 'updatedAt', 'history', 'analysisRequestId', 'intake', 'departmentId', 'selectedEvidence', 'reviewConfirmed']);
  const keys = new Set([...Object.keys(previous), ...Object.keys(saved)]);
  if (Array.from(keys).some(key => !allowed.has(key) && serial(previous[key]) !== serial(saved[key]))) return false;
  entry.value = { ...draft, formRevision: saved.revision, confirmed: false };
  publish();
  return true;
}
