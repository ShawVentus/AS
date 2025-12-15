import React, { useState, useEffect } from 'react';
import { FileText } from 'lucide-react';
import { format } from 'date-fns';
import { supabase } from './services/supabase';
import { Header } from './components/layout/Header';
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

import { ReportGenerationModal } from './components/features/ReportGenerationModal';

import { MainView } from './components/layout/MainView';

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

    const handleRefreshProfile = async () => {
        await queryClient.invalidateQueries({ queryKey: ['userProfile'] });
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
                        <MainView
                            currentView={currentView}
                            userProfile={userProfile}
                            selectedReport={selectedReport}
                            selectedPaper={selectedPaper}
                            recommendations={recommendations}
                            latestReport={latestReport}
                            loadingPapers={dataLoading}
                            dateFilter={dateFilter}
                            onNavigate={setCurrentView}
                            onSelectReport={setSelectedReport}
                            onSelectPaper={setSelectedPaper}
                            onNavigateToPaper={handleNavigateToPaper}
                            onFeedback={handleFeedback}
                            onOpenDetail={(paper) => {
                                setModalPaper(paper);
                                setModalPapers(recommendations);
                                setModalPaperIndex(recommendations.findIndex(p => p.meta.id === paper.meta.id));
                            }}
                            onClearDateFilter={() => setDateFilter(null)}
                            onRefreshProfile={handleRefreshProfile}
                        />
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
