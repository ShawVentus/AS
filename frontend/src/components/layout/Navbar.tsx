import React from 'react';
import { LayoutDashboard, FileText, BookOpen, Settings, Brain } from 'lucide-react';
import { cn } from '../../utils/cn';
import { UserMenu } from '../features/profile/UserProfile';

interface NavbarProps {
    currentView: string;
    setCurrentView: (view: string) => void;
}

export const Navbar: React.FC<NavbarProps> = ({ currentView, setCurrentView }) => {
    const menuItems = [
        { id: 'dashboard', icon: LayoutDashboard, label: '概览' },
        { id: 'reports', icon: FileText, label: '历史报告' },
        { id: 'papers', icon: BookOpen, label: '论文管理' },
    ];

    return (
        <nav className="h-14 bg-slate-950 border-b border-slate-800 flex items-center justify-between px-4 fixed top-0 left-0 right-0 z-50">
            <div className="flex items-center gap-8">
                {/* Logo */}
                <div className="flex items-center gap-2 font-bold text-lg text-cyan-400">
                    <Brain className="w-6 h-6" />
                    <span>ArxivScout</span>
                </div>

                {/* Navigation Links */}
                <div className="flex items-center gap-1">
                    {menuItems.map((item) => (
                        <button
                            key={item.id}
                            onClick={() => setCurrentView(item.id)}
                            className={cn(
                                "flex items-center gap-2 px-3 py-1.5 rounded-md transition-all duration-200 text-sm font-medium",
                                currentView === item.id
                                    ? "bg-cyan-500/10 text-cyan-400"
                                    : "text-slate-400 hover:text-slate-200 hover:bg-slate-900"
                            )}
                        >
                            <item.icon size={16} strokeWidth={currentView === item.id ? 2.5 : 2} />
                            <span>{item.label}</span>
                        </button>
                    ))}
                </div>
            </div>

            {/* Right Side Actions */}
            <div className="flex items-center gap-4">
                <button
                    onClick={() => setCurrentView('settings')}
                    className={cn(
                        "p-2 rounded-full transition-colors",
                        currentView === 'settings' ? "text-cyan-400 bg-cyan-500/10" : "text-slate-400 hover:text-slate-200 hover:bg-slate-900"
                    )}
                    title="全局设置"
                >
                    <Settings size={20} />
                </button>

                <div className="h-6 w-px bg-slate-800 mx-2"></div>

                <UserMenu onNavigate={setCurrentView} />
            </div>
        </nav>
    );
};
