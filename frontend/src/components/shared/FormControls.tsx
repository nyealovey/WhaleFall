import { useMemo, useState, type ReactNode } from "react";

import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
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

export type MultiSelectOption = SelectOption;

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

function reactNodeText(value: ReactNode): string {
  if (typeof value === "string" || typeof value === "number") {
    return String(value);
  }
  return "";
}

export function MultiSelectDialogControl({
  className,
  disabled,
  emptyLabel = "全部",
  label,
  onValueChange,
  options,
  placeholder = "请选择",
  value
}: {
  className?: string;
  disabled?: boolean;
  emptyLabel?: string;
  label: string;
  onValueChange: (value: string[]) => void;
  options: MultiSelectOption[];
  placeholder?: string;
  value: string[];
}) {
  const [open, setOpen] = useState(false);
  const selectedSet = useMemo(() => new Set(value), [value]);
  const selectedLabels = options
    .filter((option) => selectedSet.has(option.value))
    .map((option) => reactNodeText(option.label) || option.value);
  const buttonText = selectedLabels.length > 0 ? selectedLabels.join("、") : emptyLabel;

  function toggleOption(optionValue: string, checked: boolean) {
    if (checked) {
      onValueChange(value.includes(optionValue) ? value : [...value, optionValue]);
      return;
    }
    onValueChange(value.filter((item) => item !== optionValue));
  }

  return (
    <>
      <Button
        aria-label={`${label} ${buttonText}`}
        className={cn("w-full justify-between", className)}
        disabled={disabled}
        onClick={() => setOpen(true)}
        type="button"
        variant="outline"
      >
        <span className="truncate">{buttonText || placeholder}</span>
        <span className="text-xs text-muted-foreground">{selectedLabels.length > 0 ? `${selectedLabels.length} 项` : ""}</span>
      </Button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>选择{label}</DialogTitle>
            <DialogDescription>可同时选择多项，关闭后仍需点击应用筛选才会刷新数据。</DialogDescription>
          </DialogHeader>
          <div className="grid max-h-[24rem] gap-2 overflow-y-auto pr-1">
            {options.length > 0 ? (
              options.map((option) => {
                const optionLabel = reactNodeText(option.label) || option.value;
                return (
                  <CheckboxLine
                    checked={selectedSet.has(option.value)}
                    disabled={option.disabled}
                    key={option.value}
                    label={`选择 ${optionLabel}`}
                    onCheckedChange={(checked) => toggleOption(option.value, checked)}
                  >
                    {option.label}
                  </CheckboxLine>
                );
              })
            ) : (
              <div className="rounded-md border border-dashed p-6 text-center text-sm text-muted-foreground">暂无可选项</div>
            )}
          </div>
          <DialogFooter>
            <Button onClick={() => onValueChange([])} type="button" variant="outline">
              清空
            </Button>
            <Button onClick={() => setOpen(false)} type="button">
              完成
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
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
  onCheckedChange,
  switchLabel = "启用"
}: {
  checked: boolean;
  label: string;
  onCheckedChange: (checked: boolean) => void;
  switchLabel?: string;
}) {
  return (
    <div className="flex items-center justify-between gap-3 rounded-md border bg-secondary/30 px-3 py-2 text-sm font-medium">
      <Label>{label}</Label>
      <span className="flex items-center gap-2">
        <Switch aria-label={switchLabel} checked={checked} onCheckedChange={onCheckedChange} />
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
