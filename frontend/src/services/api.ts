import type { UserProfile, Paper, Report, UserInfo, UserFeedback, PaperAnalysis } from '../types';

import { supabase } from './supabase';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api';

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
        throw new Error('Unauthorized');
    }

    if (!response.ok) {
        throw new Error(`API 错误: ${response.statusText}`);
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
    initialize: (userInfo: UserInfo) => fetchJSON<UserProfile>('/user/initialize', {
        method: 'POST',
        body: JSON.stringify(userInfo)
    }),
    updateNL: (text: string, userId: string) => fetchJSON<UserProfile>('/user/update/nl', {
        method: 'POST',
        body: JSON.stringify({ text, user_id: userId })
    }),
    updateFeedback: (userId: string, feedbacks: UserFeedback[]) => fetchJSON<UserProfile>(`/user/update/feedback?user_id=${userId}`, {
        method: 'POST',
        body: JSON.stringify(feedbacks)
    }),
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

import { MockUserAPI, MockPaperAPI, MockReportAPI } from './mockApi';

const useMock = import.meta.env.VITE_USE_MOCK === 'true';

export const UserAPI = useMock ? MockUserAPI : RealUserAPI;
export const PaperAPI = useMock ? MockPaperAPI : RealPaperAPI;
export const ReportAPI = useMock ? MockReportAPI : RealReportAPI;

