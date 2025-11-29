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
                    <p className="text-slate-300 text-sm leading-relaxed">
                        {profile.context.preferences}
                    </p>
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
