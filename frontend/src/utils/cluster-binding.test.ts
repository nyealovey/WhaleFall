import { describe, expect, it } from "vitest";

import { getClusterInstanceBindingState } from "./cluster-binding";

describe("cluster instance binding state", () => {
  it("shows the bound cluster name and disables instances bound to another cluster", () => {
    const state = getClusterInstanceBindingState(
      { bound_cluster_id: 8, bound_cluster_name: "gf-cqsmysql" },
      9
    );

    expect(state.boundClusterText).toBe("已绑定：gf-cqsmysql");
    expect(state.badgeLabel).toBe("已绑定");
    expect(state.disabled).toBe(true);
  });

  it("keeps instances bound to the current cluster selectable", () => {
    const state = getClusterInstanceBindingState(
      { bound_cluster_id: 9, bound_cluster_name: "jt-srmmysql-group-02" },
      9
    );

    expect(state.boundClusterText).toBe("已绑定：jt-srmmysql-group-02");
    expect(state.badgeLabel).toBe("当前群集");
    expect(state.disabled).toBe(false);
  });
});
