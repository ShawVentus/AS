#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ArxivScout 一键启动脚本

主要功能：
    一键启动前端和后端开发服务器，简化开发流程。

功能特性：
    1. 同时启动前后端服务
    2. 端口占用检测
    3. 环境检查（.env 文件等）
    4. 健康检查（轮询检测服务是否成功启动）
    5. 彩色日志输出（区分前后端）
    6. 日志文件保存（按时间戳分目录存储）
    7. 自动打开浏览器
    8. 优雅退出（Ctrl+C 同时停止所有服务）

使用方法：
    python app.py

作者：ArxivScout Team
创建日期：2025-12-20
"""

import os
import sys
import signal
import socket
import atexit
import webbrowser
import subprocess
import threading
import re
from pathlib import Path
from datetime import datetime
from urllib.request import urlopen
from urllib.error import URLError
from typing import Optional, Callable, TextIO


# ============================================================================
# 配置常量区
# ============================================================================

# 目录配置
BACKEND_DIR = "backend"
FRONTEND_DIR = "frontend"
LOG_ROOT = "logs"

# 端口配置
BACKEND_PORT = 8000
FRONTEND_PORT = 5173

# URL 配置
BACKEND_URL = f"http://localhost:{BACKEND_PORT}"
FRONTEND_URL = f"http://localhost:{FRONTEND_PORT}"

# 健康检查配置
HEALTH_CHECK_TIMEOUT = 30      # 健康检查超时时间（秒）
HEALTH_CHECK_INTERVAL = 0.5    # 健康检查间隔（秒）

# 进程终止配置
TERMINATE_TIMEOUT = 5          # 进程终止等待时间（秒）


# ============================================================================
# 工具类：彩色终端输出
# ============================================================================

class ColorPrinter:
    """
    彩色终端输出工具类
    
    主要功能：
        提供统一的彩色输出接口，用于区分不同类型的日志信息。
        后端日志使用蓝色，前端日志使用绿色，便于开发者快速识别日志来源。
    """
    
    # ANSI 颜色转义码
    RESET = "\033[0m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    
    @staticmethod
    def backend(msg: str) -> str:
        """
        格式化后端日志消息
        
        Args:
            msg: 原始日志消息
            
        Returns:
            带蓝色 [后端] 前缀的格式化消息
        """
        return f"{ColorPrinter.BLUE}[后端]{ColorPrinter.RESET} {msg}"
    
    @staticmethod
    def frontend(msg: str) -> str:
        """
        格式化前端日志消息
        
        Args:
            msg: 原始日志消息
            
        Returns:
            带绿色 [前端] 前缀的格式化消息
        """
        return f"{ColorPrinter.GREEN}[前端]{ColorPrinter.RESET} {msg}"
    
    @staticmethod
    def info(msg: str) -> str:
        """
        格式化信息日志
        
        Args:
            msg: 原始日志消息
            
        Returns:
            青色格式化的消息
        """
        return f"{ColorPrinter.CYAN}{msg}{ColorPrinter.RESET}"
    
    @staticmethod
    def success(msg: str) -> str:
        """
        格式化成功日志
        
        Args:
            msg: 原始日志消息
            
        Returns:
            绿色加粗格式化的消息
        """
        return f"{ColorPrinter.GREEN}{ColorPrinter.BOLD}{msg}{ColorPrinter.RESET}"
    
    @staticmethod
    def error(msg: str) -> str:
        """
        格式化错误日志
        
        Args:
            msg: 原始日志消息
            
        Returns:
            红色加粗格式化的消息
        """
        return f"{ColorPrinter.RED}{ColorPrinter.BOLD}{msg}{ColorPrinter.RESET}"
    
    @staticmethod
    def warning(msg: str) -> str:
        """
        格式化警告日志
        
        Args:
            msg: 原始日志消息
            
        Returns:
            黄色格式化的消息
        """
        return f"{ColorPrinter.YELLOW}{msg}{ColorPrinter.RESET}"
    
    @staticmethod
    def dim(msg: str) -> str:
        """
        格式化次要信息
        
        Args:
            msg: 原始日志消息
            
        Returns:
            暗色格式化的消息
        """
        return f"{ColorPrinter.DIM}{msg}{ColorPrinter.RESET}"


# ============================================================================
# 工具函数：ANSI 转义码处理
# ============================================================================

def strip_ansi(text: str) -> str:
    """
    移除字符串中的 ANSI 转义码
    
    主要功能：
        将包含颜色等 ANSI 转义码的字符串转换为纯文本，
        用于写入日志文件时保持文件可读性。
    
    Args:
        text: 可能包含 ANSI 转义码的字符串
        
    Returns:
        移除所有 ANSI 转义码后的纯文本字符串
    """
    ansi_pattern = re.compile(r'\x1b\[[0-9;]*m')
    return ansi_pattern.sub('', text)


# ============================================================================
# 核心功能：日志系统
# ============================================================================

def setup_logging(project_root: Path) -> tuple[Path, Path]:
    """
    创建日志目录和日志文件
    
    主要功能：
        按时间戳创建独立的日志会话目录，确保每次运行的日志互不干扰。
        目录命名格式：YYYY-MM-DD_HH-MM-SS
    
    Args:
        project_root: 项目根目录路径
        
    Returns:
        (backend_log_path, frontend_log_path): 后端和前端日志文件路径的元组
        
    日志目录结构示例：
        logs/
        └── 2025-12-20_23-05-30/
            ├── backend.log
            └── frontend.log
    """
    # 生成时间戳目录名
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_dir = project_root / LOG_ROOT / timestamp
    
    # 创建多级目录（如果不存在）
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # 定义日志文件路径
    backend_log = log_dir / "backend.log"
    frontend_log = log_dir / "frontend.log"
    
    # 在日志文件开头写入启动时间标记
    startup_header = f"\n{'='*60}\n启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n{'='*60}\n\n"
    
    for log_path in [backend_log, frontend_log]:
        with open(log_path, 'w', encoding='utf-8') as f:
            f.write(startup_header)
    
    print(ColorPrinter.info(f"[日志] 日志目录已创建: {log_dir}"))
    
    return backend_log, frontend_log


# ============================================================================
# 核心功能：端口检测
# ============================================================================

def check_port_available(port: int) -> bool:
    """
    检测指定端口是否可用
    
    主要功能：
        通过尝试绑定端口来判断该端口是否被其他程序占用。
        这可以在启动服务前提前发现端口冲突，给出友好提示。
    
    Args:
        port: 要检测的端口号
        
    Returns:
        True 表示端口可用，False 表示端口已被占用
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            # 设置 SO_REUSEADDR 避免 TIME_WAIT 状态影响检测
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(('localhost', port))
            return True
    except OSError:
        return False


