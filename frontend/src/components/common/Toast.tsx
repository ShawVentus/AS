import React, { useEffect } from 'react';
import { CheckCircle, AlertCircle, Info, X } from 'lucide-react';
import { motion } from 'framer-motion';

export type ToastType = 'success' | 'error' | 'info' | 'warning';

export interface ToastProps {
    id: string;
    message: string;
    type: ToastType;
    duration?: number;
    onClose: (id: string) => void;
    action?: {
        label: string;
        onClick: () => void;
    };
}

/**
 * Toast 通知组件
 * 
 * 功能：
 * 1. 显示成功、错误或信息类型的通知。
 * 2. 支持自动关闭和手动关闭。
 * 3. 支持自定义操作按钮（如“查看报告”）。
 * 
 * Args:
 *   id (string): 通知的唯一标识符。
 *   message (string): 通知内容。
 *   type (ToastType): 通知类型 ('success', 'error', 'info', 'warning')。
 *   duration (number): 显示时长（毫秒），默认 3000ms。
 *   onClose (function): 关闭回调函数。
 *   action (object): 可选的操作按钮配置。
 */
export const Toast: React.FC<ToastProps> = ({
    id,
    message,
    type,
    duration = 3000,
    onClose,
    action
}) => {
    useEffect(() => {
        if (duration > 0) {
            const timer = setTimeout(() => {
                onClose(id);
            }, duration);
            return () => clearTimeout(timer);
        }
    }, [id, duration, onClose]);

    const icons = {
        success: <CheckCircle className="w-7 h-7 text-green-400" />,
        error: <AlertCircle className="w-7 h-7 text-red-400" />,
        info: <Info className="w-7 h-7 text-blue-400" />,
        warning: <AlertCircle className="w-7 h-7 text-yellow-400" />
    };

    const bgColors = {
        success: 'bg-slate-900 border-green-500/20',
        error: 'bg-slate-900 border-red-500/20',
        info: 'bg-slate-900 border-blue-500/20',
        warning: 'bg-slate-900 border-yellow-500/20'
    };

    return (
        <motion.div
            layout
            initial={{ opacity: 0, y: 50, scale: 0.9 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 20, scale: 0.9 }}
            className={`
                flex items-center gap-4 p-6 rounded-lg border shadow-xl 
                ${bgColors[type]} backdrop-blur-sm min-w-[400px] max-w-md pointer-events-auto
            `}
        >
            <div className="shrink-0">
                {icons[type]}
            </div>
            <div className="flex-1 text-base text-slate-200">
                {message}
            </div>
            {action && (
                <button
                    onClick={action.onClick}
                    className="text-sm font-medium text-indigo-400 hover:text-indigo-300 transition-colors px-3 py-2 rounded hover:bg-white/5"
                >
                    {action.label}
                </button>
            )}
            <button
                onClick={() => onClose(id)}
                className="shrink-0 text-slate-500 hover:text-slate-300 transition-colors"
            >
                <X size={16} />
            </button>
        </motion.div>
    );
};
