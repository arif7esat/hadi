"""
File Monitor System
Real-time file change monitoring with intelligent filtering and batching.
"""

import os
import time
import json
import threading
from typing import Dict, List, Set, Callable, Optional
from datetime import datetime, timedelta
from pathlib import Path
import hashlib
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent
from concurrent.futures import ThreadPoolExecutor
import fnmatch


class FileChangeEvent:
    """Represents a file change event with metadata."""
    
    def __init__(self, file_path: str, event_type: str, timestamp: datetime = None):
        self.file_path = file_path
        self.event_type = event_type  # 'created', 'modified', 'deleted', 'moved'
        self.timestamp = timestamp or datetime.now()
        self.file_size = self._get_file_size()
        self.file_hash = self._get_file_hash()
    
    def _get_file_size(self) -> int:
        """Get file size safely."""
        try:
            return os.path.getsize(self.file_path) if os.path.exists(self.file_path) else 0
        except (OSError, FileNotFoundError):
            return 0
    
    def _get_file_hash(self) -> str:
        """Generate hash of file content for change detection."""
        try:
            if not os.path.exists(self.file_path) or not os.path.isfile(self.file_path):
                return ""
            
            with open(self.file_path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except (OSError, FileNotFoundError, PermissionError):
            return ""
    
    def __repr__(self):
        return f"FileChangeEvent({self.file_path}, {self.event_type}, {self.timestamp})"


class IntelligentFileHandler(FileSystemEventHandler):
    """Intelligent file system event handler with filtering and batching."""
    
    def __init__(self, monitor: 'FileMonitor'):
        self.monitor = monitor
        self.config = monitor.config
        self.recent_events: Dict[str, FileChangeEvent] = {}
        self.debounce_interval = 2.0  # seconds
        self.cleanup_thread = None
        self.start_cleanup_thread()
    
    def start_cleanup_thread(self):
        """Start background thread for event cleanup."""
        def cleanup_old_events():
            while True:
                time.sleep(self.debounce_interval)
                current_time = datetime.now()
                expired_files = []
                
                for file_path, event in self.recent_events.items():
                    if (current_time - event.timestamp).total_seconds() > self.debounce_interval:
                        expired_files.append(file_path)
                
                for file_path in expired_files:
                    event = self.recent_events.pop(file_path)
                    self.monitor._process_file_change(event)
        
        self.cleanup_thread = threading.Thread(target=cleanup_old_events, daemon=True)
        self.cleanup_thread.start()
    
    def should_ignore_file(self, file_path: str) -> bool:
        """Check if file should be ignored based on configuration."""
        file_path = os.path.normpath(file_path)
        
        # Check excluded directories
        excluded_dirs = self.config.get("monitoring", {}).get("exclude_directories", [])
        for excluded_dir in excluded_dirs:
            if excluded_dir in file_path:
                return True
        
        # Check file extensions
        allowed_extensions = self.config.get("monitoring", {}).get("file_extensions", [])
        if allowed_extensions:
            file_ext = Path(file_path).suffix
            if file_ext not in allowed_extensions:
                return True
        
        # Check git ignore patterns
        ignore_patterns = self.config.get("git", {}).get("ignore_patterns", [])
        file_name = os.path.basename(file_path)
        for pattern in ignore_patterns:
            if fnmatch.fnmatch(file_name, pattern) or fnmatch.fnmatch(file_path, pattern):
                return True
        
        # Ignore temporary and system files
        temp_patterns = ["*.tmp", "*.temp", "*.swp", "*.swo", "*~", ".DS_Store"]
        for pattern in temp_patterns:
            if fnmatch.fnmatch(file_name, pattern):
                return True
        
        return False
    
    def on_modified(self, event: FileSystemEvent):
        """Handle file modification events."""
        if event.is_directory:
            return
        
        if self.should_ignore_file(event.src_path):
            return
        
        # Debounce rapid changes to the same file
        file_path = os.path.normpath(event.src_path)
        current_event = FileChangeEvent(file_path, 'modified')
        
        # Check if we've seen this file recently
        if file_path in self.recent_events:
            previous_event = self.recent_events[file_path]
            # If hash is the same, ignore (probably just timestamp change)
            if current_event.file_hash == previous_event.file_hash:
                return
        
        self.recent_events[file_path] = current_event
    
    def on_created(self, event: FileSystemEvent):
        """Handle file creation events."""
        if event.is_directory:
            return
        
        if self.should_ignore_file(event.src_path):
            return
        
        file_path = os.path.normpath(event.src_path)
        self.recent_events[file_path] = FileChangeEvent(file_path, 'created')
    
    def on_deleted(self, event: FileSystemEvent):
        """Handle file deletion events."""
        if event.is_directory:
            return
        
        if self.should_ignore_file(event.src_path):
            return
        
        file_path = os.path.normpath(event.src_path)
        self.recent_events[file_path] = FileChangeEvent(file_path, 'deleted')
    
    def on_moved(self, event: FileSystemEvent):
        """Handle file move events."""
        if event.is_directory:
            return
        
        if hasattr(event, 'dest_path'):
            # File was moved
            if not self.should_ignore_file(event.dest_path):
                dest_path = os.path.normpath(event.dest_path)
                self.recent_events[dest_path] = FileChangeEvent(dest_path, 'moved')


class FileMonitor:
    """Main file monitoring system with intelligent change detection."""
    
    def __init__(self, config_path: str = "config.json", watch_directory: str = "."):
        self.config = self._load_config(config_path)
        self.watch_directory = os.path.abspath(watch_directory)
        self.observer = Observer()
        self.event_handler = IntelligentFileHandler(self)
        
        # Change tracking
        self.pending_changes: List[FileChangeEvent] = []
        self.change_callbacks: List[Callable] = []
        self.last_batch_time = datetime.now()
        self.batch_interval = self.config.get("system", {}).get("monitoring_interval", 30)
        
        # Thread safety
        self.lock = threading.Lock()
        self.executor = ThreadPoolExecutor(max_workers=2)
        
        # Statistics
        self.stats = {
            "total_events": 0,
            "ignored_events": 0,
            "processed_batches": 0,
            "start_time": datetime.now()
        }
    
    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from JSON file."""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Warning: Config file not found: {config_path}. Using defaults.")
            return self._get_default_config()
        except json.JSONDecodeError as e:
            print(f"Warning: Invalid JSON in config file: {e}. Using defaults.")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict:
        """Get default configuration."""
        return {
            "system": {"monitoring_interval": 30},
            "monitoring": {
                "exclude_directories": [".git", "__pycache__", "node_modules"],
                "file_extensions": [".py", ".js", ".ts", ".html", ".css", ".md"]
            },
            "git": {"ignore_patterns": ["*.log", "*.tmp", ".DS_Store"]}
        }
    
    def add_change_callback(self, callback: Callable[[List[FileChangeEvent]], None]):
        """Add a callback function to be called when changes are detected."""
        self.change_callbacks.append(callback)
    
    def _process_file_change(self, event: FileChangeEvent):
        """Process a single file change event."""
        with self.lock:
            self.pending_changes.append(event)
            self.stats["total_events"] += 1
            
            # Check if we should trigger a batch processing
            time_since_last_batch = (datetime.now() - self.last_batch_time).total_seconds()
            
            if (time_since_last_batch >= self.batch_interval or 
                len(self.pending_changes) >= 10):  # Process when enough changes or time elapsed
                self._trigger_batch_processing()
    
    def _trigger_batch_processing(self):
        """Trigger batch processing of pending changes."""
        if not self.pending_changes:
            return
        
        changes_to_process = self.pending_changes.copy()
        self.pending_changes.clear()
        self.last_batch_time = datetime.now()
        self.stats["processed_batches"] += 1
        
        # Process in background thread
        self.executor.submit(self._process_change_batch, changes_to_process)
    
    def _process_change_batch(self, changes: List[FileChangeEvent]):
        """Process a batch of file changes."""
        if not changes:
            return
        
        # Deduplicate changes by file path (keep latest)
        unique_changes = {}
        for change in changes:
            unique_changes[change.file_path] = change
        
        final_changes = list(unique_changes.values())
        
        # Sort by timestamp
        final_changes.sort(key=lambda x: x.timestamp)
        
        # Call all registered callbacks
        for callback in self.change_callbacks:
            try:
                callback(final_changes)
            except Exception as e:
                print(f"Error in change callback: {e}")
    
    def start_monitoring(self):
        """Start the file monitoring system."""
        print(f"Starting file monitor for directory: {self.watch_directory}")
        
        # Schedule the observer
        self.observer.schedule(self.event_handler, self.watch_directory, recursive=True)
        self.observer.start()
        
        # Start background batch processing timer
        self._start_batch_timer()
        
        print("File monitoring started successfully")
    
    def stop_monitoring(self):
        """Stop the file monitoring system."""
        print("Stopping file monitor...")
        
        self.observer.stop()
        self.observer.join()
        
        # Process any remaining changes
        with self.lock:
            if self.pending_changes:
                self._trigger_batch_processing()
        
        # Shutdown executor
        self.executor.shutdown(wait=True)
        
        print("File monitoring stopped")
    
    def _start_batch_timer(self):
        """Start background timer for batch processing."""
        def timer_callback():
            while self.observer.is_alive():
                time.sleep(self.batch_interval)
                with self.lock:
                    if self.pending_changes:
                        self._trigger_batch_processing()
        
        timer_thread = threading.Thread(target=timer_callback, daemon=True)
        timer_thread.start()
    
    def get_stats(self) -> Dict:
        """Get monitoring statistics."""
        current_time = datetime.now()
        uptime = (current_time - self.stats["start_time"]).total_seconds()
        
        return {
            **self.stats,
            "uptime_seconds": uptime,
            "uptime_formatted": str(timedelta(seconds=int(uptime))),
            "pending_changes": len(self.pending_changes),
            "active_callbacks": len(self.change_callbacks)
        }
    
    def force_process_changes(self):
        """Force processing of any pending changes."""
        with self.lock:
            if self.pending_changes:
                self._trigger_batch_processing()


def main():
    """Main function for testing the file monitor."""
    def on_changes(changes: List[FileChangeEvent]):
        print(f"\n📁 Detected {len(changes)} file changes:")
        for change in changes:
            print(f"  {change.event_type.upper()}: {change.file_path}")
            print(f"    Time: {change.timestamp.strftime('%H:%M:%S')}")
            print(f"    Size: {change.file_size} bytes")
    
    monitor = FileMonitor(watch_directory=".")
    monitor.add_change_callback(on_changes)
    
    try:
        monitor.start_monitoring()
        print("File monitor is running. Press Ctrl+C to stop.")
        
        while True:
            time.sleep(10)
            stats = monitor.get_stats()
            print(f"\n📊 Stats - Events: {stats['total_events']}, "
                  f"Batches: {stats['processed_batches']}, "
                  f"Uptime: {stats['uptime_formatted']}")
    
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        monitor.stop_monitoring()


if __name__ == "__main__":
    main()
