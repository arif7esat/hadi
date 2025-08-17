"""
Advanced Logging and Error Management System
Comprehensive logging with multiple output formats, error tracking, and performance monitoring.
"""

import os
import sys
import json
import logging
import traceback
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from pathlib import Path
import threading
import queue
import time
from enum import Enum
from dataclasses import dataclass, asdict
from rich.console import Console
from rich.logging import RichHandler
from rich.table import Table
from rich.panel import Panel
from rich import box
import colorama
from colorama import Fore, Back, Style


class LogLevel(Enum):
    """Enhanced log levels with custom priorities."""
    TRACE = 5
    DEBUG = 10
    INFO = 20
    SUCCESS = 25
    WARNING = 30
    ERROR = 40
    CRITICAL = 50


@dataclass
class LogEntry:
    """Structured log entry with metadata."""
    timestamp: datetime
    level: LogLevel
    message: str
    module: str
    function: str
    line_number: int
    thread_id: str
    process_id: int
    context: Dict[str, Any] = None
    exception: Optional[str] = None
    performance_data: Optional[Dict] = None
    
    def to_dict(self) -> Dict:
        """Convert log entry to dictionary."""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        data['level'] = self.level.name
        return data
    
    def to_json(self) -> str:
        """Convert log entry to JSON string."""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


class PerformanceTracker:
    """Performance monitoring and timing utility."""
    
    def __init__(self):
        self.timers: Dict[str, float] = {}
        self.counters: Dict[str, int] = {}
        self.measurements: List[Dict] = []
    
    def start_timer(self, name: str):
        """Start a performance timer."""
        self.timers[name] = time.time()
    
    def stop_timer(self, name: str) -> float:
        """Stop a timer and return elapsed time."""
        if name not in self.timers:
            return 0.0
        
        elapsed = time.time() - self.timers[name]
        del self.timers[name]
        
        self.measurements.append({
            'name': name,
            'elapsed_time': elapsed,
            'timestamp': datetime.now().isoformat()
        })
        
        return elapsed
    
    def increment_counter(self, name: str, value: int = 1):
        """Increment a counter."""
        self.counters[name] = self.counters.get(name, 0) + value
    
    def get_stats(self) -> Dict:
        """Get performance statistics."""
        return {
            'active_timers': list(self.timers.keys()),
            'counters': self.counters.copy(),
            'recent_measurements': self.measurements[-20:],  # Last 20 measurements
            'total_measurements': len(self.measurements)
        }


class LogFormatter:
    """Custom log formatters for different output types."""
    
    @staticmethod
    def format_console(entry: LogEntry) -> str:
        """Format log entry for console output with colors."""
        colorama.init(autoreset=True)
        
        # Color mapping for log levels
        level_colors = {
            LogLevel.TRACE: Fore.CYAN,
            LogLevel.DEBUG: Fore.BLUE,
            LogLevel.INFO: Fore.WHITE,
            LogLevel.SUCCESS: Fore.GREEN,
            LogLevel.WARNING: Fore.YELLOW,
            LogLevel.ERROR: Fore.RED,
            LogLevel.CRITICAL: Fore.RED + Back.WHITE + Style.BRIGHT
        }
        
        color = level_colors.get(entry.level, Fore.WHITE)
        timestamp = entry.timestamp.strftime("%H:%M:%S")
        
        # Create formatted message
        formatted = f"{color}[{timestamp}] {entry.level.name:8} {entry.module}:{entry.line_number} - {entry.message}{Style.RESET_ALL}"
        
        if entry.exception:
            formatted += f"\n{Fore.RED}Exception: {entry.exception}{Style.RESET_ALL}"
        
        return formatted
    
    @staticmethod
    def format_file(entry: LogEntry) -> str:
        """Format log entry for file output."""
        timestamp = entry.timestamp.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        
        base_msg = f"[{timestamp}] {entry.level.name:8} [{entry.thread_id}] {entry.module}:{entry.function}:{entry.line_number} - {entry.message}"
        
        if entry.context:
            base_msg += f" | Context: {json.dumps(entry.context, ensure_ascii=False)}"
        
        if entry.exception:
            base_msg += f"\nException: {entry.exception}"
        
        if entry.performance_data:
            base_msg += f"\nPerformance: {json.dumps(entry.performance_data)}"
        
        return base_msg


