import React, { useState, useMemo } from 'react';
import { Calendar, Filter, Download, ChevronDown } from 'lucide-react';
import { PaperAPI } from '../../../services/api';
import type { Paper } from '../../../types';
import { PaperCard } from './PaperCard';
import { PaperDetailModal } from '../../shared/PaperDetailModal';

interface PaperListProps {
    // onOpenDetail is no longer strictly needed if handled internally, 
    // but we can keep it if we want to support external control or just ignore it.
    // For now, I'll make it optional or just not use it.
    onOpenDetail?: (paper: Paper) => void;
    selectedPaper?: Paper | null;
    setSelectedPaper?: (paper: Paper | null) => void;
}

export const PaperList: React.FC<PaperListProps> = () => {
    const [selectedDate, setSelectedDate] = useState('2025-10-24');
    const [modalPaper, setModalPaper] = useState<Paper | null>(null);

    const [papers, setPapers] = useState<Paper[]>([]);

    React.useEffect(() => {
        PaperAPI.getPapers().then(setPapers).catch(console.error);
    }, []);

    // In a real app, we would filter papers based on selectedDate
    // For now, we use the fetched papers as the source
    const filteredPapers = useMemo(() => {
        return papers;
    }, [papers]);

    const handleOpenDetail = (paper: Paper) => {
        setModalPaper(paper);
    };

    const handleCloseDetail = () => {
        setModalPaper(null);
    };

    const handleNextPaper = () => {
        if (!modalPaper) return;
        const currentIndex = filteredPapers.findIndex(p => p.meta?.id === modalPaper.meta?.id);
        if (currentIndex !== -1 && currentIndex < filteredPapers.length - 1) {
            setModalPaper(filteredPapers[currentIndex + 1]);
        } else if (currentIndex === filteredPapers.length - 1) {
            // Loop back to start? Or stop? Let's loop for better UX
            setModalPaper(filteredPapers[0]);
        }
    };

    const handlePrevPaper = () => {
        if (!modalPaper) return;
        const currentIndex = filteredPapers.findIndex(p => p.meta?.id === modalPaper.meta?.id);
        if (currentIndex !== -1 && currentIndex > 0) {
            setModalPaper(filteredPapers[currentIndex - 1]);
        } else if (currentIndex === 0) {
            // Loop to end
            setModalPaper(filteredPapers[filteredPapers.length - 1]);
        }
    };

    return (
        <div className="p-6 max-w-7xl mx-auto h-full flex flex-col animate-in fade-in">
            {/* Header Toolbar */}
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-6 pb-4 border-b border-slate-800 gap-4">
                <div className="flex items-center gap-4">
                    <h2 className="text-2xl font-bold text-white">论文管理</h2>
                    <div className="relative group">
                        <button className="flex items-center gap-2 bg-slate-900 border border-slate-700 text-slate-300 px-3 py-1.5 rounded text-xs hover:border-cyan-500 transition-colors">
                            <Calendar size={14} />
                            <span>{selectedDate}</span>
                            <ChevronDown size={14} />
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
                    <button className="flex items-center gap-1.5 bg-slate-800 hover:bg-slate-700 text-white px-3 py-1.5 rounded text-xs border border-slate-700 transition-colors">
                        <Filter size={14} /> 筛选
                    </button>
                    <button className="flex items-center gap-1.5 bg-cyan-600 hover:bg-cyan-500 text-white px-3 py-1.5 rounded text-xs font-medium shadow-lg shadow-cyan-900/20 transition-colors">
                        <Download size={14} /> 批量下载列表
                    </button>
                </div>
            </div>

            {/* Paper Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 pb-20">
                {filteredPapers.map(p => (
                    <PaperCard key={p.meta?.id || Math.random()} paper={p} onOpenDetail={handleOpenDetail} />
                ))}
            </div>

            {/* Internal Modal */}
            <PaperDetailModal
                paper={modalPaper}
                onClose={handleCloseDetail}
                onNext={handleNextPaper}
                onPrev={handlePrevPaper}
            />
        </div>
    );
};
