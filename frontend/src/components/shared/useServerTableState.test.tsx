import { act, renderHook } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { useServerTableState } from "./useServerTableState";

describe("useServerTableState", () => {
  it("resets the page when page size or a filter changes", () => {
    const { result } = renderHook(() => useServerTableState({ initialFilters: { status: "" } }));

    act(() => result.current.setPage(3));
    act(() => result.current.setPageSize(50));
    expect(result.current.page).toBe(1);
    expect(result.current.pageSize).toBe(50);

    act(() => result.current.setPage(2));
    act(() => result.current.setFilter("status", "active"));
    expect(result.current.page).toBe(1);
    expect(result.current.filters.status).toBe("active");
  });

  it("debounces search and resets the page immediately", () => {
    vi.useFakeTimers();
    const { result } = renderHook(() => useServerTableState({ initialFilters: {} }));

    act(() => result.current.setPage(4));
    act(() => result.current.setSearchInput("mysql"));
    expect(result.current.page).toBe(1);
    expect(result.current.search).toBe("");

    act(() => vi.advanceTimersByTime(300));
    expect(result.current.search).toBe("mysql");
    vi.useRealTimers();
  });
});
