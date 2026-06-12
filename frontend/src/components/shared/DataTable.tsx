import {
  type ColumnFiltersState,
  type ColumnDef,
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  useReactTable
} from "@tanstack/react-table";
import { useState, type ReactNode } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

export type DataTableFilter = {
  columnId: string;
  label: string;
  options: Array<{
    label: string;
    value: string;
  }>;
};

type DataTableProps<TData, TValue> = {
  columns: ColumnDef<TData, TValue>[];
  data: TData[];
  emptyText?: string;
  filters?: DataTableFilter[];
  searchPlaceholder?: string;
  toolbarExtras?: ReactNode;
};

const selectClassName =
  "border-input bg-background ring-offset-background focus-visible:ring-ring h-9 rounded-md border px-3 py-1 text-sm shadow-xs outline-none transition-colors focus-visible:ring-2 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50";

export function DataTable<TData, TValue>({
  columns,
  data,
  emptyText = "暂无数据",
  filters = [],
  searchPlaceholder,
  toolbarExtras
}: DataTableProps<TData, TValue>) {
  const [globalFilter, setGlobalFilter] = useState("");
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([]);
  const hasToolbar = Boolean(searchPlaceholder) || filters.length > 0 || Boolean(toolbarExtras);

  // TanStack Table returns function-heavy instances that React Compiler cannot memoize safely.
  // eslint-disable-next-line react-hooks/incompatible-library
  const table = useReactTable({
    data,
    columns,
    state: {
      globalFilter,
      columnFilters
    },
    onGlobalFilterChange: setGlobalFilter,
    onColumnFiltersChange: setColumnFilters,
    getCoreRowModel: getCoreRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    globalFilterFn: (row, _columnId, filterValue) => {
      const keyword = String(filterValue ?? "").trim().toLowerCase();
      if (!keyword) {
        return true;
      }
      return JSON.stringify(row.original).toLowerCase().includes(keyword);
    },
    getPaginationRowModel: getPaginationRowModel()
  });

  return (
    <div className="grid gap-3">
      {hasToolbar ? (
        <div className="flex items-end justify-between gap-3 max-xl:grid" role="search">
          {searchPlaceholder ? (
            <label className="grid min-w-60 flex-1 gap-1.5 text-sm font-medium text-foreground">
              <span>搜索</span>
              <Input
                aria-label="搜索"
                onChange={(event) => {
                  setGlobalFilter(event.target.value);
                }}
                placeholder={searchPlaceholder}
                type="search"
                value={globalFilter}
              />
            </label>
          ) : null}
          {filters.length > 0 ? (
            <div className="grid grid-cols-3 gap-3 max-lg:grid-cols-2 max-sm:grid-cols-1">
              {filters.map((filter) => (
                <label className="grid gap-1.5 text-sm font-medium text-foreground" key={filter.columnId}>
                  <span>{filter.label}</span>
                  <select
                    aria-label={filter.label}
                    className={selectClassName}
                    onChange={(event) => {
                      table.getColumn(filter.columnId)?.setFilterValue(event.target.value || undefined);
                    }}
                    value={(table.getColumn(filter.columnId)?.getFilterValue() as string | undefined) ?? ""}
                  >
                    <option value="">全部</option>
                    {filter.options.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </label>
              ))}
              {toolbarExtras}
            </div>
          ) : toolbarExtras ? (
            <div className="grid grid-cols-3 gap-3 max-lg:grid-cols-2 max-sm:grid-cols-1">{toolbarExtras}</div>
          ) : null}
        </div>
      ) : null}
      <div className="overflow-hidden rounded-md border">
        <Table>
          <TableHeader>
            {table.getHeaderGroups().map((headerGroup) => (
              <TableRow key={headerGroup.id}>
                {headerGroup.headers.map((header) => (
                  <TableHead key={header.id}>
                    {header.isPlaceholder ? null : flexRender(header.column.columnDef.header, header.getContext())}
                  </TableHead>
                ))}
              </TableRow>
            ))}
          </TableHeader>
          <TableBody>
            {table.getRowModel().rows.length > 0 ? (
              table.getRowModel().rows.map((row) => (
                <TableRow data-state={row.getIsSelected() ? "selected" : undefined} key={row.id}>
                  {row.getVisibleCells().map((cell) => (
                    <TableCell key={cell.id}>{flexRender(cell.column.columnDef.cell, cell.getContext())}</TableCell>
                  ))}
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell className="h-24 text-center text-sm text-muted-foreground" colSpan={columns.length}>
                  {emptyText}
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>
      <div className="flex items-center justify-between gap-3">
        <p className="text-sm text-muted-foreground">{table.getFilteredRowModel().rows.length} 条记录</p>
        <div className="flex items-center gap-2">
          <Button
            disabled={!table.getCanPreviousPage()}
            onClick={() => {
              table.previousPage();
            }}
            size="sm"
            variant="outline"
          >
            上一页
          </Button>
          <Button
            disabled={!table.getCanNextPage()}
            onClick={() => {
              table.nextPage();
            }}
            size="sm"
            variant="outline"
          >
            下一页
          </Button>
        </div>
      </div>
    </div>
  );
}
