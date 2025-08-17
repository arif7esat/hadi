#!/usr/bin/env python3
"""
AutoCommit Pro - Intelligent Auto-Commit and Push System
Main launcher script with CLI interface and advanced features.

Created for protecting your code against system crashes and ensuring
continuous backup to remote repositories with AI-generated commit messages.
"""

import os
import sys
import json
import time
import signal
import argparse
import subprocess
from typing import Dict, Optional
from pathlib import Path
import threading
from datetime import datetime

# Rich console for beautiful output
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt, Confirm
from rich import box
from rich.layout import Layout
from rich.live import Live

# Import our modules
from auto_git_manager import AutoGitManager
from ai_commit_generator import AICommitGenerator
from file_monitor import FileMonitor
from logger import logger


class AutoCommitPro:
    """Main application class for AutoCommit Pro."""
    
    def __init__(self):
        self.console = Console()
        self.manager: Optional[AutoGitManager] = None
        self.running = False
        self.config_path = "config.json"
        # Read watch directory from config, fallback to current directory
        config = self._load_config()
        self.watch_directory = config.get("monitoring", {}).get("directory", ".")
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        self.console.print("\n🛑 [yellow]Shutdown signal received...[/yellow]")
        self.stop()
        sys.exit(0)
    
    def print_banner(self):
        """Print application banner."""
        banner = """
[bold blue]╔═══════════════════════════════════════════════════════════════╗
║                      🚀 AutoCommit Pro                        ║
║           Intelligent Auto-Commit & Push System               ║
║                                                              ║
║  • AI-Powered Commit Messages                                ║
║  • Real-time File Monitoring                                 ║
║  • Automatic Git Push                                        ║
║  • Advanced Error Handling                                   ║
║  • Performance Tracking                                      ║
╚═══════════════════════════════════════════════════════════════╝[/bold blue]
        """
        self.console.print(banner)
    
    def check_prerequisites(self) -> bool:
        """Check if all prerequisites are met and auto-install if needed."""
        errors = []
        
        # Check if we're in a git repository
        if not os.path.exists(".git"):
            self.console.print("🔧 [yellow]Git repository not found. Initializing...[/yellow]")
            try:
                subprocess.run(["git", "init"], check=True)
                self.console.print("✅ [green]Git repository initialized![/green]")
            except Exception as e:
                errors.append(f"❌ Failed to initialize git: {e}")
        
        # Check if config file exists
        if not os.path.exists(self.config_path):
            self.console.print("⚙️  [yellow]Config file not found. Creating default config...[/yellow]")
            self._create_default_config()
        
        # Check and auto-install Python dependencies
        missing_deps = []
        try:
            import openai
        except ImportError:
            missing_deps.append("openai")
        
        try:
            import anthropic
        except ImportError:
            missing_deps.append("anthropic")
            
        try:
            import watchdog
        except ImportError:
            missing_deps.append("watchdog")
            
        try:
            import git
        except ImportError:
            missing_deps.append("gitpython")
            
        try:
            import rich
        except ImportError:
            missing_deps.append("rich")
            
        try:
            import colorama
        except ImportError:
            missing_deps.append("colorama")
        
        # Auto-install missing dependencies
        if missing_deps:
            self.console.print(f"📦 [yellow]Installing missing dependencies: {', '.join(missing_deps)}[/yellow]")
            try:
                for dep in missing_deps:
                    if dep == "gitpython":
                        subprocess.run([sys.executable, "-m", "pip", "install", "gitpython"], check=True)
                    else:
                        subprocess.run([sys.executable, "-m", "pip", "install", dep], check=True)
                self.console.print("✅ [green]Dependencies installed successfully![/green]")
            except Exception as e:
                errors.append(f"❌ Failed to install dependencies: {e}")
        
        # Check git configuration
        try:
            result = subprocess.run(["git", "config", "user.name"], capture_output=True, text=True)
            if not result.stdout.strip():
                self.console.print("👤 [yellow]Git user.name not configured. Please set it:[/yellow]")
                self.console.print("   git config user.name 'Your Name'")
                errors.append("❌ Git user.name not configured")
            
            result = subprocess.run(["git", "config", "user.email"], capture_output=True, text=True)
            if not result.stdout.strip():
                self.console.print("📧 [yellow]Git user.email not configured. Please set it:[/yellow]")
                self.console.print("   git config user.email 'your.email@example.com'")
                errors.append("❌ Git user.email not configured")
        except Exception:
            errors.append("❌ Git not available")
        
        if errors:
            self.console.print("[bold red]Setup issues found:[/bold red]")
            for error in errors:
                self.console.print(f"  {error}")
            return False
        
        self.console.print("✅ [green]All prerequisites met![/green]")
        return True
    
    def _create_default_config(self):
        """Create default configuration file."""
        default_config = {
            "system": {
                "monitoring_interval": 30,
                "max_commit_frequency": 300,
                "auto_push_enabled": True,
                "debug_mode": False
            },
            "git": {
                "default_branch": "main",
                "remote_name": "origin",
                "auto_add_all": True,
                "ignore_patterns": [
                    "*.log", "*.tmp", "__pycache__/", ".DS_Store",
                    "node_modules/", ".vscode/", ".idea/"
                ]
            },
            "ai_commit": {
                "enabled": True,
                "provider": "openai",
                "model": "gpt-4",
                "api_key": "",
                "max_tokens": 200,
                "temperature": 0.3,
                "languages": ["tr", "en"],
                "preferred_language": "tr"
            },
            "notifications": {
                "enabled": True,
                "methods": ["console", "system"]
            },
            "monitoring": {
                "exclude_directories": [
                    ".git", "__pycache__", "node_modules", ".vscode", ".idea", "venv", "env"
                ],
                "file_extensions": [
                    ".py", ".js", ".ts", ".jsx", ".tsx", ".html", ".css", ".scss",
                    ".md", ".txt", ".json", ".xml", ".yaml", ".yml", ".sql",
                    ".php", ".java", ".cpp", ".c", ".h", ".swift", ".kt", ".go", ".rs", ".rb"
                ]
            },
            "logging": {
                "level": "INFO",
                "console_enabled": True,
                "file_enabled": True,
                "log_directory": "./logs"
            }
        }
        
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, indent=2, ensure_ascii=False)
        
        self.console.print(f"✅ [green]Created default config: {self.config_path}[/green]")
    
    def setup_ai_api_key(self):
        """Interactive setup for AI API key with zero-friction experience."""
        config = self._load_config()
        
        # Check if API key is already set
        if config.get("ai_commit", {}).get("api_key"):
            return  # Already configured
        
        # Check environment variable first
        env_api_key = os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
        if env_api_key:
            config["ai_commit"]["api_key"] = env_api_key
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            self.console.print("✅ [green]AI API key found in environment variables![/green]")
            return
        
        # Super easy setup wizard
        self.console.print("\n🤖 [bold cyan]AI Setup - Just 2 Clicks![/bold cyan]")
        self.console.print("📱 [yellow]1. Click this link:[/yellow] https://aistudio.google.com/app/apikey")
        self.console.print("📋 [yellow]2. Copy your API key and paste below[/yellow]")
        self.console.print("💡 [green]It's FREE and takes 30 seconds![/green]")
        
        # Auto-detect provider preference
        provider = "gemini"  # Default to free option
        
        self.console.print(f"\n🎯 [blue]Using {provider.upper()} (Free tier available)[/blue]")
        
        # Get API key with helpful hints
        api_key = Prompt.ask(
            "📋 Paste your API key here",
            password=True,
            default=""
        )
        
        if api_key and len(api_key) > 10:  # Basic validation
            config["ai_commit"]["provider"] = provider
            config["ai_commit"]["api_key"] = api_key
            
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            self.console.print("🎉 [green]Perfect! AI is now ready to generate smart commit messages![/green]")
            
            # Also save to environment for this session
            os.environ[f"{provider.upper()}_API_KEY"] = api_key
            
        else:
            self.console.print("⚠️  [yellow]No API key provided. Using basic commit messages.[/yellow]")
            self.console.print("💡 [blue]You can always add it later with: python main.py --setup[/blue]")
    
    def _load_config(self) -> Dict:
        """Load configuration from file."""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}
    
    def interactive_setup(self):
        """Interactive setup wizard."""
        self.console.print("\n🛠️  [bold cyan]Interactive Setup[/bold cyan]")
        
        # Directory selection
        current_dir = os.getcwd()
        use_current = Confirm.ask(f"Monitor current directory? ({current_dir})", default=True)
        
        if not use_current:
            self.watch_directory = Prompt.ask("Enter directory to monitor", default=".")
        
        # Auto-push setting
        config = self._load_config()
        auto_push = Confirm.ask("Enable automatic push to remote?", default=True)
        config.setdefault("system", {})["auto_push_enabled"] = auto_push
        
        # Commit frequency
        frequency = Prompt.ask(
            "Maximum time between commits (seconds)",
            default="300"
        )
        try:
            config["system"]["max_commit_frequency"] = int(frequency)
        except ValueError:
            config["system"]["max_commit_frequency"] = 300
        
        # Save configuration
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        self.console.print("✅ [green]Setup completed![/green]")
    
    def start(self, interactive: bool = False):
        """Start the AutoCommit Pro system."""
        try:
            if interactive:
                self.interactive_setup()
                self.setup_ai_api_key()
            
            # Initialize manager
            self.console.print("\n🚀 [bold blue]Starting AutoCommit Pro...[/bold blue]")
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=self.console
            ) as progress:
                task = progress.add_task("Initializing system...", total=None)
                
                self.manager = AutoGitManager(self.config_path, self.watch_directory)
                progress.update(task, description="Starting file monitoring...")
                
                self.manager.start()
                progress.update(task, description="System ready!")
            
            self.running = True
            
            # Show initial status
            self._show_status()
            
            # Start monitoring loop
            self._run_monitoring_loop()
            
        except Exception as e:
            logger.critical(f"Failed to start AutoCommit Pro", exception=e)
            self.console.print(f"❌ [red]Failed to start: {e}[/red]")
            return False
        
        return True
    
    def stop(self):
        """Stop the AutoCommit Pro system."""
        if not self.running:
            return
        
        self.running = False
        
        if self.manager:
            self.console.print("🛑 [yellow]Stopping AutoCommit Pro...[/yellow]")
            self.manager.stop()
            self.console.print("✅ [green]Stopped successfully![/green]")
    
    def _show_status(self):
        """Show current system status."""
        if not self.manager:
            return
        
        status = self.manager.get_status()
        
        # Create status table
        table = Table(title="🔍 System Status", box=box.ROUNDED)
        table.add_column("Component", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Details", style="white")
        
        # Git status
        git_status = status.get('git_status', {})
        table.add_row(
            "Git Repository",
            "✅ Connected",
            f"Branch: {git_status.get('branch', 'unknown')}"
        )
        
        # File monitoring
        monitor_stats = status.get('monitor_stats', {})
        table.add_row(
            "File Monitor",
            "🔍 Active",
            f"Events: {monitor_stats.get('total_events', 0)}"
        )
        
        # Auto-commit
        auto_stats = status.get('auto_git_stats', {})
        table.add_row(
            "Auto-Commit",
            "🤖 Enabled",
            f"Commits: {auto_stats.get('total_commits', 0)}"
        )
        
        # Auto-push
        push_status = "✅ Enabled" if status.get('auto_push_enabled') else "❌ Disabled"
        table.add_row(
            "Auto-Push",
            push_status,
            f"Pushes: {auto_stats.get('total_pushes', 0)}"
        )
        
        self.console.print(table)
    
    def _run_monitoring_loop(self):
        """Main monitoring loop with live updates."""
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main"),
            Layout(name="footer", size=3)
        )
        
        def make_header():
            return Panel(
                "🚀 AutoCommit Pro - Monitoring Active",
                style="bold blue"
            )
        
        def make_footer():
            return Panel(
                "Press [bold]Ctrl+C[/bold] to stop | Press [bold]s[/bold] for status | Press [bold]h[/bold] for help",
                style="dim"
            )
        
        def make_main():
            if not self.manager:
                return Panel("System not initialized", style="red")
            
            status = self.manager.get_status()
            auto_stats = status.get('auto_git_stats', {})
            git_status = status.get('git_status', {})
            
            content = f"""
[bold cyan]📊 Live Statistics[/bold cyan]
  Total Commits: {auto_stats.get('total_commits', 0)}
  Total Pushes: {auto_stats.get('total_pushes', 0)}
  Pending Changes: {status.get('pending_changes', 0)}
  
[bold cyan]📁 Repository Status[/bold cyan]
  Branch: {git_status.get('branch', 'unknown')}
  Dirty: {git_status.get('is_dirty', False)}
  Ahead/Behind: {git_status.get('ahead_behind', {})}
  
[bold cyan]⏰ Last Activity[/bold cyan]
  Last Commit: {status.get('last_commit_time', 'Never')[:19]}
  Last Push: {status.get('last_push_time', 'Never')[:19]}
            """
            return Panel(content.strip(), title="System Status", border_style="green")
        
        with Live(layout, refresh_per_second=1, console=self.console) as live:
            layout["header"].update(make_header())
            layout["footer"].update(make_footer())
            
            while self.running:
                layout["main"].update(make_main())
                time.sleep(2)
    
    def manual_commit(self, message: str = None):
        """Trigger manual commit."""
        if not self.manager:
            self.console.print("❌ [red]System not initialized[/red]")
            return
        
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
            task = progress.add_task("Creating commit...", total=None)
            result = self.manager.manual_commit(message)
            
            if result.success:
                self.console.print(f"✅ [green]{result.message}[/green]")
            else:
                self.console.print(f"❌ [red]{result.message}[/red]")
    
    def manual_push(self):
        """Trigger manual push."""
        if not self.manager:
            self.console.print("❌ [red]System not initialized[/red]")
            return
        
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
            task = progress.add_task("Pushing to remote...", total=None)
            result = self.manager.manual_push()
            
            if result.success:
                self.console.print(f"✅ [green]{result.message}[/green]")
            else:
                self.console.print(f"❌ [red]{result.message}[/red]")


