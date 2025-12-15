import React from 'react';
import { Plus, Loader2, ChevronRight } from 'lucide-react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { ReportAPI } from '../../../services/api';
import type { Report } from '../../../types';

import { formatReportTime } from '../../../utils/date';

interface ReportListProps {
    onSelectReport: (report: Report) => void;
}

export const ReportList: React.FC<ReportListProps> = ({ onSelectReport }) => {
    const queryClient = useQueryClient();
    const [generating, setGenerating] = React.useState(false);

    const { data: reports = [] } = useQuery({
        queryKey: ['reports'],
        queryFn: ReportAPI.getReports,
        staleTime: 1000 * 60 * 5, // 5 minutes
    });

    const handleGenerate = async () => {
        setGenerating(true);
        try {
            await ReportAPI.generateReport();
            // Invalidate query to refetch list
            queryClient.invalidateQueries({ queryKey: ['reports'] });
        } catch (error) {
            console.error('Failed to generate report:', error);
            alert('生成失败');
        } finally {
            setGenerating(false);
        }
    };

    return (
        <div className="p-6 max-w-4xl mx-auto animate-in fade-in">
            <div className="flex justify-between items-center mb-6">
                <h2 className="text-xl font-bold text-white">历史研报</h2>
                <button
                    onClick={handleGenerate}
                    disabled={generating}
                    className="flex items-center gap-2 px-4 py-2 bg-cyan-600 hover:bg-cyan-500 disabled:bg-slate-800 disabled:text-slate-500 text-white text-sm font-medium rounded-lg transition-colors shadow-lg shadow-cyan-900/20"
                >
                    {generating ? <Loader2 size={16} className="animate-spin" /> : <Plus size={16} />}
                    生成今日研报
                </button>
            </div>
            <div className="space-y-3">
                {reports.map(report => (
                    <div key={report.id} onClick={() => onSelectReport(report)} className="bg-slate-900 border border-slate-800 p-4 rounded-lg hover:border-cyan-500/50 cursor-pointer group flex justify-between items-center transition-all">
                        <div>
                            <h3 className="text-sm font-bold text-slate-200 group-hover:text-cyan-400 mb-1 transition-colors">{report.title}</h3>
                            <p className="text-xs text-slate-500 line-clamp-1">{report.summary}</p>
                        </div>
                        <div className="flex items-center gap-3 ml-4 shrink-0">
                            <span className="text-xs text-slate-500 bg-slate-800 px-2 py-0.5 rounded-full">
                                {formatReportTime(report.created_at || report.date)}
                            </span>
                            <ChevronRight size={16} className="text-slate-600 group-hover:text-cyan-500 transition-colors" />
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
};
