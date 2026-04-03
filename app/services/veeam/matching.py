"""Veeam 机器名匹配辅助."""

from __future__ import annotations

import ipaddress
import re


def normalize_machine_name(value: str | None) -> str:
    """统一机器名归一化."""
    return str(value or "").strip().lower()


def normalize_domain(value: str | None) -> str:
    """统一域名归一化."""
    return str(value or "").strip().strip(".").lower()


def normalize_ip_address(value: str | None) -> str | None:
    """归一化 IP 地址，仅保留有效 IPv4/IPv6."""
    if not value:
        return None
    normalized = str(value).strip()
    try:
        ip = ipaddress.ip_address(normalized)
        return str(ip)
    except ValueError:
        return None


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


def build_instance_ip_candidates(instance_host: str | None) -> list[str]:
    """基于实例 host 构建 IP 候选集合."""
    if not instance_host:
        return []

    candidates: list[str] = []
    seen: set[str] = set()

    normalized_ip = normalize_ip_address(instance_host)
    if normalized_ip:
        candidates.append(normalized_ip)
        seen.add(normalized_ip)

    host_str = str(instance_host).strip()
    if host_str and host_str not in seen:
        candidates.append(host_str.lower())
        seen.add(host_str.lower())

    return candidates