def check_all_ports() -> bool:
    """
    检查所有必需端口的可用性
    
    主要功能：
        批量检测后端和前端服务所需的端口，任一端口被占用则返回失败。
    
    Returns:
        True 表示所有端口可用，False 表示存在端口冲突
    """
    ports_to_check = [
        (BACKEND_PORT, "后端"),
        (FRONTEND_PORT, "前端"),
    ]
    
    all_available = True
    
    for port, name in ports_to_check:
        if check_port_available(port):
            print(ColorPrinter.success(f"[检查] 端口 {port} ({name}) 可用 ✓"))
        else:
            print(ColorPrinter.error(f"[检查] 端口 {port} ({name}) 已被占用 ✗"))
            print(ColorPrinter.warning(f"        请先关闭占用端口 {port} 的程序，或使用 'lsof -i :{port}' 查看占用进程"))
            all_available = False
    
    return all_available


# ============================================================================
# 核心功能：环境检查
# ============================================================================

def check_environment(project_root: Path) -> bool:
    """
    检查运行环境
    
    主要功能：
        验证项目结构和配置文件是否完整，包括：
        1. 后端目录和 .env 文件
        2. 前端目录和 node_modules
        
        缺少关键文件会给出警告，但不会阻止启动。
    
    Args:
        project_root: 项目根目录路径
        
    Returns:
        True 表示环境检查通过（可能有警告），False 表示存在致命错误
    """
    has_fatal_error = False
    
    # 检查后端目录
    backend_dir = project_root / BACKEND_DIR
    if not backend_dir.exists():
        print(ColorPrinter.error(f"[检查] 后端目录不存在: {backend_dir} ✗"))
        has_fatal_error = True
    else:
        print(ColorPrinter.success(f"[检查] 后端目录存在 ✓"))
        
        # 检查 .env 文件
        env_file = backend_dir / ".env"
        if env_file.exists():
            print(ColorPrinter.success(f"[检查] backend/.env 文件存在 ✓"))
        else:
            print(ColorPrinter.warning(f"[检查] backend/.env 文件不存在 ⚠"))
            print(ColorPrinter.dim("        服务可能因缺少配置而无法正常运行"))
    
    # 检查前端目录
    frontend_dir = project_root / FRONTEND_DIR
    if not frontend_dir.exists():
        print(ColorPrinter.error(f"[检查] 前端目录不存在: {frontend_dir} ✗"))
        has_fatal_error = True
    else:
        print(ColorPrinter.success(f"[检查] 前端目录存在 ✓"))
        
        # 检查 node_modules
        node_modules = frontend_dir / "node_modules"
        if node_modules.exists():
            print(ColorPrinter.success(f"[检查] node_modules 目录存在 ✓"))
        else:
            print(ColorPrinter.warning(f"[检查] node_modules 目录不存在 ⚠"))
            print(ColorPrinter.dim("        请先运行 'cd frontend && npm install'"))
    
    return not has_fatal_error


