import type { UserProfile, Paper, Report, UserInfo, UserFeedback, PaperAnalysis } from '../types';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api';

async function fetchJSON<T>(url: string, options?: RequestInit): Promise<T> {
    const response = await fetch(`${API_BASE}${url}`, options);
    if (!response.ok) {
        throw new Error(`API 错误: ${response.statusText}`);
    }
    return response.json();
}

export const RealUserAPI = {
    getProfile: () => fetchJSON<UserProfile>('/user/profile'),
    initialize: (userInfo: UserInfo) => fetchJSON<UserProfile>('/user/initialize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(userInfo)
    }),
    updateNL: (text: string, userId: string) => fetchJSON<UserProfile>('/user/update/nl', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, user_id: userId })
    }),
    updateFeedback: (userId: string, feedbacks: UserFeedback[]) => fetchJSON<UserProfile>(`/user/update/feedback?user_id=${userId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(feedbacks)
    }),
};

export const RealPaperAPI = {
    getPapers: () => fetchJSON<Paper[]>('/papers/'),
    fetchPapers: (limit: number = 100) => fetchJSON<Paper[]>(`/papers/fetch?limit=${limit}`, { method: 'POST' }),
    getDailyPapers: () => fetchJSON<Paper[]>('/papers/daily'),
    getRecommendations: () => fetchJSON<Paper[]>('/papers/recommendations'),
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

