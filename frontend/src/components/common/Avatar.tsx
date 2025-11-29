import React, { useMemo } from 'react';

interface AvatarProps {
    name: string;
    avatarUrl?: string;
    size?: 'sm' | 'md' | 'lg' | 'xl';
    className?: string;
    onClick?: () => void;
}

const COLORS = [
    'bg-red-500',
    'bg-orange-500',
    'bg-amber-500',
    'bg-yellow-500',
    'bg-lime-500',
    'bg-green-500',
    'bg-emerald-500',
    'bg-teal-500',
    'bg-cyan-500',
    'bg-sky-500',
    'bg-blue-500',
    'bg-indigo-500',
    'bg-violet-500',
    'bg-purple-500',
    'bg-fuchsia-500',
    'bg-pink-500',
    'bg-rose-500',
];

export const Avatar: React.FC<AvatarProps> = ({
    name,
    avatarUrl,
    size = 'md',
    className = '',
    onClick
}) => {
    const initial = useMemo(() => {
        if (!name) return '?';
        // 如果是中文，取第一个字
        if (/[\u4e00-\u9fa5]/.test(name)) {
            return name[0];
        }
        // 否则取首字母大写
        return name[0].toUpperCase();
    }, [name]);

    const bgColor = useMemo(() => {
        if (!name) return 'bg-slate-700';
        let hash = 0;
        for (let i = 0; i < name.length; i++) {
            hash = name.charCodeAt(i) + ((hash << 5) - hash);
        }
        const index = Math.abs(hash) % COLORS.length;
        return COLORS[index];
    }, [name]);

    const sizeClasses = {
        sm: 'w-8 h-8 text-xs',
        md: 'w-10 h-10 text-sm',
        lg: 'w-12 h-12 text-base',
        xl: 'w-16 h-16 text-xl',
    };

    const [imgError, setImgError] = React.useState(false);

    // Reset error state when avatarUrl changes
    React.useEffect(() => {
        setImgError(false);
    }, [avatarUrl]);

    // 如果有头像 URL 且没有加载错误，显示图片
    if (avatarUrl && !imgError) {
        return (
            <div
                onClick={onClick}
                className={`
                    ${sizeClasses[size]}
                    rounded-full
                    overflow-hidden
                    ring-2 ring-slate-900
                    ${onClick ? 'cursor-pointer hover:ring-slate-700 transition-all' : ''}
                    ${className}
                `}
            >
                <img
                    src={avatarUrl}
                    alt={name}
                    loading="lazy"
                    onError={() => setImgError(true)}
                    className="w-full h-full object-cover"
                />
            </div>
        );
    }

    // 否则显示首字母头像
    return (
        <div
            onClick={onClick}
            className={`
                ${sizeClasses[size]}
                ${bgColor}
                rounded-full
                flex items-center justify-center
                font-bold text-white
                ring-2 ring-slate-900
                ${onClick ? 'cursor-pointer hover:ring-slate-700 transition-all' : ''}
                ${className}
            `}
        >
            {initial}
        </div>
    );
};
