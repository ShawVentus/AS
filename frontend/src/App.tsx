import React, { useState } from 'react';
import { FileText, Target, Brain } from 'lucide-react';
import { Navbar } from './components/layout/Navbar';
import { ReportDetail } from './components/features/reports/ReportDetail';
import { ReportList } from './components/features/reports/ReportList';
import { PaperList } from './components/features/papers/PaperList';
import { PaperCard } from './components/features/papers/PaperCard';
import { SettingsPage } from './components/features/settings/SettingsPage';
import { PaperDetailModal } from './components/shared/PaperDetailModal';
import { Heatmap } from './components/shared/Heatmap';
import { USER_PROFILE, MOCK_PAPERS } from './data/mockData';
import type { Report, Paper } from './data/mockData';

function App() {
  const [currentView, setCurrentView] = useState('dashboard');
  const [selectedReport, setSelectedReport] = useState<Report | null>(null);
  const [selectedPaper, setSelectedPaper] = useState<Paper | null>(null);
  const [modalPaper, setModalPaper] = useState<Paper | null>(null);

  const handleNavigateToPaper = (paperId: string | null) => {
    if (!paperId) {
      setCurrentView('papers');
      return;
    }
    const paper = MOCK_PAPERS.find(p => p.id === paperId);
    if (paper) {
      setModalPaper(paper);
    }
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
          <h1 className="text-xl font-bold text-white mb-1">早安，{USER_PROFILE.info.name}</h1>
          <p className="text-xs text-slate-500 mb-6">今日有 3 篇新论文可能相关。</p>

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

          <h2 className="text-sm font-bold text-white mb-3">推荐论文</h2>
          <div className="space-y-3 pb-10">
            {MOCK_PAPERS.slice(0, 2).map(p => (
              <PaperCard key={p.id} paper={p} onOpenDetail={(paper) => setModalPaper(paper)} />
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
    <div className="min-h-screen bg-slate-950 text-slate-200 font-sans selection:bg-cyan-500/30 selection:text-cyan-100">
      <Navbar currentView={currentView} setCurrentView={setCurrentView} />

      <main className="pt-14 min-h-screen">
        <div className="h-full overflow-y-auto scrollbar-thin scrollbar-thumb-slate-800 scrollbar-track-transparent">
          {renderContent()}
        </div>
      </main>

      {/* Global Modal */}
      <PaperDetailModal paper={modalPaper} onClose={() => setModalPaper(null)} />
    </div>
  );
}

export default App;
