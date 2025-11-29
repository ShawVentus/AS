import React from 'react';

interface SkeletonProps {
    variant?: 'circle' | 'rect' | 'text';
    width?: string | number;
    height?: string | number;
    className?: string;
}

export const Skeleton: React.FC<SkeletonProps> = ({
    variant = 'rect',
    width,
    height,
    className = ''
}) => {
    const baseClasses = "bg-slate-800 animate-pulse";

    const variantClasses = {
        circle: "rounded-full",
        rect: "rounded-lg",
        text: "rounded h-4 w-full"
    };

    const style = {
        width: width,
        height: height
    };

    return (
        <div
            className={`${baseClasses} ${variantClasses[variant]} ${className}`}
            style={style}
        />
    );
};
