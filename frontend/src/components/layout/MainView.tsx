import React, { memo } from 'react';
import { formatReportTime } from '../../utils/date';

import { Onboarding } from '../features/Onboarding';
import { Settings } from '../features/Settings';
import { ReportDetail } from '../features/reports/ReportDetail';
import { ReportList } from '../features/reports/ReportList';
import { PaperList } from '../features/papers/PaperList';
import { PaperCard } from '../features/papers/PaperCard';
import { FeedbackPage } from '../features/FeedbackPage';
import { WorkflowPage } from '../../features/admin/WorkflowPage';
import { ManualReportPage } from '../features/ManualReportPage';
import { LoadingScreen } from '../common/LoadingScreen';
import { FileText, Compass } from 'lucide-react';
import type { Report, Paper, UserProfile } from '../../types';

interface MainViewProps {
    currentView: string;
    userProfile: UserProfile | null | undefined;
    selectedReport: Report | null;
    selectedPaper: Paper | null;
    recommendations: Paper[];
    latestReport: Report | null;
    loadingPapers: boolean;
    dateFilter: string | null;
    onNavigate: (view: string) => void;
    onSelectReport: (report: Report | null) => void;
    onSelectPaper: (paper: Paper | null) => void;
    onNavigateToPaper: (paperOrId: string | Paper | null, papersList?: Paper[], filterDate?: string) => void;
    onFeedback: (paperId: string, data: { liked?: boolean, feedback?: string, note?: string }) => void;
    onOpenDetail: (paper: Paper) => void;
    onClearDateFilter: () => void;
    onRefreshProfile: () => Promise<void>;
    // 手动报告表单状态
    manualReportQuery: string;
    manualReportCategories: string[];
    manualReportAuthors: string[];
    onManualReportQueryChange: (query: string) => void;
    onManualReportCategoriesChange: (categories: string[]) => void;
    onManualReportAuthorsChange: (authors: string[]) => void;
}

export const MainView = memo(({
    currentView,
    userProfile,
    selectedReport,
    selectedPaper,
    recommendations,
    latestReport,
    loadingPapers,
    dateFilter,
    onNavigate,
    onSelectReport,
    onSelectPaper,
    onNavigateToPaper,
    onFeedback,
    onOpenDetail,
    onClearDateFilter,
    onRefreshProfile,
    manualReportQuery,
    manualReportCategories,
    manualReportAuthors,
    onManualReportQueryChange,
    onManualReportCategoriesChange,
    onManualReportAuthorsChange
}: MainViewProps) => {
    console.log("renderContent called. currentView:", currentView, "userProfile:", userProfile);

    // 1. Onboarding view
    if (currentView === 'onboarding') {
        console.log("Rendering Onboarding component");
        return <Onboarding
            onComplete={() => {
                console.log("Onboarding complete, switching to dashboard");
                onRefreshProfile().then(() => onNavigate('dashboard')).catch(err => {
                    console.error("Failed to refresh profile:", err);
                    alert("初始化失败，请重试");
                });
            }}
            initialName={userProfile?.info?.name}
        />;
    }

    // 2. For all other views, userProfile is strictly required
    if (!userProfile) {
        console.log("userProfile is null, showing LoadingScreen inside renderContent");
        return (
            <div className="flex items-center justify-center h-full">
                <LoadingScreen />
            </div>
        );
    }

    if (currentView === 'settings') {
        return <Settings
            userProfile={userProfile}
            onUpdate={onRefreshProfile}
            onBack={() => onNavigate('dashboard')}
            onNavigate={onNavigate}
        />;
    }

    if (currentView === 'reports' && selectedReport) {
        return <ReportDetail
            report={selectedReport}
            onBack={() => onSelectReport(null)}
            onNavigateToPaper={onNavigateToPaper}
        />;
    }

    if (currentView === 'dashboard') {
        return (
            <div className="p-6 max-w-7xl mx-auto animate-in fade-in">
                {/* Today's Report Push */}
                {latestReport && (
                    <div className="mb-8">
                        <h2 className="text-lg font-bold text-white mb-3">最新报告推送</h2>
                        <div
                            onClick={() => {
                                onSelectReport(latestReport);
                                onNavigate('reports');
                            }}
                            className="bg-gradient-to-r from-indigo-900/50 to-slate-900 border border-indigo-500/30 rounded-lg p-4 cursor-pointer hover:border-indigo-500/50 transition-all group"
                        >
                            <div className="flex items-center justify-between mb-2">
                                <div className="flex items-center gap-2">
                                    <FileText size={16} className="text-indigo-400" />
                                    <span className="font-bold text-white group-hover:text-indigo-300 transition-colors">
                                        {latestReport.title}
                                    </span>
                                </div>
                                <div className="flex items-center gap-3">
                                    <span className="text-xs text-slate-500 bg-slate-800 px-2 py-0.5 rounded-full">
                                        {formatReportTime(latestReport.created_at || latestReport.date)}
                                    </span>
                                    <div className="text-xs text-indigo-400 group-hover:translate-x-1 transition-transform">
                                        阅读报告 &rarr;
                                    </div>
                                </div>
                            </div>
                            <p className="text-sm text-slate-400 line-clamp-2">
                                {latestReport.summary}
                            </p>
                        </div>
                    </div>
                )}

                <div className="flex items-center justify-between mb-3">
                    <h2 className="text-lg font-bold text-white">最新相关论文推荐</h2>
                    <button
                        onClick={() => onNavigate('papers')}
                        className="text-xs text-cyan-400 hover:text-cyan-300 flex items-center gap-1 transition-colors"
                    >
                        查看更多 &rarr;
                    </button>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 pb-10">
                    {recommendations.map((p, idx) => (
                        <PaperCard
                            key={p.meta?.id || Math.random()}
                            paper={p}
                            index={idx + 1}
                            showIndex={true}
                            onOpenDetail={(paper) => {
                                onOpenDetail(paper);
                            }}
                            onFeedback={onFeedback}
                        />
                    ))}
                </div>
            </div>
        );
    }

    if (currentView === 'reports') {
        return <ReportList onSelectReport={onSelectReport} />;
    }

    if (currentView === 'papers') {
        return <PaperList
            onOpenDetail={onOpenDetail}
            selectedPaper={selectedPaper}
            setSelectedPaper={onSelectPaper}
            dateFilter={dateFilter}
            onClearDateFilter={onClearDateFilter}
        />
    }

    if (currentView === 'feedback') {
        return <FeedbackPage />;
    }

    if (currentView === 'workflow') {
        return <WorkflowPage />;
    }

    if (currentView === 'manual-report') {
        return <ManualReportPage
            userProfile={userProfile}
            onBack={() => onNavigate('dashboard')}
            naturalQuery={manualReportQuery}
            categories={manualReportCategories}
            authors={manualReportAuthors}
            onNaturalQueryChange={onManualReportQueryChange}
            onCategoriesChange={onManualReportCategoriesChange}
            onAuthorsChange={onManualReportAuthorsChange}
        />;
    }
    return null;
});
