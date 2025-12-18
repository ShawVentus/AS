import React from 'react';
import type { UserProfile as UserProfileType } from '../../../types';
import { Avatar } from '../../common/Avatar';

interface UserProfileProps {
    profile: UserProfileType;
}

export const UserProfile: React.FC<UserProfileProps> = ({ profile }) => {
    if (!profile) return null;

    return (
        <div className="bg-slate-900 border border-slate-800 rounded-lg p-6">
            <div className="flex items-center gap-4 mb-6">
                <Avatar name={profile.info.name} size="lg" />
                <div>
                    <h2 className="text-xl font-bold text-white">{profile.info.name}</h2>
                    <p className="text-slate-400">{profile.info.role}</p>
                </div>
            </div>

            <div className="space-y-4">
                <div>
                    <h3 className="text-sm font-medium text-slate-500 mb-2">研究偏好</h3>
                    {profile.context.preferences && profile.context.preferences.length > 0 ? (
                        <ul className="space-y-1.5">
                            {profile.context.preferences.map((pref, idx) => (
                                <li key={idx} className="text-slate-300 text-sm flex items-start">
                                    <span className="text-cyan-400 mr-2 mt-0.5">•</span>
                                    <span>{pref}</span>
                                </li>
                            ))}
                        </ul>
                    ) : (
                        <p className="text-slate-500 text-sm italic">暂无偏好设置</p>
                    )}
                </div>

                <div>
                    <h3 className="text-sm font-medium text-slate-500 mb-2">关注领域</h3>
                    <div className="flex flex-wrap gap-2">
                        {profile.focus.category.map(cat => (
                            <span key={cat} className="px-2 py-1 bg-slate-800 text-slate-300 text-xs rounded">
                                {cat}
                            </span>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
};

export const UserMenu: React.FC<{ onNavigate: (view: string) => void }> = ({ onNavigate }) => {
    return (
        <button
            onClick={() => onNavigate('settings')}
            className="flex items-center gap-2 text-sm font-medium text-slate-400 hover:text-white transition-colors"
        >
            <Avatar name="User" size="sm" />
            <span>我的账户</span>
        </button>
    );
};
