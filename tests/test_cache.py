# -*- coding: utf-8 -*-
"""
统一缓存层单元测试
"""
import os
import sys
import time
import threading

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cache import LRUCache


class TestLRUCacheBasic:
    """基础功能测试"""

    def test_set_and_get(self):
        cache = LRUCache(maxsize=10)
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

    def test_get_missing_key(self):
        cache = LRUCache(maxsize=10)
        assert cache.get("nonexistent") is None

    def test_delete(self):
        cache = LRUCache(maxsize=10)
        cache.set("key1", "value1")
        assert cache.delete("key1") is True
        assert cache.get("key1") is None
        assert cache.delete("nonexistent") is False

    def test_clear(self):
        cache = LRUCache(maxsize=10)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.clear()
        assert cache.size() == 0
        assert cache.get("a") is None

    def test_stats(self):
        cache = LRUCache(maxsize=10)
        cache.set("k", "v")
        cache.get("k")       # hit
        cache.get("missing")  # miss
        s = cache.stats()
        assert s["hits"] == 1
        assert s["misses"] == 1
        assert s["hit_rate"] == 50.0
        assert s["size"] == 1
        assert s["maxsize"] == 10


class TestLRUEviction:
    """LRU 淘汰测试"""

    def test_lru_eviction(self):
        cache = LRUCache(maxsize=3)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)
        # 缓存满了，再插入应淘汰最旧的 a
        cache.set("d", 4)
        assert cache.get("a") is None
        assert cache.get("b") == 2
        assert cache.get("c") == 3
        assert cache.get("d") == 4
        assert cache.size() == 3

    def test_lru_access_renews_order(self):
        """访问某个 key 使其成为最近使用，保护它不被淘汰"""
        cache = LRUCache(maxsize=3)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)
        # 访问 a，使其变为最近使用
        cache.get("a")
        # 插入 d，应淘汰 b（最久未使用）
        cache.set("d", 4)
        assert cache.get("a") == 1   # 还在
        assert cache.get("b") is None  # 被淘汰
        assert cache.get("c") == 3
        assert cache.get("d") == 4

    def test_update_existing_key(self):
        """更新已有 key 不增加条目数"""
        cache = LRUCache(maxsize=2)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("a", 10)  # 更新 a
        assert cache.size() == 2
        assert cache.get("a") == 10
        # a 被更新为最近使用，b 应该被淘汰
        cache.set("c", 3)
        assert cache.get("b") is None
        assert cache.get("c") == 3


class TestTTLOverride:
    """TTL 过期测试"""

    def test_ttl_expiry(self):
        cache = LRUCache(maxsize=10, ttl=0.2)
        cache.set("k", "v")
        assert cache.get("k") == "v"
        time.sleep(0.3)
        assert cache.get("k") is None

    def test_no_ttl_means_forever(self):
        cache = LRUCache(maxsize=10, ttl=0)
        cache.set("k", "v")
        time.sleep(0.2)
        assert cache.get("k") == "v"

    def test_per_key_ttl_override(self):
        cache = LRUCache(maxsize=10, ttl=100)
        cache.set("short", "v", ttl=0.1)
        cache.set("long", "v", ttl=100)
        time.sleep(0.2)
        assert cache.get("short") is None
        assert cache.get("long") == "v"

    def test_default_ttl(self):
        cache = LRUCache(maxsize=10, ttl=0.15)
        cache.set("k", "v")  # 使用默认 TTL
        time.sleep(0.2)
        assert cache.get("k") is None


class TestThreadSafety:
    """线程安全性测试"""

    def test_concurrent_writes(self):
        """多线程并发写入不崩溃"""
        cache = LRUCache(maxsize=500)
        errors = []

        def writer(start: int):
            try:
                for i in range(start, start + 200):
                    cache.set(f"k{i}", f"v{i}")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=writer, args=(i * 200,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert not errors, f"Thread errors: {errors}"
        # 由于 maxsize=500 而写入了 1000 个不同 key，部分会被 LRU 淘汰
        # 但至少不会崩溃，能读到的都是正确值
        read_ok = sum(1 for i in range(1000) if cache.get(f"k{i}") == f"v{i}")
        assert read_ok > 0, f"None of the 1000 keys could be read"

    def test_concurrent_read_write(self):
        """读写混合操作不崩溃"""
        cache = LRUCache(maxsize=50)
        errors = []

        def writer():
            try:
                for i in range(500):
                    cache.set(f"rw{i}", f"v{i}")
                    cache.get(f"rw{i}")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=writer) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert not errors, f"Thread errors: {errors}"