# ============================================================================
# 核心功能：进程管理
# ============================================================================

class ProcessManager:
    """
    进程管理器
    
    主要功能：
        统一管理后端和前端子进程的生命周期，包括：
        1. 启动进程
        2. 监控进程状态
        3. 优雅终止进程
        4. 日志输出转发
    
    Attributes:
        project_root: 项目根目录
        backend_proc: 后端进程对象
        frontend_proc: 前端进程对象
        backend_log_file: 后端日志文件句柄
        frontend_log_file: 前端日志文件句柄
        is_running: 运行状态标志
        output_lock: 输出锁，防止多线程输出混乱
    """
    
    def __init__(self, project_root: Path):
        """
        初始化进程管理器
        
        Args:
            project_root: 项目根目录路径
        """
        self.project_root = project_root
        self.backend_proc: Optional[subprocess.Popen] = None
        self.frontend_proc: Optional[subprocess.Popen] = None
        self.backend_log_file: Optional[TextIO] = None
        self.frontend_log_file: Optional[TextIO] = None
        self.is_running = threading.Event()
        self.output_lock = threading.Lock()
        self.output_threads: list[threading.Thread] = []
    
    def start_backend(self, log_path: Path) -> bool:
        """
        启动后端服务
        
        Args:
            log_path: 日志文件路径
            
        Returns:
            True 表示启动成功，False 表示启动失败
        """
        print(ColorPrinter.info("[启动] 正在启动后端服务..."))
        
        try:
            # 打开日志文件（追加模式）
            self.backend_log_file = open(log_path, 'a', encoding='utf-8')
            
            # 构建启动命令
            cmd = [
                sys.executable, "-m", "uvicorn",
                "app.main:app",
                "--reload",
                "--port", str(BACKEND_PORT)
            ]
            
            # 启动进程
            self.backend_proc = subprocess.Popen(
                cmd,
                cwd=self.project_root / BACKEND_DIR,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                bufsize=1,  # 行缓冲
            )
            
            print(ColorPrinter.success(f"[启动] 后端服务已启动 (PID: {self.backend_proc.pid}) ✓"))
            return True
            
        except Exception as e:
            print(ColorPrinter.error(f"[启动] 后端服务启动失败: {e}"))
            return False
    
    def start_frontend(self, log_path: Path) -> bool:
        """
        启动前端服务
        
        Args:
            log_path: 日志文件路径
            
        Returns:
            True 表示启动成功，False 表示启动失败
        """
        print(ColorPrinter.info("[启动] 正在启动前端服务..."))
        
        try:
            # 打开日志文件（追加模式）
            self.frontend_log_file = open(log_path, 'a', encoding='utf-8')
            
            # 构建启动命令
            cmd = ["npm", "run", "dev"]
            
            # 启动进程
            self.frontend_proc = subprocess.Popen(
                cmd,
                cwd=self.project_root / FRONTEND_DIR,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                bufsize=1,  # 行缓冲
            )
            
            print(ColorPrinter.success(f"[启动] 前端服务已启动 (PID: {self.frontend_proc.pid}) ✓"))
            return True
            
        except Exception as e:
            print(ColorPrinter.error(f"[启动] 前端服务启动失败: {e}"))
            return False
    
    def stream_output(
        self,
        process: subprocess.Popen,
        log_file: TextIO,
        prefix_func: Callable[[str], str],
        service_name: str
    ) -> None:
        """
        流式读取进程输出并转发
        
        主要功能：
            在单独线程中运行，实时将子进程输出：
            1. 带颜色前缀打印到终端
            2. 去除颜色码后写入日志文件
        
        Args:
            process: 子进程对象
            log_file: 日志文件句柄
            prefix_func: 添加颜色前缀的函数
            service_name: 服务名称（用于日志标记）
        """
        try:
            while self.is_running.is_set() and process.poll() is None:
                line = process.stdout.readline()
                if line:
                    # 移除行尾换行符
                    line = line.rstrip('\n\r')
                    
                    # 带颜色输出到终端（加锁防止混乱）
                    with self.output_lock:
                        print(prefix_func(line), flush=True)
                    
                    # 去除颜色码后写入日志文件
                    clean_line = strip_ansi(line)
                    log_file.write(f"{clean_line}\n")
                    log_file.flush()
                    
        except Exception as e:
            with self.output_lock:
                print(ColorPrinter.error(f"[错误] {service_name}输出读取失败: {e}"))
    
    def start_output_threads(self) -> None:
        """
        启动日志输出转发线程
        
        主要功能：
            为后端和前端分别创建输出转发线程，实现日志的实时显示和保存。
        """
        self.is_running.set()
        
        # 后端输出线程
        if self.backend_proc and self.backend_log_file:
            backend_thread = threading.Thread(
                target=self.stream_output,
                args=(self.backend_proc, self.backend_log_file, ColorPrinter.backend, "后端"),
                daemon=True
            )
            backend_thread.start()
            self.output_threads.append(backend_thread)
        
        # 前端输出线程
        if self.frontend_proc and self.frontend_log_file:
            frontend_thread = threading.Thread(
                target=self.stream_output,
                args=(self.frontend_proc, self.frontend_log_file, ColorPrinter.frontend, "前端"),
                daemon=True
            )
            frontend_thread.start()
            self.output_threads.append(frontend_thread)
    
    def cleanup(self) -> None:
        """
        清理函数，终止所有子进程
        
        主要功能：
            1. 发送 SIGTERM 信号请求进程终止
            2. 等待最多 TERMINATE_TIMEOUT 秒让进程自行退出
            3. 若仍未退出则发送 SIGKILL 强制终止
            4. 关闭日志文件句柄
        """
        print(ColorPrinter.info("\n[停止] 正在关闭所有服务..."))
        
        # 停止输出线程
        self.is_running.clear()
        
        # 终止前端进程
        if self.frontend_proc and self.frontend_proc.poll() is None:
            print(ColorPrinter.info("[停止] 正在关闭前端服务..."))
            try:
                self.frontend_proc.terminate()
                self.frontend_proc.wait(timeout=TERMINATE_TIMEOUT)
                print(ColorPrinter.success("[停止] 前端服务已关闭 ✓"))
            except subprocess.TimeoutExpired:
                print(ColorPrinter.warning("[停止] 前端服务未响应，强制终止..."))
                self.frontend_proc.kill()
                self.frontend_proc.wait()
        
        # 终止后端进程
        if self.backend_proc and self.backend_proc.poll() is None:
            print(ColorPrinter.info("[停止] 正在关闭后端服务..."))
            try:
                self.backend_proc.terminate()
                self.backend_proc.wait(timeout=TERMINATE_TIMEOUT)
                print(ColorPrinter.success("[停止] 后端服务已关闭 ✓"))
            except subprocess.TimeoutExpired:
                print(ColorPrinter.warning("[停止] 后端服务未响应，强制终止..."))
                self.backend_proc.kill()
                self.backend_proc.wait()
        
        # 关闭日志文件
        if self.frontend_log_file:
            self.frontend_log_file.close()
        if self.backend_log_file:
            self.backend_log_file.close()
        
        print(ColorPrinter.success("[停止] 所有服务已停止 ✓"))


