#!/usr/bin/env python3
"""
cmd-sniper - Linux command line audit and analysis tool.

Captures all command executions on a Linux system and provides
detailed analysis and reporting capabilities.
"""
import sys
import os
import signal
import time
from datetime import datetime, timedelta
from pathlib import Path

import click

# Add module path for imports
# Handle multiple installation scenarios:
# 1. Direct run: cli.py in src/ directory
# 2. Installed: cli.py in /var/lib/cmd-sniper/cmd-sniper/cli.py (with src/ subdirectory)
# 3. Development: cli.py in project root with src/ subdirectory
cli_file = Path(__file__).resolve()
cli_dir = cli_file.parent

# Possible module locations
module_paths = [
    cli_dir,                      # cli.py is in src/ with modules alongside
    cli_dir / "src",              # cli.py is in project root, modules in src/
    cli_dir.parent,               # cli.py is in src/, modules in parent
    cli_dir / "lib" / "cmd-sniper",  # Installed to lib/cmd-sniper
    "/var/lib/cmd-sniper/cmd-sniper",  # Default install location
]

for path in module_paths:
    if str(path) not in sys.path and path.exists():
        sys.path.insert(0, str(path))

from storage import Database, Config, load_config
from capture import AuditdCapture, EbpfCapture, CaptureNotAvailableError
from analyzer import CommandStats
from reporter import HTMLReporter, JSONReporter


def get_db(config_path: str = None) -> Database:
    """Get database instance with config."""
    config = load_config(config_path)
    config.ensure_directories()
    return Database(config.storage.db_path)


def check_root():
    """Check if running as root."""
    if os.geteuid() != 0:
        click.echo("Error: This command requires root privileges.", err=True)
        click.echo("Please run with sudo.", err=True)
        sys.exit(1)


@click.group()
@click.option("--config", "-c", help="Path to configuration file")
@click.pass_context
def cli(ctx, config):
    """cmd-sniper - Linux command audit and analysis tool."""
    ctx.ensure_object(dict)
    ctx.obj["config"] = config


@cli.command()
@click.option("--method", "-m", type=click.Choice(["auditd", "ebpf", "both"]), default="auditd",
              help="Capture method to use")
@click.option("--foreground", "-f", is_flag=True, help="Run in foreground")
@click.option("--daemon", "-d", is_flag=True, help="Run as daemon")
@click.option("--pid-file", default="/run/cmd-sniper/pid", help="PID file location")
@click.pass_context
def start(ctx, method, foreground, daemon, pid_file):
    """Start command capture."""
    check_root()

    config = load_config(ctx.obj["config"])
    db = Database(config.storage.db_path)

    click.echo("Starting cmd-sniper capture...")

    instances = []
    if method in ("auditd", "both"):
        try:
            auditd = AuditdCapture(db, config)
            if not auditd.is_available():
                click.echo("Warning: auditd capture not available", err=True)
            else:
                auditd.start()
                instances.append(("auditd", auditd))
                click.echo(f"  - auditd capture started")
        except CaptureNotAvailableError as e:
            click.echo(f"  - auditd: {e}", err=True)

    if method in ("ebpf", "both"):
        try:
            ebpf = EbpfCapture(db, config)
            if not ebpf.is_available():
                click.echo("Warning: eBPF capture not available", err=True)
            else:
                ebpf.start()
                instances.append(("ebpf", ebpf))
                click.echo(f"  - eBPF capture started")
        except CaptureNotAvailableError as e:
            click.echo(f"  - eBPF: {e}", err=True)

    if not instances:
        click.echo("Error: No capture method available!", err=True)
        sys.exit(1)

    # Write PID file
    Path(pid_file).parent.mkdir(parents=True, exist_ok=True)
    with open(pid_file, "w") as f:
        f.write(str(os.getpid()))

    if daemon:
        # Fork to background
        click.echo(f"Running in background (PID: {os.getpid()})")
        click.echo(f"Logs: {config.log_dir}")

    # Setup signal handler for cleanup
    def cleanup(signum, frame):
        click.echo("\nStopping capture...")
        for name, instance in instances:
            try:
                instance.stop()
                click.echo(f"  - {name} stopped")
            except Exception as e:
                click.echo(f"  - {name} error: {e}", err=True)

        # Remove PID file
        try:
            os.remove(pid_file)
        except FileNotFoundError:
            pass

        sys.exit(0)

    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    # Main capture loop
    click.echo("Capturing commands... Press Ctrl+C to stop.")
    last_report = time.time()

    try:
        while True:
            for name, instance in instances:
                try:
                    if name == "auditd":
                        count = instance.capture_once()
                    else:
                        count = instance.capture_once(timeout_ms=100)

                    if count > 0:
                        click.echo(f"\rCaptured {count} commands   ", nl=False)

                except Exception as e:
                    click.echo(f"\nError in {name}: {e}", err=True)

            # Periodic status update
            if time.time() - last_report > 60:
                stats = db.get_stats()
                click.echo(f"\nTotal: {stats['total_commands']:,} commands")
                last_report = time.time()

            time.sleep(1)

    except KeyboardInterrupt:
        cleanup(None, None)


