import { fireEvent, render, screen } from "@testing-library/react";
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
