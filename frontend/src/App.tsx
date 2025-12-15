import React, { useState, useEffect } from 'react';
import { FileText } from 'lucide-react';
import { format } from 'date-fns';
import { supabase } from './services/supabase';
import { Header } from './components/layout/Header';
import { ReportDetail } from './components/features/reports/ReportDetail';
import { ReportList } from './components/features/reports/ReportList';
import { PaperList } from './components/features/papers/PaperList';
import { PaperCard } from './components/features/papers/PaperCard';
import { PaperDetailModal } from './components/shared/PaperDetailModal';
import { ErrorBoundary } from './components/common/ErrorBoundary';
import { LoadingScreen } from './components/common/LoadingScreen';
import type { Report, Paper } from './types';
import { UserAPI, PaperAPI, ReportAPI } from './services/api';

import { useAuth } from './contexts/AuthContext';
import { Login } from './components/auth/Login';
import { Register } from './components/auth/Register';

import { Onboarding } from './components/features/Onboarding';
import { Settings } from './components/features/Settings';
import { FeedbackPage } from './components/features/FeedbackPage';
import { WorkflowPage } from './features/admin/WorkflowPage';
import { ReportGenerationModal } from './components/features/ReportGenerationModal';
import { ManualReportPage } from './components/features/ManualReportPage';

// [NEW] Import React Query and ToastProvider
import { QueryClient, QueryClientProvider, useQuery, useQueryClient } from '@tanstack/react-query';
import { ToastProvider } from './contexts/ToastContext';
import { TaskProvider, useTaskContext } from './contexts/TaskContext';

// [NEW] Initialize QueryClient
const queryClient = new QueryClient({
    defaultOptions: {
        queries: {
            staleTime: 1000 * 60 * 5, // 5 minutes
            retry: 1,
            refetchOnWindowFocus: false,
        },
    },
});

