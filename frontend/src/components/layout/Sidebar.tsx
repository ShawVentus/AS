import React, { useState } from 'react';
import {
    LayoutDashboard,
    FileText,
    BookOpen,
    Settings,
    ChevronLeft,
    ChevronRight,
    Menu
} from 'lucide-react';

interface SidebarProps {
    currentView: string;
    setCurrentView: (view: string) => void;
}

export function Sidebar({ currentView, setCurrentView }: SidebarProps) {
    const [isCollapsed, setIsCollapsed] = useState(false);

    const menuItems = [
        { id: 'dashboard', label: '概览', icon: LayoutDashboard },
        { id: 'reports', label: '研报', icon: FileText },
        { id: 'papers', label: '论文库', icon: BookOpen },
        { id: 'settings', label: '设置', icon: Settings },
    ];

    return (
        <div
            className={`
        h-screen bg-slate-900 border-r border-slate-800 
        transition-all duration-300 ease-in-out flex flex-col
        ${isCollapsed ? 'w-16' : 'w-64'}
      `}
        >
            {/* Header */}
            <div className="h-16 flex items-center justify-between px-4 border-b border-slate-800">
                {!isCollapsed && (
                    <span className="font-bold text-lg text-white tracking-tight">
                        Paper Scout
                    </span>
                )}
                <button
                    onClick={() => setIsCollapsed(!isCollapsed)}
                    className="p-1.5 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-white transition-colors"
                >
                    {isCollapsed ? <Menu size={20} /> : <ChevronLeft size={20} />}
                </button>
            </div>

            {/* Navigation */}
            <nav className="flex-1 py-6 px-2 space-y-1">
                {menuItems.map((item) => {
                    const isActive = currentView === item.id;
                    return (
                        <button
                            key={item.id}
                            onClick={() => setCurrentView(item.id)}
                            className={`
                w-full flex items-center px-3 py-2.5 rounded-lg transition-all duration-200 group
                ${isActive
                                    ? 'bg-blue-600 text-white shadow-lg shadow-blue-900/20'
                                    : 'text-slate-400 hover:bg-slate-800 hover:text-white'
                                }
              `}
                            title={isCollapsed ? item.label : undefined}
                        >
                            <item.icon
                                size={20}
                                className={`
                  ${isActive ? 'text-white' : 'text-slate-400 group-hover:text-white'}
                  ${isCollapsed ? 'mx-auto' : 'mr-3'}
                `}
                            />
                            {!isCollapsed && (
                                <span className="font-medium text-sm">{item.label}</span>
                            )}
                        </button>
                    );
                })}
            </nav>

            {/* Footer / User Info (Optional) */}
            <div className="p-4 border-t border-slate-800">
                {!isCollapsed ? (
                    <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-blue-500 to-purple-500 flex items-center justify-center text-xs font-bold text-white">
                            U
                        </div>
                        <div className="flex-1 min-w-0">
                            <div className="text-sm font-medium text-white truncate">User</div>
                            <div className="text-xs text-slate-500 truncate">Researcher</div>
                        </div>
                    </div>
                ) : (
                    <div className="w-8 h-8 mx-auto rounded-full bg-gradient-to-tr from-blue-500 to-purple-500 flex items-center justify-center text-xs font-bold text-white">
                        U
                    </div>
                )}
            </div>
        </div>
    );
}
