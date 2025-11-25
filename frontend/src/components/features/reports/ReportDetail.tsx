import React, { useState, useEffect } from 'react';
import { ChevronLeft, Brain, Microscope, ArrowRightCircle, Compass, Mail, Loader2 } from 'lucide-react';
import type { Report, Paper } from '../../../types';
import { PaperAPI, ReportAPI } from '../../../services/api';
import { cn } from '../../../utils/cn';

interface ReportDetailProps {
    report: Report;
    onBack: () => void;
    onNavigateToPaper: (paperId: string | null) => void;
}

export const ReportDetail: React.FC<ReportDetailProps> = ({ report, onBack, onNavigateToPaper }) => {
    const [hoveredRefIds, setHoveredRefIds] = useState<string[]>([]);
    const [papers, setPapers] = useState<Paper[]>([]);
    const [sendingEmail, setSendingEmail] = useState(false);

    useEffect(() => {
        PaperAPI.getPapers().then(setPapers).catch(console.error);
    }, []);

    const activePapers = hoveredRefIds.map(id => papers.find(p => p.id === id)).filter(Boolean);

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
                                <span className="text-[11px] text-slate-500">{report.date}</span>
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
                        <button onClick={() => onNavigateToPaper(null)} className="text-xs bg-slate-900 hover:bg-slate-800 text-slate-300 px-3 py-1.5 rounded border border-slate-800 hover:border-slate-600 transition-all">
                            查看论文列表
                        </button>
                    </div>
                </div>

                <div className="flex-1 overflow-y-auto p-6 md:p-8">
                    <div className="max-w-3xl mx-auto pb-20">
                        <div className="bg-slate-900/50 p-4 rounded-lg border border-slate-800 mb-6">
                            <h3 className="text-emerald-500 font-bold text-xs mb-1.5 flex items-center gap-1.5">
                                <Brain size={14} /> 核心摘要
                            </h3>
                            <p className="text-sm text-slate-300 leading-relaxed">{report.summary}</p>
                        </div>

                        <div className="space-y-4 text-sm md:text-[15px] leading-7 text-slate-300">
                            {report.content.map((paragraph, idx) => (
                                <div key={idx} className="group relative pl-4 border-l-2 border-transparent hover:border-slate-700 transition-colors">
                                    <p>
                                        <span
                                            className={cn(
                                                "cursor-pointer transition-all duration-150 rounded px-1 -mx-1",
                                                paragraph.refIds.some(id => hoveredRefIds.includes(id))
                                                    ? 'text-cyan-200 bg-cyan-950/60 shadow-sm'
                                                    : 'hover:text-cyan-300 hover:bg-slate-800/50 border-b border-dashed border-slate-600 hover:border-transparent'
                                            )}
                                            onMouseEnter={() => setHoveredRefIds(paragraph.refIds)}
                                            onClick={() => paragraph.refIds.length > 0 && onNavigateToPaper(paragraph.refIds[0])}
                                            title="点击跳转到论文详情"
                                        >
                                            {paragraph.text}
                                            <sup className="text-[10px] text-cyan-500 ml-0.5 font-bold opacity-70">
                                                [{paragraph.refIds.map(id => id.replace('p', '')).join(', ')}]
                                            </sup>
                                        </span>
                                    </p>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            </div>

            {/* Right Side: Fixed Context Panel */}
            <div className="w-80 border-l border-slate-800 bg-slate-950 hidden lg:flex flex-col">
                <div className="p-4 border-b border-slate-800 bg-slate-900/30">
                    <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider flex items-center gap-2">
                        <Microscope size={14} /> 关联论文预览 ({activePapers.length})
                    </h3>
                </div>
                <div className="flex-1 p-4 overflow-y-auto space-y-4">
                    {activePapers.length > 0 ? (
                        activePapers.map((activePaper) => (
                            <div key={activePaper!.id} className="animate-in fade-in slide-in-from-right-2 duration-200 bg-slate-900/50 p-3 rounded border border-slate-800 hover:border-cyan-500/30 transition-colors">
                                <div className="flex items-start gap-2 mb-2">
                                    <span className="text-[10px] bg-cyan-950 text-cyan-400 px-1.5 py-0.5 rounded border border-cyan-900 font-mono">ID: {activePaper!.id}</span>
                                    <span className="text-[10px] text-emerald-500 border border-emerald-900/50 px-1.5 py-0.5 rounded">{activePaper!.suggestion}</span>
                                </div>
                                <h4 className="text-sm font-bold text-white mb-1 leading-snug">{activePaper!.title}</h4>
                                <p className="text-xs text-slate-500 mb-2">{activePaper!.authors.join(", ")}</p>

                                <div className="text-xs text-slate-400 leading-relaxed mb-3 line-clamp-3">
                                    {activePaper!.abstract}
                                </div>

                                <button
                                    onClick={() => onNavigateToPaper(activePaper!.id)}
                                    className="w-full flex items-center justify-center gap-2 bg-cyan-600 hover:bg-cyan-500 text-white text-xs py-1.5 rounded transition-colors font-medium"
                                >
                                    查看详情 <ArrowRightCircle size={12} />
                                </button>
                            </div>
                        ))
                    ) : (
                        <div className="h-full flex flex-col items-center justify-center text-slate-600 space-y-2 opacity-50">
                            <Compass size={32} strokeWidth={1.5} />
                            <p className="text-xs text-center px-4">鼠标停留在左侧高亮语句上，此处将显示关联论文详情。</p>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};
