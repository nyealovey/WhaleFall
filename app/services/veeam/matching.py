"""Veeam 机器名匹配辅助."""

from __future__ import annotations


def normalize_machine_name(value: str | None) -> str:
    """统一机器名归一化."""
    return str(value or "").strip().lower()


def normalize_domain(value: str | None) -> str:
    """统一域名归一化."""
    return str(value or "").strip().strip(".").lower()


def build_instance_match_candidates(instance_name: str | None, domains: list[str] | None) -> list[str]:
    """基于实例名称与全局域名列表构建候选机器名集合."""
    base_name = normalize_machine_name(instance_name)
    if not base_name:
        return []

    candidates = [base_name]
    seen = {base_name}
    for domain in domains or []:
        normalized_domain = normalize_domain(domain)
        if not normalized_domain:
            continue
        candidate = base_name if base_name.endswith(f".{normalized_domain}") else f"{base_name}.{normalized_domain}"
        if candidate in seen:
            continue
        seen.add(candidate)
        candidates.append(candidate)
    return candidates
