type ClusterBindingOption = {
  bound_cluster_id?: number | null;
  bound_cluster_name?: string | null;
};

export type ClusterInstanceBindingState = {
  badgeLabel: string | null;
  boundClusterText: string | null;
  disabled: boolean;
};

export function getClusterInstanceBindingState(
  option: ClusterBindingOption,
  currentClusterId: number
): ClusterInstanceBindingState {
  const boundClusterId = option.bound_cluster_id;
  const boundClusterName = option.bound_cluster_name?.trim() || null;
  if (typeof boundClusterId !== "number" || !Number.isFinite(boundClusterId)) {
    return {
      badgeLabel: null,
      boundClusterText: null,
      disabled: false
    };
  }

  const isCurrentCluster = boundClusterId === currentClusterId;
  return {
    badgeLabel: isCurrentCluster ? "当前群集" : "已绑定",
    boundClusterText: `已绑定：${boundClusterName ?? "未知群集"}`,
    disabled: !isCurrentCluster
  };
}
