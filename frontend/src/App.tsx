import React, { useState, useEffect } from 'react';
import { format } from 'date-fns';
import { supabase } from './services/supabase';
import { Header } from './components/layout/Header';
import { PaperDetailModal } from './components/shared/PaperDetailModal';
import { ErrorBoundary } from './components/common/ErrorBoundary';
import { LoadingScreen } from './components/common/LoadingScreen';
import type { Report, Paper } from './types';
import { UserAPI, PaperAPI, ReportAPI } from './services/api';

import { useAuth } from './contexts/AuthContext';
// 🚧 已移除: 系统已切换到玻尔平台认证，不再使用邮箱密码登录
// import { Login } from './components/auth/Login';
// import { Register } from './components/auth/Register';

import { ReportGenerationModal } from './components/features/ReportGenerationModal';

import { MainView } from './components/layout/MainView';
import { GuidedTour } from './components/features/GuidedTour';

import { QueryClient, QueryClientProvider, useQuery, useQueryClient } from '@tanstack/react-query';
import { ToastProvider } from './contexts/ToastContext';
import { TaskProvider, useTaskContext } from './contexts/TaskContext';

// [NEW] Initialize QueryClient
const queryClient = new QueryClient({
    defaultOptions: {
        queries: {
            staleTime: 1000 * 30, // 30 seconds
            retry: 1,
            refetchOnWindowFocus: false,
        },
    },
});

function AppContent() {
    const { user, loading, error: authError } = useAuth();
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

    // [NEW] 手动报告表单状态 - 在应用生命周期内保持（刷新后重置）
    const [manualReportQuery, setManualReportQuery] = useState('');
    const [manualReportCategories, setManualReportCategories] = useState<string[]>([]);
    const [manualReportAuthors, setManualReportAuthors] = useState<string[]>([]);
    
    // [NEW] 产品引导状态
    const [runTour, setRunTour] = useState(false);

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

    /**
     * 处理 Profile 错误和新用户引导
     * 
     * 功能：
     * 1. 404错误：新用户没有profile，停留在dashboard，等待引导气泡
     * 2. 401错误：Session过期，登出
     * 
     * Args:
     *   无
     * 
     * Returns:
     *   void
     */
    React.useEffect(() => {
        if (profileError) {
            const error = profileError as any;
            const errorStatus = error?.response?.status || error?.status;
            if (errorStatus === 404) {
                // 新用户没有 profile，停留在 dashboard
                // 引导气泡会自动触发，引导用户生成报告
                console.log('[引导] Profile not found, but will show guided tour');
                // 不跳转，保持在 dashboard
            } else if (errorStatus === 401) {
                console.log('[引导] Session expired, logging out');
                supabase.auth.signOut();
            }
        }
        // 移除未初始化检查，不再跳转到 onboarding
        // 新用户通过引导气泡了解功能即可
    }, [profileError]);
    
    /**
     * 检测是否需要显示产品引导
     * 
     * 触发条件：
     * 1. userProfile 已加载
     * 2. 用户未完成过引导 (has_completed_tour === false)
     * 
     * Args:
     *   无
     * 
     * Returns:
     *   void
     */
    React.useEffect(() => {
        if (userProfile && userProfile.has_completed_tour === false) {
            console.log('[引导] 检测到新用户，准备显示引导...');
            // 延迟 500ms 确保页面完全加载和渲染
            const timer = setTimeout(() => {
                console.log('[引导] 开始显示引导气泡');
                setRunTour(true);
            }, 500);
            
            return () => clearTimeout(timer);
        } else if (userProfile?.has_completed_tour === true) {
            console.log('[引导] 用户已完成引导，跳过显示');
        }
    }, [userProfile]);
    
    /**
     * 引导完成或跳过时的回调处理
     * 
     * 功能：
     * 1. 隐藏引导气泡
     * 2. 调用后端 API 标记引导完成
     * 3. 刷新用户信息（确保 has_completed_tour 更新）
     * 4. 🆕 强制清理所有可能的滚动锁定样式（包括 body, html 和内部容器）
     * 
     * Args:
     *   无
     * 
     * Returns:
     *   Promise<void>
     */
    const handleTourComplete = async () => {
        console.log('[引导] 用户完成或跳过引导');
        setRunTour(false);
        
        // 🆕 延迟清理样式，确保 Joyride 先执行内部清理逻辑
        // 增加超时时间到 300ms，并同时清理 body、html 以及识别出的内部滚动容器
        setTimeout(() => {
            document.body.style.overflow = '';
            document.documentElement.style.overflow = '';
            
            // 针对 F12 发现的元凶：清理内部滚动容器的内联样式
            const container = document.getElementById('main-scroll-container');
            if (container) {
                container.style.overflow = '';
                console.log('[引导] ✅ 已清理内部滚动容器样式');
            }
            
            console.log('[引导] ✅ 已清理所有滚动锁定样式，恢复页面滚动');
        }, 300);
        
        try {
            await UserAPI.completeTour();
            // 刷新用户信息，获取最新的 has_completed_tour 状态
            queryClient.invalidateQueries({ queryKey: ['userProfile'] });
            console.log('[引导] ✅ 引导状态已同步');
        } catch (error) {
            console.error('[引导] ❌ 标记引导完成失败:', error);
            // 即使失败也隐藏引导，避免用户体验问题
            // 用户下次登录时会重新显示引导
        }
    };

    if (loading) {
        return <LoadingScreen />;
    }

    // 认证失败或未登录：显示错误页面
    if (!user) {
        return (
            <div className="flex h-screen items-center justify-center bg-slate-950">
                <div className="text-center p-8 bg-slate-900 rounded-xl border border-slate-800 max-w-md">
                    <div className="text-4xl mb-4">⚠️</div>
                    <h1 className="text-xl font-bold text-white mb-4">访问受限</h1>
                    <p className="text-slate-400 mb-6">
                        {authError || "获取您的信息失败，请刷新重试"}
                    </p>
                    <button 
                        onClick={() => window.location.reload()}
                        className="px-6 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg transition-colors"
                    >
                        刷新重试
                    </button>
                </div>
            </div>
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
                            manualReportQuery={manualReportQuery}
                            manualReportCategories={manualReportCategories}
                            manualReportAuthors={manualReportAuthors}
                            onManualReportQueryChange={setManualReportQuery}
                            onManualReportCategoriesChange={setManualReportCategories}
                            onManualReportAuthorsChange={setManualReportAuthors}
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
                        // 全局刷新：研报列表、推荐论文、论文库
                        queryClient.invalidateQueries({ queryKey: ['reports'] });
                        queryClient.invalidateQueries({ queryKey: ['recommendations'] });
                        queryClient.invalidateQueries({ queryKey: ['papers'] });
                    }}
                />
            )}
            
            {/* 🆕 产品引导组件：采用条件渲染确保引导结束后组件彻底卸载，触发内部清理逻辑 */}
            {runTour && (
                <GuidedTour 
                    run={runTour} 
                    onComplete={handleTourComplete} 
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