class AsyncLogWriter:
    """Asynchronous log writer for high-performance logging."""
    
    def __init__(self, file_path: str, max_queue_size: int = 1000):
        self.file_path = file_path
        self.queue = queue.Queue(maxsize=max_queue_size)
        self.writer_thread = None
        self.running = False
        self.ensure_directory()
    
    def ensure_directory(self):
        """Ensure log directory exists."""
        Path(self.file_path).parent.mkdir(parents=True, exist_ok=True)
    
    def start(self):
        """Start the async writer thread."""
        if self.running:
            return
        
        self.running = True
        self.writer_thread = threading.Thread(target=self._write_loop, daemon=True)
        self.writer_thread.start()
    
    def stop(self):
        """Stop the async writer thread."""
        if not self.running:
            return
        
        self.running = False
        # Send poison pill to stop the thread
        self.queue.put(None)
        
        if self.writer_thread:
            self.writer_thread.join(timeout=5.0)
    
    def write(self, message: str):
        """Queue a message for writing."""
        if not self.running:
            return
        
        try:
            self.queue.put(message, timeout=0.1)
        except queue.Full:
            # If queue is full, drop the message to prevent blocking
            pass
    
    def _write_loop(self):
        """Main writer loop running in background thread."""
        with open(self.file_path, 'a', encoding='utf-8') as f:
            while self.running:
                try:
                    message = self.queue.get(timeout=1.0)
                    
                    if message is None:  # Poison pill
                        break
                    
                    f.write(message + '\n')
                    f.flush()
                    
                except queue.Empty:
                    continue
                except Exception as e:
                    # Log error to stderr if file logging fails
                    print(f"Log writer error: {e}", file=sys.stderr)


