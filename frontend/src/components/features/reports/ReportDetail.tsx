import React, { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ChevronLeft, Microscope, ArrowRightCircle, Compass, Mail, Loader2, X, Target, Quote } from 'lucide-react';
import type { Report, Paper } from '../../../types';
import { PaperAPI } from '../../../services/api/paper';
import { ReportAPI } from '../../../services/api/report';
import { cn } from '../../../utils/cn';
import { parseMarkdown } from '../../../utils/markdownParser';
import type { ParsedParagraph } from '../../../utils/markdownParser';
import { RefSentence } from './RefSentence';


interface ReportDetailProps {
    report: Report;
    onBack: () => void;
    onNavigateToPaper: (paper: Paper | null, papersList?: Paper[], filterDate?: string) => void;
}

export const ReportDetail: React.FC<ReportDetailProps> = ({ report, onBack, onNavigateToPaper }) => {
    // 状态管理
    const [hoveredRefIds, setHoveredRefIds] = useState<string[]>([]); // 实时悬停状态（用于高亮）
    const [lockedRefIds, setLockedRefIds] = useState<string[]>([]); // 锁定的引用 ID（用于右侧显示）
    const [viewMode, setViewMode] = useState<'all' | 'preview'>('all'); // 显示模式: 'all' 显示全部, 'preview' 显示预览
    const [hoveredPaperId, setHoveredPaperId] = useState<string | null>(null); // 悬停的论文 ID (右侧)

    const [parsedContent, setParsedContent] = useState<ParsedParagraph[]>([]);
    const [sendingEmail, setSendingEmail] = useState(false);

    // [Refactor] Use React Query for fetching referenced papers
    const { data: papers = [], isLoading: loadingPapers } = useQuery({
        queryKey: ['papersByIds', report.refPapers],
        queryFn: async () => {
            if (!report.refPapers || report.refPapers.length === 0) return [];
            return PaperAPI.getPapersByIds(report.refPapers);
        },
        enabled: !!report.refPapers && report.refPapers.length > 0,
        staleTime: 1000 * 60 * 30, // 30 minutes (report refs rarely change)
    });

    useEffect(() => {
        // 1. 解析 Markdown 内容
        if (report.content) {
            setParsedContent(parseMarkdown(report.content));
        }
    }, [report]);

    // 计算当前激活的论文列表
    let activePapers = papers;
    // 根据显示模式过滤论文
    if (viewMode === 'preview' && lockedRefIds.length > 0) {
        activePapers = papers.filter(p => lockedRefIds.includes(p.meta.id));
    }
    // 如果是 'all' 模式，则显示所有论文

    // Debug logs

    /**
     * 处理引用句子悬停进入事件
     * 
     * 功能: 更新实时悬停状态，并切换到预览模式锁定当前引用
     * 
     * Args:
     *   refIds (string[]): 引用句子的关联论文ID列表
     */
    const handleRefMouseEnter = (refIds: string[]) => {
        setHoveredRefIds(refIds); // 更新实时悬停状态（用于高亮）
        setLockedRefIds(refIds); // 锁定引用 ID
        setViewMode('preview'); // 切换到预览模式
    };

    /**
     * 处理引用句子悬停离开事件
     * 
     * 功能: 仅清除实时高亮状态，保持右侧预览内容不变
     */
    const handleRefMouseLeave = () => {
        setHoveredRefIds([]); // 清除实时悬停（取消高亮）
        // 不清除 lockedRefIds，保持预览状态
    };

    /**
     * 切换回"全部引用论文"模式
     * 
     * 功能: 清除锁定状态，显示所有论文
     */
    const handleShowAllPapers = () => {
        setViewMode('all');
        setLockedRefIds([]);
        setHoveredRefIds([]);
    };
    // 处理引用点击事件 (直接跳转到第一篇论文详情)
    const handleRefClick = (refIds: string[]) => {
        // 找到对应的第一篇论文
        const targetPaper = papers.find(p => refIds.includes(p.meta.id));
        if (targetPaper) {
            // 传递完整的 papers 列表，以便在详情页中翻页
            onNavigateToPaper(targetPaper, papers);
        }
    };

    // 处理右侧论文卡片悬停
    const handlePaperHover = (paperId: string | null) => {
        setHoveredPaperId(paperId);
    };

    const handleSendEmail = async () => {
        const email = prompt("请输入接收邮箱:");
        if (!email) return;

        setSendingEmail(true);
        try {
            await ReportAPI.sendEmail(report.id, email);
            alert('邮件发送成功');
        } catch (error) {
            console.error('Failed to send email:', error);
            alert('发送失败');
        } finally {
            setSendingEmail(false);
        }
    };

    return (
        <div className="flex h-full overflow-hidden animate-in fade-in">
            {/* Left Side: Report Content */}
            <div className="flex-1 flex flex-col min-w-0">
                <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-slate-950 sticky top-0 z-10">
                    <div className="flex items-center gap-3">
                        <button onClick={onBack} className="p-1.5 hover:bg-slate-800 rounded-full text-slate-400 hover:text-white transition-colors">
                            <ChevronLeft size={18} />
                        </button>
                        <div>
                            <h2 className="text-base font-bold text-white leading-tight">{report.title}</h2>
                            <div className="flex items-center gap-2 mt-0.5">
                                <span className="text-[11px] text-slate-500">{report.createdAt?.split('T')[0] || report.date}</span>
                            </div>
                        </div>
                    </div>
                    <div className="flex gap-2">
                        <button
                            onClick={handleSendEmail}
                            disabled={sendingEmail}
                            className="text-xs bg-slate-900 hover:bg-slate-800 text-slate-300 px-3 py-1.5 rounded border border-slate-800 hover:border-slate-600 transition-all flex items-center gap-2"
                        >
                            {sendingEmail ? <Loader2 size={14} className="animate-spin" /> : <Mail size={14} />}
                            发送邮件
                        </button>
                        <button onClick={() => onNavigateToPaper(null, [], report.date)} className="text-xs bg-slate-900 hover:bg-slate-800 text-slate-300 px-3 py-1.5 rounded border border-slate-800 hover:border-slate-600 transition-all">
                            查看论文列表
                        </button>
                    </div>
                </div>

                <div className="flex-1 overflow-y-auto p-6 md:p-8">
                    <div className="max-w-3xl mx-auto pb-20">
                        <div className="relative bg-gradient-to-br from-slate-900 via-slate-900 to-purple-950/40 border border-purple-800/50 rounded-xl p-6 shadow-xl shadow-purple-900/20 overflow-hidden mb-8 group">
                            {/* Decorative Background Icon */}
                            <Quote className="absolute top-4 right-6 text-purple-600/10 rotate-12 transform scale-150" size={80} />

                            <div className="relative z-10">
                                <h3 className="flex items-center gap-2 text-lg font-bold mb-4">
                                    <Target size={18} className="text-purple-500" />
                                    <span className="text-transparent bg-clip-text bg-gradient-to-r from-purple-500 to-violet-500">
                                        核心摘要
                                    </span>
                                </h3>
                                <p className="text-base md:text-lg text-slate-300 leading-relaxed italic border-l-2 border-purple-700/50 pl-4">
                                    {report.summary}
                                </p>
                            </div>
                        </div>

                        <div className="space-y-6 text-base md:text-lg leading-relaxed text-slate-300">
                            {parsedContent.map((paragraph, idx) => {
                                // 渲染标题
                                if (paragraph.type === 'heading') {
                                    const Tag = `h${Math.min(paragraph.level || 2, 6)}` as React.ElementType;
                                    return (
                                        <Tag key={idx} className={cn(
                                            "font-bold text-white mt-6 mb-3",
                                            paragraph.level === 1 ? "text-2xl" : "text-xl"
                                        )}>
                                            {paragraph.fragments.map((f, _) => f.content).join('')}
                                        </Tag>
                                    );
                                }

                                // 渲染列表
                                if (paragraph.type === 'list') {
                                    return (
                                        <ul key={idx} className="list-disc list-inside space-y-1 pl-4">
                                            <li className="text-slate-300">
                                                {paragraph.fragments.map((frag, fragIdx) =>
                                                    frag.type === 'ref-sentence' && frag.refIds ? (
                                                        <RefSentence
                                                            key={fragIdx}
                                                            text={frag.content}
                                                            refIds={frag.refIds}
                                                            isHovered={frag.refIds.some(id => hoveredRefIds.includes(id))}
                                                            isPaperHovered={hoveredPaperId ? frag.refIds.includes(hoveredPaperId) : false}
                                                            isSelected={false} // 不再使用固定状态，传 false 或移除属性(需改接口)
                                                            onMouseEnter={handleRefMouseEnter}
                                                            onMouseLeave={handleRefMouseLeave}
                                                            onClick={handleRefClick}
                                                            className={fragIdx === 0 ? "-ml-1" : ""}
                                                        />
                                                    ) : (
                                                        <span key={fragIdx}>{frag.content}</span>
                                                    )
                                                )}
                                            </li>
                                        </ul>
                                    );
                                }

                                // 渲染普通段落
                                return (
                                    <div key={idx} className="group relative pl-4 border-l-2 border-transparent hover:border-slate-700 transition-colors">
                                        <p>
                                            {paragraph.fragments.map((frag, fragIdx) =>
                                                frag.type === 'ref-sentence' && frag.refIds ? (
                                                    <RefSentence
                                                        key={fragIdx}
                                                        text={frag.content}
                                                        refIds={frag.refIds}
                                                        isHovered={frag.refIds.some(id => hoveredRefIds.includes(id))}
                                                        isPaperHovered={hoveredPaperId ? frag.refIds.includes(hoveredPaperId) : false}
                                                        isSelected={false}
                                                        onMouseEnter={handleRefMouseEnter}
                                                        onMouseLeave={handleRefMouseLeave}
                                                        onClick={handleRefClick}
                                                        className={fragIdx === 0 ? "-ml-1" : ""}
                                                    />
                                                ) : (
                                                    <span key={fragIdx}>{frag.content}</span>
                                                )
                                            )}
                                        </p>
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                </div>
            </div>

            {/* Right Side: Fixed Context Panel */}
            <div className="w-80 border-l border-slate-800 bg-slate-950 hidden lg:flex flex-col">
                <div className="p-4 border-b border-slate-800 bg-slate-900/30 flex items-center justify-between gap-2">
                    {/* 左侧：标题按钮 - 点击可切换回全部显示 */}
                    <button
                        onClick={handleShowAllPapers}
                        className="text-xs font-bold text-slate-500 uppercase tracking-wider flex items-center gap-2 hover:text-slate-300 transition-colors cursor-pointer flex-1 text-left"
                        title="点击显示全部引用论文"
                    >
                        <Microscope size={14} />
                        {viewMode === 'preview' ? `关联论文预览 (${activePapers.length})` : `全部引用论文 (${activePapers.length})`}
                    </button>

                    {/* 右侧：关闭预览按钮（仅在预览模式下显示）*/}
                    {viewMode === 'preview' && (
                        <button
                            onClick={handleShowAllPapers}
                            className="p-1 hover:bg-slate-800 rounded text-slate-500 hover:text-slate-300 transition-colors"
                            title="关闭预览"
                        >
                            <X size={14} />
                        </button>
                    )}
                </div>
                <div className="flex-1 p-4 overflow-y-auto space-y-4 transition-opacity duration-200">
                    {activePapers.length > 0 ? (
                        activePapers.map((activePaper) => (
                            <div key={activePaper!.meta.id}
                                className={cn(
                                    "animate-in fade-in slide-in-from-right-2 duration-300 bg-slate-900/50 p-3 rounded border transition-colors cursor-pointer",
                                    // 高亮样式：如果左侧悬停了该论文的引用，或者鼠标直接悬停在卡片上
                                    (hoveredRefIds.includes(activePaper!.meta.id) || hoveredPaperId === activePaper!.meta.id)
                                        ? "border-cyan-500/50 bg-slate-800/80 shadow-lg shadow-cyan-900/20"
                                        : "border-slate-800 hover:border-cyan-500/30"
                                )}
                                onClick={() => onNavigateToPaper(activePaper, papers)}
                                onMouseEnter={() => handlePaperHover(activePaper!.meta.id)}
                                onMouseLeave={() => handlePaperHover(null)}
                            >
                                {/* 顶部元数据栏：分数 | 日期 | 类别 (仿照 PaperCard 样式) */}
                                <div className="flex items-center gap-2 mb-2 text-[10px] font-medium text-slate-400 flex-wrap">
                                    {/* Relevance Score */}
                                    {activePaper!.user_state?.relevance_score !== undefined && (
                                        <span className={cn(
                                            (activePaper!.user_state?.relevance_score || 0) >= 0.7 ? 'text-cyan-400' :
                                                (activePaper!.user_state?.relevance_score || 0) >= 0.4 ? 'text-yellow-400' :
                                                    'text-red-400'
                                        )}>
                                            {(activePaper!.user_state?.relevance_score || 0).toFixed(2)}
                                        </span>
                                    )}
                                    <span className="text-slate-600">|</span>

                                    {/* Date */}
                                    <span className="text-slate-400">
                                        {activePaper!.meta.published_date.split('T')[0]}
                                    </span>
                                    <span className="text-slate-600">|</span>

                                    {/* Categories - Show All */}
                                    <div className="flex gap-1 flex-wrap">
                                        {activePaper!.meta.category?.map(cat => (
                                            <span key={cat} className="text-slate-400">{cat}</span>
                                        ))}
                                    </div>
                                </div>

                                <h4 className="text-sm font-bold text-white mb-1 leading-snug line-clamp-2">{activePaper!.meta.title}</h4>
                                <p className="text-xs text-slate-500 mb-2 line-clamp-1">{activePaper!.meta.authors.join(", ")}</p>

                                {/* 内容区域：优先显示推荐理由 (无颜色高亮) */}
                                <div className="text-sm text-slate-400 leading-relaxed mb-3 line-clamp-4">
                                    {activePaper!.user_state?.why_this_paper && activePaper!.user_state.why_this_paper !== "Not Filtered" ? (
                                        <span>
                                            <span className="font-bold text-slate-400 mr-1 text-base">推荐理由:</span>
                                            {activePaper!.user_state.why_this_paper}
                                        </span>
                                    ) : (
                                        activePaper!.analysis?.tldr || activePaper!.meta.abstract
                                    )}
                                </div>

                                <button
                                    className="w-full flex items-center justify-center gap-2 bg-cyan-600 hover:bg-cyan-500 text-white text-xs py-1.5 rounded transition-colors font-medium"
                                    onClick={(e) => {
                                        e.stopPropagation();
                                        onNavigateToPaper(activePaper, papers);
                                    }}
                                >
                                    查看详情 <ArrowRightCircle size={12} />
                                </button>
                            </div>
                        )
                        )
                    ) : (
                        <div className="h-full flex flex-col items-center justify-center text-slate-600 space-y-2 opacity-50">
                            <Compass size={32} strokeWidth={1.5} />
                            <p className="text-xs text-center px-4">
                                {loadingPapers ? '加载论文数据中...' : '暂无相关论文数据'}
                            </p>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};
