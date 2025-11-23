import React from 'react';
import {
    LayoutDashboard,
    FileText,
    BookOpen,
    Settings,
    Bell,
    Search
} from 'lucide-react';

interface HeaderProps {
    currentView: string;
    setCurrentView: (view: string) => void;
    userProfile?: {
        info: {
            name: string;
            role?: string;
        }
    };
}

export function Header({ currentView, setCurrentView, userProfile }: HeaderProps) {
    const menuItems = [
        { id: 'dashboard', label: '主页', icon: LayoutDashboard },
        { id: 'reports', label: '研报', icon: FileText },
        { id: 'papers', label: '论文库', icon: BookOpen },
        { id: 'settings', label: '设置', icon: Settings },
    ];

    return (
        <header className="h-16 bg-slate-950 border-b border-slate-800 flex items-center justify-between px-6 sticky top-0 z-50">
            {/* Logo & Brand */}
            <div className="flex items-center gap-8">
                <button
                    onClick={() => setCurrentView('dashboard')}
                    className="flex items-center gap-2 hover:opacity-80 transition-opacity"
                >
                    <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
                        <BookOpen className="text-white" size={20} />
                    </div>
                    <span className="font-bold text-xl text-white tracking-tight">
                        ArxivScout
                    </span>
                </button>

                {/* Navigation */}
                <nav className="hidden md:flex items-center gap-1">
                    {menuItems.map((item) => {
                        const isActive = currentView === item.id;
                        return (
                            <button
                                key={item.id}
                                onClick={() => setCurrentView(item.id)}
                                className={`
                                    flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium transition-all duration-200
                                    ${isActive
                                        ? 'bg-slate-800 text-white'
                                        : 'text-slate-400 hover:text-white hover:bg-slate-900'
                                    }
                                `}
                            >
                                <item.icon size={16} />
                                <span>{item.label}</span>
                            </button>
                        );
                    })}
                </nav>
            </div>

            {/* Right Side Actions */}
            <div className="flex items-center gap-4">
                {/* Search Bar (Visual only for now) */}
                <div className="hidden lg:flex items-center bg-slate-900 rounded-full px-4 py-1.5 border border-slate-800 focus-within:border-slate-700 transition-colors">
                    <Search size={14} className="text-slate-500 mr-2" />
                    <input
                        type="text"
                        placeholder="搜索论文..."
                        className="bg-transparent border-none outline-none text-sm text-slate-200 placeholder:text-slate-600 w-48"
                    />
                </div>

                <div className="h-6 w-px bg-slate-800 mx-2 hidden lg:block"></div>

                <button className="text-slate-400 hover:text-white transition-colors relative">
                    <Bell size={20} />
                    <span className="absolute top-0 right-0 w-2 h-2 bg-red-500 rounded-full border-2 border-slate-950"></span>
                </button>

                <div className="flex items-center gap-3 pl-2">
                    <div className="text-right hidden sm:block">
                        <div className="text-sm font-medium text-white">
                            {userProfile?.info.name || 'User'}
                        </div>
                        <div className="text-[10px] text-slate-500 uppercase tracking-wider">
                            {userProfile?.info.role || 'Researcher'}
                        </div>
                    </div>
                    <div className="w-9 h-9 rounded-full bg-gradient-to-tr from-blue-500 to-purple-500 flex items-center justify-center text-sm font-bold text-white ring-2 ring-slate-900 cursor-pointer hover:ring-slate-700 transition-all">
                        {userProfile?.info.name?.[0]?.toUpperCase() || 'U'}
                    </div>
                </div>
            </div>
        </header>
    );
}
