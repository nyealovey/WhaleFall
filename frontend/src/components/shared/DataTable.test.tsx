import { fireEvent, render, screen } from "@testing-library/react";
import { vi } from "vitest";
import type { ColumnDef } from "@tanstack/react-table";
import { describe, expect, it } from "vitest";

import { DataTable } from "./DataTable";

type Payment = {
  id: string;
  status: string;
  amount: number;
};

const columns: ColumnDef<Payment>[] = [
  {
    accessorKey: "status",
    header: "状态"
  },
  {
    accessorKey: "amount",
    header: () => <div className="text-right">金额</div>,
    cell: ({ row }) => <div className="text-right">{row.original.amount}</div>
  }
];

async function chooseOption(label: string, option: string) {
  fireEvent.pointerDown(screen.getByRole("combobox", { name: label }), { button: 0, ctrlKey: false, pointerType: "mouse" });
  fireEvent.click(await screen.findByRole("option", { name: option }));
}

describe("DataTable", () => {
  it("renders column headers, rows, and pagination controls", () => {
    render(<DataTable columns={columns} data={[{ id: "p-1", status: "success", amount: 316 }]} />);

    expect(screen.getByRole("columnheader", { name: "状态" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "金额" })).toBeInTheDocument();
    expect(screen.getByText("success")).toBeInTheDocument();
    expect(screen.getByText("316")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "上一页" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "下一页" })).toBeDisabled();
  });

  it("renders a stable empty state", () => {
    render(<DataTable columns={columns} data={[]} emptyText="暂无旧版字段数据" />);

    expect(screen.getByText("暂无旧版字段数据")).toBeInTheDocument();
  });

  it("shows twenty rows per page by default", () => {
    const data = Array.from({ length: 25 }, (_, index) => ({ id: `p-${index + 1}`, status: `status-${index + 1}`, amount: index + 1 }));

    render(<DataTable columns={columns} data={data} />);

    expect(screen.getByText("status-20")).toBeInTheDocument();
    expect(screen.queryByText("status-21")).not.toBeInTheDocument();
    expect(screen.getByText("显示 1-20，共 25 条")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "下一页" }));

    expect(screen.getByText("status-21")).toBeInTheDocument();
    expect(screen.getByText("显示 21-25，共 25 条")).toBeInTheDocument();
  });

  it("can render a static table without pagination", () => {
    const data = Array.from({ length: 25 }, (_, index) => ({ id: `p-${index + 1}`, status: `status-${index + 1}`, amount: index + 1 }));

    render(<DataTable columns={columns} data={data} pagination={false} />);

    expect(screen.getByText("status-25")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "下一页" })).not.toBeInTheDocument();
  });

  it("delegates pagination and filters in server mode", async () => {
    const onPageChange = vi.fn();
    const onPageSizeChange = vi.fn();
    const onStatusChange = vi.fn();

    render(
      <DataTable
        columns={columns}
        data={[{ id: "p-21", status: "failed", amount: 128 }]}
        filters={[{ columnId: "status", label: "状态", options: [{ label: "失败", value: "failed" }], value: "" , onValueChange: onStatusChange }]}
        pagination={{ page: 2, pageSize: 20, pages: 3, total: 41, onPageChange, onPageSizeChange }}
      />
    );

    expect(screen.getByText("显示 21-40，共 41 条")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "下一页" }));
    expect(onPageChange).toHaveBeenCalledWith(3);

    await chooseOption("状态", "失败");
    expect(onStatusChange).toHaveBeenCalledWith("failed");
  });

  it("keeps large server pagination controls on one line", () => {
    const { container } = render(
      <DataTable
        columns={columns}
        data={[{ id: "p-81", status: "success", amount: 81 }]}
        pagination={{ page: 5, pageSize: 20, pages: 383, total: 7641, onPageChange: vi.fn(), onPageSizeChange: vi.fn() }}
      />
    );

    const summary = screen.getByText("显示 81-100，共 7641 条");
    expect(summary.parentElement).not.toHaveClass("flex-wrap");
    expect(container.querySelector('nav[aria-label="分页"]')).toHaveClass("shrink-0");
    expect(container.querySelector('nav[aria-label="分页"] ul')).toHaveClass("flex-nowrap");
  });

  it("filters rows through the table toolbar", async () => {
    const { container } = render(
      <DataTable
        columns={columns}
        data={[
          { id: "p-1", status: "success", amount: 316 },
          { id: "p-2", status: "failed", amount: 128 }
        ]}
        filters={[
          {
            columnId: "status",
            label: "状态",
            options: [
              { label: "成功", value: "success" },
              { label: "失败", value: "failed" }
            ]
          }
        ]}
        searchPlaceholder="搜索支付"
      />
    );

    expect(container.querySelector('select:not([aria-hidden="true"])')).toBeNull();
    expect(screen.getByRole("combobox", { name: "状态" })).toBeInTheDocument();

    fireEvent.change(screen.getByRole("searchbox", { name: "搜索" }), { target: { value: "failed" } });

    expect(screen.queryByText("success")).not.toBeInTheDocument();
    expect(screen.getByText("failed")).toBeInTheDocument();

    fireEvent.change(screen.getByRole("searchbox", { name: "搜索" }), { target: { value: "" } });
    await chooseOption("状态", "成功");

    expect(screen.getByText("success")).toBeInTheDocument();
    expect(screen.queryByText("failed")).not.toBeInTheDocument();
  });
});
