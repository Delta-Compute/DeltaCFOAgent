"use client";

import { forwardRef, useState } from "react";
import { CalendarIcon, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

interface DatePickerProps {
  value?: Date | string;
  onChange?: (date: Date | undefined) => void;
  placeholder?: string;
  disabled?: boolean;
  clearable?: boolean;
  minDate?: Date;
  maxDate?: Date;
  className?: string;
  id?: string;
  name?: string;
}

export const DatePicker = forwardRef<HTMLInputElement, DatePickerProps>(
  (
    {
      value,
      onChange,
      placeholder = "Select date",
      disabled = false,
      clearable = true,
      minDate,
      maxDate,
      className,
      id,
      name,
    },
    ref
  ) => {
    // Convert value to string format for input
    const dateValue = value
      ? typeof value === "string"
        ? value
        : value.toISOString().split("T")[0]
      : "";

    function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
      const inputValue = e.target.value;
      if (!inputValue) {
        onChange?.(undefined);
      } else {
        const date = new Date(inputValue + "T00:00:00");
        if (!isNaN(date.getTime())) {
          onChange?.(date);
        }
      }
    }

    function handleClear() {
      onChange?.(undefined);
    }

    return (
      <div className={cn("relative flex items-center", className)}>
        <CalendarIcon className="absolute left-3 h-4 w-4 text-muted-foreground pointer-events-none" />
        <Input
          ref={ref}
          id={id}
          name={name}
          type="date"
          value={dateValue}
          onChange={handleChange}
          disabled={disabled}
          min={minDate?.toISOString().split("T")[0]}
          max={maxDate?.toISOString().split("T")[0]}
          className="pl-10 pr-10"
          placeholder={placeholder}
        />
        {clearable && dateValue && !disabled && (
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="absolute right-1 h-7 w-7"
            onClick={handleClear}
          >
            <X className="h-3 w-3" />
          </Button>
        )}
      </div>
    );
  }
);

DatePicker.displayName = "DatePicker";

// Date range picker
interface DateRangePickerProps {
  startDate?: Date | string;
  endDate?: Date | string;
  onStartDateChange?: (date: Date | undefined) => void;
  onEndDateChange?: (date: Date | undefined) => void;
  onChange?: (range: { start?: Date; end?: Date }) => void;
  disabled?: boolean;
  className?: string;
}

export function DateRangePicker({
  startDate,
  endDate,
  onStartDateChange,
  onEndDateChange,
  onChange,
  disabled = false,
  className,
}: DateRangePickerProps) {
  const [localStart, setLocalStart] = useState<Date | undefined>(
    startDate ? new Date(startDate) : undefined
  );
  const [localEnd, setLocalEnd] = useState<Date | undefined>(
    endDate ? new Date(endDate) : undefined
  );

  function handleStartChange(date: Date | undefined) {
    setLocalStart(date);
    onStartDateChange?.(date);
    onChange?.({ start: date, end: localEnd });
  }

  function handleEndChange(date: Date | undefined) {
    setLocalEnd(date);
    onEndDateChange?.(date);
    onChange?.({ start: localStart, end: date });
  }

  return (
    <div className={cn("flex items-center gap-2", className)}>
      <DatePicker
        value={localStart}
        onChange={handleStartChange}
        placeholder="Start date"
        disabled={disabled}
        maxDate={localEnd}
      />
      <span className="text-muted-foreground">to</span>
      <DatePicker
        value={localEnd}
        onChange={handleEndChange}
        placeholder="End date"
        disabled={disabled}
        minDate={localStart}
      />
    </div>
  );
}
