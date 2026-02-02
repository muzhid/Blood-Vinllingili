import React, { useState, useEffect } from 'react';
import { format, addMonths, subMonths, startOfMonth, endOfMonth, startOfWeek, endOfWeek, isSameMonth, isSameDay, addDays, eachDayOfInterval } from 'date-fns';
import { ChevronLeft, ChevronRight, Calendar as CalendarIcon } from 'lucide-react';
import { Button } from "@/components/ui/button";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { cn } from "@/lib/utils";

export function CustomDatePicker({ selected, onSelect, className }) {
    const [currentMonth, setCurrentMonth] = useState(new Date());

    // Synchronize internal month view if selected date changes externally
    useEffect(() => {
        if (selected) {
            setCurrentMonth(selected);
        }
    }, [selected]);

    const nextMonth = () => setCurrentMonth(addMonths(currentMonth, 1));
    const prevMonth = () => setCurrentMonth(subMonths(currentMonth, 1));

    const renderHeader = () => {
        return (
            <div className="flex items-center justify-between px-2 py-4">
                <Button variant="ghost" size="sm" onClick={prevMonth} className="h-7 w-7 p-0 hover:bg-slate-100 rounded-full">
                    <ChevronLeft className="h-4 w-4" />
                </Button>
                <div className="font-semibold text-sm">
                    {format(currentMonth, "MMMM yyyy")}
                </div>
                <Button variant="ghost" size="sm" onClick={nextMonth} className="h-7 w-7 p-0 hover:bg-slate-100 rounded-full">
                    <ChevronRight className="h-4 w-4" />
                </Button>
            </div>
        );
    };

    const renderDays = () => {
        const days = ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"];
        return (
            <div className="grid grid-cols-7 mb-2">
                {days.map((day) => (
                    <div key={day} className="text-xs font-medium text-center text-muted-foreground w-8 mx-auto">
                        {day}
                    </div>
                ))}
            </div>
        );
    };

    const renderCells = () => {
        const monthStart = startOfMonth(currentMonth);
        const monthEnd = endOfMonth(monthStart);
        const startDate = startOfWeek(monthStart);
        const endDate = endOfWeek(monthEnd);

        const dateFormat = "d";
        const rows = [];
        let days = [];
        let day = startDate;
        let formattedDate = "";

        while (day <= endDate) {
            for (let i = 0; i < 7; i++) {
                formattedDate = format(day, dateFormat);
                const cloneDay = day;
                const isSelected = selected ? isSameDay(day, selected) : false;
                const isCurrentMonth = isSameMonth(day, monthStart);

                days.push(
                    <div
                        key={day}
                        className="flex justify-center items-center w-full h-9"
                    >
                        <button
                            onClick={() => {
                                onSelect(cloneDay);
                            }}
                            className={cn(
                                "w-8 h-8 flex items-center justify-center rounded-full text-sm transition-all duration-200",
                                !isCurrentMonth && "text-gray-300 pointer-events-none",
                                isCurrentMonth && !isSelected && "hover:bg-red-50 text-gray-700",
                                isSelected && "bg-red-600 text-white shadow-md font-medium hover:bg-red-700 scale-105"
                            )}
                            disabled={!isCurrentMonth}
                        >
                            {formattedDate}
                        </button>
                    </div>
                );
                day = addDays(day, 1);
            }
            rows.push(
                <div className="grid grid-cols-7" key={day}>
                    {days}
                </div>
            );
            days = [];
        }
        return <div className="space-y-1">{rows}</div>;
    };

    return (
        <Popover>
            <PopoverTrigger asChild>
                <Button
                    variant={"outline"}
                    className={cn(
                        "w-full justify-start text-left font-normal border-slate-200 hover:bg-slate-50 hover:text-slate-900 transition-colors h-11",
                        !selected && "text-muted-foreground",
                        className
                    )}
                >
                    <CalendarIcon className="mr-2 h-4 w-4 text-slate-500" />
                    {selected ? (
                        <span className="text-slate-900 font-medium">{format(selected, "PPP")}</span>
                    ) : (
                        <span>Pick a donation date</span>
                    )}
                </Button>
            </PopoverTrigger>
            <PopoverContent className="w-auto p-0 border-none shadow-xl rounded-xl" align="start">
                <div className="bg-white p-3 rounded-xl border border-slate-100 w-[280px]">
                    {renderHeader()}
                    {renderDays()}
                    {renderCells()}
                </div>
            </PopoverContent>
        </Popover>
    );
}
