import { fetchJSON } from './config';
import type { Paper, PaperAnalysis } from '../../types';

export interface PaperAPIInterface {
    getPapers: () => Promise<Paper[]>;
    fetchPapers: (limit?: number) => Promise<Paper[]>;
    getDailyPapers: () => Promise<Paper[]>;
    getRecommendations: () => Promise<Paper[]>;
    getPaperDetail: (id: string) => Promise<Paper>;
    getPapersByIds: (ids: string[]) => Promise<Paper[]>;
    getAnalysis: (id: string) => Promise<PaperAnalysis>;
    submitFeedback: (id: string, feedback: any) => Promise<any>;
}

export const PaperAPI: PaperAPIInterface = {
    getPapers: () => fetchJSON<Paper[]>('/papers/'),
    fetchPapers: (limit: number = 100) => fetchJSON<Paper[]>(`/papers/fetch?limit=${limit}`, { method: 'POST' }),
    getDailyPapers: () => fetchJSON<Paper[]>('/papers/daily'),
    getRecommendations: () => fetchJSON<Paper[]>('/papers/recommendations'),
    getPaperDetail: (id: string) => fetchJSON<Paper>(`/papers/${id}`),
    getPapersByIds: (ids: string[]) => {
        const params = new URLSearchParams();
        ids.forEach(id => params.append('ids', id));
        return fetchJSON<Paper[]>(`/papers/batch?${params.toString()}`);
    },
    getAnalysis: (id: string) => fetchJSON<PaperAnalysis>(`/papers/${id}/analysis`),
    submitFeedback: (id: string, feedback: any) => fetchJSON(`/papers/${id}/feedback`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(feedback)
    }),
};

