import React from 'react';
import { cn } from '../../../utils/cn';

interface RefSentenceProps {
    /** 句子纯文本 */
    text: string;
    /** 引用的论文 ID 列表 */
    refIds: string[];
    /** 是否悬停中 */
    isHovered: boolean;
    /** 是否对应的论文卡片被悬停 */
    isPaperHovered?: boolean;
    /** 是否已固定 (点击选中) */
    isSelected: boolean;
    /** 鼠标进入事件 */
    onMouseEnter: (refIds: string[]) => void;
    /** 鼠标离开事件 */
    onMouseLeave: () => void;
    /** 点击事件 */
    onClick: (refIds: string[]) => void;
    /** 额外的 CSS 类名 */
    className?: string;
}

/**
 * 引用句子组件
 * 
 * 功能:
 *   渲染包含引用的句子，支持悬停高亮和点击固定。
 *   样式上使用浅色虚线下划线和轻微背景色提示。
 */
export const RefSentence: React.FC<RefSentenceProps> = ({
    text,
    refIds,
    isHovered,
    isPaperHovered,
    isSelected,
    onMouseEnter,
    onMouseLeave,
    onClick,
    className
}) => {
    return (
        <span
            className={cn(
                "cursor-pointer transition-all duration-150 rounded px-1",
                className,
                // 基础样式：更亮的虚线下划线
                "border-b border-dashed border-slate-400/70",

                // 状态样式
                isSelected
                    ? 'bg-cyan-950/40 border-cyan-500/50 text-cyan-100 shadow-[0_0_10px_rgba(8,145,178,0.1)]' // 固定状态
                    : (isHovered || isPaperHovered)
                        ? 'bg-indigo-500/30 border-indigo-400/80 text-indigo-50 border-solid shadow-sm' // 悬停状态 (双向) - 更明显
                        : 'hover:bg-slate-800/40 text-slate-300' // 默认状态
            )}
            onMouseEnter={() => onMouseEnter(refIds)}
            onMouseLeave={onMouseLeave}
            onClick={(e) => {
                e.stopPropagation();
                onClick(refIds);
            }}
            title={refIds.length > 0 ? `点击查看 ${refIds.length} 篇相关论文` : undefined}
        >
            {text}
        </span>
    );
};
