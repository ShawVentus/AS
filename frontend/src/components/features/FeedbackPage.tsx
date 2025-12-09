import React, { useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Star } from 'lucide-react';

export const FeedbackPage: React.FC = () => {
    const [searchParams] = useSearchParams();
    const reportId = searchParams.get('report');
    const preRating = parseInt(searchParams.get('rating') || '0');

    const [rating, setRating] = useState(preRating);
    const [feedback, setFeedback] = useState('');
    const [showPrompt, setShowPrompt] = useState(preRating <= 3 && preRating > 0);
    const [submitted, setSubmitted] = useState(false);

    const handleRatingClick = (r: number) => {
        setRating(r);
        setShowPrompt(r <= 3);
    };

    const handleSubmit = async () => {
        try {
            const response = await fetch('/api/v1/email/feedback', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    // 如果需要认证，这里需要添加 Authorization header
                    // 'Authorization': `Bearer ${token}` 
                },
                body: JSON.stringify({ report_id: reportId, rating, feedback_text: feedback })
            });

            if (response.ok) {
                setSubmitted(true);
            } else {
                alert('提交失败，请稍后重试');
            }
        } catch (error) {
            console.error('Error submitting feedback:', error);
            alert('提交出错');
        }
    };

    if (submitted) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-slate-950">
                <div className="text-center animate-in fade-in zoom-in duration-500">
                    <div className="text-6xl mb-4">🎉</div>
                    <h2 className="text-2xl font-bold text-white mb-2">感谢您的反馈！</h2>
                    <p className="text-slate-400">您的意见将帮助我们为您提供更好的服务。</p>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen flex items-center justify-center bg-slate-950 p-6">
            <div className="bg-slate-900 rounded-xl p-8 max-w-md w-full border border-slate-800 shadow-2xl animate-in fade-in slide-in-from-bottom-4 duration-500">
                <h2 className="text-2xl font-bold text-white mb-2 text-center">为今天的报告评分</h2>
                <p className="text-slate-400 text-center mb-8 text-sm">您的反馈对我们非常重要</p>

                <div className="flex justify-center gap-3 mb-8">
                    {[1, 2, 3, 4, 5].map((s) => (
                        <button
                            key={s}
                            onClick={() => handleRatingClick(s)}
                            className="transition-transform hover:scale-110 focus:outline-none"
                        >
                            <Star
                                size={40}
                                className={`${s <= rating ? 'fill-yellow-400 text-yellow-400' : 'text-slate-700'} transition-colors duration-200`}
                                strokeWidth={1.5}
                            />
                        </button>
                    ))}
                </div>

                {showPrompt && (
                    <div className="bg-blue-900/20 border border-blue-500/30 rounded-lg p-4 mb-6 text-sm text-blue-300 animate-in fade-in">
                        💡 您的反馈意见将会用于为您生成更个性化的报告，请告诉我们需要改进的地方。
                    </div>
                )}

                <textarea
                    value={feedback}
                    onChange={(e) => setFeedback(e.target.value)}
                    placeholder="告诉我们您的想法（可选）..."
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg p-4 text-white mb-6 resize-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none transition-all placeholder:text-slate-600"
                    rows={4}
                />

                <button
                    onClick={handleSubmit}
                    disabled={rating === 0}
                    className="w-full bg-blue-600 hover:bg-blue-500 disabled:bg-slate-800 disabled:text-slate-500 text-white font-medium py-3 rounded-lg transition-all shadow-lg shadow-blue-900/20"
                >
                    提交反馈
                </button>
            </div>
        </div>
    );
};
