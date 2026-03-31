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
import argparse
import csv
from datetime import datetime, timedelta
from pathlib import Path

# Add module path for imports
cli_file = Path(__file__).resolve()
cli_dir = cli_file.parent

# Possible module locations - all as Path objects
module_paths = [
    cli_dir,
    cli_dir / "src",
    cli_dir.parent,
    Path("/var/lib/cmd-sniper/cmd-sniper"),
]

for path in module_paths:
    path_str = str(path)
    if path_str not in sys.path and path.is_dir():
        sys.path.insert(0, path_str)

try:
    from storage import Database, Config, load_config
    from capture import AuditdCapture, EbpfCapture, CaptureNotAvailableError
    from analyzer import CommandStats
    from reporter import HTMLReporter, JSONReporter
except ImportError as e:
    print(f"Error importing modules: {e}", file=sys.stderr)
    print("Make sure you're running from the correct directory.", file=sys.stderr)
    sys.exit(1)


def check_root():
    """Check if running as root."""
    if os.geteuid() != 0:
        print("Error: This command requires root privileges.", file=sys.stderr)
        print("Please run with sudo.", file=sys.stderr)
        sys.exit(1)


def get_db(config_path: str = None) -> Database:
    """Get database instance with config."""
    config = load_config(config_path)
    config.ensure_directories()
    return Database(config.storage.db_path)


def cmd_start(args):
    """Start command capture."""
    if os.geteuid() != 0 and args.method != "none":
        print("Warning: Not running as root. Capture may not work properly.", file=sys.stderr)
        response = input("Continue? (y/N): ")
        if response.lower() != 'y':
            return

    config = load_config(args.config)
    db = Database(config.storage.db_path)

    print("Starting cmd-sniper capture...")

    instances = []
    method = args.method.lower()

    if method in ("auditd", "both"):
        try:
            auditd = AuditdCapture(db, config)
            if not auditd.is_available():
                print("Warning: auditd capture not available", file=sys.stderr)
            else:
                auditd.start()
                instances.append(("auditd", auditd))
                print("  - auditd capture started")
        except CaptureNotAvailableError as e:
            print(f"  - auditd: {e}", file=sys.stderr)

    if method in ("ebpf", "both"):
        try:
            ebpf = EbpfCapture(db, config)
            if not ebpf.is_available():
                print("Warning: eBPF capture not available", file=sys.stderr)
            else:
                ebpf.start()
                instances.append(("ebpf", ebpf))
                print("  - eBPF capture started")
        except CaptureNotAvailableError as e:
            print(f"  - eBPF: {e}", file=sys.stderr)

    if not instances:
        print("Error: No capture method available!", file=sys.stderr)
        sys.exit(1)

    # Write PID file
    pid_file = args.pid_file
    Path(pid_file).parent.mkdir(parents=True, exist_ok=True)
    with open(pid_file, "w") as f:
        f.write(str(os.getpid()))

    if args.daemon:
        print(f"Running in background (PID: {os.getpid()})")
        print(f"Logs: {config.log_dir}")

    # Setup signal handler
    def cleanup(signum, frame):
        print("\nStopping capture...")
        for name, instance in instances:
            try:
                instance.stop()
                print(f"  - {name} stopped")
            except Exception as e:
                print(f"  - {name} error: {e}", file=sys.stderr)
        try:
            os.remove(pid_file)
        except FileNotFoundError:
            pass
        sys.exit(0)

    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    # Main capture loop
    print("Capturing commands... Press Ctrl+C to stop.")
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
                        print(f"\rCaptured {count} commands   ", end="", flush=True)
                except Exception as e:
                    print(f"\nError in {name}: {e}", file=sys.stderr)

            if time.time() - last_report > 60:
                try:
                    stats = db.get_stats()
                    print(f"\nTotal: {stats['total_commands']:,} commands")
                except Exception:
                    pass
                last_report = time.time()

            time.sleep(1)
    except KeyboardInterrupt:
        cleanup(None, None)


