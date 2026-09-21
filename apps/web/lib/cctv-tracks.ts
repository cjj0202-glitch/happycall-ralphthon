/** Synthetic projected bounds. This contract does not establish business object identity. */
export type CctvClip = { id: string; caseId: string; system: string; cameraId: string; eventIds: string[]; occurredAt: string; url: string; startSeconds: number; endSeconds: number; synthetic: true; sha256: string; bytes: number };
export type TracksDescriptor = { url: string; bytes: number; sha256: string; videoSha256: string; schemaVersion: 'oneflow-cctv-tracks-v1' };
export type ProcessAnchor = { chuteId: string; dockId: string };
export type RegisteredTracks = { tracks?: TracksDescriptor; processAnchor?: ProcessAnchor; tracksError?: string };
export type TrackFrame = { frame: number; elapsedSeconds: number; visualObjectId: string; businessToteId: null; phase: 'approach' | 'branch' | 'chute' | 'settle'; bboxNormalizedXYXY: [number, number, number, number]; fullyInFrame: boolean };
export type CctvTracks = { source: 'synthetic-scene-ground-truth'; synthetic: true; eventAnchor: { caseId: string; eventId: string; occurredAt: string; chuteId: string; dockId: string; visualObjectId: string; businessToteId: null }; cameraId: string; coordinateSpace: 'normalized-image-top-left'; clockMode: 'illustrative-elapsed-separate-from-event-time'; occlusionTested: false; fps: number; frameCount: number; resolution: [number, number]; frames: TrackFrame[] };
type Row = Record<string, unknown>;
const object = (value: unknown): Row => value !== null && typeof value === 'object' && !Array.isArray(value) ? value as Row : {};
const finite = (value: unknown): value is number => typeof value === 'number' && Number.isFinite(value);
const text = (value: unknown): value is string => typeof value === 'string' && value.trim().length > 0;
const sha = (value: unknown): value is string => typeof value === 'string' && /^[a-f0-9]{64}$/.test(value);
const timestamp = (value: unknown): boolean => text(value) && /T.*(?:Z|[+-]\d{2}:\d{2})$/i.test(value) && Number.isFinite(Date.parse(value));
const fail = (message: string): never => { throw new Error(message); };

export function validateClip(clip: CctvClip, event: Row): void {
  if (clip.synthetic !== true || clip.system !== 'WMS' || !/^\/demo\/(?:[A-Za-z0-9_-]+\/)*[A-Za-z0-9_-]+\.mp4$/.test(clip.url) || !sha(clip.sha256) || !Number.isSafeInteger(clip.bytes) || clip.bytes <= 0 || clip.bytes > 200_000_000) fail('등록 영상 경로·해시·크기가 유효하지 않습니다');
  if (!text(clip.caseId) || !text(clip.cameraId) || !timestamp(clip.occurredAt) || !Array.isArray(clip.eventIds) || !text(event.id) || !clip.eventIds.includes(event.id) || event.time !== clip.occurredAt || ('cameraId' in event && event.cameraId !== clip.cameraId)) fail('선택 사건·이벤트·카메라·기록시각이 영상과 다릅니다');
  if (!finite(clip.startSeconds) || !finite(clip.endSeconds) || clip.startSeconds < 0 || clip.endSeconds <= clip.startSeconds) fail('등록 영상 구간이 유효하지 않습니다');
}

export function validateDescriptor(descriptor: TracksDescriptor, clip: CctvClip): void {
  if (descriptor.schemaVersion !== 'oneflow-cctv-tracks-v1' || (descriptor.url !== '/demo/sorter-demo.tracks.json' && !/^\/demo\/(?:[A-Za-z0-9_-]+\/)*[A-Za-z0-9_-]+\.json$/.test(descriptor.url)) || !sha(descriptor.sha256) || descriptor.videoSha256 !== clip.sha256 || !Number.isSafeInteger(descriptor.bytes) || descriptor.bytes <= 0 || descriptor.bytes > 10_000_000) fail('객체 좌표의 버전·경로·영상 해시 연결이 유효하지 않습니다');
}

/** The caller supplies the build-time manifest entry and canonical WMS rows, never intake media metadata. */
export function registeredTracks(assetValue: unknown, clip: CctvClip, event: Row, canonicalWms: unknown): RegisteredTracks {
  const asset = object(assetValue);
  if (!Object.hasOwn(asset, 'tracks')) return {};
  try {
    if (asset.name !== 'sorter-demo.mp4' || clip.url !== '/demo/sorter-demo.mp4' || asset.sha256 !== clip.sha256 || asset.bytes !== clip.bytes) fail('객체 좌표의 부모 영상 등록이 일치하지 않습니다');
    const descriptor = object(asset.tracks) as TracksDescriptor;
    validateDescriptor(descriptor, clip);
    if (descriptor.url !== '/demo/sorter-demo.tracks.json') fail('객체 좌표의 등록 파일명이 일치하지 않습니다');
    const wms = object(canonicalWms), sorting = object(wms.sorting), shipping = object(wms.shipping);
    if (sorting.sortedAt !== event.time || !text(sorting.rsltChuteNo) || !text(shipping.dock)) fail('객체 좌표의 원본 분류 공정·슈트·도크를 확인할 수 없습니다');
    const processAnchor = { chuteId: sorting.rsltChuteNo as string, dockId: shipping.dock as string };
    if (('chuteId' in event && event.chuteId !== processAnchor.chuteId) || ('dockId' in event && event.dockId !== processAnchor.dockId)) fail('선택 이벤트의 슈트·도크가 원본 공정과 다릅니다');
    return { tracks: { schemaVersion: descriptor.schemaVersion, url: descriptor.url, bytes: descriptor.bytes, sha256: descriptor.sha256, videoSha256: descriptor.videoSha256 }, processAnchor };
  } catch (failure) {
    return { tracksError: failure instanceof Error ? failure.message : '객체 좌표 등록 검증 실패' };
  }
}

