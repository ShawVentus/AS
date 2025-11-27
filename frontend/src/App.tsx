import React, { useState } from 'react';
import { FileText, Target, Brain } from 'lucide-react';
import { Header } from './components/layout/Header';
import { ReportDetail } from './components/features/reports/ReportDetail';
import { ReportList } from './components/features/reports/ReportList';
import { PaperList } from './components/features/papers/PaperList';
import { PaperCard } from './components/features/papers/PaperCard';
import { SettingsPage } from './components/features/settings/SettingsPage';
import { PaperDetailModal } from './components/shared/PaperDetailModal';
import { Heatmap } from './components/shared/Heatmap';
import { ErrorBoundary } from './components/common/ErrorBoundary';
import { USER_PROFILE as DEFAULT_PROFILE, MOCK_PAPERS as DEFAULT_PAPERS } from './data/mockData';
import type { Report, Paper, UserProfile } from './types';
import { UserAPI, PaperAPI } from './services/api';

function App() {
  const [currentView, setCurrentView] = useState('dashboard');
  const [userProfile, setUserProfile] = useState<UserProfile>(DEFAULT_PROFILE);
  const [recommendations, setRecommendations] = useState<Paper[]>(DEFAULT_PAPERS.slice(0, 2));
  const [selectedReport, setSelectedReport] = useState<Report | null>(null);
  const [selectedPaper, setSelectedPaper] = useState<Paper | null>(null);
  const [modalPaper, setModalPaper] = useState<Paper | null>(null);

  const [latestReport, setLatestReport] = useState<Report | null>(null);

  React.useEffect(() => {
    const fetchData = async () => {
      try {
        const profile = await UserAPI.getProfile();
        setUserProfile(profile);
        const recs = await PaperAPI.getRecommendations();
        setRecommendations(recs.slice(0, 3)); // Show 3 recommendations

        // Fetch latest report
        const reports = await import('./services/api').then(m => m.ReportAPI.getReports());
        if (reports && reports.length > 0) {
          setLatestReport(reports[0]);
        }
      } catch (error) {
        console.error("Failed to fetch data:", error);
      }
    };
    fetchData();
  }, []);

  const handleNavigateToPaper = (paperId: string | null) => {
    if (!paperId) {
      setCurrentView('papers');
      return;
    }
    PaperAPI.getPaperDetail(paperId).then(setModalPaper).catch(console.error);
  };

  const renderContent = () => {
    if (currentView === 'reports' && selectedReport) {
      return <ReportDetail
        report={selectedReport}
        onBack={() => setSelectedReport(null)}
        onNavigateToPaper={handleNavigateToPaper}
      />;
    }

    if (currentView === 'settings') return <SettingsPage />;

    if (currentView === 'dashboard') {
      return (
        <div className="p-6 max-w-5xl mx-auto animate-in fade-in">
          <h1 className="text-xl font-bold text-white mb-1">早安，{userProfile.info.name}</h1>
          <p className="text-xs text-slate-500 mb-6">今日有 3 篇新论文可能相关。</p>

          {/* Today's Report Push */}
          {latestReport && (
            <div className="mb-8">
              <h2 className="text-sm font-bold text-white mb-3">今日报告推送</h2>
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
                      {latestReport.date}
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

          <div className="grid grid-cols-3 gap-4 mb-8">
            {[{ icon: FileText, val: 12, label: '未读报告', col: 'indigo' }, { icon: Target, val: '85%', label: '覆盖率', col: 'cyan' }, { icon: Brain, val: 5, label: 'Idea', col: 'emerald' }].map((s, i) => (
              <div key={i} className={`bg-slate-900 border border-slate-800 p-4 rounded-lg flex flex-col items-center justify-center`}>
                <s.icon size={20} className={`text-${s.col}-400 mb-1`} />
                <div className="text-lg font-bold text-white">{s.val}</div>
                <div className="text-[10px] text-slate-500">{s.label}</div>
              </div>
            ))}
          </div>

          <div className="mb-8">
            <h2 className="text-sm font-bold text-white mb-3">科研热力图</h2>
            <div className="bg-slate-950 border border-slate-800 rounded-lg p-4">
              <Heatmap />
            </div>
          </div>

          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-bold text-white">推荐论文</h2>
            <button
              onClick={() => setCurrentView('papers')}
              className="text-xs text-cyan-400 hover:text-cyan-300 flex items-center gap-1 transition-colors"
            >
              查看更多 &rarr;
            </button>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 pb-10">
            {recommendations.map(p => (
              <PaperCard key={p.meta?.id || Math.random()} paper={p} onOpenDetail={(paper) => setModalPaper(paper)} />
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
      />
    }
    return null;
  };

  return (
    <div className="flex flex-col h-screen bg-slate-950 text-slate-200 font-sans selection:bg-cyan-500/30 selection:text-cyan-100 overflow-hidden">
      <Header
        currentView={currentView}
        setCurrentView={setCurrentView}
        userProfile={userProfile}
      />

      <main className="flex-1 h-full overflow-hidden relative">
        <div className="h-full overflow-y-auto scrollbar-thin scrollbar-thumb-slate-800 scrollbar-track-transparent">
          <ErrorBoundary>
            {renderContent()}
          </ErrorBoundary>
        </div>
      </main>

      {/* Global Modal */}
      <PaperDetailModal paper={modalPaper} onClose={() => setModalPaper(null)} />
    </div>
  );
}

export default App;