def cmd_stop(args):
    """Stop command capture."""
    pid_file = args.pid_file
    try:
        with open(pid_file) as f:
            pid = int(f.read().strip())
        os.kill(pid, signal.SIGTERM)
        print(f"Sent stop signal to process {pid}")
    except FileNotFoundError:
        print("cmd-sniper is not running (no PID file found)", file=sys.stderr)
        sys.exit(1)
    except ProcessLookupError:
        print(f"Process {pid} not found, cleaning up PID file", file=sys.stderr)
        try:
            os.remove(pid_file)
        except FileNotFoundError:
            pass
        sys.exit(1)


def cmd_status(args):
    """Show capture status."""
    try:
        db = get_db(args.config)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    # Check if running
    running = False
    pid_file = "/run/cmd-sniper/pid"
    try:
        with open(pid_file) as f:
            pid = int(f.read().strip())
        os.kill(pid, 0)
        running = True
    except (FileNotFoundError, ProcessLookupError):
        pass

    try:
        stats = db.get_stats()

        print("cmd-sniper Status:")
        print(f"  Running: {'Yes' if running else 'No'}")
        print(f"  Total Commands: {stats['total_commands']:,}")
        print(f"  Unique Commands: {stats['unique_commands']:,}")
        print(f"  Unique Users: {stats['unique_users']}")
        print(f"  First Record: {stats.get('first_command', 'N/A')}")
        print(f"  Last Record: {stats.get('last_command', 'N/A')}")

        if stats.get('method_breakdown'):
            print("\nCapture Methods:")
            for method, count in stats['method_breakdown'].items():
                print(f"  {method}: {count:,}")

        sessions = db.get_active_sessions()
        if sessions:
            print(f"\nActive Sessions: {len(sessions)}")
            for session in sessions:
                print(f"  - {session['capture_method']}: started {session['start_time']}")
    except Exception as e:
        print(f"Error getting stats: {e}", file=sys.stderr)


def cmd_init(args):
    """Initialize cmd-sniper (create database, directories)."""
    if os.geteuid() != 0:
        print("Warning: Not running as root. Using user-local directories.", file=sys.stderr)

    config = load_config(args.config)
    config.ensure_directories()

    db = Database(config.storage.db_path)

    db.set_metadata("initialized", datetime.now().isoformat())
    db.set_metadata("version", "1.0.0")

    print("cmd-sniper initialized successfully!")
    print(f"  Database: {config.storage.db_path}")
    print(f"  Config: {config.config_dir}")
    print(f"  Logs: {config.log_dir}")


