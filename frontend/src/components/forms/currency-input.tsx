"use client";

import { forwardRef, useState } from "react";
import { cn } from "@/lib/utils";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

// Common currencies
const currencies = [
  { code: "USD", symbol: "$", name: "US Dollar" },
  { code: "EUR", symbol: "E", name: "Euro" },
  { code: "GBP", symbol: "L", name: "British Pound" },
  { code: "BRL", symbol: "R$", name: "Brazilian Real" },
  { code: "ARS", symbol: "$", name: "Argentine Peso" },
  { code: "MXN", symbol: "$", name: "Mexican Peso" },
  { code: "CLP", symbol: "$", name: "Chilean Peso" },
  { code: "COP", symbol: "$", name: "Colombian Peso" },
  { code: "PEN", symbol: "S/", name: "Peruvian Sol" },
  { code: "PYG", symbol: "Gs", name: "Paraguayan Guarani" },
] as const;

export type CurrencyCode = (typeof currencies)[number]["code"];

interface CurrencyInputProps {
  value?: number | string;
  currency?: CurrencyCode;
  onChange?: (value: number | undefined, currency: CurrencyCode) => void;
  onValueChange?: (value: number | undefined) => void;
  onCurrencyChange?: (currency: CurrencyCode) => void;
  placeholder?: string;
  disabled?: boolean;
  readOnly?: boolean;
  showCurrencySelector?: boolean;
  className?: string;
  id?: string;
  name?: string;
}

export const CurrencyInput = forwardRef<HTMLInputElement, CurrencyInputProps>(
  (
    {
      value,
      currency = "USD",
      onChange,
      onValueChange,
      onCurrencyChange,
      placeholder = "0.00",
      disabled = false,
      readOnly = false,
      showCurrencySelector = false,
      className,
      id,
      name,
    },
    ref
  ) => {
    const [localCurrency, setLocalCurrency] = useState<CurrencyCode>(currency);
    const currencyInfo = currencies.find((c) => c.code === localCurrency);

    function handleValueChange(e: React.ChangeEvent<HTMLInputElement>) {
      const inputValue = e.target.value;

      // Allow empty input
      if (!inputValue) {
        onValueChange?.(undefined);
        onChange?.(undefined, localCurrency);
        return;
      }

      // Parse the value, removing any non-numeric characters except decimal point
      const cleanValue = inputValue.replace(/[^0-9.]/g, "");
      const numericValue = parseFloat(cleanValue);

      if (!isNaN(numericValue)) {
        onValueChange?.(numericValue);
        onChange?.(numericValue, localCurrency);
      }
    }

    function handleCurrencyChange(newCurrency: string) {
      const currencyCode = newCurrency as CurrencyCode;
      setLocalCurrency(currencyCode);
      onCurrencyChange?.(currencyCode);
      onChange?.(typeof value === "number" ? value : parseFloat(String(value)) || undefined, currencyCode);
    }

    // Format display value
    const displayValue =
      value !== undefined && value !== ""
        ? typeof value === "number"
          ? value.toString()
          : value
        : "";

    return (
      <div className={cn("flex items-center gap-2", className)}>
        <div className="relative flex-1">
          <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground text-sm">
            {currencyInfo?.symbol || "$"}
          </span>
          <Input
            ref={ref}
            id={id}
            name={name}
            type="text"
            inputMode="decimal"
            value={displayValue}
            onChange={handleValueChange}
            placeholder={placeholder}
            disabled={disabled}
            readOnly={readOnly}
            className="pl-8"
          />
        </div>

        {showCurrencySelector && (
          <Select
            value={localCurrency}
            onValueChange={handleCurrencyChange}
            disabled={disabled}
          >
            <SelectTrigger className="w-[100px]">
              <SelectValue placeholder="Currency" />
            </SelectTrigger>
            <SelectContent>
              {currencies.map((c) => (
                <SelectItem key={c.code} value={c.code}>
                  {c.code}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
      </div>
    );
  }
);

CurrencyInput.displayName = "CurrencyInput";

// Helper to format currency for display
export function formatCurrencyValue(
  value: number,
  currency: CurrencyCode = "USD",
  locale = "en-US"
): string {
  return new Intl.NumberFormat(locale, {
    style: "currency",
    currency,
  }).format(value);
}
