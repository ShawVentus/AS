import React, { useState, useEffect } from 'react';
import { ChevronLeft, ChevronRight, ChevronDown } from 'lucide-react';

interface CalendarProps {
    selectedDate: Date | null;
    onDateSelect: (date: Date | null) => void;
    paperDates: string[]; // List of dates with papers (YYYY-MM-DD)
    onMonthChange: (year: number, month: number) => void;
}

export const Calendar: React.FC<CalendarProps> = ({ selectedDate, onDateSelect, paperDates, onMonthChange }) => {
    const [currentDate, setCurrentDate] = useState(selectedDate || new Date());
    const [showMonthSelector, setShowMonthSelector] = useState(false);
    const [showYearSelector, setShowYearSelector] = useState(false);

    useEffect(() => {
        // Notify parent about initial month or when it changes
        onMonthChange(currentDate.getFullYear(), currentDate.getMonth() + 1);
    }, [currentDate.getFullYear(), currentDate.getMonth()]);

    const getDaysInMonth = (year: number, month: number) => {
        return new Date(year, month + 1, 0).getDate();
    };

    const getFirstDayOfMonth = (year: number, month: number) => {
        return new Date(year, month, 1).getDay();
    };

    const handlePrevMonth = () => {
        setCurrentDate(new Date(currentDate.getFullYear(), currentDate.getMonth() - 1, 1));
    };

    const handleNextMonth = () => {
        setCurrentDate(new Date(currentDate.getFullYear(), currentDate.getMonth() + 1, 1));
    };

    const handleMonthSelect = (monthIndex: number) => {
        setCurrentDate(new Date(currentDate.getFullYear(), monthIndex, 1));
        setShowMonthSelector(false);
    };

    const handleYearSelect = (year: number) => {
        setCurrentDate(new Date(year, currentDate.getMonth(), 1));
        setShowYearSelector(false);
    };

    const handleDateClick = (day: number) => {
        const clickedDate = new Date(currentDate.getFullYear(), currentDate.getMonth(), day);
        if (selectedDate &&
            selectedDate.getDate() === day &&
            selectedDate.getMonth() === currentDate.getMonth() &&
            selectedDate.getFullYear() === currentDate.getFullYear()) {
            onDateSelect(null);
        } else {
            onDateSelect(clickedDate);
        }
    };

    const renderCalendarDays = () => {
        const year = currentDate.getFullYear();
        const month = currentDate.getMonth();
        const daysInMonth = getDaysInMonth(year, month);
        const firstDay = getFirstDayOfMonth(year, month);
        const days = [];

        for (let i = 0; i < firstDay; i++) {
            days.push(<div key={`empty-${i}`} className="h-9 w-9" />);
        }

        for (let day = 1; day <= daysInMonth; day++) {
            const dateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
            const hasPaper = paperDates.includes(dateStr);
            const isSelected = selectedDate &&
                selectedDate.getDate() === day &&
                selectedDate.getMonth() === month &&
                selectedDate.getFullYear() === year;
            const isToday = new Date().toDateString() === new Date(year, month, day).toDateString();

            const isFuture = new Date(year, month, day) > new Date();

            let bgClass = "hover:bg-slate-700";
            let textClass = "text-slate-400";

            if (isFuture) {
                bgClass = "opacity-30 cursor-not-allowed";
                textClass = "text-slate-600";
            } else if (isSelected) {
                bgClass = "bg-blue-600 text-white shadow-lg shadow-blue-900/50";
                textClass = "text-white font-medium";
            } else if (hasPaper) {
                textClass = "text-white font-bold";
                if (isToday) bgClass = "bg-slate-700 ring-1 ring-blue-500";
            } else {
                if (isToday) bgClass = "bg-slate-800 ring-1 ring-slate-600";
            }

            days.push(
                <button
                    key={day}
                    onClick={() => !isFuture && handleDateClick(day)}
                    disabled={isFuture}
                    className={`h-9 w-9 rounded-full flex items-center justify-center text-sm transition-all ${bgClass} ${textClass}`}
                >
                    {day}
                </button>
            );
        }
        return days;
    };

    const monthNames = ["January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
    ];

    // Generate years (current year - 5 to + 5)
    const currentYear = new Date().getFullYear();
    const years = Array.from({ length: 11 }, (_, i) => currentYear - 5 + i);

    return (
        <div className="bg-slate-900 p-4 rounded-xl border border-slate-700 shadow-xl w-[320px] select-none">
            {/* Header */}
            <div className="flex justify-between items-center mb-4 px-1">
                <button onClick={handlePrevMonth} className="p-1.5 hover:bg-slate-800 rounded-lg text-slate-400 hover:text-white transition-colors">
                    <ChevronLeft size={18} />
                </button>

                <div className="flex items-center gap-2">
                    {/* Month Selector */}
                    <div className="relative">
                        <button
                            onClick={() => setShowMonthSelector(!showMonthSelector)}
                            className="flex items-center gap-1 text-white font-semibold hover:bg-slate-800 px-2 py-1 rounded transition-colors"
                        >
                            {monthNames[currentDate.getMonth()]}
                            <ChevronDown size={14} className={`transition-transform ${showMonthSelector ? 'rotate-180' : ''}`} />
                        </button>

                        {showMonthSelector && (
                            <div className="absolute top-full left-1/2 -translate-x-1/2 mt-1 w-32 bg-slate-800 border border-slate-700 rounded-lg shadow-xl z-50 max-h-60 overflow-y-auto py-1">
                                {monthNames.map((m, idx) => (
                                    <button
                                        key={m}
                                        onClick={() => handleMonthSelect(idx)}
                                        className={`w-full text-left px-3 py-1.5 text-sm hover:bg-slate-700 ${idx === currentDate.getMonth() ? 'text-blue-400 font-medium' : 'text-slate-300'}`}
                                    >
                                        {m}
                                    </button>
                                ))}
                            </div>
                        )}
                    </div>

                    {/* Year Selector */}
                    <div className="relative">
                        <button
                            onClick={() => setShowYearSelector(!showYearSelector)}
                            className="flex items-center gap-1 text-white font-semibold hover:bg-slate-800 px-2 py-1 rounded transition-colors"
                        >
                            {currentDate.getFullYear()}
                            <ChevronDown size={14} className={`transition-transform ${showYearSelector ? 'rotate-180' : ''}`} />
                        </button>

                        {showYearSelector && (
                            <div className="absolute top-full left-1/2 -translate-x-1/2 mt-1 w-24 bg-slate-800 border border-slate-700 rounded-lg shadow-xl z-50 max-h-60 overflow-y-auto py-1">
                                {years.map(y => (
                                    <button
                                        key={y}
                                        onClick={() => handleYearSelect(y)}
                                        className={`w-full text-left px-3 py-1.5 text-sm hover:bg-slate-700 ${y === currentDate.getFullYear() ? 'text-blue-400 font-medium' : 'text-slate-300'}`}
                                    >
                                        {y}
                                    </button>
                                ))}
                            </div>
                        )}
                    </div>
                </div>

                <button onClick={handleNextMonth} className="p-1.5 hover:bg-slate-800 rounded-lg text-slate-400 hover:text-white transition-colors">
                    <ChevronRight size={18} />
                </button>
            </div>

            {/* Weekdays */}
            <div className="grid grid-cols-7 gap-1 mb-2">
                {['Su', 'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa'].map(day => (
                    <div key={day} className="h-8 w-9 flex items-center justify-center text-xs font-medium text-slate-500">
                        {day}
                    </div>
                ))}
            </div>

            {/* Days Grid */}
            <div className="grid grid-cols-7 gap-1">
                {renderCalendarDays()}
            </div>

            {/* Footer / Legend */}
            <div className="mt-4 pt-3 border-t border-slate-800 flex justify-end items-center px-2">
                <button
                    onClick={() => {
                        const today = new Date();
                        setCurrentDate(today);
                        onDateSelect(today);
                    }}
                    className="text-xs text-blue-400 hover:text-blue-300 transition-colors"
                >
                    Today
                </button>
            </div>
        </div>
    );
};
