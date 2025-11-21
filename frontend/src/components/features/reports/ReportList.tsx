import React from 'react';
import { ChevronRight } from 'lucide-react';
import { MOCK_REPORTS } from '../../../data/mockData';
import type { Report } from '../../../data/mockData';

interface ReportListProps {
    onSelectReport: (report: Report) => void;
}

export const ReportList: React.FC<ReportListProps> = ({ onSelectReport }) => {
    return (
        <div className="p-6 max-w-4xl mx-auto animate-in fade-in">
            <h2 className="text-xl font-bold text-white mb-6">历史研读报告</h2>
            <div className="space-y-3">
                {MOCK_REPORTS.map(report => (
                    <div key={report.id} onClick={() => onSelectReport(report)} className="bg-slate-900 border border-slate-800 p-4 rounded-lg hover:border-cyan-500/50 cursor-pointer group flex justify-between items-center transition-all">
                        <div>
                            <h3 className="text-sm font-bold text-slate-200 group-hover:text-cyan-400 mb-1 transition-colors">{report.title}</h3>
                            <p className="text-xs text-slate-500 line-clamp-1">{report.summary}</p>
                        </div>
                        <ChevronRight size={16} className="text-slate-600 group-hover:text-cyan-500 transition-colors" />
                    </div>
                ))}
            </div>
        </div>
    );
};
