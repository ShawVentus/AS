import React from 'react';
import { Lightbulb, Maximize2, ThumbsUp, ThumbsDown } from 'lucide-react';
import type { Paper } from '../../../types';

import { formatReportTime } from '../../../utils/date';

interface PaperCardProps {
    paper: Paper;
    index: number;
    showIndex?: boolean; // 是否显示序号标签，默认 true
    onOpenDetail: (paper: Paper) => void;
    onFeedback?: (paperId: string, data: { liked?: boolean, feedback?: string, note?: string }) => void;
}

export const PaperCard: React.FC<PaperCardProps> = ({ paper, index, showIndex = true, onOpenDetail, onFeedback }) => {
    const [showFeedbackMenu, setShowFeedbackMenu] = React.useState(false);
    const [feedbackType, setFeedbackType] = React.useState<'like' | 'dislike' | null>(null);
    const [customReason, setCustomReason] = React.useState('');

    const handleFeedbackClick = (e: React.MouseEvent, isLike: boolean) => {
        e.stopPropagation();
        if (isLike) {
            // Like usually doesn't need a reason, but we could add tags later.
            // For now, just trigger it.
            if (onFeedback) onFeedback(paper.meta.id, { liked: true });
            setShowFeedbackMenu(false);
        } else {
            // Dislike triggers menu
            setFeedbackType('dislike');
            setShowFeedbackMenu(!showFeedbackMenu);
        }
    };

    const submitDislike = (reason: string) => {
        if (onFeedback) onFeedback(paper.meta.id, { liked: false, feedback: reason });
        setShowFeedbackMenu(false);
        setCustomReason('');
    };

    // Close menu when clicking outside (simplified)
    React.useEffect(() => {
        const closeMenu = () => setShowFeedbackMenu(false);
        if (showFeedbackMenu) {
            window.addEventListener('click', closeMenu);
        }
        return () => window.removeEventListener('click', closeMenu);
    }, [showFeedbackMenu]);

    if (!paper?.meta) {
        console.warn('PaperCard received invalid paper data:', paper);
        return null;
    }



    return (
        <div
            className="group relative flex flex-col bg-slate-900/50 backdrop-blur-sm border border-slate-700 rounded-xl hover:border-cyan-500/50 transition-all duration-300 hover:shadow-2xl hover:shadow-cyan-900/10 cursor-pointer h-full"
            onClick={() => onOpenDetail(paper)}
        >
            {/* Index Tag */}
            {showIndex && (
                <div className="absolute -top-3 -left-3 w-6 h-6 rounded-full bg-indigo-600 flex items-center justify-center text-white text-xs font-bold shadow-lg shadow-indigo-900/20 z-20">
                    {index}
                </div>
            )}

            {/* Card Header */}
            <div className="p-5 pb-0 flex-grow relative">
                {/* Removed Top-Left Info as per request */}
                <div className="flex justify-between items-start mb-1 pl-8">
                    {/* Placeholder for spacing if needed, or just margin */}
                </div>

                <h3 className="text-base font-bold text-white mb-2 leading-snug group-hover:text-cyan-400 transition-colors line-clamp-2 mt-1">
                    {paper.meta.title}
                </h3>
                <p className="text-xs text-slate-500 mb-4 line-clamp-1">{paper.meta.authors.join(", ")}</p>

                {/* Why This Paper - Highlight */}
                {paper.user_state?.why_this_paper ? (
                    <div className="bg-indigo-950/30 border border-indigo-500/20 rounded-lg p-3 mb-2 relative overflow-hidden">
                        <div className="absolute top-0 left-0 w-1 h-full bg-indigo-500/50"></div>
                        <div className="text-indigo-400 text-sm font-bold mb-1 flex items-center gap-1.5 uppercase tracking-wider">
                            <Lightbulb size={16} />
                            推荐理由
                        </div>
                        <p className="text-slate-300 text-sm leading-relaxed">
                            {paper.user_state.why_this_paper}
                        </p>
                    </div>
                ) : (
                    <div className="bg-slate-800/30 border border-slate-700/30 rounded-lg p-3 mb-2">
                        <div className="text-slate-500 text-[10px] font-bold mb-1 uppercase tracking-wider">
                            一句话总结
                        </div>
                        <p className="text-slate-400 text-xs leading-relaxed line-clamp-3">
                            {paper.analysis?.tldr || paper.meta.abstract}
                        </p>
                    </div>
                )}
            </div>

            {/* Card Footer */}
            <div className="p-4 pt-0 mt-auto flex items-center justify-between border-t border-slate-800/50 pt-2 relative">
                <div className="flex flex-col gap-1.5 w-full">
                    {/* Bottom-Left Info: Score | Date | Category */}
                    <div className="flex items-center gap-2 text-xs font-medium flex-wrap">
                        {/* Relevance Score */}
                        <span className={`${(paper.user_state?.relevance_score || 0) >= 0.7 ? 'text-cyan-400' :
                            (paper.user_state?.relevance_score || 0) >= 0.4 ? 'text-yellow-400' :
                                'text-red-400'
                            }`}>
                            {(paper.user_state?.relevance_score || 0).toFixed(2)}
                        </span>
                        <span className="text-slate-600">|</span>
                        {/* Published Date (Now using Created At) */}
                        <span className="text-slate-400">{formatReportTime(paper.meta.created_at || paper.meta.published_date)}</span>
                        <span className="text-slate-600">|</span>
                        {/* Category - Show All */}
                        <div className="flex gap-1 flex-wrap">
                            {paper.meta.category?.map(cat => (
                                <span key={cat} className="text-slate-400">{cat}</span>
                            ))}
                        </div>
                    </div>


                </div>

                <div className="flex items-center gap-2">

                    <button
                        onClick={(e) => handleFeedbackClick(e, true)}
                        className={`p-1.5 rounded-full transition-colors ${paper.user_state?.user_liked === true ? 'text-green-400 bg-green-950/30' : 'text-slate-500 hover:text-green-400 hover:bg-green-950/30'}`}
                        title="喜欢"
                    >
                        <ThumbsUp size={14} />
                    </button>
                    <div className="relative">
                        <button
                            onClick={(e) => handleFeedbackClick(e, false)}
                            className={`p-1.5 rounded-full transition-colors ${paper.user_state?.user_liked === false ? 'text-red-400 bg-red-950/30' : 'text-slate-500 hover:text-red-400 hover:bg-red-950/30'}`}
                            title="不喜欢"
                        >
                            <ThumbsDown size={14} />
                        </button>

                        {/* Feedback Menu */}
                        {showFeedbackMenu && feedbackType === 'dislike' && (
                            <div
                                className="absolute bottom-full right-0 mb-2 w-48 bg-slate-900 border border-slate-700 rounded-lg shadow-xl z-50 p-2 animate-in fade-in zoom-in-95 duration-200"
                                onClick={(e) => e.stopPropagation()}
                            >
                                <div className="text-[10px] text-slate-500 font-bold px-2 py-1 mb-1">不感兴趣的原因?</div>
                                <div className="space-y-1">
                                    {['不相关', '太旧了', '已读过', '质量差'].map(reason => (
                                        <button
                                            key={reason}
                                            onClick={() => submitDislike(reason)}
                                            className="w-full text-left px-2 py-1.5 text-xs text-slate-300 hover:bg-slate-800 hover:text-white rounded transition-colors"
                                        >
                                            {reason}
                                        </button>
                                    ))}
                                    <div className="pt-1 border-t border-slate-800 mt-1">
                                        <input
                                            type="text"
                                            placeholder="其他原因..."
                                            className="w-full bg-slate-950 border border-slate-800 rounded px-2 py-1 text-xs text-white focus:border-cyan-500 focus:outline-none"
                                            value={customReason}
                                            onChange={(e) => setCustomReason(e.target.value)}
                                            onKeyDown={(e) => {
                                                if (e.key === 'Enter' && customReason.trim()) {
                                                    submitDislike(customReason);
                                                }
                                            }}
                                        />
                                    </div>
                                </div>
                            </div>
                        )}
                    </div>
                    <button
                        className="p-1.5 text-slate-500 hover:text-cyan-400 hover:bg-cyan-950/30 rounded-full transition-colors opacity-0 group-hover:opacity-100"
                        title="查看详情"
                    >
                        <Maximize2 size={14} />
                    </button>
                </div>
            </div>
        </div>
    );
};
