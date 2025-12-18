import type { UserProfile, Paper, Report, UserInfo, UserFeedback, PaperAnalysis } from '../types';

import { supabase } from './supabase';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api';

export class ApiError extends Error {
    status: number;
    statusText: string;

    constructor(status: number, statusText: string, message?: string) {
        super(message || `API Error: ${status} ${statusText}`);
        this.status = status;
        this.statusText = statusText;
        this.name = 'ApiError';
    }
}

async function fetchJSON<T>(url: string, options: RequestInit = {}): Promise<T> {
    // 1. 获取当前 Session Token
    const { data: { session } } = await supabase.auth.getSession();
    const token = session?.access_token;

    // 2. 注入 Authorization Header
    const headers = {
        'Content-Type': 'application/json',
        ...options.headers,
        ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
    };

    const response = await fetch(`${API_BASE}${url}`, { ...options, headers });

    if (response.status === 401) {
        // Token 过期或无效，可以在这里处理登出逻辑
        // window.location.href = '/login'; 
        throw new ApiError(401, 'Unauthorized');
    }

    if (!response.ok) {
        throw new ApiError(response.status, response.statusText);
    }
    return response.json();
}

export const RealUserAPI = {
    getProfile: () => fetchJSON<UserProfile>('/user/me'),
    updateFocus: (focus: any) => fetchJSON<any>('/user/me/focus', {
        method: 'PUT',
        body: JSON.stringify(focus)
    }),
    updateInfo: (info: UserInfo) => fetchJSON<UserInfo>('/user/me/info', {
        method: 'PUT',
        body: JSON.stringify(info)
    }),
    updateProfile: (data: Partial<UserProfile>) => fetchJSON<UserProfile>('/user/me', {
        method: 'PUT',
        body: JSON.stringify(data)
    }),
    updateProfileNL: (text: string) => fetchJSON<UserProfile>('/user/me/nl', {
        method: 'POST',
        body: JSON.stringify({ text })
    }),
    // 保留旧接口兼容性或标记为废弃
    initialize: (data: { info: UserInfo, focus: any, context: any }) => fetchJSON<UserProfile>('/user/initialize', {
        method: 'POST',
        body: JSON.stringify(data)
    }),
    updateNL: (text: string, userId: string) => fetchJSON<UserProfile>('/user/update/nl', {
        method: 'POST',
        body: JSON.stringify({ text, user_id: userId })
    }),
    updateFeedback: (userId: string, feedbacks: UserFeedback[]) => fetchJSON<UserProfile>(`/user/update/feedback?user_id=${userId}`, {
        method: 'POST',
        body: JSON.stringify(feedbacks)
    }),
    recordInteraction: (feedback: UserFeedback) => fetchJSON<{ status: string }>('/user/me/interaction', {
        method: 'POST',
        body: JSON.stringify(feedback)
    }),
    
    /**
     * 标记用户已完成产品引导教程
     * 
     * 调用后端 API 更新 profiles 表中的 has_completed_tour 字段为 true。
     * 用于新用户首次使用时的引导流程，确保下次登录不再显示引导气泡。
     * 
     * Args:
     *   无
     * 
     * Returns:
     *   Promise<{ success: boolean; message: string }>: 操作结果
     * 
     * Throws:
     *   ApiError: API 调用失败时抛出
     */
    completeTour: async (): Promise<{ success: boolean; message: string }> => {
        console.log('[API] 正在标记用户引导完成...');
        const result = await fetchJSON<{ success: boolean; message: string }>('/user/me/complete-tour', {
            method: 'PATCH'
        });
        console.log('[API] ✅ 引导完成状态已更新');
        return result;
    },
};

