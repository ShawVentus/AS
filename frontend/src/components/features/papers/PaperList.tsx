import React, { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { Filter, Download, FileText, Calendar as CalendarIcon, X, ArrowUp } from 'lucide-react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { PaperAPI } from '../../../services/api';
import type { Paper } from '../../../types';
import { PaperCard } from './PaperCard';
import { PaperDetailModal } from '../../shared/PaperDetailModal';
import { Calendar } from '../../common/Calendar';
import { format } from 'date-fns';

interface PaperListProps {
    /** 点击打开详情的回调 */
    onOpenDetail?: (paper: Paper) => void;
    /** 当前选中的论文 */
    selectedPaper?: Paper | null;
    /** 设置选中论文的回调 */
    setSelectedPaper?: (paper: Paper | null) => void;
    /** 日期筛选 (YYYY-MM-DD) */
    dateFilter?: string | null;
    /** 清除日期筛选的回调 */
    onClearDateFilter?: () => void;
}

/**
 * 论文列表组件
 * 
 * 主要功能：
 * 1. 展示论文卡片列表
 * 2. 提供日期筛选和日历视图
 * 3. 提供相关度和类别筛选
 * 4. 支持点击查看论文详情
 * 5. 包含 Sticky Header 和回到顶部功能
 */
export const PaperList: React.FC<PaperListProps> = ({ dateFilter, onClearDateFilter }) => {
    const [selectedDate, setSelectedDate] = useState<Date | null>(new Date());
    const [paperDates, setPaperDates] = useState<string[]>([]);
    const [filteredPapers, setFilteredPapers] = useState<Paper[]>([]);
    const [modalPaper, setModalPaper] = useState<Paper | null>(null);
    const [showCalendar, setShowCalendar] = useState(false);

    // Filter States
    const [showFilterPanel, setShowFilterPanel] = useState(false);
    const [filterCategories, setFilterCategories] = useState<string[]>([]);
    const [filterRelevanceThreshold, setFilterRelevanceThreshold] = useState<number>(0.7); // Default 0.7

    // UI Refs
    const calendarRef = useRef<HTMLDivElement>(null);
    const filterRef = useRef<HTMLDivElement>(null);

    // Back to Top Logic
    const [showBackToTop, setShowBackToTop] = useState(false);
    const topSentinelRef = useRef<HTMLDivElement>(null);

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

    // Intersection Observer for Back to Top
    useEffect(() => {
        const observer = new IntersectionObserver(
            ([entry]) => {
                // 当哨兵元素离开视口时（即向下滚动后），显示回到顶部按钮
                setShowBackToTop(!entry.isIntersecting);
            },
            { threshold: 0 }
        );

        if (topSentinelRef.current) {
            observer.observe(topSentinelRef.current);
        }

        return () => observer.disconnect();
    }, []);

    /**
     * 获取指定月份的有论文的日期列表
     * 
     * Args:
     *   year (number): 年份
     *   month (number): 月份 (1-12)
     */
    const fetchPaperDates = useCallback(async (year: number, month: number) => {
        try {
            const dates = await PaperAPI.getPaperCalendar(year, month);
            setPaperDates(dates);
        } catch (error) {
            console.error("获取论文日期失败:", error);
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

    // [Refactor] Use React Query for fetching papers
    const { data: papers = [], isLoading: loading } = useQuery({
        queryKey: ['papers', effectiveDate],
        queryFn: async () => {
            const fetchedPapers = await PaperAPI.getRecommendations(effectiveDate);
            // Default sort by relevance desc
            fetchedPapers.sort((a, b) => (b.user_state?.relevance_score || 0) - (a.user_state?.relevance_score || 0));
            return fetchedPapers;
        },
        staleTime: 1000 * 60 * 5, // 5 minutes
    });

    // 1. Calculate papers that meet the relevance threshold
    const relevanceFilteredPapers = useMemo(() => {
        return papers.filter(p => (p.user_state?.relevance_score || 0) >= filterRelevanceThreshold);
    }, [papers, filterRelevanceThreshold]);

    // 2. Extract unique categories from the relevance-filtered papers
    const availableCategories = useMemo(() => {
        const cats = new Set<string>();
        relevanceFilteredPapers.forEach(p => {
            p.meta.category?.forEach(c => cats.add(c));
        });
        return Array.from(cats).sort();
    }, [relevanceFilteredPapers]);

    // 3. Apply category filter to get final list
    useEffect(() => {
        let result = relevanceFilteredPapers;

        if (filterCategories.length > 0) {
            result = result.filter(p => p.meta.category?.some(c => filterCategories.includes(c)));
        }

        setFilteredPapers(result);
    }, [relevanceFilteredPapers, filterCategories]);

    /**
     * 处理日历月份切换
     * 
     * Args:
     *   year (number): 年份
     *   month (number): 月份
     */
    const handleMonthChange = (year: number, month: number) => {
        fetchPaperDates(year, month);
    };

    /**
     * 处理日期选择
     * 
     * Args:
     *   date (Date | null): 选中的日期
     */
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

    /**
     * 打开论文详情模态框
     * 
     * Args:
     *   paper (Paper): 论文对象
     */
    const handleOpenDetail = (paper: Paper) => {
        setModalPaper(paper);
    };

    /**
     * 关闭论文详情模态框
     */
    const handleCloseDetail = () => {
        setModalPaper(null);
    };

    /**
     * 切换到下一篇论文
     */
    const handleNextPaper = () => {
        if (!modalPaper) return;
        const currentIndex = filteredPapers.findIndex(p => p.meta?.id === modalPaper.meta?.id);
        if (currentIndex !== -1 && currentIndex < filteredPapers.length - 1) {
            setModalPaper(filteredPapers[currentIndex + 1]);
        } else if (currentIndex === filteredPapers.length - 1) {
            setModalPaper(filteredPapers[0]);
        }
    };

    /**
     * 切换到上一篇论文
     */
    const handlePrevPaper = () => {
        if (!modalPaper) return;
        const currentIndex = filteredPapers.findIndex(p => p.meta?.id === modalPaper.meta?.id);
        if (currentIndex !== -1 && currentIndex > 0) {
            setModalPaper(filteredPapers[currentIndex - 1]);
        } else if (currentIndex === 0) {
            setModalPaper(filteredPapers[filteredPapers.length - 1]);
        }
    };

    /**
     * 重置筛选条件
     */
    const resetFilters = () => {
        setFilterCategories([]);
        setFilterRelevanceThreshold(0.7); // Reset to default 0.7
    };

    /**
     * 切换类别筛选选中状态
     * 
     * Args:
     *   cat (string): 类别名称
     */
    const toggleCategory = (cat: string) => {
        setFilterCategories(prev =>
            prev.includes(cat)
                ? prev.filter(c => c !== cat)
                : [...prev, cat]
        );
    };

    /**
     * 滚动回顶部
     */
    const scrollToTop = () => {
        topSentinelRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    const queryClient = useQueryClient();

    /**
     * 处理论文反馈 (Like, Dislike, Note)
     *
     * Args:
     *   paperId (string): 论文 ID
     *   data (object): 反馈数据 (liked, feedback, note)
     */
    const handleFeedback = async (paperId: string, data: { liked?: boolean, feedback?: string, note?: string }) => {
        // 辅助函数：确保 user_state 存在并合并数据
        const mergeState = (paper: Paper) => {
            const currentState = paper.user_state || {
                paper_id: paper.meta.id,
                user_id: '', // Placeholder
                relevance_score: 0,
                why_this_paper: '',
                accepted: false,
                user_accepted: false
            };
            return {
                ...paper,
                user_state: {
                    ...currentState,
                    ...data
                }
            };
        };

        // 1. 乐观更新列表状态 (Optimistic update)
        queryClient.setQueryData(['papers', effectiveDate], (oldPapers: Paper[] | undefined) => {
            if (!oldPapers) return [];
            return oldPapers.map(p => {
                if (p.meta.id === paperId) {
                    return mergeState(p);
                }
                return p;
            });
        });

        // 2. 如果当前模态框打开的是同一篇论文，也更新模态框状态
        if (modalPaper && modalPaper.meta.id === paperId) {
            setModalPaper(prev => {
                if (!prev) return null;
                return mergeState(prev);
            });
        }

        // 3. 发送 API 请求
        try {
            await PaperAPI.submitFeedback(paperId, data);
        } catch (error) {
            console.error("提交反馈失败:", error);
            // 失败时回滚乐观更新状态 (Revert optimistic update on failure)
            queryClient.invalidateQueries({ queryKey: ['papers', effectiveDate] });
        }
    };

    return (
        <div className="max-w-7xl mx-auto min-h-full flex flex-col animate-in fade-in relative">
            {/* 哨兵元素：用于检测是否需要显示回到顶部按钮 */}
            <div ref={topSentinelRef} className="absolute top-0 h-0 w-full pointer-events-none" />

            {/* Sticky Header Toolbar */}
            <div className="sticky top-0 z-50 bg-slate-950/80 backdrop-blur-md border-b border-slate-800 px-6 py-6 pb-4 transition-all">
                <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
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
                        <span className="text-sm font-medium text-slate-400 mr-2">
                            <span className="text-cyan-400">{filteredPapers.length}</span>
                            <span className="mx-1">/</span>
                            <span>{papers.length}</span>
                        </span>
                        <button
                            onClick={() => setShowFilterPanel(!showFilterPanel)}
                            className={`flex items-center gap-1.5 px-3 py-1.5 rounded text-xs border transition-colors ${showFilterPanel || filterCategories.length > 0 || filterRelevanceThreshold > 0.7
                                ? 'bg-slate-800 text-white border-blue-500 ring-1 ring-blue-500'
                                : 'bg-slate-800 hover:bg-slate-700 text-white border-slate-700'
                                }`}
                        >
                            <Filter size={14} /> 筛选
                            {(filterCategories.length > 0 || filterRelevanceThreshold > 0.7) && (
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
                                    <div className="text-xs text-slate-400 mb-2">类别 (多选)</div>
                                    <div className="max-h-40 overflow-y-auto scrollbar-thin scrollbar-thumb-slate-700">
                                        <div className="flex flex-wrap gap-2">
                                            {availableCategories.map(cat => {
                                                const isSelected = filterCategories.includes(cat);
                                                return (
                                                    <button
                                                        key={cat}
                                                        onClick={() => toggleCategory(cat)}
                                                        className={`px-2.5 py-1 rounded text-xs font-medium transition-colors border ${isSelected
                                                            ? 'bg-cyan-600 text-white border-cyan-500 shadow-sm shadow-cyan-900/50'
                                                            : 'bg-slate-800 text-slate-400 border-slate-700 hover:border-slate-600 hover:text-slate-300'
                                                            }`}
                                                    >
                                                        {cat}
                                                    </button>
                                                );
                                            })}
                                            {availableCategories.length === 0 && (
                                                <div className="text-xs text-slate-600 italic w-full">暂无类别</div>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            </div>
                        )}

                        <button className="flex items-center gap-1.5 bg-cyan-600 hover:bg-cyan-500 text-white px-3 py-1.5 rounded text-xs font-medium shadow-lg shadow-cyan-900/20 transition-colors">
                            <Download size={14} /> 批量下载
                        </button>
                    </div>
                </div>
            </div>

            {/* Paper Grid or Empty State */}
            <div className="px-6 pb-20 pt-8 flex-1">
                {loading ? (
                    <div className="flex-1 flex items-center justify-center text-slate-500 h-64">
                        加载中...
                    </div>
                ) : filteredPapers.length > 0 ? (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {filteredPapers.map((p, idx) => (
                            <PaperCard
                                key={p.meta?.id || Math.random()}
                                paper={p}
                                index={idx + 1}
                                onOpenDetail={handleOpenDetail}
                                onFeedback={handleFeedback}
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
            </div>

            {/* Back to Top Button */}
            <button
                onClick={scrollToTop}
                className={`fixed bottom-8 right-8 p-3 rounded-full bg-slate-800 border border-slate-700 text-white shadow-lg shadow-slate-900/50 hover:bg-slate-700 hover:border-cyan-500 transition-all duration-300 z-40 ${showBackToTop ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-10 pointer-events-none'
                    }`}
                aria-label="回到顶部"
                title="回到顶部"
            >
                <ArrowUp size={24} />
            </button>

            {/* Internal Modal */}
            <PaperDetailModal
                paper={modalPaper}
                index={modalPaper ? filteredPapers.findIndex(p => p.meta?.id === modalPaper.meta?.id) : undefined}
                total={filteredPapers.length}
                onClose={handleCloseDetail}
                onNext={handleNextPaper}
                onPrev={handlePrevPaper}
                onFeedback={handleFeedback}
            />
        </div>
    );
};
