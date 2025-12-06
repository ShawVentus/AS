import React, { useEffect } from 'react';
import { X, Download, ExternalLink, FileText, Brain, Microscope, Lightbulb, Target, ChevronLeft, ChevronRight, ThumbsUp, ThumbsDown, Save } from 'lucide-react';
import type { Paper } from '../../types';

interface PaperDetailModalProps {
    paper: Paper | null;
    index?: number;
    total?: number;
    onClose: () => void;
    onNext?: () => void;
    onPrev?: () => void;
    onFeedback?: (paperId: string, isLike: boolean, reason?: string) => void;
}

export const PaperDetailModal: React.FC<PaperDetailModalProps> = ({ paper, index, total, onClose, onNext, onPrev, onFeedback }) => {
    // Analysis state removed as per request to remove Deep Analysis section
    // const [analysis, setAnalysis] = useState<PaperAnalysis | null>(null);
    // const [loadingAnalysis, setLoadingAnalysis] = useState(false);

    // useEffect(() => {
    //     if (paper) {
    //         // setLoadingAnalysis(true);
    //         // PaperAPI.getAnalysis(paper.id)
    //         //     .then(setAnalysis)
    //         //     .catch(console.error)
    //         //     .finally(() => setLoadingAnalysis(false));
    //     } else {
    //         // setAnalysis(null);
    //     }
    // }, [paper]);

    const scrollRef = React.useRef<HTMLDivElement>(null);

    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            if (!paper) return;
            if (e.key === 'ArrowLeft' && onPrev) onPrev();
            if (e.key === 'ArrowRight' && onNext) onNext();
            if (e.key === 'Escape') onClose();
        };

        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, [paper, onNext, onPrev, onClose]);

    // Reset scroll position when paper changes
    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = 0;
        }
    }, [paper]);

    if (!paper?.meta) return null;

    return (
        <div
            className="fixed inset-0 z-[100] flex items-center justify-center p-4 md:p-8 bg-black/80 backdrop-blur-sm animate-in fade-in duration-200"
            onClick={onClose}
        >
            {/* Navigation Buttons (Outside Modal) */}
            {onPrev && (
                <button
                    onClick={(e) => { e.stopPropagation(); onPrev(); }}
                    className="absolute left-4 top-1/2 -translate-y-1/2 p-3 bg-slate-900/50 hover:bg-slate-800 text-slate-400 hover:text-white rounded-full border border-slate-700/50 transition-all hover:scale-110 hidden md:flex"
                >
                    <ChevronLeft size={24} />
                </button>
            )}
            {onNext && (
                <button
                    onClick={(e) => { e.stopPropagation(); onNext(); }}
                    className="absolute right-4 top-1/2 -translate-y-1/2 p-3 bg-slate-900/50 hover:bg-slate-800 text-slate-400 hover:text-white rounded-full border border-slate-700/50 transition-all hover:scale-110 hidden md:flex z-50"
                >
                    <ChevronRight size={24} />
                </button>
            )}

            <div className="absolute inset-0 bg-black/80 backdrop-blur-sm" onClick={onClose} />
            <div
                className="bg-slate-900 w-full max-w-4xl max-h-full rounded-2xl shadow-2xl border border-slate-800 flex flex-col relative animate-in fade-in zoom-in-95 duration-300 overflow-visible"
                onClick={(e) => e.stopPropagation()}
            > {/* Added animation and overflow-visible */}

                {/* Floating Index Tag */}
                {index !== undefined && total !== undefined && (
                    <div className="absolute -top-3 -left-3 w-8 h-8 rounded-full bg-indigo-600 flex items-center justify-center text-white text-sm font-bold shadow-lg shadow-indigo-900/20 z-50">
                        {index}
                    </div>
                )}

                <button
                    onClick={onClose}
                    className="absolute top-4 right-4 text-slate-400 hover:text-white transition-colors z-10"
                >
                    <X size={24} />
                </button>

                {/* Header */}
                <div className="p-6 border-b border-slate-800 bg-slate-900/30 shrink-0 pr-16 rounded-t-2xl">
                    <div className="flex justify-between items-start">
                        <div>
                            {/* Top Info Bar: Score | Date | Category */}
                            <div className="flex items-center gap-2 text-xs font-medium mb-3">
                                {/* Relevance Score */}
                                <span className={`${(paper.user_state?.relevance_score || 0) >= 0.7 ? 'text-cyan-400' :
                                    (paper.user_state?.relevance_score || 0) >= 0.4 ? 'text-yellow-400' :
                                        'text-red-400'
                                    }`}>
                                    {(paper.user_state?.relevance_score || 0).toFixed(2)}
                                </span>
                                <span className="text-slate-600">|</span>
                                <span className="text-slate-400">{paper.meta.published_date}</span>
                                <span className="text-slate-600">|</span>
                                <div className="flex gap-1 flex-wrap">
                                    {paper.meta.category?.map(cat => (
                                        <span key={cat} className="text-slate-400">{cat}</span>
                                    ))}
                                </div>
                            </div>

                            <h2 className="text-xl md:text-2xl font-bold text-white mb-2 leading-snug">{paper.meta.title}</h2>
                            <p className="text-slate-400 text-sm">{paper.meta.authors.join(", ")}</p>
                        </div>
                        <div className="flex gap-2">
                            <button
                                onClick={() => onFeedback && onFeedback(paper.meta.id, true)}
                                className={`p-2 rounded-full transition-colors ${paper.user_state?.user_liked === true ? 'text-green-400 bg-green-950/30' : 'text-slate-500 hover:text-green-400 hover:bg-green-950/30'}`}
                                title="喜欢"
                            >
                                <ThumbsUp size={20} />
                            </button>
                            <button
                                onClick={() => onFeedback && onFeedback(paper.meta.id, false)}
                                className={`p-2 rounded-full transition-colors ${paper.user_state?.user_liked === false ? 'text-red-400 bg-red-950/30' : 'text-slate-500 hover:text-red-400 hover:bg-red-950/30'}`}
                                title="不喜欢"
                            >
                                <ThumbsDown size={20} />
                            </button>
                        </div>
                    </div>
                </div>

                {/* Content Scrollable Area */}
                <div
                    ref={scrollRef}
                    className="flex-1 overflow-y-auto p-6 space-y-6 scrollbar-thin scrollbar-thumb-slate-800 scrollbar-track-transparent"
                >

                    {/* Why This Paper (Top Priority) */}
                    {paper.user_state?.why_this_paper && (
                        <div className="bg-indigo-950/20 border border-indigo-500/30 rounded-lg p-5 relative overflow-hidden">
                            <div className="absolute top-0 left-0 w-1 h-full bg-indigo-500"></div>
                            <h3 className="text-indigo-400 font-bold text-sm mb-2 flex items-center gap-2 uppercase tracking-wider">
                                <Lightbulb size={16} /> 推荐理由
                            </h3>
                            <p className="text-slate-200 text-sm leading-relaxed">{paper.user_state.why_this_paper}</p>
                        </div>
                    )}



                    {/* TLDR */}
                    <div className="bg-slate-900/50 p-5 rounded-lg border border-slate-800/50">
                        <h3 className="text-slate-300 font-bold text-xs uppercase tracking-wider mb-2 flex items-center gap-2">
                            <span className="font-mono font-bold">TL;DR（一句话总结）</span>
                        </h3>
                        <p className="text-slate-300 font-medium text-sm leading-relaxed">
                            {/* Try multiple fields for robustness */}
                            {paper.analysis?.tldr || (paper.analysis as any)?.summary || "暂无"}
                        </p>
                    </div>

                    {/* Grid for Details */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        {/* Motivation */}
                        <div className="bg-slate-900/20 p-4 rounded-lg border border-slate-800/30">
                            <h3 className="text-slate-300 font-bold text-xs uppercase tracking-wider mb-2 flex items-center gap-2">
                                <Target size={14} /> Motivation（研究动机）
                            </h3>
                            <p className="text-slate-400 text-sm leading-relaxed">{paper.analysis?.motivation || "暂无"}</p>
                        </div>

                        {/* Method */}
                        <div className="bg-slate-900/20 p-4 rounded-lg border border-slate-800/30">
                            <h3 className="text-slate-300 font-bold text-xs uppercase tracking-wider mb-2 flex items-center gap-2">
                                <Brain size={14} /> Method（研究方法）
                            </h3>
                            <p className="text-slate-400 text-sm leading-relaxed">{paper.analysis?.method || "暂无"}</p>
                        </div>

                        {/* Result */}
                        <div className="bg-slate-900/20 p-4 rounded-lg border border-slate-800/30">
                            <h3 className="text-slate-300 font-bold text-xs uppercase tracking-wider mb-2 flex items-center gap-2">
                                <Brain size={14} /> Result（实验结果）
                            </h3>
                            <p className="text-slate-400 text-sm leading-relaxed">{paper.analysis?.result || "暂无"}</p>
                        </div>

                        {/* Conclusion */}
                        <div className="bg-slate-900/20 p-4 rounded-lg border border-slate-800/30">
                            <h3 className="text-slate-300 font-bold text-xs uppercase tracking-wider mb-2 flex items-center gap-2">
                                <Microscope size={14} /> Conclusion（结论）
                            </h3>
                            <p className="text-slate-400 text-sm leading-relaxed">{paper.analysis?.conclusion || "暂无"}</p>
                        </div>
                    </div>

                    {/* Abstract (Moved to bottom) */}
                    <div>
                        <h3 className="text-slate-500 font-bold text-xs uppercase tracking-wider mb-2 flex items-center gap-2">
                            <FileText size={14} /> Abstract（摘要）
                        </h3>
                        <p className="text-slate-300 leading-7 text-sm text-justify">{paper.meta.abstract}</p>
                    </div>
                </div>

                {/* Footer Actions */}
                <div className="p-4 border-t border-slate-800 bg-slate-900/50 flex flex-col gap-4 shrink-0">

                    {/* Notes Section */}
                    <div className="w-full">
                        <label className="text-xs font-bold text-slate-500 mb-2 block flex items-center gap-2">
                            <FileText size={12} /> 个人笔记 (Notes)
                        </label>
                        <div className="flex gap-2">
                            <textarea
                                className="flex-1 bg-slate-950 border border-slate-800 rounded-lg p-3 text-sm text-slate-300 focus:border-cyan-500 focus:outline-none resize-none h-20"
                                placeholder="记录对此论文的想法、启发或备忘..."
                            ></textarea>
                            <button className="h-20 px-4 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-lg text-xs font-medium text-slate-400 hover:text-white transition-colors flex flex-col items-center justify-center gap-1">
                                <Save size={16} />
                                保存
                            </button>
                        </div>
                    </div>

                    <div className="flex items-center justify-between w-full pt-2 border-t border-slate-800/50">
                        <div className="flex gap-3 items-center text-xs text-slate-500 font-medium">
                            {/* Bottom Left Progress: Just numbers */}
                            {index !== undefined && total !== undefined && (
                                <span>{index} / {total}</span>
                            )}
                        </div>

                        <div className="flex gap-3 items-center">
                            <span className="text-[10px] text-slate-500 hidden md:inline-block mr-2">
                                使用 <span className="border border-slate-700 rounded px-1">←</span> <span className="border border-slate-700 rounded px-1">→</span> 切换
                            </span>

                            {/* Links Moved to Bottom Right */}
                            <a href={paper.meta.links.html} target="_blank" rel="noreferrer" className="flex items-center gap-2 px-3 py-2 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-lg text-xs font-medium text-slate-300 hover:text-white transition-colors">
                                <ExternalLink size={14} /> HTML
                            </a>
                            <a href={paper.meta.links.arxiv} target="_blank" rel="noreferrer" className="flex items-center gap-2 px-3 py-2 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-lg text-xs font-medium text-slate-300 hover:text-white transition-colors">
                                <ExternalLink size={14} /> Arxiv
                            </a>
                            <a href={paper.meta.links.pdf} target="_blank" rel="noreferrer" className="flex items-center gap-2 px-3 py-2 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-lg text-xs font-medium text-slate-300 hover:text-white transition-colors">
                                <FileText size={14} /> PDF
                            </a>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};
