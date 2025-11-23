const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api/v1';

export async function fetchJSON<T>(url: string, options?: RequestInit): Promise<T> {
    const response = await fetch(`${API_BASE}${url}`, options);
    if (!response.ok) {
        throw new Error(`API 错误: ${response.statusText}`);
    }
    return response.json();
}