def cmd_report(args):
    """Generate analysis report."""
    try:
        db = get_db(args.config)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    # Parse time range
    start_time = None
    end_time = None

    if args.start:
        try:
            start_time = datetime.fromisoformat(args.start)
        except ValueError:
            print(f"Error: Invalid start time format: {args.start}", file=sys.stderr)
            sys.exit(1)

    if args.end:
        try:
            end_time = datetime.fromisoformat(args.end)
        except ValueError:
            print(f"Error: Invalid end time format: {args.end}", file=sys.stderr)
            sys.exit(1)

    if args.days:
        start_time = datetime.now() - timedelta(days=args.days)
        end_time = datetime.now()

    print(f"Generating {args.format} report...")

    try:
        if args.format == "html":
            reporter = HTMLReporter(db)
            reporter.generate(args.output, start_time=start_time, end_time=end_time)
            print(f"HTML report saved to: {args.output}")

            # Also generate CSV/Excel file
            # Generate CSV filename by replacing .html with .csv
            base_name = os.path.splitext(args.output)[0]
            csv_output = f"{base_name}.csv"

            # Export full command data to CSV
            commands = db.get_commands(
                limit=100000,
                start_time=start_time,
                end_time=end_time,
            )

            Path(csv_output).parent.mkdir(parents=True, exist_ok=True)
            with open(csv_output, "w", newline="") as f:
                if commands:
                    # Define column order for better readability
                    fieldnames = [
                        "id", "timestamp", "username", "uid",
                        "command", "full_command", "pid", "cwd",
                        "capture_method"
                    ]
                    # Filter to only existing fields
                    available_fields = [f for f in fieldnames if f in commands[0]]
                    writer = csv.DictWriter(f, fieldnames=available_fields, extrasaction="ignore")
                    writer.writeheader()
                    writer.writerows(commands)

            print(f"CSV/Excel file saved to: {csv_output}")

        elif args.format == "json":
            reporter = JSONReporter(db)
            reporter.export(args.output, start_time=start_time, end_time=end_time)
            print(f"Report saved to: {args.output}")
        elif args.format == "json-summary":
            reporter = JSONReporter(db)
            reporter.export_summary(args.output)
            print(f"Report saved to: {args.output}")

    except Exception as e:
        print(f"Error generating report: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_query(args):
    """Search for commands matching pattern."""
    try:
        db = get_db(args.config)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    results = db.get_commands(
        limit=args.limit,
        user=args.user,
        search=args.pattern,
    )

    if args.json:
        import json
        print(json.dumps(results, indent=2, default=str))
    else:
        print(f"Found {len(results)} matching commands:\n")
        for cmd in results:
            print(f"  [{cmd['timestamp'][:19]}] {cmd['username']}: {cmd['full_command'][:80]}")


def cmd_top(args):
    """Show top commands."""
    try:
        db = get_db(args.config)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    stats = CommandStats(db)
    commands = stats.get_top_commands(args.limit, user=args.user)

    print(f"\nTop {len(commands)} Commands:")
    for i, cmd in enumerate(commands, 1):
        print(f"  {i:2}. {cmd['command']:20} ({cmd['count']:>5}x)")


def cmd_users(args):
    """Show top users."""
    try:
        db = get_db(args.config)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    stats = CommandStats(db)
    user_stats = stats.get_top_users(args.limit)

    print(f"\nTop {len(user_stats)} Users:")
    for i, user in enumerate(user_stats, 1):
        print(f"  {i:2}. {user['username']:15} ({user['command_count']:>5} commands, {user['unique_commands']} unique)")


def cmd_risky(args):
    """Show risky commands."""
    try:
        db = get_db(args.config)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    stats = CommandStats(db)
    commands = stats.get_risk_commands(args.limit)

    if not commands:
        print("No risky commands found.")
        return

    print(f"\nRisky Commands ({len(commands)}):")
    for cmd in commands:
        print(f"  [{cmd['risk_level'].upper():^8}] {cmd['username']}: {cmd['full_command'][:70]}")


def cmd_summary(args):
    """Show text summary report."""
    try:
        db = get_db(args.config)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    stats = CommandStats(db)

    start_time = None
    end_time = None
    if args.days:
        start_time = datetime.now() - timedelta(days=args.days)
        end_time = datetime.now()

    try:
        print(stats.get_summary_report())
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)


def cmd_export(args):
    """Export command data."""
    try:
        db = get_db(args.config)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    reporter = JSONReporter(db)

    try:
        reporter.export_commands_only(
            output_path=args.output,
            user=args.user,
            limit=args.limit,
            format=args.format,
        )
        print(f"Exported to: {args.output}")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_cleanup(args):
    """Clean up old records."""
    if os.geteuid() != 0:
        print("Error: This command requires root privileges.", file=sys.stderr)
        sys.exit(1)

    try:
        db = get_db(args.config)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    if args.dry_run:
        print(f"Dry run: would delete records older than {args.retention} days")
        try:
            stats = db.get_stats()
            print(f"Total records in database: {stats['total_commands']}")
        except Exception:
            pass
    else:
        count = db.cleanup_old_records(args.retention)
        print(f"Deleted {count} old records")
        db.vacuum()
        print("Database vacuumed")


