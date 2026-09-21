const BASE = (process.env.NEXT_PUBLIC_API_BASE || 'http://127.0.0.1:8100').replace(/\/$/, '');

export async function request<T>(path: string, method = 'GET', body?: unknown, role = 'counselor'): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), path.endsWith('/analyze') ? 120000 : 15000);
  try {
    const response = await fetch(`${BASE}${path}`, {
      method, headers: { 'Content-Type': 'application/json', 'X-Demo-Role': role },
      body: body === undefined ? undefined : JSON.stringify(body), signal: controller.signal,
      cache: 'no-store',
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      const detail = data.detail || data.error?.message || data.error || data.message;
      throw new Error(typeof detail === 'string' ? detail : `요청을 처리하지 못했습니다. (HTTP ${response.status})`);
    }
    return data as T;
  } catch (error) {
    if (error instanceof Error && error.name === 'AbortError') throw new Error('응답 시간이 초과되었습니다. 연결 상태를 확인하고 다시 시도해 주세요.');
    if (error instanceof TypeError) throw new Error('해피콜 서버에 연결하지 못했습니다. 로컬 API 실행 상태를 확인한 후 다시 시도해 주세요.');
    throw error;
  } finally { clearTimeout(timer); }
}
