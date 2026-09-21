'use client';

import { useCallback, useSyncExternalStore } from 'react';

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
