import React, { useState } from 'react';
import { Calendar, Filter, Download, ChevronDown, X } from 'lucide-react';
import { MOCK_PAPERS } from '../../../data/mockData';
import type { Paper } from '../../../data/mockData';
import { PaperCard } from './PaperCard';
import { cn } from '../../../utils/cn';

interface PaperListProps {
    onOpenDetail: (paper: Paper) => void;
    selectedPaper: Paper | null;
    setSelectedPaper: (paper: Paper | null) => void;
}

export const PaperList: React.FC<PaperListProps> = ({ onOpenDetail, selectedPaper, setSelectedPaper }) => {
    const [selectedDate, setSelectedDate] = useState('2025-10-24');

    return (
        <div className="p-6 max-w-5xl mx-auto h-full flex flex-col animate-in fade-in">
            {/* Header Toolbar */}
            <div className="flex justify-between items-center mb-4 pb-4 border-b border-slate-800">
                <div className="flex items-center gap-4">
                    <h2 className="text-xl font-bold text-white">论文管理</h2>
                    <div className="relative group">
                        <button className="flex items-center gap-2 bg-slate-900 border border-slate-700 text-slate-300 px-3 py-1.5 rounded text-xs hover:border-cyan-500 transition-colors">
                            <Calendar size={12} />
                            <span>{selectedDate}</span>
                            <ChevronDown size={12} />
                        </button>
                        <div className="absolute top-full left-0 mt-1 w-32 bg-slate-900 border border-slate-700 rounded shadow-xl hidden group-hover:block z-20">
                            {['2025-10-24', '2025-10-23', '2025-10-22'].map(d => (
                                <div key={d} onClick={() => setSelectedDate(d)} className="px-3 py-2 text-xs text-slate-400 hover:text-white hover:bg-slate-800 cursor-pointer">
                                    {d}
                                </div>
                            ))}
                        </div>
                    </div>
                </div>

                <div className="flex items-center gap-2">
                    <button className="flex items-center gap-1.5 bg-slate-800 hover:bg-slate-700 text-white px-3 py-1.5 rounded text-xs border border-slate-700">
                        <Filter size={12} /> 筛选
                    </button>
                    <button className="flex items-center gap-1.5 bg-cyan-600 hover:bg-cyan-500 text-white px-3 py-1.5 rounded text-xs font-medium shadow-lg shadow-cyan-900/20 transition-colors">
                        <Download size={12} /> 批量下载列表
                    </button>
                </div>
            </div>

            {selectedPaper && (
                <div className="mb-6 bg-slate-950 border border-slate-700 rounded-lg p-5 relative ring-1 ring-cyan-500/30 shadow-2xl animate-in fade-in slide-in-from-top-2">
                    <button onClick={() => setSelectedPaper(null)} className="absolute top-3 right-3 text-slate-500 hover:text-white"><X size={16} /></button>
                    <div className="flex gap-2 mb-3">
                        <span className="bg-cyan-950 text-cyan-400 px-1.5 py-0.5 rounded text-[10px] font-bold border border-cyan-900">FULL DETAIL</span>
                        {selectedPaper.tags.map(t => <span key={t} className="bg-slate-800 text-slate-400 px-1.5 py-0.5 rounded text-[10px]">{t}</span>)}
                    </div>
                    <h1 className="text-lg font-bold text-white mb-1">{selectedPaper.title}</h1>
                    <p className="text-xs text-slate-400 mb-4">{selectedPaper.authors.join(", ")}</p>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4 text-xs">
                        <div className="md:col-span-2 bg-slate-900 p-3 rounded border border-slate-800">
                            <h3 className="text-[10px] font-bold text-white mb-1 uppercase opacity-70">Abstract</h3>
                            <p className="text-slate-400 leading-relaxed">{selectedPaper.details.abstract}</p>
                        </div>
                        <div className="space-y-2">
                            <div className="bg-slate-900 p-3 rounded border border-slate-800">
                                <h3 className="text-[10px] font-bold text-emerald-500 mb-1 uppercase">Result</h3>
                                <p className="text-slate-400">{selectedPaper.details.result}</p>
                            </div>
                        </div>
                    </div>
                    <div className="flex justify-end">
                        <button className="bg-white text-slate-900 px-4 py-1.5 rounded text-xs font-bold hover:bg-slate-200">Open PDF</button>
                    </div>
                </div>
            )}

            <div className="space-y-3 pb-20">
                {MOCK_PAPERS.map(p => (
                    <PaperCard key={p.id} paper={p} onOpenDetail={onOpenDetail} />
                ))}
            </div>
        </div>
    );
};
