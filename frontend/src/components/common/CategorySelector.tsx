/**
 * 类别选择器组件
 * 功能：支持arXiv论文类别的层级选择，包括：
 * - 二级选择：适用于Mathematics、CS等主类别
 * - 三级选择：适用于Physics主类别下的astro-ph、cond-mat、nlin、physics次类别
 * - All（全选）选项：快速选择整个主类别或次类别
 */
import React, { useState } from 'react';
import { Plus, X, Check, AlertCircle } from 'lucide-react';
import arxivCategories from '../../assets/arxiv_category.json';

// 主类别英文名到arXiv代码的映射
// 用于实现"All（全选）"选项的正确存储
const MAIN_CATEGORY_CODE_MAP: Record<string, string> = {
    'Physics': 'physics',
    'Mathematics': 'math',
    'Computer Science': 'cs',
    'Quantitative Biology': 'q-bio',
    'Quantitative Finance': 'q-fin',
    'Statistics': 'stat',
    'Electrical Engineering and Systems Science': 'eess',
    'Economics': 'econ'
};

interface CategorySelectorProps {
    selectedCategories: string[];
    onChange: (categories: string[]) => void;
}

export const CategorySelector: React.FC<CategorySelectorProps> = ({ selectedCategories, onChange }) => {
    // ========== 状态管理 ==========
    const [isAdding, setIsAdding] = useState(false); // 是否正在添加类别
    const [selectedMainCategory, setSelectedMainCategory] = useState(''); // 第一级：主类别（如Physics、Mathematics）
    const [selectedSubCategory, setSelectedSubCategory] = useState(''); // 第二级：次类别（如astro-ph、math.AG）
    const [selectedLeafCategory, setSelectedLeafCategory] = useState(''); // 第三级：下属类别（仅Physics的部分次类别有）

    /**
     * 添加类别的处理函数
     * 功能：根据不同的选择路径，决定添加哪一级的类别代码
     * 
     * 逻辑分支：
     * 1. Physics + 有三级的次类别（astro-ph/cond-mat/nlin/physics）→ 必须选择第三级
     * 2. Physics + 无三级的次类别（gr-qc/hep-ex等）→ 直接添加次类别
     * 3. 其他主类别 → 直接添加次类别（可能是具体分类或All）
     */
    const handleAddCategory = () => {
        let categoryToAdd = '';
        
        // 判断添加哪一级的分类
        if (selectedMainCategory === 'Physics') {
            // Physics类别：检查是否有第三级
            if (needsLeafSelection) {
                // 有三级分类的次类别（astro-ph、cond-mat、nlin、physics）
                if (selectedLeafCategory) {
                    // 用户选择了具体的三级分类或All（All的值就是次类别代码）
                    categoryToAdd = selectedLeafCategory;
                } else {
                    // 未选择第三级，不允许添加
                    return;
                }
            } else {
                // 无三级分类的次类别（gr-qc、hep-ex等）
                categoryToAdd = selectedSubCategory;
            }
        } else {
            // 其他主类别（Math、CS等）
            categoryToAdd = selectedSubCategory;
        }
        
        // 检查是否已存在，避免重复添加
        if (categoryToAdd && !selectedCategories.includes(categoryToAdd)) {
            onChange([...selectedCategories, categoryToAdd]);
            
            // 重置所有选择状态
            setSelectedSubCategory('');
            setSelectedLeafCategory('');
            setIsAdding(false);
        }
    };

    /**
     * 移除类别的处理函数
     * 
     * Args:
     *   categoryToRemove: string - 要移除的类别代码
     */
    const handleRemoveCategory = (categoryToRemove: string) => {
        onChange(selectedCategories.filter(c => c !== categoryToRemove));
    };

    // ========== 数据计算 ==========
    // 将JSON数据转换为组件使用的格式
    const mainCategories = arxivCategories.map(c => ({
        name: c.MainCategory_ZH,
        value: c.MainCategory_EN,
        subcategories: c.Subcategories
    }));

    // 获取当前选中主类别的次类别列表
    const currentSubcategories = mainCategories.find(c => c.value === selectedMainCategory)?.subcategories || [];

    // 获取当前选中的次类别对象（用于判断是否有第三级）
    const currentSubCategory = currentSubcategories.find(sub => sub.Abbreviation === selectedSubCategory);

    // 获取当前次类别下的三级分类列表（如果有Subcategories字段）
    const currentLeafCategories = currentSubCategory?.Subcategories || [];

    // 判断是否需要显示第三级下拉框（有Subcategories字段且不为空）
    const needsLeafSelection = currentLeafCategories.length > 0;

    return (
        <div className="space-y-2">
            <div className="flex items-center gap-2 border-l-4 border-emerald-500 pl-3">
                <h3 className="text-base font-medium text-white">类别 (Category)</h3>
                <div className="relative group cursor-help">
                    <AlertCircle size={16} className="text-slate-400 hover:text-white transition-colors" />
                    <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-64 p-3 bg-slate-800 border border-slate-700 rounded-lg shadow-xl opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-10">
                        <p className="text-xs text-slate-300 leading-relaxed">
                            stat,q-bio,econ,eess,q-fin等主类别每日新增论文较少（20篇以内），建议全部获取
                        </p>
                        <div className="absolute bottom-[-4px] left-1/2 -translate-x-1/2 w-2 h-2 bg-slate-800 border-r border-b border-slate-700 rotate-45"></div>
                    </div>
                </div>
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
                                setSelectedSubCategory(''); // 切换主类别时重置次类别
                                setSelectedLeafCategory(''); // 同时重置第三级
                            }}
                            className="bg-slate-900 border border-slate-700 rounded-md px-2 py-1.5 text-white text-sm focus:border-blue-500 outline-none max-w-[140px]"
                        >
                            <option value="">主类别...</option>
                            {mainCategories.map(c => (
                                <option key={c.value} value={c.value}>{c.name}</option>
                            ))}
                        </select>

                        {/* 第二级下拉框：次类别选择 */}
                        <select
                            value={selectedSubCategory}
                            onChange={e => {
                                setSelectedSubCategory(e.target.value);
                                setSelectedLeafCategory(''); // 切换次类别时重置第三级
                            }}
                            disabled={!selectedMainCategory}
                            className="bg-slate-900 border border-slate-700 rounded-md px-2 py-1.5 text-white text-sm focus:border-blue-500 outline-none max-w-[200px] disabled:opacity-50"
                        >
                            <option value="">次类别...</option>
                            
                            {/* 非Physics主类别：添加All（全选）选项 */}
                            {selectedMainCategory && selectedMainCategory !== 'Physics' && (
                                <option value={MAIN_CATEGORY_CODE_MAP[selectedMainCategory]}>
                                    All（全选）
                                </option>
                            )}
                            
                            {/* 显示所有次类别 */}
                            {currentSubcategories.map(sub => (
                                <option key={sub.Abbreviation} value={sub.Abbreviation}>
                                    {sub.Name}
                                </option>
                            ))}
                        </select>

                        {/* 第三级下拉框：仅Physics的有Subcategories的次类别显示 */}
                        {needsLeafSelection && (
                            <select
                                value={selectedLeafCategory}
                                onChange={e => setSelectedLeafCategory(e.target.value)}
                                disabled={!selectedSubCategory}
                                className="bg-slate-900 border border-slate-700 rounded-md px-2 py-1.5 text-white text-sm focus:border-blue-500 outline-none max-w-[200px] disabled:opacity-50"
                            >
                                <option value="">下属类别...</option>
                                
                                {/* All选项：值为次类别代码（如astro-ph） */}
                                <option value={selectedSubCategory}>All（全选）</option>
                                
                                {/* 显示所有三级分类 */}
                                {currentLeafCategories.map(leaf => (
                                    <option key={leaf.Abbreviation} value={leaf.Abbreviation}>
                                        {leaf.Name}
                                    </option>
                                ))}
                            </select>
                        )}

                        {/* 添加按钮 */}
                        <button
                            onClick={handleAddCategory}
                            disabled={
                                !selectedSubCategory || 
                                (needsLeafSelection && !selectedLeafCategory) // 需要第三级但未选择时禁用
                            }
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
