import type { ReactNode } from "react";

import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { cn } from "@/utils/cn";

export type SelectOption = {
  label: ReactNode;
  value: string;
  disabled?: boolean;
};

const emptySelectValue = "__empty__";

function toSelectValue(value: string): string {
  return value === "" ? emptySelectValue : value;
}

function fromSelectValue(value: string): string {
  return value === emptySelectValue ? "" : value;
}

export function SelectControl({
  className,
  defaultValue,
  disabled,
  label,
  onValueChange,
  options,
  placeholder,
  value
}: {
  className?: string;
  defaultValue?: string;
  disabled?: boolean;
  label: string;
  onValueChange?: (value: string) => void;
  options: SelectOption[];
  placeholder?: string;
  value?: string;
}) {
  return (
    <Select
      defaultValue={defaultValue === undefined ? undefined : toSelectValue(defaultValue)}
      disabled={disabled}
      onValueChange={onValueChange ? (nextValue) => onValueChange(fromSelectValue(nextValue)) : undefined}
      value={value === undefined ? undefined : toSelectValue(value)}
    >
      <SelectTrigger aria-label={label} className={className}>
        <SelectValue placeholder={placeholder} />
      </SelectTrigger>
      <SelectContent>
        {options.map((option) => (
          <SelectItem disabled={option.disabled} key={`${option.value}:${String(option.label)}`} value={toSelectValue(option.value)}>
            {option.label}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}

export function Field({ children, label }: { children: ReactNode; label: string }) {
  return (
    <div className="grid gap-1.5">
      <Label>{label}</Label>
      {children}
    </div>
  );
}

export function SwitchField({
  checked,
  label,
  onCheckedChange
}: {
  checked: boolean;
  label: string;
  onCheckedChange: (checked: boolean) => void;
}) {
  return (
    <div className="flex items-center justify-between gap-3 rounded-md border bg-secondary/30 px-3 py-2 text-sm font-medium">
      <Label>{label}</Label>
      <span className="flex items-center gap-2">
        <Switch aria-label="启用" checked={checked} onCheckedChange={onCheckedChange} />
        <span className="text-muted-foreground">启用</span>
      </span>
    </div>
  );
}

export function CheckboxLine({
  checked,
  children,
  disabled,
  label,
  onCheckedChange
}: {
  checked?: boolean;
  children: ReactNode;
  disabled?: boolean;
  label: string;
  onCheckedChange?: (checked: boolean) => void;
}) {
  return (
    <Label className="flex items-center justify-between gap-3 rounded-md border bg-secondary/20 px-3 py-2 text-sm font-normal">
      <span>{children}</span>
      <Checkbox
        aria-label={label}
        checked={checked}
        disabled={disabled}
        onCheckedChange={(nextChecked) => onCheckedChange?.(nextChecked === true)}
      />
    </Label>
  );
}

export function TruncatedTooltip({ children, className, content }: { children: ReactNode; className?: string; content: string }) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <div className={cn("truncate", className)}>{children}</div>
      </TooltipTrigger>
      <TooltipContent>{content}</TooltipContent>
    </Tooltip>
  );
}