# ============================================================================
# 核心功能：健康检查
# ============================================================================

def wait_for_service(url: str, service_name: str, timeout: int = HEALTH_CHECK_TIMEOUT) -> bool:
    """
    等待服务启动并可访问
    
    主要功能：
        通过轮询 HTTP 请求检测服务是否成功启动。
        每隔 HEALTH_CHECK_INTERVAL 秒发送一次请求，
        收到任何响应即认为服务已启动。
    
    Args:
        url: 服务地址
        service_name: 服务名称（用于日志显示）
        timeout: 超时时间（秒）
        
    Returns:
        True 表示服务可访问，False 表示超时
    """
    import time
    
    start_time = time.time()
    attempt = 0
    
    while time.time() - start_time < timeout:
        attempt += 1
        try:
            response = urlopen(url, timeout=1)
            response.close()
            print(ColorPrinter.success(f"[健康检查] {service_name}服务已就绪 ✓"))
            return True
        except URLError:
            # 服务尚未启动，继续等待
            pass
        except Exception:
            # 其他错误也继续等待
            pass
        
        time.sleep(HEALTH_CHECK_INTERVAL)
    
    print(ColorPrinter.error(f"[健康检查] {service_name}服务启动超时（{timeout}秒）✗"))
    return False


# ============================================================================
# 核心功能：浏览器打开
# ============================================================================