function AppContent() {
    const { user, loading } = useAuth();
    const [showRegister, setShowRegister] = useState(false);
    const [currentView, setCurrentView] = useState('dashboard');
    // const [userProfile, setUserProfile] = useState<UserProfile | null>(null); // Removed: Handled by React Query
    // const [recommendations, setRecommendations] = useState<Paper[]>([]); // Removed: Handled by React Query
    const [selectedReport, setSelectedReport] = useState<Report | null>(null);
    const [selectedPaper, setSelectedPaper] = useState<Paper | null>(null);
    const [modalPaper, setModalPaper] = useState<Paper | null>(null);
    const [modalPapers, setModalPapers] = useState<Paper[]>([]); // 论文列表上下文
    const [modalPaperIndex, setModalPaperIndex] = useState(0); // 当前论文索引
    // const [latestReport, setLatestReport] = useState<Report | null>(null); // Removed: Derived from reports query
    const [dateFilter, setDateFilter] = useState<string | null>(null); // 论文列表日期筛选
    const [showReportModal, setShowReportModal] = useState(false);

    // [NEW] Use QueryClient for invalidation
    const queryClient = useQueryClient();
    const { registerNavigation } = useTaskContext();

    // Register navigation handler for TaskContext
    React.useEffect(() => {
        registerNavigation(async (view: string, data?: any) => {
            console.log("TaskContext requested navigation:", view, data);

            if (view === 'reports' && data?.selectLatest) {
                // 1. Invalidate queries to ensure we have fresh data
                await queryClient.invalidateQueries({ queryKey: ['reports'] });

                // 2. Fetch the latest reports directly to ensure we get the new one immediately
                // We use fetchQuery instead of relying on the hook's next render cycle
                try {
                    const latestReports = await queryClient.fetchQuery({
                        queryKey: ['reports'],
                        queryFn: ReportAPI.getReports,
                        staleTime: 0 // Force fetch
                    });

                    if (latestReports && latestReports.length > 0) {
                        console.log("Selecting latest report:", latestReports[0].title);
                        setSelectedReport(latestReports[0]);
                        setCurrentView('reports');
                    } else {
                        console.warn("No reports found after generation.");
                        setCurrentView('reports');
                    }
                } catch (err) {
                    console.error("Failed to fetch reports for navigation:", err);
                    setCurrentView('reports');
                }
            } else {
                setCurrentView(view);
            }
        });
    }, [registerNavigation, queryClient]);

    // [Refactor] Use React Query for initial data
    const { data: userProfile, isLoading: profileLoading, error: profileError } = useQuery({
        queryKey: ['userProfile', user?.id],
        queryFn: UserAPI.getProfile,
        enabled: !!user,
        retry: false,
    });

    const handleFeedback = async (paperId: string, data: { liked?: boolean, feedback?: string, note?: string }) => {
        try {
            console.log("Submitting feedback:", paperId, data);
            await PaperAPI.submitFeedback(paperId, data);

            // Invalidate queries to refresh data
            queryClient.invalidateQueries({ queryKey: ['recommendations'] });

            // Optimistically update modal paper if it's the one being edited
            if (modalPaper?.meta.id === paperId) {
                setModalPaper(prev => {
                    if (!prev) return null;
                    // Ensure we have a valid user_state object with required fields
                    const currentUserState = prev.user_state || {
                        paper_id: paperId,
                        user_id: user?.id || '',
                        relevance_score: 0,
                        why_this_paper: "Not Filtered",
                        accepted: false,
                        user_accepted: false
                    };

                    return {
                        ...prev,
                        user_state: {
                            ...currentUserState,
                            ...data
                        }
                    };
                });
            }
        } catch (error) {
            console.error("Failed to submit feedback:", error);
            // Optionally show toast error
        }
    };

    const { data: recommendations = [] } = useQuery({
        queryKey: ['recommendations'],
        queryFn: async () => {
            const recs = await PaperAPI.getRecommendations();
            // Sort by date descending first, then by relevance score descending
            return recs.sort((a, b) => {
                const dateA = new Date(a.meta.published_date).getTime();
                const dateB = new Date(b.meta.published_date).getTime();
                if (dateA !== dateB) return dateB - dateA;
                return (b.user_state?.relevance_score || 0) - (a.user_state?.relevance_score || 0);
            }).slice(0, 6);
        },
        enabled: !!user,
        staleTime: 1000 * 60 * 5,
    });

    const { data: reports = [] } = useQuery({
        queryKey: ['reports'],
        queryFn: ReportAPI.getReports,
        enabled: !!user,
        staleTime: 1000 * 60 * 5,
    });

    const latestReport = reports.length > 0 ? reports[0] : null;

    // [NEW] Prefetch Data Logic
    useEffect(() => {
        if (!user) return;

        // 1. Prefetch Today's Papers (for Paper Library)
        const todayStr = format(new Date(), 'yyyy-MM-dd');
        queryClient.prefetchQuery({
            queryKey: ['papers', todayStr],
            queryFn: async () => {
                const fetchedPapers = await PaperAPI.getRecommendations(todayStr);
                fetchedPapers.sort((a, b) => (b.user_state?.relevance_score || 0) - (a.user_state?.relevance_score || 0));
                return fetchedPapers;
            },
            staleTime: 1000 * 60 * 5,
        });

        // 2. Prefetch Latest Report's Referenced Papers (for Report Detail)
        if (latestReport && latestReport.refPapers && latestReport.refPapers.length > 0) {
            queryClient.prefetchQuery({
                queryKey: ['papersByIds', latestReport.refPapers],
                queryFn: () => PaperAPI.getPapersByIds(latestReport.refPapers),
                staleTime: 1000 * 60 * 30,
            });
        }
    }, [user, latestReport, queryClient]);
    const dataLoading = profileLoading; // Simplified loading state

    // Handle Profile Error / Onboarding Redirect
    React.useEffect(() => {
        if (profileError) {
            const error = profileError as any;
            const errorStatus = error?.response?.status || error?.status;
            if (errorStatus === 404) {
                console.log("Profile not found, redirecting to onboarding");
                setCurrentView('onboarding');
            } else if (errorStatus === 401) {
                console.log("Session expired, logging out");
                supabase.auth.signOut();
            }
        } else if (userProfile) {
            // Check if profile is initialized (has focus category)
            if (!userProfile.focus?.category || userProfile.focus.category.length === 0) {
                setCurrentView('onboarding');
            }
        }
    }, [userProfile, profileError]);

    if (loading) {
        return <LoadingScreen />;
    }

    if (!user) {
        return showRegister ? (
            <Register onLoginClick={() => setShowRegister(false)} />
        ) : (
            <Login onRegisterClick={() => setShowRegister(true)} />
        );
    }

    // Show loading screen while fetching initial data
    if (dataLoading && !userProfile) {
        return <LoadingScreen />;
    }

    const handleNavigateToPaper = (paperOrId: string | Paper | null, papersList?: Paper[], filterDate?: string) => {
        if (!paperOrId) {
            setCurrentView('papers');
            // 如果提供了日期筛选，设置筛选状态
            if (filterDate) {
                setDateFilter(filterDate);
            }
            return;
        }

        if (typeof paperOrId === 'string') {
            PaperAPI.getPaperDetail(paperOrId).then(paper => {
                setModalPaper(paper);
                setModalPapers(papersList || [paper]);
                setModalPaperIndex(0);
            }).catch(console.error);
        } else {
            // 直接使用缓存的 Paper 对象，避免 API 调用
            setModalPaper(paperOrId);
            // 如果提供了论文列表，找到当前论文的索引
            if (papersList && papersList.length > 0) {
                setModalPapers(papersList);
                const index = papersList.findIndex(p => p.meta.id === paperOrId.meta.id);
                setModalPaperIndex(index >= 0 ? index : 0);
            } else {
                setModalPapers([paperOrId]);
                setModalPaperIndex(0);
            }
        }
    };



    const renderContent = () => {
        console.log("renderContent called. currentView:", currentView, "userProfile:", userProfile);

        // 1. Onboarding view should be rendered regardless of userProfile status
        // This must be checked BEFORE the null check for userProfile
        if (currentView === 'onboarding') {
            console.log("Rendering Onboarding component");
            return <Onboarding
                onComplete={() => {
                    console.log("Onboarding complete, switching to dashboard");
                    // Refresh profile
                    queryClient.invalidateQueries({ queryKey: ['userProfile'] })
                        .then(() => {
                            setCurrentView('dashboard');
                        })
                        .catch((err) => {
                            console.error("Failed to refresh profile after onboarding:", err);
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
                onUpdate={() => {
                    queryClient.invalidateQueries({ queryKey: ['userProfile'] });
                }}
                onBack={() => setCurrentView('dashboard')}
                onNavigate={setCurrentView}
            />;
        }

        if (currentView === 'reports' && selectedReport) {
            return <ReportDetail
                report={selectedReport}
                onBack={() => setSelectedReport(null)}
                onNavigateToPaper={handleNavigateToPaper}
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
                                    setSelectedReport(latestReport);
                                    setCurrentView('reports');
                                }}
                                className="bg-gradient-to-r from-indigo-900/50 to-slate-900 border border-indigo-500/30 rounded-lg p-4 cursor-pointer hover:border-indigo-500/50 transition-all group"
                            >
                                <div className="flex items-center justify-between mb-2">
                                    <div className="flex items-center gap-2">
                                        <FileText size={16} className="text-indigo-400" />
                                        <span className="font-bold text-white group-hover:text-indigo-300 transition-colors">
                                            {latestReport.title}
                                        </span>
                                        <span className="text-xs text-slate-500 bg-slate-800 px-2 py-0.5 rounded-full">
                                            {latestReport.createdAt?.split('T')[0] || latestReport.date}
                                        </span>
                                    </div>
                                    <div className="text-xs text-indigo-400 group-hover:translate-x-1 transition-transform">
                                        阅读报告 &rarr;
                                    </div>
                                </div>
                                <p className="text-sm text-slate-400 line-clamp-2">
                                    {latestReport.summary}
                                </p>
                            </div>
                        </div>
                    )}

                    {/* Heatmap Removed as per request */}

                    <div className="flex items-center justify-between mb-3">
                        <h2 className="text-lg font-bold text-white">最新相关论文推荐</h2>
                        <button
                            onClick={() => setCurrentView('papers')}
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
                                showIndex={true} // Show index 1-6
                                onOpenDetail={(paper) => {
                                    setModalPaper(paper);
                                    setModalPapers(recommendations); // Set context for navigation
                                    setModalPaperIndex(idx);
                                }}
                                onFeedback={handleFeedback}
                            />
                        ))}
                    </div>
                </div>
            );
        }

        if (currentView === 'reports') {
            return <ReportList onSelectReport={setSelectedReport} />;
        }

        if (currentView === 'papers') {
            return <PaperList
                onOpenDetail={(paper) => setModalPaper(paper)}
                selectedPaper={selectedPaper}
                setSelectedPaper={setSelectedPaper}
                dateFilter={dateFilter}
                onClearDateFilter={() => setDateFilter(null)}
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
                onBack={() => setCurrentView('dashboard')}
            />;
        }
        return null;
    };

    return (
        <div className="flex flex-col h-screen bg-slate-950 text-slate-200 font-sans selection:bg-cyan-500/30 selection:text-cyan-100 overflow-hidden">
            {/* Hide Header on Onboarding */}
            {currentView !== 'onboarding' && (
                <Header
                    currentView={currentView}
                    setCurrentView={setCurrentView}
                    userProfile={userProfile}
                    isLoading={dataLoading}
                    onGenerateReport={() => setShowReportModal(true)}
                />
            )}

            <main className="flex-1 h-full overflow-hidden relative">
                <div className="h-full overflow-y-auto scrollbar-thin scrollbar-thumb-slate-800 scrollbar-track-transparent">
                    <ErrorBoundary>
                        {renderContent()}
                    </ErrorBoundary>
                </div>
            </main>

            {/* Global Modal */}
            <PaperDetailModal
                paper={modalPaper}
                index={modalPaperIndex}
                total={modalPapers.length}
                onClose={() => {
                    setModalPaper(null);
                    setModalPapers([]);
                    setModalPaperIndex(0);
                }}
                onNext={modalPaperIndex < modalPapers.length - 1 ? () => {
                    const nextIndex = modalPaperIndex + 1;
                    setModalPaperIndex(nextIndex);
                    setModalPaper(modalPapers[nextIndex]);
                } : undefined}
                onPrev={modalPaperIndex > 0 ? () => {
                    const prevIndex = modalPaperIndex - 1;
                    setModalPaperIndex(prevIndex);
                    setModalPaper(modalPapers[prevIndex]);
                } : undefined}
                onFeedback={handleFeedback}
            />

            {/* Report Generation Modal */}
            {user && (
                <ReportGenerationModal
                    isOpen={showReportModal}
                    onClose={() => setShowReportModal(false)}
                    userId={user.id}
                    onComplete={() => {
                        // Refresh reports list
                        queryClient.invalidateQueries({ queryKey: ['reports'] });
                    }}
                />
            )}
        </div>
    );
}



function App() {
    return (
        <QueryClientProvider client={queryClient}>
            <ToastProvider>
                <TaskProvider>
                    <AppContent />
                </TaskProvider>
            </ToastProvider>
        </QueryClientProvider>
    );
}

export default App;
