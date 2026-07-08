# -*- coding: utf-8 -*-
"""统一异常定义与错误码规范。

错误码规范：
    ERR_VALIDATION  - 验证失败（HTTP 422）
    ERR_NOT_FOUND   - 资源不存在（HTTP 404）
    ERR_PERMISSION  - 权限不足（HTTP 403）
    ERR_DATA        - 数据错误（HTTP 400）
    ERR_SERVICE     - 服务异常（HTTP 500）
    ERR_IMPORT      - 导入失败（HTTP 400）
    ERR_EXPORT      - 导出失败（HTTP 500）
"""
from __future__ import annotations


# ── 错误码常量 ──────────────────────────────────────────────
ERR_VALIDATION = "ERR_VALIDATION"
ERR_NOT_FOUND = "ERR_NOT_FOUND"
ERR_PERMISSION = "ERR_PERMISSION"
ERR_DATA = "ERR_DATA"
ERR_SERVICE = "ERR_SERVICE"
ERR_IMPORT = "ERR_IMPORT"
ERR_EXPORT = "ERR_EXPORT"


# ── 异常类定义 ──────────────────────────────────────────────
class MonitorException(Exception):
    """Monitor 自定义异常基类。

    Attributes:
        code: 错误码字符串（如 ERR_VALIDATION）。
        message: 面向用户的错误提示消息。
        status_code: HTTP 状态码。
        details: 附加详情（可选）。
    """

    code: str
    message: str
    status_code: int
    details: str | None

    def __init__(
        self,
        message: str,
        code: str = "",
        status_code: int = 500,
        details: str | None = None,
    ) -> None:
        self.message = message
        self.code = code or self._default_code()
        self.status_code = status_code
        self.details = details
        super().__init__(self.message)

    def _default_code(self) -> str:
        return "ERR_SERVICE"

    def to_dict(self) -> dict:
        """序列化为字典，供 API 返回。"""
        result: dict = {"success": False, "code": self.code, "message": self.message}
        if self.details:
            result["details"] = self.details
        return result


class NotFoundError(MonitorException):
    """资源不存在 - HTTP 404。"""

    def __init__(self, message: str = "资源不存在", details: str | None = None) -> None:
        super().__init__(message, ERR_NOT_FOUND, 404, details)


class ValidationError(MonitorException):
    """数据验证失败 - HTTP 422。"""

    def __init__(self, message: str = "验证失败", details: str | None = None) -> None:
        super().__init__(message, ERR_VALIDATION, 422, details)


class PermissionDenied(MonitorException):
    """权限不足 - HTTP 403。"""

    def __init__(self, message: str = "权限不足", details: str | None = None) -> None:
        super().__init__(message, ERR_PERMISSION, 403, details)


class DataError(MonitorException):
    """数据错误 - HTTP 400。"""

    def __init__(self, message: str = "数据错误", details: str | None = None) -> None:
        super().__init__(message, ERR_DATA, 400, details)


class ImportError(MonitorException):
    """导入失败 - HTTP 400。"""

    def __init__(self, message: str = "导入失败", details: str | None = None) -> None:
        super().__init__(message, ERR_IMPORT, 400, details)


class ExportError(MonitorException):
    """导出失败 - HTTP 500。"""

    def __init__(self, message: str = "导出失败", details: str | None = None) -> None:
        super().__init__(message, ERR_EXPORT, 500, details)


class ServiceError(MonitorException):
    """服务异常 - HTTP 500。"""

    def __init__(self, message: str = "服务异常", details: str | None = None) -> None:
        super().__init__(message, ERR_SERVICE, 500, details)
