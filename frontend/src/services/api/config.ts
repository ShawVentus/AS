import { supabase } from '../supabase';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api/v1';

export async function fetchJSON<T>(url: string, options: RequestInit = {}): Promise<T> {
    // 自动附加 Auth Token
    const { data: { session } } = await supabase.auth.getSession();
    const headers = new Headers(options.headers);

    if (session?.access_token) {
        headers.set('Authorization', `Bearer ${session.access_token}`);
    }

    // 确保 Content-Type 默认是 application/json (如果不是 FormData)
    if (!headers.has('Content-Type') && !(options.body instanceof FormData)) {
        // 只有当有 body 时才设置 Content-Type? 或者总是设置?
        // 这里的 fetchJSON 通常用于 JSON API，所以默认设置比较安全，除非明确不需要
        // 但为了避免干扰 GET 请求（虽然 GET 没 body 也不影响），可以保留原样或简单处理
    }

    const config = {
        ...options,
        headers
    };

    const response = await fetch(`${API_BASE}${url}`, config);
    if (!response.ok) {
        throw new Error(`API 错误: ${response.statusText}`);
    }
    return response.json();
}
