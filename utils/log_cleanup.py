# -*- coding: utf-8 -*-
"""
日志清理工具 - 清理超过指定大小的 .log 文件
供 daemon.py 和 app_init.py.bak 共享使用
"""
from __future__ import annotations

import glob
import gzip
import os
import shutil
import time
from datetime import datetime

import logging

logger = logging.getLogger(__name__)


def cleanup_logs(max_size_mb: int = 50, data_dir: str | None = None, log_dirs: list[str] | None = None) -> tuple[int, int]:
    """清理超过指定大小的 .log 文件

    清理策略：
    1. 遍历 log_dirs（默认 [data_dir]）下所有 .log 文件
    2. 单个文件超过 max_size_mb 时，归档为 .log.YYYYMMDD_HHMMSS.gz
    3. 超过 7 天的 .log.gz 归档文件被删除

    Args:
        max_size_mb: 单个日志文件最大大小（MB）
        data_dir: 数据目录（当 log_dirs 为空时使用）
        log_dirs: 日志目录列表（优先使用）

    Returns:
        (cleaned_count, freed_bytes)
    """
    if log_dirs is None:
        log_dirs = [data_dir or os.environ.get("DATA_DIR", os.path.dirname(os.path.abspath(__file__)))]

    cleaned_count = 0
    freed_bytes = 0
    threshold_bytes = max_size_mb * 1024 * 1024

    for log_dir in log_dirs:
        if not os.path.isdir(log_dir):
            continue

        # 清理 .log 文件
        for log_file in glob.glob(os.path.join(log_dir, "*.log")):
            try:
                file_size = os.path.getsize(log_file)
                if file_size > threshold_bytes:
                    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                    archive_path = log_file + "." + ts + ".gz"
                    with open(log_file, "rb") as f_in:
                        with gzip.open(archive_path, "wb") as f_out:
                            shutil.copyfileobj(f_in, f_out)
                    # 截断原文件
                    with open(log_file, "w") as f:
                        f.write("")
                    freed_bytes += file_size
                    cleaned_count += 1
                    logger.info(f"日志归档并清理: {log_file} ({file_size / 1024 / 1024:.1f}MB -> {archive_path})")
            except Exception as e:
                logger.warning(f"清理日志文件失败 {log_file}: {e}")

        # 删除超过 7 天的 .log.gz 归档
        cutoff = time.time() - 7 * 86400
        for archive_file in glob.glob(os.path.join(log_dir, "*.log.*.gz")):
            try:
                mtime = os.path.getmtime(archive_file)
                if mtime < cutoff:
                    os.unlink(archive_file)
                    logger.info(f"删除过期归档: {archive_file}")
                    cleaned_count += 1
            except Exception as e:
                logger.warning(f"删除归档失败 {archive_file}: {e}")

    return cleaned_count, freed_bytes
