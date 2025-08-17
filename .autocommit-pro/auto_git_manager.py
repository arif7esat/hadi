"""
Automatic Git Management System
Intelligent auto-commit and push system with AI-powered commit messages and smart batching.
"""

import os
import sys
import json
import time
import threading
from typing import Dict, List, Optional, Set
from datetime import datetime, timedelta
from pathlib import Path
import subprocess
import git
from git import Repo, InvalidGitRepositoryError
import schedule

# Import our custom modules
from file_monitor import FileMonitor, FileChangeEvent
from ai_commit_generator import AICommitGenerator
from logger import logger


class GitOperationResult:
    """Result of a git operation with metadata."""
    
    def __init__(self, success: bool, message: str, details: Dict = None):
        self.success = success
        self.message = message
        self.details = details or {}
        self.timestamp = datetime.now()
    
    def __repr__(self):
        status = "SUCCESS" if self.success else "FAILED"
        return f"GitResult[{status}]: {self.message}"


class GitRepository:
    """Enhanced Git repository wrapper with advanced operations."""
    
    def __init__(self, repo_path: str = "."):
        self.repo_path = os.path.abspath(repo_path)
        self.repo = None
        self._initialize_repo()
    
    def _initialize_repo(self):
        """Initialize git repository connection."""
        try:
            self.repo = Repo(self.repo_path)
            logger.info(f"Connected to git repository: {self.repo_path}")
            
            # Validate repository state
            if self.repo.bare:
                raise ValueError("Cannot work with bare repository")
                
        except InvalidGitRepositoryError:
            logger.error(f"No git repository found at: {self.repo_path}")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize git repository", exception=e)
            raise
    
    def get_status(self) -> Dict:
        """Get detailed repository status."""
        try:
            # Check if repository has any commits
            if not self.repo.heads:
                # No commits yet
                return {
                    'branch': 'main',
                    'is_dirty': self.repo.is_dirty(),
                    'untracked_files': self.repo.untracked_files,
                    'modified_files': [],
                    'staged_files': [],
                    'ahead_behind': {'ahead': 0, 'behind': 0},
                    'last_commit': None
                }
            
            status = {
                'branch': self.repo.active_branch.name,
                'is_dirty': self.repo.is_dirty(),
                'untracked_files': self.repo.untracked_files,
                'modified_files': [item.a_path for item in self.repo.index.diff(None)],
                'staged_files': [item.a_path for item in self.repo.index.diff("HEAD")],
                'ahead_behind': self._get_ahead_behind_count(),
                'last_commit': {
                    'hash': self.repo.head.commit.hexsha[:8],
                    'message': self.repo.head.commit.message.strip(),
                    'author': str(self.repo.head.commit.author),
                    'date': self.repo.head.commit.committed_datetime.isoformat()
                }
            }
            return status
        except Exception as e:
            logger.error(f"Failed to get repository status", exception=e)
            return {}
    
    def _get_ahead_behind_count(self) -> Dict:
        """Get how many commits ahead/behind the remote branch."""
        try:
            origin = self.repo.remote('origin')
            origin.fetch()
            
            local_branch = self.repo.active_branch
            remote_branch = origin.refs[local_branch.name]
            
            ahead_count = len(list(self.repo.iter_commits(f'{remote_branch}..{local_branch}')))
            behind_count = len(list(self.repo.iter_commits(f'{local_branch}..{remote_branch}')))
            
            return {'ahead': ahead_count, 'behind': behind_count}
        except Exception:
            return {'ahead': 0, 'behind': 0}
    
    def add_files(self, files: List[str] = None) -> GitOperationResult:
        """Add files to staging area."""
        try:
            if files is None:
                # Add all modified and untracked files
                self.repo.git.add(A=True)
                logger.info("Added all files to staging area")
                return GitOperationResult(True, "All files added to staging")
            else:
                # Add specific files
                for file in files:
                    if os.path.exists(os.path.join(self.repo_path, file)):
                        self.repo.index.add([file])
                logger.info(f"Added {len(files)} files to staging area")
                return GitOperationResult(True, f"Added {len(files)} files to staging")
                
        except Exception as e:
            logger.error(f"Failed to add files to staging", exception=e)
            return GitOperationResult(False, f"Failed to add files: {str(e)}")
    
    def commit(self, message: str, author: str = None) -> GitOperationResult:
        """Create a commit with the given message."""
        try:
            if not self.repo.is_dirty(untracked_files=True):
                return GitOperationResult(False, "No changes to commit")
            
            # Ensure files are staged
            if not self.repo.index.diff("HEAD"):
                add_result = self.add_files()
                if not add_result.success:
                    return add_result
            
            # Create commit
            commit_kwargs = {'message': message}
            if author:
                commit_kwargs['author'] = author
            
            commit = self.repo.index.commit(**commit_kwargs)
            
            logger.success(f"Created commit: {commit.hexsha[:8]} - {message[:50]}...")
            return GitOperationResult(
                True, 
                f"Commit created: {commit.hexsha[:8]}", 
                {'commit_hash': commit.hexsha, 'message': message}
            )
            
        except Exception as e:
            logger.error(f"Failed to create commit", exception=e)
            return GitOperationResult(False, f"Commit failed: {str(e)}")
    
    def push(self, remote: str = 'origin', branch: str = None) -> GitOperationResult:
        """Push commits to remote repository."""
        try:
            if branch is None:
                branch = self.repo.active_branch.name
            
            # Check if there are commits to push
            status = self.get_status()
            if status.get('ahead_behind', {}).get('ahead', 0) == 0:
                return GitOperationResult(False, "No commits to push")
            
            # Perform push
            origin = self.repo.remote(remote)
            push_info = origin.push(branch)
            
            # Check push result
            if push_info and push_info[0].flags == 256:  # UP_TO_DATE
                logger.info("Repository is up to date")
                return GitOperationResult(True, "Repository up to date")
            elif push_info and push_info[0].flags == 0:  # OK
                logger.success(f"Successfully pushed to {remote}/{branch}")
                return GitOperationResult(
                    True, 
                    f"Pushed to {remote}/{branch}", 
                    {'remote': remote, 'branch': branch}
                )
            else:
                logger.warning(f"Push completed with warnings: {push_info}")
                return GitOperationResult(True, "Push completed with warnings")
                
        except Exception as e:
            logger.error(f"Failed to push to remote", exception=e)
            return GitOperationResult(False, f"Push failed: {str(e)}")
    
    def pull(self, remote: str = 'origin', branch: str = None) -> GitOperationResult:
        """Pull changes from remote repository."""
        try:
            if branch is None:
                branch = self.repo.active_branch.name
            
            origin = self.repo.remote(remote)
            pull_info = origin.pull(branch)
            
            logger.info(f"Pulled from {remote}/{branch}")
            return GitOperationResult(
                True, 
                f"Pulled from {remote}/{branch}", 
                {'pull_info': str(pull_info)}
            )
            
        except Exception as e:
            logger.error(f"Failed to pull from remote", exception=e)
            return GitOperationResult(False, f"Pull failed: {str(e)}")


