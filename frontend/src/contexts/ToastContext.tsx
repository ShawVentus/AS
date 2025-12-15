import React, { createContext, useContext, useState, useCallback } from 'react';
import { createPortal } from 'react-dom';
import { AnimatePresence } from 'framer-motion';
import { Toast } from '../components/common/Toast';
import type { ToastType } from '../components/common/Toast';

interface ToastData {
    id: string;
    message: string;
    type: ToastType;
    duration?: number;
    action?: {
        label: string;
        onClick: () => void;
    };
}

interface ToastContextType {
    showToast: (message: string, type?: ToastType, options?: { duration?: number; action?: ToastData['action'] }) => void;
}

const ToastContext = createContext<ToastContextType | undefined>(undefined);

/**
 * Toast Provider 组件
 * 
 * 功能：
 * 1. 提供全局 showToast 方法。
 * 2. 管理 Toast 列表状态。
 * 3. 在屏幕右下角渲染 Toast 容器。
 */
export const ToastProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    const [toasts, setToasts] = useState<ToastData[]>([]);

    const removeToast = useCallback((id: string) => {
        setToasts(prev => prev.filter(t => t.id !== id));
    }, []);

    const showToast = useCallback((message: string, type: ToastType = 'info', options?: { duration?: number; action?: ToastData['action'] }) => {
        const id = Math.random().toString(36).substring(2, 9);
        setToasts(prev => [...prev, {
            id,
            message,
            type,
            duration: options?.duration,
            action: options?.action
        }]);
    }, []);

    return (
        <ToastContext.Provider value={{ showToast }}>
            {children}
            {createPortal(
                <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 pointer-events-none">
                    <AnimatePresence mode="popLayout">
                        {toasts.map(toast => (
                            <Toast
                                key={toast.id}
                                {...toast}
                                onClose={removeToast}
                            />
                        ))}
                    </AnimatePresence>
                </div>,
                document.body
            )}
        </ToastContext.Provider>
    );
};

export const useToast = () => {
    const context = useContext(ToastContext);
    if (!context) {
        throw new Error('useToast must be used within a ToastProvider');
    }
    return context;
};
