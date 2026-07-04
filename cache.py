# -*- coding: utf-8 -*-
"""
统一缓存层 - 轻量级内存缓存

LRUCache 类：支持 TTL、最大容量、自动过期清理
使用 OrderedDict 实现 LRU，线程安全（threading.Lock）
"""
from __future__ import annotations

import time
import threading
from collections import OrderedDict
from typing import Any, Optional


class CacheEntry:
    """缓存条目，携带值与过期时间"""
    __slots__ = ("value", "expires_at")

    def __init__(self, value: Any, ttl: float) -> None:
        self.value = value
        self.expires_at = time.time() + ttl if ttl > 0 else 0.0

    @property
    def is_expired(self) -> bool:
        if self.expires_at == 0.0:
            return False
        return time.time() > self.expires_at


class LRUCache:
    """线程安全的 LRU 缓存，支持 TTL 和容量限制。

    Args:
        maxsize: 最大缓存条目数（LRU 淘汰阈值）
        ttl: 默认过期时间（秒），0 表示永不过期
    """

    def __init__(self, maxsize: int = 100, ttl: float = 0.0) -> None:
        self._maxsize = maxsize
        self._ttl = ttl
        self._store: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.Lock()

        # 命中统计
        self._hits: int = 0
        self._misses: int = 0

    # ── 核心操作 ──────────────────────────────────────────

    def get(self, key: str, ttl: Optional[float] = None) -> Any | None:
        """获取缓存值。命中返回 value，未命中或过期返回 None。"""
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                self._misses += 1
                return None
            if entry.is_expired:
                del self._store[key]
                self._misses += 1
                return None
            # 命中：移到末尾（最近使用）
            self._store.move_to_end(key)
            self._hits += 1
            return entry.value

    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        """设置缓存值。"""
        effective_ttl = ttl if ttl is not None else self._ttl
        with self._lock:
            if key in self._store:
                self._store[key] = CacheEntry(value, effective_ttl)
                self._store.move_to_end(key)
            else:
                self._store[key] = CacheEntry(value, effective_ttl)
                self._evict_if_needed()

    def delete(self, key: str) -> bool:
        """删除指定 key。成功返回 True。"""
        with self._lock:
            if key in self._store:
                del self._store[key]
                return True
            return False

    def clear(self) -> None:
        """清空所有缓存条目。"""
        with self._lock:
            self._store.clear()

    # ── 统计信息 ──────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        """返回缓存统计信息。"""
        with self._lock:
            total_requests = self._hits + self._misses
            hit_rate = round(self._hits / total_requests * 100, 2) if total_requests > 0 else 0.0
            size = len(self._store)
            return {
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": hit_rate,
                "size": size,
                "maxsize": self._maxsize,
                "ttl_default": self._ttl,
            }

    def size(self) -> int:
        """当前缓存条目数。"""
        with self._lock:
            return len(self._store)

    # ── 内部方法 ──────────────────────────────────────────

    def _evict_if_needed(self) -> None:
        """（需持有锁）当缓存满时淘汰最久未使用的条目。"""
        while len(self._store) > self._maxsize:
            self._store.popitem(last=False)  # 淘汰最旧的

    def cleanup_expired(self) -> int:
        """（需外部加锁）清理所有过期条目，返回清理数量。"""
        now = time.time()
        expired_keys = [
            k for k, v in self._store.items()
            if v.expires_at > 0 and now > v.expires_at
        ]
        for k in expired_keys:
            del self._store[k]
        return len(expired_keys)
