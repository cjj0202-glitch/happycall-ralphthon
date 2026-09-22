// Exported deployments serve the API on the page's HTTPS origin. The separate
// loopback API is only the default for the local Next development server.
const BASE = (process.env.NEXT_PUBLIC_API_BASE ??
  (process.env.NODE_ENV === 'production' ? '' : 'http://127.0.0.1:8100')).replace(/\/$/, '');

export class ApiError extends Error {
  constructor(message: string, public status?: number, public uncertain = false, public code?: string) { super(message); this.name = 'ApiError'; }
}

export async function request<T>(path: string, method = 'GET', body?: unknown, role = 'counselor', options?: { idempotencyKey?: string }): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), (path.endsWith('/analyze') || path.endsWith('/reply-draft')) ? 120000 : 15000);
  try {
    const response = await fetch(`${BASE}${path}`, {
      method, headers: { 'Content-Type': 'application/json', 'X-Demo-Role': role, ...(options?.idempotencyKey ? { 'X-Idempotency-Key': options.idempotencyKey } : {}) },
      body: body === undefined ? undefined : JSON.stringify(body), signal: controller.signal,
      cache: 'no-store',
    });
    let data;
    try { data = await response.json(); } catch { throw new ApiError('서버 응답을 확인하지 못했습니다. 저장 요청이었다면 먼저 저장 여부를 확인해 주세요.', response.status, method !== 'GET'); }
    if (!response.ok) {
      const detail = data.detail || data.error?.message || data.error || data.message;
      throw new ApiError(typeof detail === 'string' ? detail : `요청을 처리하지 못했습니다. (HTTP ${response.status})`, response.status, method !== 'GET' && response.status >= 500, data.code || data.error?.code);
    }
    return data as T;
  } catch (error) {
    if (error instanceof Error && error.name === 'AbortError') throw new ApiError(method === 'GET' ? '조회 시간이 초과되었습니다. 연결 상태를 확인해 주세요.' : '응답이 늦어 저장 결과를 확인하지 못했습니다. 먼저 저장 여부를 확인해 주세요.', undefined, method !== 'GET');
    if (error instanceof TypeError) throw new ApiError(method === 'GET' ? '최신 내용을 조회하지 못했습니다. 네트워크와 서버 연결 상태를 확인해 주세요.' : '응답을 받지 못해 저장 여부가 아직 확인되지 않았습니다. 다시 보내기 전에 저장 여부를 확인해 주세요.', undefined, method !== 'GET');
    throw error;
  } finally { clearTimeout(timer); }
}
