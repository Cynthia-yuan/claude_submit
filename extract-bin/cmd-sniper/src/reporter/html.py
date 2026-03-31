"""
HTML report generator for cmd-sniper.
"""
import json
from datetime import datetime
from typing import List, Any, Optional
from pathlib import Path

from storage import Database
from analyzer import CommandStats, PatternDetector


class HTMLReporter:
    """Generate HTML reports with interactive charts."""

    def __init__(self, db: Database):
        self.db = db
        self.stats = CommandStats(db)
        self.pattern = PatternDetector(db)

    def generate(
        self,
        output_path: str,
        title: str = "Command Analysis Report",
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> str:
        """
        Generate a complete HTML report.

        Returns the path to the generated report.
        """
        # Gather all data
        data = self._gather_data(start_time, end_time)

        # Generate HTML
        html = self._render_html(title, data)

        # Write to file
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            f.write(html)

        return output_path

    def _gather_data(self, start_time: Optional[datetime], end_time: Optional[datetime]) -> dict:
        """Gather all data for the report."""
        return {
            "overview": self.stats.get_overview(),
            "top_commands": self.stats.get_top_commands(100, start_time=start_time, end_time=end_time),
            "top_users": self.stats.get_top_users(50, start_time=start_time, end_time=end_time),
            "categories": self.stats.get_command_categories(start_time, end_time),
            "hourly_heatmap": self.stats.get_hourly_heatmap(start_time, end_time),
            "time_series": self.stats.get_time_series("hour", start_time, end_time),
            "risk_commands": self.stats.get_risk_commands(50, start_time, end_time),
            "peak_hours": self.stats.get_peak_hours(),
            "sequences": self.stats.get_command_sequences(limit=30),
            "recurring_tasks": self.pattern.detect_recurring_tasks(min_occurrences=5),
            "workflows": self.pattern.detect_workflow_patterns(),
            "time_patterns": self.pattern.detect_time_patterns(),
            "error_patterns": self.pattern.detect_error_patterns(),
            "ssh_patterns": self.pattern.detect_ssh_patterns(),
            "generated_at": datetime.now().isoformat(),
            "start_time": start_time.isoformat() if start_time else None,
            "end_time": end_time.isoformat() if end_time else None,
        }

    def _render_html(self, title: str, data: dict) -> str:
        """Render the HTML report."""
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: #f5f5f5;
            color: #333;
            line-height: 1.6;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }}
        header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        h1 {{
            font-size: 2em;
            margin-bottom: 10px;
        }}
        .subtitle {{
            opacity: 0.9;
            font-size: 0.9em;
        }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .card {{
            background: white;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .card h3 {{
            color: #667eea;
            margin-bottom: 15px;
            font-size: 1.1em;
            border-bottom: 2px solid #f0f0f0;
            padding-bottom: 10px;
        }}
        .stat {{
            text-align: center;
            padding: 15px;
        }}
        .stat-value {{
            font-size: 2.5em;
            font-weight: bold;
            color: #667eea;
        }}
        .stat-label {{
            color: #666;
            font-size: 0.9em;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        .chart {{
            min-height: 400px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #eee;
        }}
        th {{
            background: #f8f9fa;
            font-weight: 600;
            color: #555;
            position: sticky;
            top: 0;
        }}
        tr:hover {{
            background: #f8f9fa;
        }}
        .risk-critical {{
            background: #fee;
            border-left: 4px solid #e53e3e;
        }}
        .risk-high {{
            background: #fff5f5;
            border-left: 4px solid #fc8181;
        }}
        .risk-medium {{
            background: #fffaf0;
            border-left: 4px solid #f6ad55;
        }}
        .badge {{
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.8em;
            font-weight: 600;
        }}
        .badge-critical {{
            background: #e53e3e;
            color: white;
        }}
        .badge-high {{
            background: #fc8181;
            color: white;
        }}
        .badge-medium {{
            background: #f6ad55;
            color: white;
        }}
        .tab-container {{
            margin-bottom: 30px;
        }}
        .tabs {{
            display: flex;
            gap: 5px;
            margin-bottom: 0;
        }}
        .tab {{
            padding: 12px 24px;
            background: #e0e0e0;
            border: none;
            border-radius: 8px 8px 0 0;
            cursor: pointer;
            font-size: 0.95em;
            transition: all 0.2s;
        }}
        .tab:hover {{
            background: #d0d0d0;
        }}
        .tab.active {{
            background: white;
            color: #667eea;
        }}
        .tab-content {{
            display: none;
            background: white;
            padding: 20px;
            border-radius: 0 10px 10px 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .tab-content.active {{
            display: block;
        }}
        .search-box {{
            width: 100%;
            padding: 12px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            font-size: 1em;
            margin-bottom: 15px;
        }}
        .search-box:focus {{
            outline: none;
            border-color: #667eea;
        }}
        .command-cell {{
            font-family: 'Monaco', 'Menlo', monospace;
            font-size: 0.9em;
            background: #f5f5f5;
            padding: 4px 8px;
            border-radius: 4px;
        }}
        footer {{
            text-align: center;
            padding: 30px;
            color: #666;
            font-size: 0.9em;
        }}
        .section {{
            margin-bottom: 40px;
        }}
        .section-title {{
            font-size: 1.5em;
            color: #333;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 3px solid #667eea;
        }}
        .heatmap-container {{
            display: grid;
            grid-template-columns: auto repeat(24, 1fr);
            gap: 2px;
        }}
        .heatmap-label {{
            font-size: 0.8em;
            padding: 5px;
            color: #666;
        }}
        .heatmap-cell {{
            aspect-ratio: 1;
            border-radius: 2px;
            transition: transform 0.1s;
        }}
        .heatmap-cell:hover {{
            transform: scale(1.2);
            z-index: 10;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>{title}</h1>
            <p class="subtitle">Generated on {data['generated_at'][:19]}</p>
            <p class="subtitle">
                {data['overview']['total_commands']:,} commands captured from {data['overview']['unique_users']} users
            </p>
        </header>

        <!-- Overview Stats -->
        <div class="grid">
            <div class="card stat">
                <div class="stat-value">{data['overview']['total_commands']:,}</div>
                <div class="stat-label">Total Commands</div>
            </div>
            <div class="card stat">
                <div class="stat-value">{data['overview']['unique_commands']:,}</div>
                <div class="stat-label">Unique Commands</div>
            </div>
            <div class="card stat">
                <div class="stat-value">{data['overview']['unique_users']}</div>
                <div class="stat-label">Active Users</div>
            </div>
            <div class="card stat">
                <div class="stat-value">{data['overview']['timespan_days']:.1f}</div>
                <div class="stat-label">Days Span</div>
            </div>
        </div>

        <!-- Tabs -->
        <div class="tab-container">
            <div class="tabs">
                <button class="tab active" onclick="showTab('commands')">Commands</button>
                <button class="tab" onclick="showTab('users')">Users</button>
                <button class="tab" onclick="showTab('timeline')">Timeline</button>
                <button class="tab" onclick="showTab('security')">Security</button>
                <button class="tab" onclick="showTab('patterns')">Patterns</button>
            </div>

            <!-- Commands Tab -->
            <div id="commands" class="tab-content active">
                <div class="section">
                    <h2 class="section-title">Top Commands</h2>
                    <input type="text" class="search-box" id="command-search" placeholder="Search commands..." onkeyup="filterTable('command-table', this.value)">
                    <div style="overflow-x: auto; max-height: 500px;">
                        <table id="command-table">
                            <thead>
                                <tr>
                                    <th>Rank</th>
                                    <th>Command</th>
                                    <th>Count</th>
                                    <th>Unique Users</th>
                                </tr>
                            </thead>
                            <tbody>
                                {self._render_command_rows(data['top_commands'])}
                            </tbody>
                        </table>
                    </div>
                </div>

                <div class="section">
                    <h2 class="section-title">Command Categories</h2>
                    <div id="category-chart" class="chart"></div>
                </div>
            </div>

            <!-- Users Tab -->
            <div id="users" class="tab-content">
                <div class="section">
                    <h2 class="section-title">Top Users</h2>
                    <input type="text" class="search-box" id="user-search" placeholder="Search users..." onkeyup="filterTable('user-table', this.value)">
                    <div style="overflow-x: auto; max-height: 500px;">
                        <table id="user-table">
                            <thead>
                                <tr>
                                    <th>Rank</th>
                                    <th>User</th>
                                    <th>UID</th>
                                    <th>Commands</th>
                                    <th>Unique Commands</th>
                                </tr>
                            </thead>
                            <tbody>
                                {self._render_user_rows(data['top_users'])}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>

            <!-- Timeline Tab -->
            <div id="timeline" class="tab-content">
                <div class="section">
                    <h2 class="section-title">Activity Over Time</h2>
                    <div id="time-chart" class="chart"></div>
                </div>

                <div class="section">
                    <h2 class="section-title">Peak Hours</h2>
                    <div id="peak-chart" class="chart"></div>
                </div>
            </div>

            <!-- Security Tab -->
            <div id="security" class="tab-content">
                <div class="section">
                    <h2 class="section-title">Risky Commands</h2>
                    {self._render_risk_commands(data['risk_commands'])}
                </div>
            </div>

            <!-- Patterns Tab -->
            <div id="patterns" class="tab-content">
                <div class="section">
                    <h2 class="section-title">Command Sequences</h2>
                    <div style="overflow-x: auto; max-height: 400px;">
                        <table>
                            <thead>
                                <tr>
                                    <th>Sequence</th>
                                    <th>Count</th>
                                </tr>
                            </thead>
                            <tbody>
                                {self._render_sequence_rows(data['sequences'])}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>

        <footer>
            <p>Generated by <strong>cmd-sniper</strong> - Linux Command Audit Tool</p>
        </footer>
    </div>

    <script>
        // Tab switching
        function showTab(tabName) {{
            document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
            document.querySelectorAll('.tab').forEach(el => el.classList.remove('active'));
            document.getElementById(tabName).classList.add('active');
            event.target.classList.add('active');
        }}

        // Table filtering
        function filterTable(tableId, query) {{
            const table = document.getElementById(tableId);
            const rows = table.querySelectorAll('tbody tr');
            query = query.toLowerCase();

            rows.forEach(row => {{
                const text = row.textContent.toLowerCase();
                row.style.display = text.includes(query) ? '' : 'none';
            }});
        }}

        // Charts data
        const chartData = {json.dumps(data, default=str)};

        // Category pie chart
        const categoryData = [{{
            values: Object.values(chartData.categories),
            labels: Object.keys(chartData.categories),
            type: 'pie',
            hole: 0.4,
            marker: {{
                colors: ['#667eea', '#764ba2', '#f093fb', '#4facfe', '#43e97b', '#fa709a', '#fee140']
            }}
        }}];
        Plotly.newPlot('category-chart', categoryData, {{
            margin: {{t: 20, b: 20, l: 20, r: 20}},
            showlegend: true
        }});

        // Time series chart
        const timeData = chartData.time_series.map(d => ({{
            x: d.time_bucket,
            y: d.count,
            type: 'scatter',
            mode: 'lines+markers',
            line: {{color: '#667eea'}}
        }}));
        Plotly.newPlot('time-chart', timeData, {{
            margin: {{t: 20, b: 40, l: 40, r: 20}},
            xaxis: {{title: 'Time'}},
            yaxis: {{title: 'Commands'}}
        }});

        // Peak hours bar chart
        const peakData = [{{
            x: chartData.peak_hours.map(d => d.hour),
            y: chartData.peak_hours.map(d => d.count),
            type: 'bar',
            marker: {{color: '#667eea'}}
        }}];
        Plotly.newPlot('peak-chart', peakData, {{
            margin: {{t: 20, b: 40, l: 40, r: 20}},
            xaxis: {{title: 'Hour of Day'}},
            yaxis: {{title: 'Commands'}}
        }});
    </script>
</body>
</html>"""

    def _render_command_rows(self, commands: List[dict]) -> str:
        """Render table rows for commands."""
        rows = []
        for i, cmd in enumerate(commands[:100], 1):
            rows.append(f"""
                <tr>
                    <td>{i}</td>
                    <td><span class="command-cell">{self._escape_html(cmd['command'])}</span></td>
                    <td>{cmd['count']:,}</td>
                    <td>{cmd.get('unique_users', 1)}</td>
                </tr>
            """)
        return "".join(rows)

    def _render_user_rows(self, users: List[dict]) -> str:
        """Render table rows for users."""
        rows = []
        for i, user in enumerate(users[:50], 1):
            rows.append(f"""
                <tr>
                    <td>{i}</td>
                    <td>{self._escape_html(user['username'])}</td>
                    <td>{user['uid']}</td>
                    <td>{user['command_count']:,}</td>
                    <td>{user['unique_commands']:,}</td>
                </tr>
            """)
        return "".join(rows)

    def _render_risk_commands(self, commands: List[dict]) -> str:
        """Render risky commands table."""
        if not commands:
            return "<p>No risky commands detected.</p>"

        rows = []
        for cmd in commands[:50]:
            risk_class = f"risk-{cmd['risk_level']}"
            badge_class = f"badge-{cmd['risk_level']}"
            rows.append(f"""
                <tr class="{risk_class}">
                    <td><span class="badge {badge_class}">{cmd['risk_level'].upper()}</span></td>
                    <td>{self._escape_html(cmd['username'])}</td>
                    <td><span class="command-cell">{self._escape_html(cmd['full_command'][:80])}</span></td>
                    <td>{cmd['timestamp'][:19]}</td>
                </tr>
            """)

        return f"""
            <table>
                <thead>
                    <tr>
                        <th>Risk Level</th>
                        <th>User</th>
                        <th>Command</th>
                        <th>Time</th>
                    </tr>
                </thead>
                <tbody>
                    {"".join(rows)}
                </tbody>
            </table>
        """

    def _render_sequence_rows(self, sequences: List[dict]) -> str:
        """Render command sequences."""
        rows = []
        for seq in sequences[:30]:
            rows.append(f"""
                <tr>
                    <td><span class="command-cell">{self._escape_html(seq['sequence'])}</span></td>
                    <td>{seq['count']}</td>
                </tr>
            """)
        return "".join(rows)

    def _escape_html(self, text: str) -> str:
        """Escape HTML special characters."""
        return (str(text)
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;"))
