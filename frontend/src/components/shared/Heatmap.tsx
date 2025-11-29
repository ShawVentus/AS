import React from 'react';
import { Calendar } from 'lucide-react';
import { EmptyState } from '../common/EmptyState';

export const Heatmap = () => {
    // TODO: Implement real data fetching from /api/v1/user/me/activity-heatmap

    return (
        <div className="w-full h-48 flex items-center justify-center">
            <EmptyState
                icon={Calendar}
                title="活跃度数据收集中"
                description="多使用系统后这里会显示您的科研热力图"
                className="scale-90"
            />
        </div>
    );
};
