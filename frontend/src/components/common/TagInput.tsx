import React, { useState, useRef, useEffect } from 'react';
import type { KeyboardEvent } from 'react';
import { X, Plus } from 'lucide-react';

interface TagInputProps {
    tags: string[];
    onChange: (tags: string[]) => void;
    placeholder?: string;
    suggestions?: string[];
    label?: string;
    addButtonText?: string;
}

export const TagInput: React.FC<TagInputProps> = ({ tags, onChange, placeholder, suggestions = [], label, addButtonText = "添加" }) => {
    const [isEditing, setIsEditing] = useState(false);
    const [input, setInput] = useState('');
    const inputRef = useRef<HTMLInputElement>(null);

    useEffect(() => {
        if (isEditing && inputRef.current) {
            inputRef.current.focus();
        }
    }, [isEditing]);

    const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            if (input.trim()) {
                if (!tags.includes(input.trim())) {
                    onChange([...tags, input.trim()]);
                }
                setInput('');
                setIsEditing(false);
            } else {
                setIsEditing(false);
            }
        } else if (e.key === 'Escape') {
            setIsEditing(false);
            setInput('');
        }
    };

    const handleBlur = () => {
        if (input.trim()) {
            if (!tags.includes(input.trim())) {
                onChange([...tags, input.trim()]);
            }
            setInput('');
        }
        setIsEditing(false);
    };

    const removeTag = (tagToRemove: string) => {
        onChange(tags.filter(tag => tag !== tagToRemove));
    };

    const addTag = (tag: string) => {
        if (!tags.includes(tag)) {
            onChange([...tags, tag]);
        }
    };

    return (
        <div className="space-y-2">
            {label && (
                <div className="flex items-center gap-2 border-l-4 border-emerald-500 pl-3">
                    <h3 className="text-base font-medium text-white">{label}</h3>
                </div>
            )}

            <div className="flex flex-wrap gap-2">
                {tags.map(tag => (
                    <span key={tag} className="flex items-center gap-2 px-2 py-1 bg-slate-950 text-slate-200 text-sm rounded-md border border-slate-800 group hover:border-slate-600 transition-colors">
                        {tag}
                        <button
                            onClick={() => removeTag(tag)}
                            className="text-slate-500 hover:text-white transition-colors opacity-0 group-hover:opacity-100"
                        >
                            <X size={14} />
                        </button>
                    </span>
                ))}

                {isEditing ? (
                    <input
                        ref={inputRef}
                        type="text"
                        value={input}
                        onChange={e => setInput(e.target.value)}
                        onKeyDown={handleKeyDown}
                        onBlur={handleBlur}
                        placeholder={placeholder}
                        className="px-3 py-1.5 bg-slate-900 border border-blue-500 rounded-md text-white text-sm outline-none min-w-[120px]"
                    />
                ) : (
                    <button
                        onClick={() => setIsEditing(true)}
                        className="flex items-center gap-1.5 px-3 py-1.5 border border-dashed border-slate-600 rounded-md text-slate-400 text-sm hover:text-white hover:border-slate-400 transition-all hover:bg-slate-800/50"
                    >
                        <Plus size={14} />
                        {addButtonText}
                    </button>
                )}
            </div>

            {suggestions.length > 0 && isEditing && (
                <div className="flex flex-wrap gap-2 mt-2">
                    {suggestions.filter(s => !tags.includes(s)).map(suggestion => (
                        <button
                            key={suggestion}
                            onClick={() => addTag(suggestion)}
                            className="text-xs text-slate-500 hover:text-blue-400 transition-colors"
                        >
                            + {suggestion}
                        </button>
                    ))}
                </div>
            )}
        </div>
    );
};
