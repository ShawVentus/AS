import React, { useState, useEffect, useCallback, useRef, useMemo } from 'react';
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
    dateFilter?: string | null; // 日期筛选 (YYYY-MM-DD)
    onClearDateFilter?: () => void; // 清除日期筛选
}

export const PaperList: React.FC<PaperListProps> = ({ dateFilter, onClearDateFilter }) => {
    const [selectedDate, setSelectedDate] = useState<Date | null>(new Date());
    const [paperDates, setPaperDates] = useState<string[]>([]);
    const [papers, setPapers] = useState<Paper[]>([]);
    const [filteredPapers, setFilteredPapers] = useState<Paper[]>([]);
    const [loading, setLoading] = useState(false);
    const [modalPaper, setModalPaper] = useState<Paper | null>(null);
    const [showCalendar, setShowCalendar] = useState(false);

    // Filter States
    const [showFilterPanel, setShowFilterPanel] = useState(false);
    const [filterCategory, setFilterCategory] = useState<string | null>(null);
    const [filterRelevanceThreshold, setFilterRelevanceThreshold] = useState<number>(0.7); // Default 0.7

    const calendarRef = useRef<HTMLDivElement>(null);
    const filterRef = useRef<HTMLDivElement>(null);

    // Close calendar and filter when clicking outside
    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (calendarRef.current && !calendarRef.current.contains(event.target as Node)) {
                setShowCalendar(false);
            }
            if (filterRef.current && !filterRef.current.contains(event.target as Node)) {
                setShowFilterPanel(false);
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

    // 计算实际使用的日期：优先使用 dateFilter，否则使用 selectedDate
    const effectiveDate = useMemo(() => {
        return dateFilter || (selectedDate ? format(selectedDate, 'yyyy-MM-dd') : undefined);
    }, [dateFilter, selectedDate]);

    // 当 dateFilter 传入时，同步更新 selectedDate（用于日历显示）
    useEffect(() => {
        if (dateFilter && selectedDate) {
            const currentDateStr = format(selectedDate, 'yyyy-MM-dd');
            // 只有不一致时才更新
            if (currentDateStr !== dateFilter) {
                setSelectedDate(new Date(dateFilter));
            }
        } else if (dateFilter && !selectedDate) {
            setSelectedDate(new Date(dateFilter));
        }
    }, [dateFilter]);

    // Fetch papers when effectiveDate changes
    useEffect(() => {
        const fetchPapers = async () => {
            setLoading(true);
            try {
                const fetchedPapers = await PaperAPI.getRecommendations(effectiveDate);

                // Default sort by relevance desc
                fetchedPapers.sort((a, b) => (b.user_state?.relevance_score || 0) - (a.user_state?.relevance_score || 0));

                setPapers(fetchedPapers);
            } catch (error) {
                console.error("Failed to fetch papers:", error);
            } finally {
                setLoading(false);
            }
        };

        fetchPapers();
    }, [effectiveDate]); // 只依赖 effectiveDate

    // Apply filters locally
    useEffect(() => {
        let result = [...papers];

        // 1. Category Filter
        if (filterCategory) {
            result = result.filter(p => p.meta.category?.includes(filterCategory));
        }

        // 2. Relevance Threshold Filter (Show papers >= threshold)
        result = result.filter(p => (p.user_state?.relevance_score || 0) >= filterRelevanceThreshold);

        setFilteredPapers(result);
    }, [papers, filterCategory, filterRelevanceThreshold]);

    // Extract unique categories for filter
    const availableCategories = Array.from(new Set(papers.flatMap(p => p.meta.category || []))).sort();

    const handleMonthChange = (year: number, month: number) => {
        fetchPaperDates(year, month);
    };

    const handleDateSelect = (date: Date | null) => {
        setSelectedDate(date);
        // 清除 dateFilter，使用手动选择的日期优先
        if (onClearDateFilter) {
            onClearDateFilter();
        }
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
        const currentIndex = filteredPapers.findIndex(p => p.meta?.id === modalPaper.meta?.id);
        if (currentIndex !== -1 && currentIndex < filteredPapers.length - 1) {
            setModalPaper(filteredPapers[currentIndex + 1]);
        } else if (currentIndex === filteredPapers.length - 1) {
            setModalPaper(filteredPapers[0]);
        }
    };

    const handlePrevPaper = () => {
        if (!modalPaper) return;
        const currentIndex = filteredPapers.findIndex(p => p.meta?.id === modalPaper.meta?.id);
        if (currentIndex !== -1 && currentIndex > 0) {
            setModalPaper(filteredPapers[currentIndex - 1]);
        } else if (currentIndex === 0) {
            setModalPaper(filteredPapers[filteredPapers.length - 1]);
        }
    };

    const resetFilters = () => {
        setFilterCategory(null);
        setFilterRelevanceThreshold(0.7); // Reset to default 0.7
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

                <div className="flex items-center gap-2 relative" ref={filterRef}>
                    <button
                        onClick={() => setShowFilterPanel(!showFilterPanel)}
                        className={`flex items-center gap-1.5 px-3 py-1.5 rounded text-xs border transition-colors ${showFilterPanel || filterCategory || filterRelevanceThreshold > 0.7
                            ? 'bg-slate-800 text-white border-blue-500 ring-1 ring-blue-500'
                            : 'bg-slate-800 hover:bg-slate-700 text-white border-slate-700'
                            }`}
                    >
                        <Filter size={14} /> 筛选
                        {(filterCategory || filterRelevanceThreshold > 0.7) && (
                            <span className="w-2 h-2 rounded-full bg-blue-500 ml-1"></span>
                        )}
                    </button>

                    {/* Filter Panel */}
                    {showFilterPanel && (
                        <div className="absolute top-full right-0 mt-2 w-72 bg-slate-900 border border-slate-700 rounded-xl shadow-2xl z-50 p-4 animate-in fade-in zoom-in-95 duration-200">
                            <div className="flex justify-between items-center mb-4">
                                <h3 className="text-sm font-bold text-white">筛选条件</h3>
                                <button onClick={resetFilters} className="text-xs text-slate-400 hover:text-white">重置</button>
                            </div>

                            {/* Relevance Slider */}
                            <div className="mb-6">
                                <div className="flex justify-between text-xs text-slate-400 mb-2">
                                    <span>最低相关度</span>
                                    <span className="text-cyan-400 font-bold">{filterRelevanceThreshold.toFixed(1)}</span>
                                </div>
                                <input
                                    type="range"
                                    min="0"
                                    max="1"
                                    step="0.1"
                                    value={filterRelevanceThreshold}
                                    onChange={(e) => setFilterRelevanceThreshold(parseFloat(e.target.value))}
                                    className="w-full h-1 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-cyan-500"
                                />
                                <div className="flex justify-between text-[10px] text-slate-600 mt-1">
                                    <span>0.0</span>
                                    <span>1.0</span>
                                </div>
                            </div>

                            {/* Categories */}
                            <div>
                                <div className="text-xs text-slate-400 mb-2">类别</div>
                                <div className="max-h-40 overflow-y-auto space-y-1 scrollbar-thin scrollbar-thumb-slate-700">
                                    {availableCategories.map(cat => (
                                        <label key={cat} className="flex items-center gap-2 p-1.5 hover:bg-slate-800 rounded cursor-pointer">
                                            <input
                                                type="checkbox"
                                                checked={filterCategory === cat}
                                                onChange={() => setFilterCategory(filterCategory === cat ? null : cat)}
                                                className="rounded border-slate-700 bg-slate-950 text-cyan-500 focus:ring-offset-0 focus:ring-1 focus:ring-cyan-500"
                                            />
                                            <span className="text-xs text-slate-300">{cat}</span>
                                        </label>
                                    ))}
                                    {availableCategories.length === 0 && (
                                        <div className="text-xs text-slate-600 italic">暂无类别</div>
                                    )}
                                </div>
                            </div>
                        </div>
                    )}

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
            ) : filteredPapers.length > 0 ? (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 pb-20">
                    {filteredPapers.map((p, idx) => (
                        <PaperCard
                            key={p.meta?.id || Math.random()}
                            paper={p}
                            index={idx + 1}
                            onOpenDetail={handleOpenDetail}
                        />
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
                index={modalPaper ? filteredPapers.findIndex(p => p.meta?.id === modalPaper.meta?.id) + 1 : undefined}
                total={filteredPapers.length}
                onClose={handleCloseDetail}
                onNext={handleNextPaper}
                onPrev={handlePrevPaper}
            />
        </div>
    );
};
