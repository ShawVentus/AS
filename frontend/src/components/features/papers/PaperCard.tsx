import React, { useState, useEffect } from 'react';
import { ThumbsUp, ThumbsDown, X, Download, Lightbulb, ChevronUp, ChevronDown, ExternalLink, Maximize2 } from 'lucide-react';
import type { Paper } from '../../../data/mockData';
import { cn } from '../../../utils/cn';

interface PaperCardProps {
    paper: Paper;
    onOpenDetail: (paper: Paper) => void;
}

export const PaperCard: React.FC<PaperCardProps> = ({ paper, onOpenDetail }) => {
    const [isExpanded, setIsExpanded] = useState(false);
    const [feedback, setFeedback] = useState<'like' | 'dislike' | null>(paper.isLiked === true ? 'like' : paper.isLiked === false ? 'dislike' : null);
    const [showDislikeForm, setShowDislikeForm] = useState(false);
    const [dislikeReason, setDislikeReason] = useState("");

    useEffect(() => {
        if (feedback === 'dislike') {
            setShowDislikeForm(true);
        } else {
            setShowDislikeForm(false);
        }
    }, [feedback]);

    const handleDislikeSubmit = () => {
        // Simulate AI feedback
        alert("已收到反馈。Agent将减少此类推荐，并优化您的个性化模型。");
        setShowDislikeForm(false);
        setFeedback(null);
    };

    return (
        <div className={cn(
            "group relative bg-slate-900 border border-slate-800 rounded-lg overflow-hidden hover:border-slate-600 transition-all",
            isExpanded ? "ring-1 ring-cyan-900" : ""
        )}>
            {/* Summary View */}
            <div className="p-4">
                <div className="flex justify-between items-start mb-2">
                    <div className="flex gap-2 mb-2">
                        <span className="px-2 py-0.5 rounded text-xs font-bold bg-cyan-950 text-cyan-400 border border-cyan-900/50">{paper.category}</span>
                        <span className="px-2 py-0.5 rounded text-xs font-bold bg-slate-800 text-slate-400 border border-slate-700">{paper.date}</span>
                    </div>
                    <div className="flex gap-2">
                        <button
                            onClick={() => onOpenDetail && onOpenDetail(paper)}
                            className="p-1.5 text-slate-400 hover:text-white hover:bg-slate-800 rounded transition-colors"
                            title="Full Detail"
                        >
                            <Maximize2 size={16} />
                        </button>
                    </div>
                </div>

                <h3
                    className="text-lg font-bold text-white mb-2 leading-snug cursor-pointer hover:text-cyan-400 transition-colors"
                    onClick={() => onOpenDetail && onOpenDetail(paper)}
                >
                    {paper.title}
                </h3>
                <p className="text-sm text-slate-400 mb-4">{paper.authors.join(", ")}</p>

                {/* Why This Paper - Always Visible */}
                {paper.whyThisPaper && (
                    <div className="bg-indigo-950/20 border border-indigo-500/30 rounded-lg p-3 mb-4">
                        <div className="text-indigo-400 text-xs font-bold mb-1 flex items-center gap-1.5">
                            <Lightbulb size={12} />
                            Why This Paper
                        </div>
                        <p className="text-slate-300 text-sm leading-relaxed">{paper.whyThisPaper}</p>
                    </div>
                )}

                <div className="flex items-center justify-between">
                    <div className="flex gap-2">
                        {paper.tags.map(tag => (
                            <span key={tag} className="text-xs text-slate-500 bg-slate-900 px-2 py-1 rounded border border-slate-800">#{tag}</span>
                        ))}
                    </div>
                    <div className="flex items-center gap-2">
                        <button
                            onClick={() => setIsExpanded(!isExpanded)}
                            className="flex items-center gap-1 text-xs font-medium text-slate-400 hover:text-white transition-colors"
                        >
                            {isExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                            {isExpanded ? '收起' : '展开'}
                        </button>
                    </div>
                </div>
            </div>

            {showDislikeForm && (
                <div className="mx-4 mb-3 p-3 bg-red-950/10 border border-red-900/20 rounded animate-in fade-in slide-in-from-top-1" onClick={e => e.stopPropagation()}>
                    <div className="flex justify-between items-center mb-2">
                        <span className="text-[10px] font-bold text-red-400">请告知原因，以便优化推荐：</span>
                        <button onClick={() => { setShowDislikeForm(false); setFeedback(null) }} className="text-slate-500 hover:text-white"><X size={12} /></button>
                    </div>
                    <div className="flex flex-wrap gap-1.5 mb-2">
                        {["类别不相关", "质量低", "已读过", "方法陈旧"].map(tag => (
                            <button key={tag} onClick={() => setDislikeReason(tag)} className="text-[10px] bg-slate-800 hover:bg-red-900/30 text-slate-400 hover:text-red-300 px-2 py-0.5 rounded border border-transparent hover:border-red-900/50 transition-colors">{tag}</button>
                        ))}
                    </div>
                    <div className="flex gap-2">
                        <input
                            type="text"
                            placeholder="其他原因..."
                            value={dislikeReason}
                            onChange={(e) => setDislikeReason(e.target.value)}
                            className="flex-1 bg-slate-950 border border-slate-700 rounded px-2 py-1 text-[10px] text-white placeholder-slate-600 focus:outline-none focus:border-red-500/50"
                        />
                        <button onClick={handleDislikeSubmit} className="bg-red-900/30 hover:bg-red-900/50 text-red-300 text-[10px] px-3 rounded border border-red-900/50">提交</button>
                    </div>
                </div>
            )}

            {/* Expanded Content */}
            {isExpanded && (
                <div className="border-t border-slate-800 bg-slate-900/30 p-4 animate-in slide-in-from-top-2 duration-200">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                        <div>
                            <h4 className="text-xs font-bold text-slate-500 uppercase mb-2">Motivation</h4>
                            <p className="text-sm text-slate-300 leading-relaxed">{paper.details.motivation}</p>
                        </div>
                        <div>
                            <h4 className="text-xs font-bold text-slate-500 uppercase mb-2">Method</h4>
                            <p className="text-sm text-slate-300 leading-relaxed">{paper.details.method}</p>
                        </div>
                    </div>

                    <div className="mb-4">
                        <h4 className="text-xs font-bold text-slate-500 uppercase mb-2">TL;DR</h4>
                        <p className="text-sm text-slate-300 leading-relaxed">{paper.tldr}</p>
                    </div>

                    <div className="flex justify-between items-center pt-2 border-t border-slate-800/50">
                        <div className="flex gap-3">
                            <a href={paper.links.html} target="_blank" rel="noreferrer" className="flex items-center gap-1 text-xs text-slate-400 hover:text-cyan-400">
                                <ExternalLink size={12} /> HTML
                            </a>
                            <a href={paper.links.arxiv} target="_blank" rel="noreferrer" className="flex items-center gap-1 text-xs text-slate-400 hover:text-red-400">
                                <ExternalLink size={12} /> Arxiv
                            </a>
                            <a href={paper.links.pdf} target="_blank" rel="noreferrer" className="flex items-center gap-1 text-xs text-slate-400 hover:text-white">
                                <Download size={12} /> PDF
                            </a>
                        </div>
                        <div className="flex gap-2">
                            <button
                                onClick={() => setFeedback(feedback === 'like' ? null : 'like')}
                                className={cn(
                                    "p-2 rounded-full transition-colors",
                                    feedback === 'like' ? "bg-green-500/20 text-green-400" : "hover:bg-slate-800 text-slate-400"
                                )}
                            >
                                <ThumbsUp size={16} />
                            </button>
                            <button
                                onClick={() => setFeedback(feedback === 'dislike' ? null : 'dislike')}
                                className={cn(
                                    "p-2 rounded-full transition-colors",
                                    feedback === 'dislike' ? "bg-red-500/20 text-red-400" : "hover:bg-slate-800 text-slate-400"
                                )}
                            >
                                <ThumbsDown size={16} />
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};
