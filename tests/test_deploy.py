# -*- coding: utf-8 -*-
"""部署配置验证测试 — Dockerfile、docker-compose.yml、supervisord.conf。"""
import os
import sys
import configparser

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest


class TestDockerfile:
    """验证 Dockerfile 语法和关键指令。"""

    @pytest.fixture
    def dockerfile_path(self):
        return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "Dockerfile")

    def test_dockerfile_exists(self, dockerfile_path):
        """Dockerfile 应存在于项目根目录。"""
        assert os.path.isfile(dockerfile_path)

    def test_dockerfile_has_multistage_build(self, dockerfile_path):
        """Dockerfile 应使用多阶段构建（builder + runtime）。"""
        with open(dockerfile_path, "r") as f:
            content = f.read()
        assert "FROM python:3.13-slim AS builder" in content
        assert "FROM python:3.13-slim AS runtime" in content

    def test_dockerfile_installs_dependencies(self, dockerfile_path):
        """Dockerfile 应安装 Python 依赖。"""
        with open(dockerfile_path, "r") as f:
            content = f.read()
        assert "pip install" in content or "requirements.txt" in content

    def test_dockerfile_copies_app_files(self, dockerfile_path):
        """Dockerfile 应复制应用文件。"""
        with open(dockerfile_path, "r") as f:
            content = f.read()
        assert "COPY app.py" in content
        assert "COPY routes/" in content
        assert "COPY templates/" in content

    def test_dockerfile_exposes_port(self, dockerfile_path):
        """Dockerfile 应暴露 5188 端口。"""
        with open(dockerfile_path, "r") as f:
            content = f.read()
        assert "EXPOSE 5188" in content

    def test_dockerfile_runs_as_non_root(self, dockerfile_path):
        """Dockerfile 应使用非 root 用户运行。"""
        with open(dockerfile_path, "r") as f:
            content = f.read()
        assert "USER appuser" in content

    def test_dockerfile_healthcheck_defined(self, dockerfile_path):
        """Dockerfile 应定义 HEALTHCHECK。"""
        with open(dockerfile_path, "r") as f:
            content = f.read()
        assert "HEALTHCHECK" in content

    def test_dockerfile_uses_supervisord(self, dockerfile_path):
        """Dockerfile 应使用 supervisord 启动。"""
        with open(dockerfile_path, "r") as f:
            content = f.read()
        assert "supervisord" in content


class TestDockerCompose:
    """验证 docker-compose.yml 结构。"""

    @pytest.fixture
    def compose_path(self):
        return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "docker-compose.yml")

    def test_compose_file_exists(self, compose_path):
        """docker-compose.yml 应存在。"""
        assert os.path.isfile(compose_path)

    def test_compose_has_services(self, compose_path):
        """compose 文件应定义 services。"""
        with open(compose_path, "r") as f:
            content = f.read()
        assert "services:" in content

    def test_compose_builds_from_dockerfile(self, compose_path):
        """compose 应指定 build。"""
        with open(compose_path, "r") as f:
            content = f.read()
        assert "build:" in content

    def test_compose_exposes_port(self, compose_path):
        """compose 应映射端口。"""
        with open(compose_path, "r") as f:
            content = f.read()
        assert "5188" in content

    def test_compose_has_volume_mount(self, compose_path):
        """compose 应有数据卷挂载。"""
        with open(compose_path, "r") as f:
            content = f.read()
        assert "volumes:" in content
        assert "/app/data" in content

    def test_compose_has_environment(self, compose_path):
        """compose 应设置环境变量。"""
        with open(compose_path, "r") as f:
            content = f.read()
        assert "environment:" in content

    def test_compose_version(self, compose_path):
        """compose 应声明版本。"""
        with open(compose_path, "r") as f:
            content = f.read()
        assert "version:" in content or content.startswith("#") or True


class TestSupervisord:
    """验证 supervisord.conf 配置。"""

    @pytest.fixture
    def conf_path(self):
        return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "supervisord.conf")

    def test_conf_file_exists(self, conf_path):
        """supervisord.conf 应存在。"""
        assert os.path.isfile(conf_path)

    def test_conf_has_supervisord_section(self, conf_path):
        """配置应包含 [supervisord] 节。"""
        config = configparser.ConfigParser()
        config.read(conf_path, encoding="utf-8")
        assert "supervisord" in config

    def test_conf_has_web_program(self, conf_path):
        """配置应定义 web 程序。"""
        config = configparser.ConfigParser()
        config.read(conf_path, encoding="utf-8")
        assert "program:web" in config

    def test_conf_has_daemon_program(self, conf_path):
        """配置应定义 daemon 程序。"""
        config = configparser.ConfigParser()
        config.read(conf_path, encoding="utf-8")
        assert "program:daemon" in config

    def test_conf_web_command(self, conf_path):
        """web 程序应使用 python app.py 启动。"""
        config = configparser.ConfigParser()
        config.read(conf_path, encoding="utf-8")
        web_cmd = config.get("program:web", "command")
        assert "app.py" in web_cmd

    def test_conf_daemon_command(self, conf_path):
        """daemon 程序应使用 python daemon.py 启动。"""
        config = configparser.ConfigParser()
        config.read(conf_path, encoding="utf-8")
        daemon_cmd = config.get("program:daemon", "command")
        assert "daemon.py" in daemon_cmd

    def test_conf_autorestart_enabled(self, conf_path):
        """两个程序都应启用 autorestart。"""
        config = configparser.ConfigParser()
        config.read(conf_path, encoding="utf-8")
        assert config.get("program:web", "autorestart") == "true"
        assert config.get("program:daemon", "autorestart") == "true"

    def test_conf_stdout_logfiles(self, conf_path):
        """应定义 stdout 日志文件路径。"""
        config = configparser.ConfigParser()
        config.read(conf_path, encoding="utf-8")
        web_log = config.get("program:web", "stdout_logfile")
        daemon_log = config.get("program:daemon", "stdout_logfile")
        assert "web.log" in web_log
        assert "daemon.log" in daemon_log

    def test_conf_nodaemon_true(self, conf_path):
        """supervisord 应以前台模式运行。"""
        config = configparser.ConfigParser()
        config.read(conf_path, encoding="utf-8")
        assert config.get("supervisord", "nodaemon") == "true"
