import React, { useEffect, useState } from 'react';
import { X, Download, ExternalLink, FileText, Brain, Microscope, Lightbulb, Target, ChevronLeft, ChevronRight, ThumbsUp, ThumbsDown, Loader2, Save } from 'lucide-react';
import type { Paper, PaperAnalysis } from '../../types';
import { PaperAPI } from '../../services/api';

interface PaperDetailModalProps {
    paper: Paper | null;
    onClose: () => void;
    onNext?: () => void;
    onPrev?: () => void;
    onFeedback?: (paperId: string, isLike: boolean, reason?: string) => void;
}

export const PaperDetailModal: React.FC<PaperDetailModalProps> = ({ paper, onClose, onNext, onPrev, onFeedback }) => {
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

    if (!paper) return null;

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
                    className="absolute right-4 top-1/2 -translate-y-1/2 p-3 bg-slate-900/50 hover:bg-slate-800 text-slate-400 hover:text-white rounded-full border border-slate-700/50 transition-all hover:scale-110 hidden md:flex"
                >
                    <ChevronRight size={24} />
                </button>
            )}

            <div
                className="bg-slate-950 w-full max-w-4xl h-[90vh] rounded-xl border border-slate-800 shadow-2xl flex flex-col overflow-hidden relative ring-1 ring-slate-700"
                onClick={(e) => e.stopPropagation()}
            >

                {/* Close Button */}
                <button
                    onClick={onClose}
                    className="absolute top-4 right-4 z-10 p-2 bg-slate-900/80 hover:bg-slate-800 rounded-full text-slate-400 hover:text-white transition-colors border border-slate-800"
                >
                    <X size={20} />
                </button>

                {/* Header */}
                <div className="p-6 border-b border-slate-800 bg-slate-900/30 shrink-0 pr-16">
                    <div className="flex justify-between items-start">
                        <div>
                            <div className="flex gap-3 mb-3">
                                <span className="px-2 py-0.5 rounded text-xs font-bold bg-cyan-950 text-cyan-400 border border-cyan-900/50">{paper.category}</span>
                                <span className="px-2 py-0.5 rounded text-xs font-bold bg-slate-800 text-slate-400 border border-slate-700">{paper.date}</span>
                            </div>
                            <h2 className="text-xl md:text-2xl font-bold text-white mb-2 leading-snug">{paper.title}</h2>
                            <p className="text-slate-400 text-sm">{paper.authors.join(", ")}</p>
                        </div>
                        <div className="flex gap-2">
                            <button
                                onClick={() => onFeedback && onFeedback(paper.id, true)}
                                className={`p-2 rounded-full transition-colors ${paper.isLiked === true ? 'text-green-400 bg-green-950/30' : 'text-slate-500 hover:text-green-400 hover:bg-green-950/30'}`}
                                title="喜欢"
                            >
                                <ThumbsUp size={20} />
                            </button>
                            <button
                                onClick={() => onFeedback && onFeedback(paper.id, false)}
                                className={`p-2 rounded-full transition-colors ${paper.isLiked === false ? 'text-red-400 bg-red-950/30' : 'text-slate-500 hover:text-red-400 hover:bg-red-950/30'}`}
                                title="不喜欢"
                            >
                                <ThumbsDown size={20} />
                            </button>
                        </div>
                    </div>
                </div>

                {/* Content Scrollable Area */}
                <div className="flex-1 overflow-y-auto p-6 space-y-6 scrollbar-thin scrollbar-thumb-slate-800 scrollbar-track-transparent">

                    {/* Why This Paper (Top Priority) */}
                    {paper.whyThisPaper && (
                        <div className="bg-indigo-950/20 border border-indigo-500/30 rounded-lg p-5 relative overflow-hidden">
                            <div className="absolute top-0 left-0 w-1 h-full bg-indigo-500"></div>
                            <h3 className="text-indigo-400 font-bold text-sm mb-2 flex items-center gap-2 uppercase tracking-wider">
                                <Lightbulb size={16} /> 推荐理由
                            </h3>
                            <p className="text-slate-200 text-sm leading-relaxed">{paper.whyThisPaper}</p>
                        </div>
                    )}



                    {/* TLDR */}
                    <div className="bg-slate-900/50 p-5 rounded-lg border border-slate-800/50">
                        <h3 className="text-slate-500 font-bold text-xs uppercase tracking-wider mb-2 flex items-center gap-2">
                            <span className="font-mono font-bold text-cyan-500">一句话总结</span>
                        </h3>
                        <p className="text-slate-300 font-medium text-sm leading-relaxed">{paper.tldr}</p>
                    </div>

                    {/* Abstract */}
                    <div>
                        <h3 className="text-slate-500 font-bold text-xs uppercase tracking-wider mb-2 flex items-center gap-2">
                            <FileText size={14} /> 摘要
                        </h3>
                        <p className="text-slate-300 leading-7 text-sm text-justify">{paper.details.abstract}</p>
                    </div>

                    {/* Grid for Details */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        {/* Motivation */}
                        <div className="bg-slate-900/20 p-4 rounded-lg border border-slate-800/30">
                            <h3 className="text-slate-500 font-bold text-xs uppercase tracking-wider mb-2 flex items-center gap-2">
                                <Target size={14} /> 研究动机
                            </h3>
                            <p className="text-slate-400 text-sm leading-relaxed">{paper.details.motivation}</p>
                        </div>

                        {/* Method */}
                        <div className="bg-slate-900/20 p-4 rounded-lg border border-slate-800/30">
                            <h3 className="text-slate-500 font-bold text-xs uppercase tracking-wider mb-2 flex items-center gap-2">
                                <Brain size={14} /> 研究方法
                            </h3>
                            <p className="text-slate-400 text-sm leading-relaxed">{paper.details.method}</p>
                        </div>

                        {/* Result */}
                        <div className="bg-slate-900/20 p-4 rounded-lg border border-slate-800/30">
                            <h3 className="text-emerald-500/80 font-bold text-xs uppercase tracking-wider mb-2 flex items-center gap-2">
                                <Brain size={14} /> 实验结果
                            </h3>
                            <p className="text-slate-400 text-sm leading-relaxed">{paper.details.result}</p>
                        </div>

                        {/* Conclusion */}
                        <div className="bg-slate-900/20 p-4 rounded-lg border border-slate-800/30">
                            <h3 className="text-cyan-500/80 font-bold text-xs uppercase tracking-wider mb-2 flex items-center gap-2">
                                <Microscope size={14} /> 结论
                            </h3>
                            <p className="text-slate-400 text-sm leading-relaxed">{paper.details.conclusion}</p>
                        </div>
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
                        <div className="flex gap-3">
                            <a href={paper.links.html} target="_blank" rel="noreferrer" className="flex items-center gap-2 px-3 py-2 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-lg text-xs font-medium text-slate-300 hover:text-white transition-colors">
                                <ExternalLink size={14} /> HTML
                            </a>
                            <a href={paper.links.arxiv} target="_blank" rel="noreferrer" className="flex items-center gap-2 px-3 py-2 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-lg text-xs font-medium text-slate-300 hover:text-white transition-colors">
                                <ExternalLink size={14} /> Arxiv
                            </a>
                            <a href={paper.links.pdf} target="_blank" rel="noreferrer" className="flex items-center gap-2 px-3 py-2 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-lg text-xs font-medium text-slate-300 hover:text-white transition-colors">
                                <Download size={14} /> PDF
                            </a>
                        </div>

                        <div className="flex gap-3 items-center">
                            <span className="text-[10px] text-slate-500 hidden md:inline-block mr-2">
                                使用 <span className="border border-slate-700 rounded px-1">←</span> <span className="border border-slate-700 rounded px-1">→</span> 切换
                            </span>
                            <a
                                href={paper.links.pdf}
                                download
                                target="_blank"
                                rel="noreferrer"
                                className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-white text-sm font-medium rounded-lg transition-colors shadow-lg shadow-cyan-900/20 flex items-center gap-2"
                            >
                                <Download size={16} /> 下载 PDF
                            </a>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};
