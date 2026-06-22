import { useCallback, useEffect, useState } from "react";

type ServerTableStateOptions<TFilters extends Record<string, string>> = {
  debounceMs?: number;
  initialFilters: TFilters;
  initialPageSize?: number;
};

export function useServerTableState<TFilters extends Record<string, string>>({
  debounceMs = 300,
  initialFilters,
  initialPageSize = 20
}: ServerTableStateOptions<TFilters>) {
  const [page, setPage] = useState(1);
  const [pageSize, setPageSizeValue] = useState(initialPageSize);
  const [searchInput, setSearchInputValue] = useState("");
  const [search, setSearch] = useState("");
  const [filters, setFilters] = useState<TFilters>(initialFilters);

  useEffect(() => {
    const timeout = window.setTimeout(() => setSearch(searchInput.trim()), debounceMs);
    return () => window.clearTimeout(timeout);
  }, [debounceMs, searchInput]);

  const setPageSize = useCallback((value: number) => {
    setPageSizeValue(value);
    setPage(1);
  }, []);

  const setSearchInput = useCallback((value: string) => {
    setSearchInputValue(value);
    setPage(1);
  }, []);

  const setFilter = useCallback(<TKey extends keyof TFilters>(key: TKey, value: TFilters[TKey]) => {
    setFilters((current) => ({ ...current, [key]: value }));
    setPage(1);
  }, []);

  const reset = useCallback(() => {
    setPage(1);
    setSearchInputValue("");
    setSearch("");
    setFilters(initialFilters);
  }, [initialFilters]);

  return { filters, page, pageSize, reset, search, searchInput, setFilter, setPage, setPageSize, setSearchInput };
}
