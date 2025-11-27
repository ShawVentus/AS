import { USER_PROFILE, MOCK_PAPERS, MOCK_REPORTS } from '../data/mockData';
import type { UserProfile, Paper, Report, UserInfo, UserFeedback, PaperAnalysis } from '../types';

// Helper to simulate network delay
const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

export const MockUserAPI = {
    getProfile: async () => {
        await delay(500);
        return USER_PROFILE;
    },
    initialize: async (userInfo: UserInfo) => {
        await delay(500);
        return { ...USER_PROFILE, info: { ...USER_PROFILE.info, ...userInfo } };
    },
    updateNL: async (text: string, userId: string) => {
        await delay(500);
        console.log(`[Mock] Updated NL for ${userId}: ${text}`);
        return USER_PROFILE;
    },
    updateFeedback: async (userId: string, feedbacks: UserFeedback[]) => {
        await delay(500);
        console.log(`[Mock] Updated feedback for ${userId}:`, feedbacks);
        return USER_PROFILE;
    },
};

export const MockPaperAPI = {
    getPapers: async () => {
        await delay(500);
        return MOCK_PAPERS;
    },
    fetchPapers: async (limit: number = 100) => {
        await delay(800);
        console.log(`[Mock] Fetched ${limit} papers`);
        return MOCK_PAPERS;
    },
    getDailyPapers: async () => {
        await delay(500);
        return MOCK_PAPERS.slice(0, 5);
    },
    getRecommendations: async () => {
        await delay(600);
        return MOCK_PAPERS;
    },
    getPaperDetail: async (id: string) => {
        await delay(300);
        const paper = MOCK_PAPERS.find(p => p.meta.id === id);
        if (!paper) throw new Error('Paper not found');
        return paper;
    },
    getAnalysis: async (id: string) => {
        await delay(1000);
        return {
            id,
            analysis: "Mock analysis content...",
            // Add other required fields if any, based on PaperAnalysis type
        } as unknown as PaperAnalysis; // Casting as we might not have full mock structure for analysis yet
    },
    submitFeedback: async (id: string, feedback: any) => {
        await delay(400);
        console.log(`[Mock] Feedback for ${id}:`, feedback);
        return { success: true };
    },
};

export const MockReportAPI = {
    getReports: async () => {
        await delay(500);
        return MOCK_REPORTS;
    },
    getReportDetail: async (id: string) => {
        await delay(300);
        const report = MOCK_REPORTS.find(r => r.id === id);
        if (!report) throw new Error('Report not found');
        return report;
    },
    generateReport: async () => {
        await delay(2000);
        return MOCK_REPORTS[0];
    },
    sendEmail: async (reportId: string, email: string) => {
        await delay(1000);
        console.log(`[Mock] Sent report ${reportId} to ${email}`);
        return { success: true };
    },
};