class AutoGitManager:
    """Main auto-commit and push management system."""
    
    def __init__(self, config_path: str = "config.json", watch_directory: str = "."):
        self.config = self._load_config(config_path)
        # Read watch directory from config, fallback to parameter
        config_watch_dir = self.config.get("monitoring", {}).get("directory", watch_directory)
        self.watch_directory = os.path.abspath(config_watch_dir)
        
        # Initialize components
        git_repo_path = self.config.get("git", {}).get("repository_path", watch_directory)
        self.git_repo = GitRepository(git_repo_path)
        # Use monitoring directory from config for file monitoring
        monitoring_dir = self.config.get("monitoring", {}).get("directory", watch_directory)
        self.file_monitor = FileMonitor(config_path, monitoring_dir)
        # Use the same config path for AI generator
        self.ai_generator = AICommitGenerator(config_path)
        
        # State management
        self.pending_changes: Set[str] = set()
        self.last_commit_time = datetime.now()
        self.last_push_time = datetime.now()
        
        # Configuration
        self.auto_push_enabled = self.config.get("git", {}).get("auto_push_enabled", True)
        self.max_commit_frequency = self.config.get("system", {}).get("max_commit_frequency", 300)  # 5 minutes
        self.monitoring_interval = self.config.get("system", {}).get("monitoring_interval", 30)    # 30 seconds
        
        # Statistics
        self.stats = {
            'total_commits': 0,
            'total_pushes': 0,
            'auto_commits': 0,
            'manual_commits': 0,
            'failed_operations': 0,
            'start_time': datetime.now()
        }
        
        # Setup
        self._setup_monitoring()
        self._setup_scheduler()
        
        logger.info(f"AutoGitManager initialized for: {self.watch_directory}")
    
    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from file."""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            logger.warning(f"Could not load config from {config_path}, using defaults")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict:
        """Get default configuration."""
        return {
            "system": {
                "monitoring_interval": 30,
                "max_commit_frequency": 300,
                "auto_push_enabled": True
            },
            "git": {
                "auto_add_all": True,
                "default_branch": "main",
                "remote_name": "origin"
            }
        }
    
    def _setup_monitoring(self):
        """Setup file monitoring with change callbacks."""
        self.file_monitor.add_change_callback(self._on_file_changes)
        logger.info("File monitoring callback registered")
    
    def _setup_scheduler(self):
        """Setup scheduled tasks for periodic operations."""
        # Schedule periodic commit checks
        schedule.every(self.monitoring_interval).seconds.do(self._periodic_commit_check)
        
        # Schedule periodic push (if enabled)
        if self.auto_push_enabled:
            schedule.every(5).minutes.do(self._periodic_push_check)
        
        # Schedule status reports
        schedule.every(1).hours.do(self._periodic_status_report)
        
        logger.info("Scheduled tasks configured")
    
    def _on_file_changes(self, changes: List[FileChangeEvent]):
        """Handle file change events from the monitor."""
        if not changes:
            return
        
        logger.debug(f"Processing {len(changes)} file changes")
        
        # Add changed files to pending set
        for change in changes:
            if change.event_type != 'deleted':  # Don't track deleted files
                self.pending_changes.add(change.file_path)
        
        # Check if we should auto-commit
        time_since_last_commit = (datetime.now() - self.last_commit_time).total_seconds()
        
        if (len(self.pending_changes) >= 5 or  # Many files changed
            time_since_last_commit >= self.max_commit_frequency):  # Time threshold reached
            
            self._auto_commit()
    
    def _auto_commit(self):
        """Perform automatic commit of pending changes."""
        if not self.pending_changes:
            logger.debug("No pending changes for auto-commit")
            return
        
        try:
            logger.info(f"Starting auto-commit for {len(self.pending_changes)} changed files")
            
            # Generate AI commit message
            commit_message = self.ai_generator.generate_commit_message()
            
            # Perform commit
            result = self.git_repo.commit(commit_message)
            
            if result.success:
                self.stats['total_commits'] += 1
                self.stats['auto_commits'] += 1
                self.last_commit_time = datetime.now()
                self.pending_changes.clear()
                
                logger.success(f"Auto-commit successful: {result.message}")
                
                # Auto-push if enabled
                if self.auto_push_enabled:
                    self._auto_push()
            else:
                self.stats['failed_operations'] += 1
                logger.error(f"Auto-commit failed: {result.message}")
                
        except Exception as e:
            self.stats['failed_operations'] += 1
            logger.error(f"Auto-commit error", exception=e)
    
    def _auto_push(self):
        """Perform automatic push to remote repository."""
        try:
            logger.info("Starting auto-push to remote repository")
            
            result = self.git_repo.push()
            
            if result.success:
                self.stats['total_pushes'] += 1
                self.last_push_time = datetime.now()
                logger.success(f"Auto-push successful: {result.message}")
            else:
                self.stats['failed_operations'] += 1
                logger.warning(f"Auto-push failed: {result.message}")
                
        except Exception as e:
            self.stats['failed_operations'] += 1
            logger.error(f"Auto-push error", exception=e)
    
    def _periodic_commit_check(self):
        """Periodic check for uncommitted changes."""
        try:
            status = self.git_repo.get_status()
            
            if status.get('is_dirty', False):
                time_since_last_commit = (datetime.now() - self.last_commit_time).total_seconds()
                
                if time_since_last_commit >= self.max_commit_frequency:
                    logger.info("Periodic commit check: triggering auto-commit")
                    self._auto_commit()
            
        except Exception as e:
            logger.error(f"Periodic commit check error", exception=e)
    
    def _periodic_push_check(self):
        """Periodic check for unpushed commits."""
        if not self.auto_push_enabled:
            return
        
        try:
            status = self.git_repo.get_status()
            ahead_count = status.get('ahead_behind', {}).get('ahead', 0)
            
            if ahead_count > 0:
                time_since_last_push = (datetime.now() - self.last_push_time).total_seconds()
                
                if time_since_last_push >= 300:  # 5 minutes
                    logger.info("Periodic push check: triggering auto-push")
                    self._auto_push()
            
        except Exception as e:
            logger.error(f"Periodic push check error", exception=e)
    
    def _periodic_status_report(self):
        """Generate periodic status report."""
        try:
            uptime = datetime.now() - self.stats['start_time']
            git_status = self.git_repo.get_status()
            monitor_stats = self.file_monitor.get_stats()
            
            logger.info(f"📊 Hourly Status Report:")
            logger.info(f"  Uptime: {uptime}")
            logger.info(f"  Total commits: {self.stats['total_commits']}")
            logger.info(f"  Total pushes: {self.stats['total_pushes']}")
            logger.info(f"  Failed operations: {self.stats['failed_operations']}")
            logger.info(f"  Current branch: {git_status.get('branch', 'unknown')}")
            logger.info(f"  Ahead/behind: {git_status.get('ahead_behind', {})}")
            logger.info(f"  Monitored events: {monitor_stats.get('total_events', 0)}")
            
        except Exception as e:
            logger.error(f"Status report error", exception=e)
    
    # Public methods
    def start(self):
        """Start the auto-git management system."""
        try:
            logger.info("🚀 Starting AutoGitManager...")
            
            # Initial repository status
            status = self.git_repo.get_status()
            logger.info(f"Repository status: Branch={status.get('branch')}, Dirty={status.get('is_dirty')}")
            
            # Start file monitoring
            self.file_monitor.start_monitoring()
            
            # Start scheduler thread
            self._start_scheduler_thread()
            
            logger.success("AutoGitManager started successfully!")
            
        except Exception as e:
            logger.critical(f"Failed to start AutoGitManager", exception=e)
            raise
    
    def stop(self):
        """Stop the auto-git management system."""
        try:
            logger.info("🛑 Stopping AutoGitManager...")
            
            # Commit any pending changes
            if self.pending_changes:
                logger.info("Committing pending changes before shutdown...")
                self._auto_commit()
            
            # Stop file monitoring
            self.file_monitor.stop_monitoring()
            
            # Final push if enabled
            if self.auto_push_enabled:
                logger.info("Final push before shutdown...")
                self._auto_push()
            
            logger.success("AutoGitManager stopped successfully!")
            
        except Exception as e:
            logger.error(f"Error during shutdown", exception=e)
    
    def _start_scheduler_thread(self):
        """Start background thread for scheduled tasks."""
        def scheduler_loop():
            while True:
                try:
                    schedule.run_pending()
                    time.sleep(1)
                except Exception as e:
                    logger.error(f"Scheduler error", exception=e)
                    time.sleep(5)  # Wait longer on error
        
        scheduler_thread = threading.Thread(target=scheduler_loop, daemon=True)
        scheduler_thread.start()
        logger.info("Scheduler thread started")
    
    def manual_commit(self, message: str = None) -> GitOperationResult:
        """Manually trigger a commit with optional custom message."""
        try:
            if message is None:
                message = self.ai_generator.generate_commit_message()
            
            result = self.git_repo.commit(message)
            
            if result.success:
                self.stats['total_commits'] += 1
                self.stats['manual_commits'] += 1
                self.last_commit_time = datetime.now()
                self.pending_changes.clear()
            
            return result
            
        except Exception as e:
            logger.error(f"Manual commit error", exception=e)
            return GitOperationResult(False, f"Manual commit failed: {str(e)}")
    
    def manual_push(self) -> GitOperationResult:
        """Manually trigger a push."""
        try:
            result = self.git_repo.push()
            
            if result.success:
                self.stats['total_pushes'] += 1
                self.last_push_time = datetime.now()
            
            return result
            
        except Exception as e:
            logger.error(f"Manual push error", exception=e)
            return GitOperationResult(False, f"Manual push failed: {str(e)}")
    
    def get_status(self) -> Dict:
        """Get comprehensive system status."""
        return {
            'git_status': self.git_repo.get_status(),
            'monitor_stats': self.file_monitor.get_stats(),
            'pending_changes': len(self.pending_changes),
            'auto_git_stats': self.stats.copy(),
            'last_commit_time': self.last_commit_time.isoformat(),
            'last_push_time': self.last_push_time.isoformat(),
            'auto_push_enabled': self.auto_push_enabled
        }


def main():
    """Main function for testing the auto-git manager."""
    try:
        manager = AutoGitManager()
        
        # Start the system
        manager.start()
        
        print("🚀 AutoGitManager is running!")
        print("📁 Monitoring file changes and auto-committing...")
        print("Press Ctrl+C to stop")
        
        # Keep running
        while True:
            time.sleep(10)
            status = manager.get_status()
            print(f"\n📊 Status: Pending={status['pending_changes']}, "
                  f"Commits={status['auto_git_stats']['total_commits']}, "
                  f"Pushes={status['auto_git_stats']['total_pushes']}")
    
    except KeyboardInterrupt:
        print("\n🛑 Shutting down...")
    except Exception as e:
        logger.critical(f"Fatal error in main", exception=e)
    finally:
        if 'manager' in locals():
            manager.stop()


if __name__ == "__main__":
    main()
