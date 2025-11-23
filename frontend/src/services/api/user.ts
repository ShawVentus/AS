import { fetchJSON } from './config';
import type { UserProfile, UserInfo, UserFeedback } from '../../types';

export const UserAPI = {
    getProfile: () => fetchJSON<UserProfile>('/user/profile'),
    initialize: (userInfo: UserInfo) => fetchJSON<UserProfile>('/user/initialize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(userInfo)
    }),
    updateNL: (text: string, userId: string) => fetchJSON<UserProfile>('/user/nl', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, user_id: userId })
    }),
    updateFeedback: (userId: string, feedbacks: UserFeedback[]) => fetchJSON<UserProfile>(`/user/update/feedback?user_id=${userId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(feedbacks)
    }),
};