class SmartLogger:
    """Advanced logger with multiple outputs, performance tracking, and error analysis."""
    
    def __init__(self, name: str = "AutoCommit", config_path: str = "config.json"):
        self.name = name
        self.config = self._load_config(config_path)
        self.console = Console()
        self.performance = PerformanceTracker()
        
        # Log storage
        self.log_entries: List[LogEntry] = []
        self.max_memory_logs = 1000
        
        # File writers
        self.writers: Dict[str, AsyncLogWriter] = {}
        
        # Error tracking
        self.error_counts: Dict[str, int] = {}
        self.critical_errors: List[LogEntry] = []
        
        # Setup logging
        self._setup_logging()
        
        # Statistics
        self.stats = {
            'total_logs': 0,
            'logs_by_level': {level.name: 0 for level in LogLevel},
            'start_time': datetime.now(),
            'errors_in_last_hour': 0
        }
    
    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from file."""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict:
        """Get default logging configuration."""
        return {
            "logging": {
                "level": "INFO",
                "console_enabled": True,
                "file_enabled": True,
                "json_enabled": True,
                "log_directory": "./logs",
                "max_file_size_mb": 10,
                "max_files": 5,
                "performance_tracking": True
            }
        }
    
    def _setup_logging(self):
        """Setup logging infrastructure."""
        log_config = self.config.get("logging", {})
        
        if log_config.get("file_enabled", True):
            log_dir = log_config.get("log_directory", "./logs")
            
            # Setup different log files
            self.writers["main"] = AsyncLogWriter(f"{log_dir}/main.log")
            self.writers["error"] = AsyncLogWriter(f"{log_dir}/error.log")
            self.writers["json"] = AsyncLogWriter(f"{log_dir}/logs.json")
            
            # Start all writers
            for writer in self.writers.values():
                writer.start()
    
    def _create_log_entry(self, level: LogLevel, message: str, **kwargs) -> LogEntry:
        """Create a structured log entry."""
        frame = sys._getframe(2)  # Get caller's frame
        
        entry = LogEntry(
            timestamp=datetime.now(),
            level=level,
            message=message,
            module=frame.f_globals.get('__name__', 'unknown'),
            function=frame.f_code.co_name,
            line_number=frame.f_lineno,
            thread_id=threading.current_thread().name,
            process_id=os.getpid(),
            context=kwargs.get('context'),
            exception=kwargs.get('exception'),
            performance_data=kwargs.get('performance')
        )
        
        return entry
    
    def _log(self, level: LogLevel, message: str, **kwargs):
        """Internal logging method."""
        entry = self._create_log_entry(level, message, **kwargs)
        
        # Store in memory (with rotation)
        self.log_entries.append(entry)
        if len(self.log_entries) > self.max_memory_logs:
            self.log_entries.pop(0)
        
        # Update statistics
        self.stats['total_logs'] += 1
        self.stats['logs_by_level'][level.name] += 1
        
        # Track errors
        if level in [LogLevel.ERROR, LogLevel.CRITICAL]:
            error_key = f"{entry.module}:{entry.function}"
            self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1
            
            if level == LogLevel.CRITICAL:
                self.critical_errors.append(entry)
                # Keep only last 50 critical errors
                if len(self.critical_errors) > 50:
                    self.critical_errors.pop(0)
        
        # Console output
        if self.config.get("logging", {}).get("console_enabled", True):
            console_msg = LogFormatter.format_console(entry)
            print(console_msg)
        
        # File output
        if "main" in self.writers:
            file_msg = LogFormatter.format_file(entry)
            self.writers["main"].write(file_msg)
            
            # Write errors to separate file
            if level in [LogLevel.ERROR, LogLevel.CRITICAL] and "error" in self.writers:
                self.writers["error"].write(file_msg)
        
        # JSON output
        if "json" in self.writers:
            self.writers["json"].write(entry.to_json())
    
    # Public logging methods
    def trace(self, message: str, **kwargs):
        """Log trace message."""
        self._log(LogLevel.TRACE, message, **kwargs)
    
    def debug(self, message: str, **kwargs):
        """Log debug message."""
        self._log(LogLevel.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs):
        """Log info message."""
        self._log(LogLevel.INFO, message, **kwargs)
    
    def success(self, message: str, **kwargs):
        """Log success message."""
        self._log(LogLevel.SUCCESS, message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message."""
        self._log(LogLevel.WARNING, message, **kwargs)
    
    def error(self, message: str, exception: Exception = None, **kwargs):
        """Log error message."""
        if exception:
            kwargs['exception'] = traceback.format_exc()
        self._log(LogLevel.ERROR, message, **kwargs)
    
    def critical(self, message: str, exception: Exception = None, **kwargs):
        """Log critical message."""
        if exception:
            kwargs['exception'] = traceback.format_exc()
        self._log(LogLevel.CRITICAL, message, **kwargs)
    
    # Performance tracking methods
    def start_timer(self, name: str):
        """Start a performance timer."""
        self.performance.start_timer(name)
        self.trace(f"Started timer: {name}")
    
    def stop_timer(self, name: str) -> float:
        """Stop a timer and log the result."""
        elapsed = self.performance.stop_timer(name)
        self.debug(f"Timer {name} completed", performance={'elapsed_time': elapsed})
        return elapsed
    
    def time_function(self, func: Callable) -> Callable:
        """Decorator to time function execution."""
        def wrapper(*args, **kwargs):
            timer_name = f"{func.__module__}.{func.__name__}"
            self.start_timer(timer_name)
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                self.stop_timer(timer_name)
        return wrapper
    
    # Analysis and reporting methods
    def get_error_summary(self) -> Dict:
        """Get summary of errors and critical issues."""
        recent_errors = [e for e in self.log_entries 
                        if e.level in [LogLevel.ERROR, LogLevel.CRITICAL] 
                        and (datetime.now() - e.timestamp).total_seconds() < 3600]
        
        return {
            'total_errors': sum(1 for e in self.log_entries if e.level == LogLevel.ERROR),
            'total_critical': sum(1 for e in self.log_entries if e.level == LogLevel.CRITICAL),
            'errors_in_last_hour': len(recent_errors),
            'most_common_errors': sorted(self.error_counts.items(), key=lambda x: x[1], reverse=True)[:5],
            'recent_critical': [e.to_dict() for e in self.critical_errors[-3:]]
        }
    
    def get_performance_summary(self) -> Dict:
        """Get performance statistics summary."""
        return self.performance.get_stats()
    
    def print_dashboard(self):
        """Print a nice dashboard with current status."""
        uptime = datetime.now() - self.stats['start_time']
        error_summary = self.get_error_summary()
        perf_summary = self.get_performance_summary()
        
        # Create dashboard table
        table = Table(title=f"🚀 {self.name} Logger Dashboard", box=box.ROUNDED)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Uptime", str(uptime).split('.')[0])
        table.add_row("Total Logs", str(self.stats['total_logs']))
        table.add_row("Errors (1h)", str(error_summary['errors_in_last_hour']))
        table.add_row("Critical Issues", str(error_summary['total_critical']))
        table.add_row("Active Timers", str(len(perf_summary['active_timers'])))
        table.add_row("Memory Logs", f"{len(self.log_entries)}/{self.max_memory_logs}")
        
        self.console.print(table)
    
    def cleanup(self):
        """Cleanup resources and stop async writers."""
        self.info("Shutting down logger...")
        
        for writer in self.writers.values():
            writer.stop()
        
        self.success("Logger shutdown complete")


# Global logger instance
logger = SmartLogger()


def main():
    """Test the logging system."""
    # Test different log levels
    logger.info("Starting logging system test")
    logger.debug("This is a debug message")
    logger.success("Operation completed successfully")
    logger.warning("This is a warning message")
    
    # Test performance tracking
    logger.start_timer("test_operation")
    time.sleep(0.1)
    logger.stop_timer("test_operation")
    
    # Test error logging
    try:
        raise ValueError("This is a test exception")
    except Exception as e:
        logger.error("Test error occurred", exception=e)
    
    # Show dashboard
    logger.print_dashboard()
    
    # Show error summary
    error_summary = logger.get_error_summary()
    print("\n📊 Error Summary:")
    print(json.dumps(error_summary, indent=2, ensure_ascii=False))
    
    # Cleanup
    logger.cleanup()


if __name__ == "__main__":
    main()