export function validateTracks(value: unknown, descriptor: TracksDescriptor, clip: CctvClip, event: Row, processAnchor?: ProcessAnchor): CctvTracks {
  validateClip(clip, event); validateDescriptor(descriptor, clip);
  const data = object(value), anchor = object(data.eventAnchor);
  if (data.source !== 'synthetic-scene-ground-truth' || data.synthetic !== true || data.coordinateSpace !== 'normalized-image-top-left' || data.clockMode !== 'illustrative-elapsed-separate-from-event-time' || data.occlusionTested !== false) fail('합성 좌표의 출처·좌표계·한계 정보가 일치하지 않습니다');
  if (anchor.caseId !== clip.caseId || anchor.eventId !== event.id || !clip.eventIds.includes(String(anchor.eventId)) || data.cameraId !== clip.cameraId || anchor.occurredAt !== clip.occurredAt || anchor.occurredAt !== event.time) fail('객체 좌표의 사건·공정·카메라·기록시각이 일치하지 않습니다');
  const expectedProcess = processAnchor ?? event;
  if (!text(expectedProcess.chuteId) || !text(expectedProcess.dockId) || anchor.chuteId !== expectedProcess.chuteId || anchor.dockId !== expectedProcess.dockId || !text(anchor.visualObjectId) || anchor.businessToteId !== null || ('chuteId' in event && anchor.chuteId !== event.chuteId) || ('dockId' in event && anchor.dockId !== event.dockId)) fail('객체 좌표의 슈트·도크·시각 객체 관계가 일치하지 않습니다');
  if (!finite(data.fps) || data.fps < 1 || data.fps > 120 || !Number.isSafeInteger(data.frameCount) || (data.frameCount as number) < 1 || (data.frameCount as number) > 72_000 || !Array.isArray(data.resolution) || data.resolution.length !== 2 || !data.resolution.every(item => Number.isSafeInteger(item) && item > 0 && item <= 8192)) fail('좌표의 fps·프레임 수·해상도가 유효하지 않습니다');
  if (!Array.isArray(data.frames) || data.frames.length !== data.frameCount) fail('좌표 프레임 수가 등록값과 다릅니다');
  let previousPhase = -1;
  for (const [index, item] of (data.frames as unknown[]).entries()) {
    const frame = object(item), box = frame.bboxNormalizedXYXY;
    const phase = ['approach', 'branch', 'chute', 'settle'].indexOf(String(frame.phase));
    if (frame.frame !== index + 1 || !finite(frame.elapsedSeconds) || Math.abs(frame.elapsedSeconds - index / (data.fps as number)) > 1e-6 || frame.visualObjectId !== anchor.visualObjectId || frame.businessToteId !== null || typeof frame.fullyInFrame !== 'boolean') fail(`프레임 ${index + 1}의 시간·객체 연결이 유효하지 않습니다`);
    if (phase < 0 || phase < previousPhase) fail(`프레임 ${index + 1}의 공정 단계가 역전되었거나 미등록입니다`);
    previousPhase = phase;
    if (!Array.isArray(box) || box.length !== 4 || !box.every(item => finite(item) && item >= 0 && item <= 1) || box[0] >= box[2] || box[1] >= box[3]) fail(`프레임 ${index + 1}의 객체 좌표가 유효하지 않습니다`);
  }
  if (clip.endSeconds > (data.frameCount as number) / (data.fps as number) + 1e-6) fail('등록 구간에 필요한 좌표 프레임이 없습니다');
  return value as CctvTracks;
}

export function validateTrackVideo(tracks: CctvTracks, width: number, height: number, duration: number): void {
  if (tracks.resolution[0] !== width || tracks.resolution[1] !== height || !finite(duration) || Math.abs(duration - tracks.frameCount / tracks.fps) > 0.5 / tracks.fps) fail('영상 해상도·길이와 객체 좌표가 다릅니다. 서로 다른 장면은 결합하지 않습니다');
}

export function frameAt(tracks: CctvTracks, mediaTime: number): TrackFrame | null {
  if (!finite(mediaTime) || mediaTime < 0 || mediaTime >= tracks.frameCount / tracks.fps) return null;
  return tracks.frames[Math.min(tracks.frameCount - 1, Math.floor(mediaTime * tracks.fps + 1e-6))] ?? null;
}

export async function verifiedBytes(url: string, bytes: number, expectedSha: string, signal: AbortSignal): Promise<ArrayBuffer> {
  const response = await fetch(url, { signal, credentials: 'same-origin', cache: 'no-store', redirect: 'error' });
  if (!response.ok) throw new Error(`응답 ${response.status}`);
  const data = await response.arrayBuffer();
  if (data.byteLength !== bytes) throw new Error('등록 바이트 수 불일치');
  const digest = await crypto.subtle.digest('SHA-256', data);
  const hash = Array.from(new Uint8Array(digest)).map(byte => byte.toString(16).padStart(2, '0')).join('');
  if (hash !== expectedSha) throw new Error('등록 SHA256 불일치');
  return data;
}
