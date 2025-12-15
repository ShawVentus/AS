import React, { useState } from 'react';
import { Plus, X, Check } from 'lucide-react';
import arxivCategories from '../../assets/arxiv_category.json';

interface CategorySelectorProps {
    selectedCategories: string[];
    onChange: (categories: string[]) => void;
}

export const CategorySelector: React.FC<CategorySelectorProps> = ({ selectedCategories, onChange }) => {
    const [isAdding, setIsAdding] = useState(false);
    const [selectedMainCategory, setSelectedMainCategory] = useState('');
    const [selectedSubCategory, setSelectedSubCategory] = useState('');

    const handleAddCategory = () => {
        if (selectedSubCategory && !selectedCategories.includes(selectedSubCategory)) {
            onChange([...selectedCategories, selectedSubCategory]);
            setSelectedSubCategory('');
            // Optional: Close after adding, or keep open to add more
            setIsAdding(false);
        }
    };

    const handleRemoveCategory = (categoryToRemove: string) => {
        onChange(selectedCategories.filter(c => c !== categoryToRemove));
    };

    const mainCategories = arxivCategories.map(c => ({
        name: c.MainCategory_ZH,
        value: c.MainCategory_EN,
        subcategories: c.Subcategories
    }));

    const currentSubcategories = mainCategories.find(c => c.value === selectedMainCategory)?.subcategories || [];

    return (
        <div className="space-y-2">
            <div className="flex items-center gap-2 border-l-4 border-emerald-500 pl-3">
                <h3 className="text-base font-medium text-white">类别 (Category)</h3>
            </div>

            <div className="flex flex-wrap gap-2">
                {selectedCategories.map(category => (
                    <span key={category} className="flex items-center gap-2 px-2 py-1 bg-slate-950 text-slate-200 text-sm rounded-md border border-slate-800 group hover:border-slate-600 transition-colors">
                        {category}
                        <button
                            onClick={() => handleRemoveCategory(category)}
                            className="text-slate-500 hover:text-white transition-colors opacity-0 group-hover:opacity-100"
                        >
                            <X size={14} />
                        </button>
                    </span>
                ))}

                {!isAdding ? (
                    <button
                        onClick={() => setIsAdding(true)}
                        className="flex items-center gap-1.5 px-3 py-1.5 border border-dashed border-slate-600 rounded-md text-slate-400 text-sm hover:text-white hover:border-slate-400 transition-all hover:bg-slate-800/50"
                    >
                        <Plus size={14} />
                        添加类别
                    </button>
                ) : (
                    <div className="flex items-center gap-2 animate-in fade-in zoom-in-95 duration-200">
                        <select
                            value={selectedMainCategory}
                            onChange={e => {
                                setSelectedMainCategory(e.target.value);
                                setSelectedSubCategory('');
                            }}
                            className="bg-slate-900 border border-slate-700 rounded-md px-2 py-1.5 text-white text-sm focus:border-blue-500 outline-none max-w-[140px]"
                        >
                            <option value="">主类别...</option>
                            {mainCategories.map(c => (
                                <option key={c.value} value={c.value}>{c.name}</option>
                            ))}
                        </select>

                        <select
                            value={selectedSubCategory}
                            onChange={e => setSelectedSubCategory(e.target.value)}
                            disabled={!selectedMainCategory}
                            className="bg-slate-900 border border-slate-700 rounded-md px-2 py-1.5 text-white text-sm focus:border-blue-500 outline-none max-w-[200px] disabled:opacity-50"
                        >
                            <option value="">子类别...</option>
                            {currentSubcategories.map(sub => (
                                <option key={sub.Abbreviation} value={sub.Abbreviation}>
                                    {sub.Name}
                                </option>
                            ))}
                        </select>

                        <button
                            onClick={handleAddCategory}
                            disabled={!selectedSubCategory}
                            className="p-1.5 bg-blue-600 hover:bg-blue-500 text-white rounded-md disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            <Check size={16} />
                        </button>
                        <button
                            onClick={() => setIsAdding(false)}
                            className="p-1.5 text-slate-400 hover:text-white"
                        >
                            <X size={16} />
                        </button>
                    </div>
                )}
            </div>
        </div>
    );
};
