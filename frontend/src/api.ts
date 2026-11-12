export interface ApiResult {
  status: number;
  ok: boolean;
  data: any;
}

export async function api(
  method: string,
  path: string,
  body?: unknown,
  token?: string | null
): Promise<ApiResult> {
  const headers: Record<string, string> = {};
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (token) headers["Authorization"] = `Bearer ${token}`;
  try {
    const res = await fetch("/api" + path, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
    const text = await res.text();
    let data: any = null;
    try {
      data = text ? JSON.parse(text) : null;
    } catch {
      data = text;
    }
    return { status: res.status, ok: res.ok, data };
  } catch {
    return { status: 0, ok: false, data: { detail: "Сервер недоступен" } };
  }
}

export function errorText(r: ApiResult): string {
  if (r.data && typeof r.data.detail === "string") return r.data.detail;
  return `Ошибка ${r.status}`;
}