def main():
    parser = argparse.ArgumentParser(
        prog="cmd-sniper",
        description="Linux command audit and analysis tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s init                    Initialize database
  %(prog)s start --method auditd    Start capturing
  %(prog)s status                   Show status
  %(prog)s report -o report.html    Generate report
  %(prog)s query "docker"           Search commands
        """,
    )

    parser.add_argument("-c", "--config", help="Path to configuration file")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # start command
    parser_start = subparsers.add_parser("start", help="Start command capture")
    parser_start.add_argument("-m", "--method", choices=["auditd", "ebpf", "both"],
                               default="auditd", help="Capture method")
    parser_start.add_argument("-f", "--foreground", action="store_true",
                               help="Run in foreground")
    parser_start.add_argument("-d", "--daemon", action="store_true",
                               help="Run as daemon")
    parser_start.add_argument("--pid-file", default="/run/cmd-sniper/pid",
                               help="PID file location")
    parser_start.set_defaults(func=cmd_start)

    # stop command
    parser_stop = subparsers.add_parser("stop", help="Stop command capture")
    parser_stop.add_argument("--pid-file", default="/run/cmd-sniper/pid",
                              help="PID file location")
    parser_stop.set_defaults(func=cmd_stop)

    # status command
    parser_status = subparsers.add_parser("status", help="Show capture status")
    parser_status.set_defaults(func=cmd_status)

    # init command
    parser_init = subparsers.add_parser("init", help="Initialize cmd-sniper")
    parser_init.set_defaults(func=cmd_init)

    # report command
    parser_report = subparsers.add_parser("report", help="Generate analysis report")
    parser_report.add_argument("-o", "--output", default="report.html",
                               help="Output file path")
    parser_report.add_argument("-f", "--format", choices=["html", "json", "json-summary"],
                               default="html", help="Report format")
    parser_report.add_argument("--start", help="Start time (ISO format)")
    parser_report.add_argument("--end", help="End time (ISO format)")
    parser_report.add_argument("-d", "--days", type=int, help="Number of days to include")
    parser_report.set_defaults(func=cmd_report)

    # query command
    parser_query = subparsers.add_parser("query", help="Search for commands matching pattern")
    parser_query.add_argument("pattern", help="Search pattern")
    parser_query.add_argument("-l", "--limit", type=int, default=50, help="Maximum results")
    parser_query.add_argument("-u", "--user", type=int, help="Filter by user ID")
    parser_query.add_argument("--json", action="store_true", help="Output as JSON")
    parser_query.set_defaults(func=cmd_query)

    # top command
    parser_top = subparsers.add_parser("top", help="Show top commands")
    parser_top.add_argument("-l", "--limit", type=int, default=20, help="Number of results")
    parser_top.add_argument("-u", "--user", type=int, help="Filter by user ID")
    parser_top.set_defaults(func=cmd_top)

    # users command
    parser_users = subparsers.add_parser("users", help="Show top users")
    parser_users.add_argument("-l", "--limit", type=int, default=10, help="Number of results")
    parser_users.set_defaults(func=cmd_users)

    # risky command
    parser_risky = subparsers.add_parser("risky", help="Show risky commands")
    parser_risky.add_argument("-l", "--limit", type=int, default=10, help="Number of results")
    parser_risky.set_defaults(func=cmd_risky)

    # summary command
    parser_summary = subparsers.add_parser("summary", help="Show text summary report")
    parser_summary.add_argument("-d", "--days", type=int, default=7,
                                help="Number of days to analyze")
    parser_summary.set_defaults(func=cmd_summary)

    # export command
    parser_export = subparsers.add_parser("export", help="Export command data")
    parser_export.add_argument("-f", "--format", choices=["json", "jsonl", "csv"],
                                default="json", help="Export format")
    parser_export.add_argument("-o", "--output", required=True, help="Output file")
    parser_export.add_argument("-u", "--user", type=int, help="Filter by user ID")
    parser_export.add_argument("-l", "--limit", type=int, default=100000, help="Maximum records")
    parser_export.set_defaults(func=cmd_export)

    # cleanup command
    parser_cleanup = subparsers.add_parser("cleanup", help="Clean up old records")
    parser_cleanup.add_argument("-r", "--retention", type=int, default=90,
                               help="Days to keep")
    parser_cleanup.add_argument("-n", "--dry-run", action="store_true",
                               help="Show what would be deleted")
    parser_cleanup.set_defaults(func=cmd_cleanup)

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