export const RealPaperAPI = {
    getPapers: () => fetchJSON<Paper[]>('/papers/'),
    fetchPapers: (limit: number = 100) => fetchJSON<Paper[]>(`/papers/fetch?limit=${limit}`, { method: 'POST' }),
    getDailyPapers: () => fetchJSON<Paper[]>('/papers/daily'),
    getRecommendations: (date?: string) => fetchJSON<Paper[]>(`/papers/recommendations${date ? `?date=${date}` : ''}`),
    getPaperCalendar: (year: number, month: number) => fetchJSON<string[]>(`/papers/calendar?year=${year}&month=${month}`),
    getPaperDetail: (id: string) => fetchJSON<Paper>(`/papers/${id}`),
    getAnalysis: (id: string) => fetchJSON<PaperAnalysis>(`/papers/${id}/analysis`),
    submitFeedback: (id: string, feedback: any) => fetchJSON(`/papers/${id}/feedback`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(feedback)
    }),
    getPapersByIds: (ids: string[]) => fetchJSON<Paper[]>('/papers/batch', {
        method: 'POST',
        body: JSON.stringify({ ids })
    }),
};

export const RealReportAPI = {
    getReports: () => fetchJSON<Report[]>('/reports/'),
    getReportDetail: (id: string) => fetchJSON<Report>(`/reports/${id}`),
    generateReport: () => fetchJSON<Report>('/reports/generate', { method: 'POST' }),
    sendEmail: (reportId: string, email: string) => fetchJSON<{ success: boolean }>('/reports/send', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ report_id: reportId, email })
    }),
};

export const RealWorkflowAPI = {
    triggerDaily: (targetUserId?: string) => fetchJSON<{ message: string; execution_id?: string }>('/workflow/trigger-daily', {
        method: 'POST',
        body: JSON.stringify({ target_user_id: targetUserId })
    }),
    resumeWorkflow: (executionId: string) => fetchJSON<{ message: string }>('/workflow/resume', {
        method: 'POST',
        body: JSON.stringify({ execution_id: executionId })
    }),
    getStatus: (executionId: string) => fetchJSON<any>(`/workflow/status/${executionId}`),
    // 手动触发工作流 (强制执行)
    manualTrigger: (data: { user_id: string, natural_query: string, categories: string[], authors: string[] }) => fetchJSON<{ message: string; execution_id: string }>('/workflow/manual-trigger', {
        method: 'POST',
        body: JSON.stringify(data)
    }),
    getActiveExecution: () => fetchJSON<{ active: boolean; execution_id?: string; status?: string; steps?: any[] }>('/workflow/active'),

    /**
     * 验证工作流执行是否真的在运行
     * @param executionId 执行记录 ID
     * @param options 可选配置，包含超时时间
     * @returns 验证结果
     */
    verifyExecution: async (executionId: string, options?: { timeout?: number }): Promise<{
        active: boolean;
        status?: string;
        reason?: string;
        current_step?: string;
        message?: string;
        last_update?: string;
        elapsed_seconds?: number;
    }> => {
        const controller = new AbortController();
        const timeout = options?.timeout || 3000; // 默认 3 秒超时

        const timeoutId = setTimeout(() => controller.abort(), timeout);

        try {
            const response = await fetch(
                `${API_BASE}/workflow/verify-execution/${executionId}`,
                { signal: controller.signal }
            );
            clearTimeout(timeoutId);

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            return await response.json();
        } catch (error: any) {
            clearTimeout(timeoutId);
            if (error.name === 'AbortError') {
                throw new Error('验证接口超时');
            }
            throw error;
        }
    }
};

export const RealToolsAPI = {
    // 提取分类和作者 (AI 辅助)
    extractCategories: (text: string) => fetchJSON<{ categories: string[], authors: string[] }>('/tools/text-to-categories', {
        method: 'POST',
        body: JSON.stringify({ text })
    }),
};

import { MockUserAPI, MockPaperAPI, MockReportAPI } from './mockApi';

const useMock = import.meta.env.VITE_USE_MOCK === 'true';

export const UserAPI = useMock ? MockUserAPI : RealUserAPI;
export const PaperAPI = useMock ? MockPaperAPI : RealPaperAPI;
export const ReportAPI = useMock ? MockReportAPI : RealReportAPI;
export const WorkflowAPI = RealWorkflowAPI; // 暂无 Mock
export const ToolsAPI = RealToolsAPI; // 暂无 Mock