def create_cli_parser():
    """Create command line argument parser."""
    parser = argparse.ArgumentParser(
        description="AutoCommit Pro - Intelligent Auto-Commit and Push System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                    # Start with interactive setup
  python main.py --start            # Start immediately
  python main.py --config custom.json --directory /path/to/repo
  python main.py --commit "Custom commit message"
  python main.py --push
  python main.py --status
        """
    )
    
    parser.add_argument("--start", action="store_true", help="Start monitoring immediately")
    parser.add_argument("--interactive", action="store_true", help="Run interactive setup")
    parser.add_argument("--config", default="config.json", help="Configuration file path")
    parser.add_argument("--directory", default=".", help="Directory to monitor")
    parser.add_argument("--commit", metavar="MESSAGE", help="Make manual commit with message")
    parser.add_argument("--push", action="store_true", help="Make manual push")
    parser.add_argument("--status", action="store_true", help="Show system status")
    parser.add_argument("--setup", action="store_true", help="Run setup wizard")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")
    
    return parser


def main():
    """Main entry point."""
    parser = create_cli_parser()
    args = parser.parse_args()
    
    app = AutoCommitPro()
    app.config_path = args.config
    app.watch_directory = args.directory
    
    # Print banner
    app.print_banner()
    
    # Handle different commands
    if args.status:
        if app.check_prerequisites():
            app.manager = AutoGitManager(app.config_path, app.watch_directory)
            app._show_status()
        return
    
    if args.commit:
        if app.check_prerequisites():
            app.manager = AutoGitManager(app.config_path, app.watch_directory)
            app.manual_commit(args.commit)
        return
    
    if args.push:
        if app.check_prerequisites():
            app.manager = AutoGitManager(app.config_path, app.watch_directory)
            app.manual_push()
        return
    
    if args.setup or args.interactive:
        if app.check_prerequisites():
            app.interactive_setup()
            app.setup_ai_api_key()
        return
    
    # Main monitoring mode
    if not app.check_prerequisites():
        return
    
    # Start the system
    try:
        success = app.start(interactive=(not args.start))
        if not success:
            sys.exit(1)
    except KeyboardInterrupt:
        app.console.print("\n🛑 [yellow]Interrupted by user[/yellow]")
    except Exception as e:
        app.console.print(f"❌ [red]Fatal error: {e}[/red]")
        sys.exit(1)
    finally:
        app.stop()


if __name__ == "__main__":
    main()
