import React, { useState } from 'react';
import { FileText } from 'lucide-react';
import { supabase } from './services/supabase';
import { Header } from './components/layout/Header';
import { ReportDetail } from './components/features/reports/ReportDetail';
import { ReportList } from './components/features/reports/ReportList';
import { PaperList } from './components/features/papers/PaperList';
import { PaperCard } from './components/features/papers/PaperCard';
import { PaperDetailModal } from './components/shared/PaperDetailModal';
import { ErrorBoundary } from './components/common/ErrorBoundary';
import { LoadingScreen } from './components/common/LoadingScreen';
import type { Report, Paper, UserProfile } from './types';
import { UserAPI, PaperAPI } from './services/api';

import { useAuth } from './contexts/AuthContext';
import { Login } from './components/auth/Login';
import { Register } from './components/auth/Register';

import { Onboarding } from './components/features/Onboarding';
import { Settings } from './components/features/Settings';
import { FeedbackPage } from './components/features/FeedbackPage';

function App() {
    const { user, loading } = useAuth();
    const [showRegister, setShowRegister] = useState(false);
    const [currentView, setCurrentView] = useState('dashboard');
    const [userProfile, setUserProfile] = useState<UserProfile | null>(null);
    const [recommendations, setRecommendations] = useState<Paper[]>([]);
    const [selectedReport, setSelectedReport] = useState<Report | null>(null);
    const [selectedPaper, setSelectedPaper] = useState<Paper | null>(null);
    const [modalPaper, setModalPaper] = useState<Paper | null>(null);
    const [modalPapers, setModalPapers] = useState<Paper[]>([]); // 论文列表上下文
    const [modalPaperIndex, setModalPaperIndex] = useState(0); // 当前论文索引
    const [latestReport, setLatestReport] = useState<Report | null>(null);
    const [dateFilter, setDateFilter] = useState<string | null>(null); // 论文列表日期筛选

    // Data loading state
    const [dataLoading, setDataLoading] = useState(true);

    React.useEffect(() => {
        if (!user) {
            setDataLoading(false);
            return;
        }

        const fetchData = async () => {
            try {
                setDataLoading(true);

                // Parallel data fetching with individual error handling for profile
                const [profileResult, recs, reports] = await Promise.all([
                    UserAPI.getProfile().catch(err => ({ error: err })),
                    PaperAPI.getRecommendations().catch(() => []),
                    import('./services/api').then(m => m.ReportAPI.getReports()).catch(() => [])
                ]);

                // Handle Profile Result
                if ('error' in profileResult) {
                    const error = profileResult.error as any;
                    const errorStatus = error?.response?.status || error?.status;

                    if (errorStatus === 404) {
                        console.log("Profile not found, redirecting to onboarding");
                        setCurrentView('onboarding');
                        // Set a temporary empty profile to allow rendering if needed, 
                        // though renderContent handles null profile for onboarding now.
                    } else {
                        throw error; // Re-throw other errors to be caught by outer catch
                    }
                } else {
                    const profile = profileResult as UserProfile;
                    setUserProfile(profile);

                    // Check if profile is initialized (has focus category)
                    if (!profile.focus?.category || profile.focus.category.length === 0) {
                        setCurrentView('onboarding');
                    }
                }

                // Sort by relevance score descending and take top 3
                recs.sort((a, b) => (b.user_state?.relevance_score || 0) - (a.user_state?.relevance_score || 0));
                setRecommendations(recs.slice(0, 6));

                if (reports && reports.length > 0) {
                    setLatestReport(reports[0]);
                }
            } catch (error: any) {
                console.error("Failed to fetch data:", error);

                // 处理不同类型的错误
                const errorStatus = error?.response?.status || error?.status;
                const errorMessage = error?.message || '';

                if (errorStatus === 404) {
                    // API 返回 404 - Profile 不存在
                    console.log("Profile not found, redirecting to onboarding");
                    setCurrentView('onboarding');
                } else if (errorStatus === 401) {
                    // 401 Unauthorized - Token 失效
                    console.log("Session expired, logging out");
                    supabase.auth.signOut();
                    // AuthContext should handle the user state update
                } else if (error?.name === 'TypeError' && errorMessage.includes('fetch')) {
                    // 网络错误
                    console.error("Network error: Unable to connect to server");
                    // TODO: 显示网络错误提示
                } else if (errorStatus >= 500) {
                    // 服务器错误
                    console.error("Server error:", errorStatus);
                    // TODO: 显示服务器错误页面
                } else {
                    // 其他未知错误
                    console.error("Critical error fetching initial data:", error);
                    // TODO: 显示通用错误页面
                }
            } finally {
                // Add a small delay to prevent flickering on fast connections
                // and ensure the loading animation is seen
                setTimeout(() => {
                    setDataLoading(false);
                }, 800);
            }
        };
        fetchData();
    }, [user]);

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
                    UserAPI.getProfile()
                        .then((profile) => {
                            setUserProfile(profile);
                            setCurrentView('dashboard');
                        })
                        .catch((err) => {
                            console.error("Failed to refresh profile after onboarding:", err);
                            // If failed, stay on onboarding or show error?
                            // For now, maybe retry or show alert
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
                    UserAPI.getProfile().then(setUserProfile);
                }}
                onBack={() => setCurrentView('dashboard')}
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
                <div className="p-6 max-w-5xl mx-auto animate-in fade-in">


                    {/* Today's Report Push */}
                    {latestReport && (
                        <div className="mb-8">
                            <h2 className="text-sm font-bold text-white mb-3">最新报告推送</h2>
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
                        <h2 className="text-sm font-bold text-white">最新相关论文推荐</h2>
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
                                showIndex={false} // Hide index tag for recommendations
                                onOpenDetail={(paper) => setModalPaper(paper)}
                            />
                        ))}
                    </div>
                </div>
            )
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
            />
        </div>
    );
}

export default App;