def open_browser(url: str = FRONTEND_URL) -> None:
    """
    打开默认浏览器访问前端页面
    
    Args:
        url: 要打开的 URL，默认为前端地址
    """
    print(ColorPrinter.info(f"[浏览器] 正在打开 {url}"))
    try:
        webbrowser.open(url)
    except Exception as e:
        print(ColorPrinter.warning(f"[浏览器] 无法自动打开浏览器: {e}"))
        print(ColorPrinter.info(f"          请手动访问: {url}"))


# ============================================================================
# 核心功能：启动横幅
# ============================================================================

def print_banner() -> None:
    """
    打印启动横幅
    
    主要功能：
        在启动时显示 ASCII 艺术横幅和基本信息，提升用户体验。
    """
    banner = f"""
{ColorPrinter.CYAN}{ColorPrinter.BOLD}
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║               ArxivScout 开发服务器启动中...                 ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
{ColorPrinter.RESET}
{ColorPrinter.DIM}后端: http://localhost:{BACKEND_PORT}
前端: http://localhost:{FRONTEND_PORT}
按 Ctrl+C 停止所有服务
{ColorPrinter.RESET}
"""
    print(banner)


# ============================================================================
# 主入口函数
# ============================================================================

def main() -> None:
    """
    主函数，协调整个启动流程
    
    执行顺序：
        1. 打印启动横幅
        2. 检测项目根目录
        3. 检查端口可用性
        4. 检查环境配置
        5. 创建日志目录和文件
        6. 启动后端服务
        7. 启动前端服务
        8. 启动日志转发线程
        9. 等待后端健康检查通过
        10. 等待前端健康检查通过
        11. 打开浏览器
        12. 进入主循环等待退出信号
    """
    # 1. 打印启动横幅
    print_banner()
    
    # 2. 获取项目根目录（脚本所在目录）
    project_root = Path(__file__).parent.resolve()
    print(ColorPrinter.info(f"[项目] 项目根目录: {project_root}"))
    print()
    
    # 3. 检查端口可用性
    if not check_all_ports():
        print(ColorPrinter.error("\n[错误] 端口检查失败，请解决端口冲突后重试"))
        sys.exit(1)
    print()
    
    # 4. 检查环境配置
    if not check_environment(project_root):
        print(ColorPrinter.error("\n[错误] 环境检查失败，请检查项目结构"))
        sys.exit(1)
    print()
    
    # 5. 创建日志目录和文件
    backend_log, frontend_log = setup_logging(project_root)
    print()
    
    # 6. 创建进程管理器
    manager = ProcessManager(project_root)
    
    # 7. 注册退出钩子，确保异常退出时也能清理
    atexit.register(manager.cleanup)
    
    # 8. 注册信号处理函数
    def signal_handler(signum, frame):
        """信号处理函数，捕获 Ctrl+C"""
        manager.cleanup()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 9. 启动后端服务
    if not manager.start_backend(backend_log):
        print(ColorPrinter.error("\n[错误] 后端服务启动失败"))
        manager.cleanup()
        sys.exit(1)
    
    # 10. 启动前端服务
    if not manager.start_frontend(frontend_log):
        print(ColorPrinter.error("\n[错误] 前端服务启动失败"))
        manager.cleanup()
        sys.exit(1)
    
    print()
    
    # 11. 启动日志输出转发线程
    manager.start_output_threads()
    
    # 12. 等待后端健康检查通过
    print(ColorPrinter.info("[健康检查] 等待后端服务就绪..."))
    if not wait_for_service(BACKEND_URL, "后端"):
        print(ColorPrinter.error("\n[错误] 后端服务健康检查失败"))
        manager.cleanup()
        sys.exit(1)
    
    # 13. 等待前端健康检查通过
    print(ColorPrinter.info("[健康检查] 等待前端服务就绪..."))
    if not wait_for_service(FRONTEND_URL, "前端"):
        print(ColorPrinter.error("\n[错误] 前端服务健康检查失败"))
        manager.cleanup()
        sys.exit(1)
    
    print()
    print(ColorPrinter.success("=" * 60))
    print(ColorPrinter.success("  ✓ 所有服务启动成功！"))
    print(ColorPrinter.success("=" * 60))
    print()
    
    # 14. 打开浏览器
    open_browser()
    
    print()
    print(ColorPrinter.dim("-" * 60))
    print(ColorPrinter.dim("以下是实时日志输出，按 Ctrl+C 停止所有服务"))
    print(ColorPrinter.dim("-" * 60))
    print()
    
    # 15. 进入主循环等待退出信号
    try:
        # 等待进程结束或被中断
        while True:
            # 检查进程是否意外退出
            if manager.backend_proc and manager.backend_proc.poll() is not None:
                print(ColorPrinter.error("\n[警告] 后端服务意外退出"))
                manager.cleanup()
                sys.exit(1)
            
            if manager.frontend_proc and manager.frontend_proc.poll() is not None:
                print(ColorPrinter.error("\n[警告] 前端服务意外退出"))
                manager.cleanup()
                sys.exit(1)
            
            # 短暂休眠避免 CPU 空转
            import time
            time.sleep(0.5)
            
    except KeyboardInterrupt:
        # Ctrl+C 已被信号处理函数捕获，这里作为备用
        manager.cleanup()
        sys.exit(0)


# ============================================================================
# 脚本入口
# ============================================================================

if __name__ == "__main__":
    main()
