import { fetchJSON } from './config';
import type { Paper, PaperAnalysis } from '../../types';

export const PaperAPI = {
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
