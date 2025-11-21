import React from 'react';
import { X, Download, ExternalLink, FileText, Brain, Microscope, Lightbulb, Target } from 'lucide-react';
import type { Paper } from '../../data/mockData';
import { cn } from '../../utils/cn';

interface PaperDetailModalProps {
    paper: Paper | null;
    onClose: () => void;
}

export const PaperDetailModal: React.FC<PaperDetailModalProps> = ({ paper, onClose }) => {
    if (!paper) return null;

    return (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 md:p-8 bg-black/80 backdrop-blur-sm animate-in fade-in duration-200">
            <div className="bg-slate-950 w-full max-w-3xl h-[90vh] rounded-xl border border-slate-800 shadow-2xl flex flex-col overflow-hidden relative ring-1 ring-slate-700">

                {/* Close Button */}
                <button
                    onClick={onClose}
                    className="absolute top-4 right-4 z-10 p-2 bg-slate-900/80 hover:bg-slate-800 rounded-full text-slate-400 hover:text-white transition-colors border border-slate-800"
                >
                    <X size={20} />
                </button>

                {/* Header */}
                <div className="p-6 border-b border-slate-800 bg-slate-900/30 shrink-0">
                    <div className="flex gap-3 mb-3">
                        <span className="px-2 py-0.5 rounded text-xs font-bold bg-cyan-950 text-cyan-400 border border-cyan-900/50">{paper.category}</span>
                        <span className="px-2 py-0.5 rounded text-xs font-bold bg-slate-800 text-slate-400 border border-slate-700">{paper.date}</span>
                    </div>
                    <h2 className="text-xl md:text-2xl font-bold text-white mb-2 leading-snug">{paper.title}</h2>
                    <p className="text-slate-400 text-sm">{paper.authors.join(", ")}</p>
                </div>

                {/* Content Scrollable Area */}
                <div className="flex-1 overflow-y-auto p-6 space-y-6 scrollbar-thin scrollbar-thumb-slate-800 scrollbar-track-transparent">

                    {/* Why This Paper */}
                    {paper.whyThisPaper && (
                        <div className="bg-indigo-950/20 border border-indigo-500/30 rounded-lg p-4">
                            <h3 className="text-indigo-400 font-bold text-sm mb-2 flex items-center gap-2">
                                <Lightbulb size={16} /> Why This Paper (推荐理由)
                            </h3>
                            <p className="text-slate-300 text-sm leading-relaxed">{paper.whyThisPaper}</p>
                        </div>
                    )}

                    {/* TLDR */}
                    <div className="bg-slate-900/50 p-4 rounded-lg border border-slate-800/50">
                        <h3 className="text-slate-400 font-bold text-xs uppercase tracking-wider mb-2 flex items-center gap-2">
                            <span className="font-mono font-bold text-cyan-500">TL;DR</span>
                        </h3>
                        <p className="text-slate-200 font-medium text-sm leading-relaxed">{paper.tldr}</p>
                    </div>

                    {/* Abstract */}
                    <div>
                        <h3 className="text-slate-500 font-bold text-xs uppercase tracking-wider mb-2 flex items-center gap-2">
                            <FileText size={14} /> Abstract
                        </h3>
                        <p className="text-slate-300 leading-7 text-sm text-justify">{paper.details.abstract}</p>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        {/* Result */}
                        <div className="bg-slate-900/30 p-4 rounded-lg border border-slate-800/50">
                            <h3 className="text-emerald-500 font-bold text-xs uppercase tracking-wider mb-2 flex items-center gap-2">
                                <Brain size={14} /> Result
                            </h3>
                            <p className="text-slate-300 leading-relaxed text-sm">{paper.details.result}</p>
                        </div>

                        {/* Conclusion */}
                        <div className="bg-slate-900/30 p-4 rounded-lg border border-slate-800/50">
                            <h3 className="text-cyan-500 font-bold text-xs uppercase tracking-wider mb-2 flex items-center gap-2">
                                <Microscope size={14} /> Conclusion
                            </h3>
                            <p className="text-slate-300 leading-relaxed text-sm">{paper.details.conclusion}</p>
                        </div>
                    </div>

                    {/* Method & Motivation */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-2">
                        <div>
                            <h3 className="text-slate-500 font-bold text-xs uppercase tracking-wider mb-2 flex items-center gap-2">
                                <Target size={14} /> Motivation
                            </h3>
                            <p className="text-slate-400 text-sm leading-relaxed">{paper.details.motivation}</p>
                        </div>
                        <div>
                            <h3 className="text-slate-500 font-bold text-xs uppercase tracking-wider mb-2 flex items-center gap-2">
                                <Brain size={14} /> Method
                            </h3>
                            <p className="text-slate-400 text-sm leading-relaxed">{paper.details.method}</p>
                        </div>
                    </div>
                </div>

                {/* Footer Actions */}
                <div className="p-4 border-t border-slate-800 bg-slate-900/50 flex items-center justify-between shrink-0">
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

                    <div className="flex gap-3">
                        <button className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-white text-sm font-medium rounded-lg transition-colors shadow-lg shadow-cyan-900/20">
                            下载 PDF
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
};
