import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Filter, Download, FileText, Calendar as CalendarIcon, X } from 'lucide-react';
import { PaperAPI } from '../../../services/api';
import type { Paper } from '../../../types';
import { PaperCard } from './PaperCard';
import { PaperDetailModal } from '../../shared/PaperDetailModal';
import { Calendar } from '../../common/Calendar';
import { format } from 'date-fns';

interface PaperListProps {
    onOpenDetail?: (paper: Paper) => void;
    selectedPaper?: Paper | null;
    setSelectedPaper?: (paper: Paper | null) => void;
}

export const PaperList: React.FC<PaperListProps> = () => {
    const [selectedDate, setSelectedDate] = useState<Date | null>(new Date());
    const [paperDates, setPaperDates] = useState<string[]>([]);
    const [papers, setPapers] = useState<Paper[]>([]);
    const [loading, setLoading] = useState(false);
    const [modalPaper, setModalPaper] = useState<Paper | null>(null);
    const [showCalendar, setShowCalendar] = useState(false);
    const calendarRef = useRef<HTMLDivElement>(null);

    // Close calendar when clicking outside
    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (calendarRef.current && !calendarRef.current.contains(event.target as Node)) {
                setShowCalendar(false);
            }
        };

        document.addEventListener('mousedown', handleClickOutside);
        return () => {
            document.removeEventListener('mousedown', handleClickOutside);
        };
    }, []);

    // Fetch paper dates for the calendar
    const fetchPaperDates = useCallback(async (year: number, month: number) => {
        try {
            const dates = await PaperAPI.getPaperCalendar(year, month);
            setPaperDates(dates);
        } catch (error) {
            console.error("Failed to fetch paper dates:", error);
        }
    }, []);

    // Fetch papers when date changes
    useEffect(() => {
        const fetchPapers = async () => {
            setLoading(true);
            try {
                const dateStr = selectedDate ? format(selectedDate, 'yyyy-MM-dd') : undefined;
                const fetchedPapers = await PaperAPI.getRecommendations(dateStr);
                setPapers(fetchedPapers);
            } catch (error) {
                console.error("Failed to fetch papers:", error);
            } finally {
                setLoading(false);
            }
        };

        fetchPapers();
    }, [selectedDate]);

    const handleMonthChange = (year: number, month: number) => {
        fetchPaperDates(year, month);
    };

    const handleDateSelect = (date: Date | null) => {
        setSelectedDate(date);
        if (date) {
            setShowCalendar(false); // Close on selection
        }
    };

    const handleOpenDetail = (paper: Paper) => {
        setModalPaper(paper);
    };

    const handleCloseDetail = () => {
        setModalPaper(null);
    };

    const handleNextPaper = () => {
        if (!modalPaper) return;
        const currentIndex = papers.findIndex(p => p.meta?.id === modalPaper.meta?.id);
        if (currentIndex !== -1 && currentIndex < papers.length - 1) {
            setModalPaper(papers[currentIndex + 1]);
        } else if (currentIndex === papers.length - 1) {
            setModalPaper(papers[0]);
        }
    };

    const handlePrevPaper = () => {
        if (!modalPaper) return;
        const currentIndex = papers.findIndex(p => p.meta?.id === modalPaper.meta?.id);
        if (currentIndex !== -1 && currentIndex > 0) {
            setModalPaper(papers[currentIndex - 1]);
        } else if (currentIndex === 0) {
            setModalPaper(papers[papers.length - 1]);
        }
    };

    return (
        <div className="p-6 max-w-7xl mx-auto h-full flex flex-col animate-in fade-in">
            {/* Header Toolbar */}
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-6 pb-4 border-b border-slate-800 gap-4">
                <div className="flex items-center gap-4">
                    <h2 className="text-2xl font-bold text-white">论文管理</h2>

                    {/* Calendar Trigger */}
                    <div className="relative" ref={calendarRef}>
                        <button
                            onClick={() => setShowCalendar(!showCalendar)}
                            className={`flex items-center gap-2 px-3 py-1.5 rounded text-sm font-medium transition-colors border ${showCalendar || selectedDate
                                ? 'bg-slate-800 text-white border-blue-500 ring-1 ring-blue-500'
                                : 'bg-slate-900 text-slate-400 border-slate-700 hover:border-slate-500'
                                }`}
                        >
                            <CalendarIcon size={16} className={selectedDate ? 'text-blue-400' : ''} />
                            <span>
                                {selectedDate ? format(selectedDate, 'yyyy-MM-dd') : 'Select Date'}
                            </span>
                            {selectedDate && (
                                <div
                                    onClick={(e) => {
                                        e.stopPropagation();
                                        setSelectedDate(null);
                                    }}
                                    className="ml-1 p-0.5 hover:bg-slate-700 rounded-full"
                                >
                                    <X size={12} />
                                </div>
                            )}
                        </button>

                        {/* Calendar Popover */}
                        {showCalendar && (
                            <div className="absolute top-full left-0 mt-2 z-50 animate-in fade-in zoom-in-95 duration-200">
                                <Calendar
                                    selectedDate={selectedDate}
                                    onDateSelect={handleDateSelect}
                                    paperDates={paperDates}
                                    onMonthChange={handleMonthChange}
                                />
                            </div>
                        )}
                    </div>
                </div>

                <div className="flex items-center gap-2">
                    <button className="flex items-center gap-1.5 bg-slate-800 hover:bg-slate-700 text-white px-3 py-1.5 rounded text-xs border border-slate-700 transition-colors">
                        <Filter size={14} /> 筛选
                    </button>
                    <button className="flex items-center gap-1.5 bg-cyan-600 hover:bg-cyan-500 text-white px-3 py-1.5 rounded text-xs font-medium shadow-lg shadow-cyan-900/20 transition-colors">
                        <Download size={14} /> 批量下载
                    </button>
                </div>
            </div>

            {/* Paper Grid or Empty State */}
            {loading ? (
                <div className="flex-1 flex items-center justify-center text-slate-500">
                    加载中...
                </div>
            ) : papers.length > 0 ? (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 pb-20">
                    {papers.map(p => (
                        <PaperCard key={p.meta?.id || Math.random()} paper={p} onOpenDetail={handleOpenDetail} />
                    ))}
                </div>
            ) : (
                <div className="flex-1 flex flex-col items-center justify-center text-slate-500 min-h-[400px]">
                    <div className="w-16 h-16 bg-slate-800 rounded-full flex items-center justify-center mb-4">
                        <FileText size={32} className="text-slate-600" />
                    </div>
                    <p className="text-lg font-medium text-slate-400">暂无论文</p>
                    <p className="text-sm text-slate-600 mt-2">
                        {selectedDate ? '该日期下没有已收录的论文' : '您的私有库中还没有论文'}
                    </p>
                </div>
            )}

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
