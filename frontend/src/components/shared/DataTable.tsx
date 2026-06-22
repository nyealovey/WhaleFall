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
import { Pagination, PaginationContent, PaginationEllipsis, PaginationItem } from "@/components/ui/pagination";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

export type DataTableFilter = {
  columnId: string;
  label: string;
  options: Array<{
    label: string;
    value: string;
  }>;
  onValueChange?: (value: string) => void;
  value?: string;
};

export type DataTableServerPagination = {
  onPageChange: (page: number) => void;
  onPageSizeChange: (pageSize: number) => void;
  page: number;
  pageSize: number;
  pages: number;
  total: number;
};

type DataTableProps<TData, TValue> = {
  columns: ColumnDef<TData, TValue>[];
  data: TData[];
  emptyText?: string;
  filters?: DataTableFilter[];
  onSearchChange?: (value: string) => void;
  pagination?: false | DataTableServerPagination;
  searchPlaceholder?: string;
  searchValue?: string;
  toolbarExtras?: ReactNode;
};

const allFilterValue = "__all__";

export function DataTable<TData, TValue>({
  columns,
  data,
  emptyText = "暂无数据",
  filters = [],
  onSearchChange,
  pagination,
  searchPlaceholder,
  searchValue,
  toolbarExtras
}: DataTableProps<TData, TValue>) {
  const [globalFilter, setGlobalFilter] = useState("");
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([]);
  const serverPagination = pagination && typeof pagination === "object" ? pagination : null;
  const paginationEnabled = pagination !== false;
  const clientPagination = paginationEnabled && serverPagination === null;
  const hasToolbar = Boolean(searchPlaceholder) || filters.length > 0 || Boolean(toolbarExtras);

  // TanStack Table returns function-heavy instances that React Compiler cannot memoize safely.
  // eslint-disable-next-line react-hooks/incompatible-library
  const table = useReactTable({
    data,
    columns,
    state: {
      globalFilter: serverPagination ? (searchValue ?? "") : globalFilter,
      columnFilters,
      ...(serverPagination
        ? { pagination: { pageIndex: Math.max(serverPagination.page - 1, 0), pageSize: serverPagination.pageSize } }
        : {})
    },
    onGlobalFilterChange: setGlobalFilter,
    onColumnFiltersChange: setColumnFilters,
    getCoreRowModel: getCoreRowModel(),
    getFilteredRowModel: serverPagination ? undefined : getFilteredRowModel(),
    globalFilterFn: (row, _columnId, filterValue) => {
      const keyword = String(filterValue ?? "").trim().toLowerCase();
      if (!keyword) {
        return true;
      }
      return JSON.stringify(row.original).toLowerCase().includes(keyword);
    },
    getPaginationRowModel: clientPagination ? getPaginationRowModel() : undefined,
    initialState: clientPagination ? { pagination: { pageIndex: 0, pageSize: 20 } } : undefined,
    manualFiltering: Boolean(serverPagination),
    manualPagination: Boolean(serverPagination),
    pageCount: serverPagination?.pages
  });

  const currentPage = serverPagination?.page ?? table.getState().pagination.pageIndex + 1;
  const pageSize = serverPagination?.pageSize ?? table.getState().pagination.pageSize;
  const total = serverPagination?.total ?? table.getFilteredRowModel().rows.length;
  const pages = serverPagination?.pages ?? Math.max(table.getPageCount(), 1);
  const firstRow = total === 0 ? 0 : (currentPage - 1) * pageSize + 1;
  const lastRow = Math.min(currentPage * pageSize, total);
  const pageNumbers = Array.from({ length: pages }, (_, index) => index + 1).filter(
    (page) => page === 1 || page === pages || Math.abs(page - currentPage) <= 1
  );

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
                  if (serverPagination) {
                    onSearchChange?.(event.target.value);
                  } else {
                    setGlobalFilter(event.target.value);
                  }
                }}
                placeholder={searchPlaceholder}
                type="search"
                value={serverPagination ? (searchValue ?? "") : globalFilter}
              />
            </label>
          ) : null}
          {filters.length > 0 ? (
            <div className="grid grid-cols-3 gap-3 max-lg:grid-cols-2 max-sm:grid-cols-1">
              {filters.map((filter) => (
                <label className="grid gap-1.5 text-sm font-medium text-foreground" key={filter.columnId}>
                  <span>{filter.label}</span>
                  <Select
                    onValueChange={(value) => {
                      const resolved = value === allFilterValue ? "" : value;
                      if (serverPagination) {
                        filter.onValueChange?.(resolved);
                      } else {
                        table.getColumn(filter.columnId)?.setFilterValue(resolved || undefined);
                      }
                    }}
                    value={(serverPagination ? filter.value : (table.getColumn(filter.columnId)?.getFilterValue() as string | undefined)) || allFilterValue}
                  >
                    <SelectTrigger aria-label={filter.label}>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value={allFilterValue}>全部</SelectItem>
                      {filter.options.map((option) => (
                        <SelectItem key={option.value} value={option.value}>
                          {option.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
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
      {paginationEnabled ? (
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-muted-foreground">显示 {firstRow}-{lastRow}，共 {total} 条</p>
        <div className="flex flex-wrap items-center gap-3">
          <Select
            onValueChange={(value) => {
              const resolved = Number(value);
              if (serverPagination) {
                serverPagination.onPageSizeChange(resolved);
              } else {
                table.setPageSize(resolved);
              }
            }}
            value={String(pageSize)}
          >
            <SelectTrigger aria-label="每页条数" className="w-24">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {[20, 50, 100].map((size) => <SelectItem key={size} value={String(size)}>{size} 条</SelectItem>)}
            </SelectContent>
          </Select>
          <Pagination className="w-auto">
            <PaginationContent>
              <PaginationItem>
          <Button
            disabled={currentPage <= 1}
            onClick={() => {
              if (serverPagination) serverPagination.onPageChange(currentPage - 1);
              else table.previousPage();
            }}
            size="sm"
            variant="outline"
          >
            上一页
          </Button>
              </PaginationItem>
              {pageNumbers.map((page, index) => (
                <PaginationItem key={page}>
                  {index > 0 && page - pageNumbers[index - 1] > 1 ? <PaginationEllipsis /> : null}
                  <Button
                    aria-current={page === currentPage ? "page" : undefined}
                    aria-label={`第 ${page} 页`}
                    onClick={() => serverPagination ? serverPagination.onPageChange(page) : table.setPageIndex(page - 1)}
                    size="icon"
                    variant={page === currentPage ? "default" : "outline"}
                  >
                    {page}
                  </Button>
                </PaginationItem>
              ))}
              <PaginationItem>
          <Button
            disabled={currentPage >= pages}
            onClick={() => {
              if (serverPagination) serverPagination.onPageChange(currentPage + 1);
              else table.nextPage();
            }}
            size="sm"
            variant="outline"
          >
            下一页
          </Button>
              </PaginationItem>
            </PaginationContent>
          </Pagination>
        </div>
      </div>
      ) : null}
    </div>
  );
}
