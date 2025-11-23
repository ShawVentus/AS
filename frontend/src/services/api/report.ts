import { fetchJSON } from './config';
import type { Report } from '../../types';

export const ReportAPI = {
    getReports: () => fetchJSON<Report[]>('/reports/'),
    getReportDetail: (id: string) => fetchJSON<Report>(`/reports/${id}`),
    generateReport: () => fetchJSON<Report>('/reports/generate', { method: 'POST' }),
    sendEmail: (reportId: string, email: string) => fetchJSON<{ success: boolean }>('/reports/send', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ report_id: reportId, email })
    }),
};