@cli.command()
@click.option("--pid-file", default="/run/cmd-sniper/pid", help="PID file location")
@click.pass_context
def stop(ctx, pid_file):
    """Stop command capture."""
    try:
        with open(pid_file) as f:
            pid = int(f.read().strip())
        os.kill(pid, signal.SIGTERM)
        click.echo(f"Sent stop signal to process {pid}")
    except FileNotFoundError:
        click.echo("cmd-sniper is not running (no PID file found)", err=True)
        sys.exit(1)
    except ProcessLookupError:
        click.echo(f"Process {pid} not found, cleaning up PID file", err=True)
        os.remove(pid_file)
        sys.exit(1)


@cli.command()
@click.option("--pid-file", default="/run/cmd-sniper/pid", help="PID file location")
@click.pass_context
def status(ctx, pid_file):
    """Show capture status."""
    db = get_db(ctx.obj["config"])

    # Check if running
    running = False
    try:
        with open(pid_file) as f:
            pid = int(f.read().strip())
        os.kill(pid, 0)  # Check if process exists
        running = True
    except (FileNotFoundError, ProcessLookupError):
        pass

    # Database stats
    stats = db.get_stats()

    click.echo("cmd-sniper Status:")
    click.echo(f"  Running: {'Yes' if running else 'No'}")
    click.echo(f"  Total Commands: {stats['total_commands']:,}")
    click.echo(f"  Unique Commands: {stats['unique_commands']:,}")
    click.echo(f"  Unique Users: {stats['unique_users']}")
    click.echo(f"  First Record: {stats.get('first_command', 'N/A')}")
    click.echo(f"  Last Record: {stats.get('last_command', 'N/A')}")

    if stats.get('method_breakdown'):
        click.echo("\nCapture Methods:")
        for method, count in stats['method_breakdown'].items():
            click.echo(f"  {method}: {count:,}")

    # Active sessions
    sessions = db.get_active_sessions()
    if sessions:
        click.echo(f"\nActive Sessions: {len(sessions)}")
        for session in sessions:
            click.echo(f"  - {session['capture_method']}: started {session['start_time']}")


@cli.command()
@click.option("--output", "-o", default="report.html", help="Output file path")
@click.option("--format", "-f", type=click.Choice(["html", "json", "json-summary"]), default="html",
              help="Report format")
@click.option("--start", "-s", help="Start time (ISO format)")
@click.option("--end", "-e", help="End time (ISO format)")
@click.option("--days", "-d", type=int, help="Number of days to include")
@click.pass_context
def report(ctx, output, format, start, end, days):
    """Generate analysis report."""
    db = get_db(ctx.obj["config"])

    # Parse time range
    start_time = datetime.fromisoformat(start) if start else None
    end_time = datetime.fromisoformat(end) if end else None

    if days:
        start_time = datetime.now() - timedelta(days=days)
        end_time = datetime.now()

    click.echo(f"Generating {format.upper()} report...")

    if format == "html":
        reporter = HTMLReporter(db)
        reporter.generate(output, start_time=start_time, end_time=end_time)
    elif format == "json":
        reporter = JSONReporter(db)
        reporter.export(output, start_time=start_time, end_time=end_time)
    elif format == "json-summary":
        reporter = JSONReporter(db)
        reporter.export_summary(output)

    click.echo(f"Report saved to: {output}")


@cli.command()
@click.argument("pattern")
@click.option("--limit", "-l", default=50, help="Maximum results")
@click.option("--user", "-u", type=int, help="Filter by user ID")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_context
def query(ctx, pattern, limit, user, as_json):
    """Search for commands matching pattern."""
    db = get_db(ctx.obj["config"])

    results = db.get_commands(
        limit=limit,
        user=user,
        search=pattern,
    )

    if as_json:
        import json
        click.echo(json.dumps(results, indent=2, default=str))
    else:
        click.echo(f"Found {len(results)} matching commands:\n")
        for cmd in results:
            click.echo(f"  [{cmd['timestamp'][:19]}] {cmd['username']}: {cmd['full_command'][:80]}")


@cli.command()
@click.option("--limit", "-l", default=20, help="Number of results")
@click.option("--user", "-u", type=int, help="Filter by user ID")
@click.pass_context
def top(ctx, limit, user):
    """Show top commands."""
    db = get_db(ctx.obj["config"])
    stats = CommandStats(db)

    commands = stats.get_top_commands(limit, user=user)

    click.echo(f"\nTop {len(commands)} Commands:")
    for i, cmd in enumerate(commands, 1):
        click.echo(f"  {i:2}. {cmd['command']:20} ({cmd['count']:>5}x)")


@cli.command()
@click.option("--limit", "-l", default=10, help="Number of results")
@click.pass_context
def users(ctx, limit):
    """Show top users."""
    db = get_db(ctx.obj["config"])
    stats = CommandStats(db)

    user_stats = stats.get_top_users(limit)

    click.echo(f"\nTop {len(user_stats)} Users:")
    for i, user in enumerate(user_stats, 1):
        click.echo(f"  {i:2}. {user['username']:15} ({user['command_count']:>5} commands, {user['unique_commands']} unique)")


@cli.command()
@click.option("--user", "-u", type=int, help="User ID to analyze")
@click.option("--limit", "-l", default=10, help="Number of results")
@click.pass_context
def risky(ctx, user, limit):
    """Show risky commands."""
    db = get_db(ctx.obj["config"])
    stats = CommandStats(db)

    commands = stats.get_risk_commands(limit)

    if not commands:
        click.echo("No risky commands found.")
        return

    click.echo(f"\nRisky Commands ({len(commands)}):")
    for cmd in commands:
        click.echo(f"  [{cmd['risk_level'].upper():^8}] {cmd['username']}: {cmd['full_command'][:70]}")


@cli.command()
@click.option("--days", "-d", type=int, default=7, help="Number of days to analyze")
@click.pass_context
def summary(ctx, days):
    """Show text summary report."""
    db = get_db(ctx.obj["config"])
    stats = CommandStats(db)

    start_time = datetime.now() - timedelta(days=days)
    end_time = datetime.now()

    # Update stats to use time range
    overview = stats.get_overview()
    top_commands = stats.get_top_commands(10)
    top_users = stats.get_top_users(10)

    click.echo(stats.get_summary_report())


@cli.command()
@click.option("--format", "-f", type=click.Choice(["json", "jsonl", "csv"]), default="json",
              help="Export format")
@click.option("--output", "-o", required=True, help="Output file")
@click.option("--user", "-u", type=int, help="Filter by user ID")
@click.option("--limit", "-l", type=int, default=100000, help="Maximum records")
@click.pass_context
def export(ctx, format, output, user, limit):
    """Export command data."""
    db = get_db(ctx.obj["config"])
    reporter = JSONReporter(db)

    reporter.export_commands_only(
        output_path=output,
        user=user,
        limit=limit,
        format=format,
    )

    click.echo(f"Exported to: {output}")


@cli.command()
@click.option("--retention", "-r", type=int, default=90, help="Days to keep")
@click.option("--dry-run", "-n", is_flag=True, help="Show what would be deleted")
@click.pass_context
def cleanup(ctx, retention, dry_run):
    """Clean up old records."""
    check_root()

    db = get_db(ctx.obj["config"])

    if dry_run:
        click.echo(f"Dry run: would delete records older than {retention} days")
        # Count would-be deleted records
        stats = db.get_stats()
        click.echo(f"Total records in database: {stats['total_commands']}")
    else:
        count = db.cleanup_old_records(retention)
        click.echo(f"Deleted {count} old records")

        # Vacuum database
        db.vacuum()
        click.echo("Database vacuumed")


@cli.command()
@click.pass_context
def init(ctx):
    """Initialize cmd-sniper (create database, directories)."""
    check_root()

    config = load_config(ctx.obj["config"])
    config.ensure_directories()

    db = Database(config.storage.db_path)

    # Set metadata
    db.set_metadata("initialized", datetime.now().isoformat())
    db.set_metadata("version", "1.0.0")

    click.echo("cmd-sniper initialized successfully!")
    click.echo(f"  Database: {config.storage.db_path}")
    click.echo(f"  Config: {config.config_dir}")
    click.echo(f"  Logs: {config.log_dir}")


def main():
    """Main entry point."""
    cli(obj={})


if __name__ == "__main__":
    main()
