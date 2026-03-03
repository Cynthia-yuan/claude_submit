#!/usr/bin/env python3
"""
KCSAN Report Analyzer
Analyzes Kernel Concurrency Sanitizer reports to identify data races,
locate code positions, and provide fix suggestions.
"""

import re
import json
import os
import sys
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path


@dataclass
class RaceAccess:
    """Represents a single access in a data race"""
    access_type: str  # 'read' or 'write'
    address: str
    size: int
    task_info: str
    cpu: int
    stack_trace: List[str]

    def __str__(self) -> str:
        return f"{self.access_type} to {self.address} of {self.size} bytes"


@dataclass
class DataRace:
    """Represents a complete data race report"""
    raw_report: str
    race_type: str  # 'data-race', 'assert', etc.
    access1: RaceAccess
    access2: RaceAccess
    value_change: Optional[str] = None
    variable_name: Optional[str] = None
    function_name: Optional[str] = None
    file_location: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return {
            'race_type': self.race_type,
            'variable_name': self.variable_name,
            'function_name': self.function_name,
            'file_location': self.file_location,
            'access1': {
                'type': self.access1.access_type,
                'address': self.access1.address,
                'size': self.access1.size,
                'stack': self.access1.stack_trace
            },
            'access2': {
                'type': self.access2.access_type,
                'address': self.access2.address,
                'size': self.access2.size,
                'stack': self.access2.stack_trace
            },
            'value_change': self.value_change,
            'timestamp': self.timestamp
        }


class KCSANParser:
    """Parser for KCSAN reports"""

    # Regex patterns for KCSAN report parsing
    RACE_HEADER = re.compile(r'\[.*?\]\s*BUG:\s*KCSAN:\s*(\S+)\s*in\s*(.+?)\s*$')
    ACCESS_PATTERN = re.compile(
        r'\[.*?\]\s+(read|write)\s+to\s+(0x[0-9a-f]+)\s+of\s+(\d+)\s+bytes\s+'
        r'by\s+task\s+(\d+)\s+on\s+cpu\s+(\d+):'
    )
    VALUE_CHANGE = re.compile(r'\[.*?\]\s*value changed:\s+(0x[0-9a-f]+)\s*->\s*(0x[0-9a-f]+)')
    STACK_FRAME = re.compile(r'\[.*?\]\s+([<]?.+?[>]?)\+0x[0-9a-f]+/0x[0-9a-f]+')
    STACK_FRAME_ALT = re.compile(r'\[.*?\]\s+(.+?)$')  # Alternative pattern for file:line format
    FUNCTION_NAME = re.compile(r'([a-zA-Z_][a-zA-Z0-9_]*)')

    def __init__(self):
        self.races: List[DataRace] = []

    def parse_dmesg_output(self, text: str) -> List[DataRace]:
        """Parse KCSAN report from dmesg output"""
        self.races = []
        reports = self._split_reports(text)

        for report in reports:
            race = self._parse_single_report(report)
            if race:
                self.races.append(race)

        return self.races

    def _split_reports(self, text: str) -> List[str]:
        """Split text into individual KCSAN reports"""
        # Find all report start positions
        reports = []
        report_start_pattern = re.compile(r'\[.*?\]\s*BUG:\s*KCSAN:')

        # Find all matches
        matches = list(report_start_pattern.finditer(text))

        for i, match in enumerate(matches):
            start = match.start()
            # End is start of next report or end of text
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            report = text[start:end].strip()
            if report:
                reports.append(report)

        return reports

    def _parse_single_report(self, report: str) -> Optional[DataRace]:
        """Parse a single KCSAN report"""
        lines = report.strip().split('\n')

        # Extract race type and functions
        race_type = None
        functions = None
        for line in lines[:5]:  # Check first few lines
            match = self.RACE_HEADER.search(line)
            if match:
                race_type = match.group(1)
                functions = match.group(2)
                break

        if not race_type:
            return None

        # Find the two accesses
        accesses = []
        current_access = None
        stack_trace = []

        for line in lines:
            access_match = self.ACCESS_PATTERN.search(line)
            if access_match:
                # Save previous access if exists
                if current_access:
                    current_access.stack_trace = stack_trace
                    accesses.append(current_access)

                # Start new access
                current_access = RaceAccess(
                    access_type=access_match.group(1),
                    address=access_match.group(2),
                    size=int(access_match.group(3)),
                    task_info=access_match.group(4),
                    cpu=int(access_match.group(5)),
                    stack_trace=[]
                )
                stack_trace = []
            elif current_access:
                # Collect stack trace - try multiple patterns
                frame = None
                frame_match = self.STACK_FRAME.search(line)
                if frame_match:
                    frame = frame_match.group(1).strip()
                else:
                    # Try alternative pattern for file:line format
                    alt_match = self.STACK_FRAME_ALT.search(line)
                    if alt_match and alt_match.group(1).strip():
                        potential = alt_match.group(1).strip()
                        # Skip if it's a known non-frame line
                        if not any(x in potential for x in ['bytes by task', 'Reported by', 'value changed']):
                            frame = potential

                if frame:
                    stack_trace.append(frame)

        # Don't forget the last access
        if current_access:
            current_access.stack_trace = stack_trace
            accesses.append(current_access)

        if len(accesses) < 2:
            return None

        # Extract value change if present
        value_change = None
        for line in lines:
            match = self.VALUE_CHANGE.search(line)
            if match:
                value_change = f"{match.group(1)} -> {match.group(2)}"
                break

        # Try to extract variable name from function names
        function_name = None
        if functions:
            func_parts = functions.split('/')
            if func_parts:
                function_name = func_parts[0].strip()

        # Try to find file location from stack trace
        file_location = None
        for access in accesses:
            for frame in access.stack_trace:
                if '/' in frame and '.' in frame:
                    # This looks like a file path
                    file_location = frame
                    break
            if file_location:
                break

        return DataRace(
            raw_report=report,
            race_type=race_type,
            access1=accesses[0],
            access2=accesses[1],
            value_change=value_change,
            function_name=function_name,
            file_location=file_location
        )


class KCSANAnalyzer:
    """Analyzer for KCSAN reports with analysis and suggestions"""

    def __init__(self, parser: KCSANParser):
        self.parser = parser
        self.races = parser.races

    def analyze_race(self, race: DataRace) -> dict:
        """Analyze a single data race and provide suggestions"""
        analysis = {
            'severity': self._assess_severity(race),
            'race_pattern': self._identify_pattern(race),
            'likely_cause': self._determine_cause(race),
            'fix_suggestions': self._generate_fix_suggestions(race),
            'related_locations': self._find_related_locations(race)
        }
        return analysis

    def _assess_severity(self, race: DataRace) -> str:
        """Assess the severity of a data race"""
        # Write-write races are usually more severe than read-write
        if race.access1.access_type == 'write' and race.access2.access_type == 'write':
            return 'HIGH'
        elif race.access1.access_type == 'write' or race.access2.access_type == 'write':
            return 'MEDIUM'
        else:
            return 'LOW'

    def _identify_pattern(self, race: DataRace) -> str:
        """Identify common race patterns"""
        func1 = race.access1.stack_trace[0] if race.access1.stack_trace else ''
        func2 = race.access2.stack_trace[0] if race.access2.stack_trace else ''

        if 'lock' in func1.lower() or 'lock' in func2.lower():
            return 'missing-lock-protection'
        elif 'atomic' in func1.lower() or 'atomic' in func2.lower():
            return 'mixed-atomic-non-atomic'
        elif 'init' in func1.lower() or 'init' in func2.lower():
            return 'initialization-race'
        else:
            return 'unknown-pattern'

    def _determine_cause(self, race: DataRace) -> str:
        """Determine the likely cause of the race"""
        pattern = self._identify_pattern(race)

        causes = {
            'missing-lock-protection': 'Concurrent access without proper synchronization (missing lock or atomic operation)',
            'mixed-atomic-non-atomic': 'Mixing atomic and non-atomic accesses to the same variable',
            'initialization-race': 'Race during variable initialization or cleanup',
            'unknown-pattern': 'Unsynchronized concurrent access to shared data'
        }

        return causes.get(pattern, 'Unknown - needs manual investigation')

    def _generate_fix_suggestions(self, race: DataRace) -> List[str]:
        """Generate fix suggestions for the race"""
        suggestions = []
        pattern = self._identify_pattern(race)

        if pattern == 'missing-lock-protection':
            suggestions.append('Add a spinlock or mutex to protect the shared variable')
            suggestions.append('Use READ_ONCE/WRITE_ONCE if ordering is not required')
            suggestions.append('Consider using atomic operations for simple counters')
        elif pattern == 'mixed-atomic-non-atomic':
            suggestions.append('Ensure all accesses use atomic_*() operations')
            suggestions.append('Or protect all accesses with a lock instead')
        elif pattern == 'initialization-race':
            suggestions.append('Use __read_mostly annotation for read-after-init variables')
            suggestions.append('Add proper initialization barriers')
            suggestions.append('Consider using once mechanisms for one-time init')

        # General suggestions
        suggestions.append('Review if the variable can be made local (not shared)')
        suggestions.append('Consider using kcsan_check_*() annotations to suppress false positives')

        return suggestions

    def _find_related_locations(self, race: DataRace) -> List[str]:
        """Find related code locations"""
        locations = []

        # Add top of stack traces
        if race.access1.stack_trace:
            locations.append(f"Access 1: {race.access1.stack_trace[0]}")
        if race.access2.stack_trace:
            locations.append(f"Access 2: {race.access2.stack_trace[0]}")

        # Add file location if available
        if race.file_location:
            locations.append(f"File: {race.file_location}")

        return locations


class KCSANStatistics:
    """Statistics tracker for multiple KCSAN reports"""

    def __init__(self):
        self.history_file = Path.home() / '.kcsan_history.json'
        self.history = self._load_history()

    def _load_history(self) -> dict:
        """Load analysis history"""
        if self.history_file.exists():
            try:
                with open(self.history_file, 'r') as f:
                    return json.load(f)
            except:
                return {'races': [], 'stats': {}}
        return {'races': [], 'stats': {}}

    def _save_history(self):
        """Save analysis history"""
        with open(self.history_file, 'w') as f:
            json.dump(self.history, f, indent=2)

    def add_races(self, races: List[DataRace]):
        """Add new races to history"""
        for race in races:
            race_dict = race.to_dict()
            self.history['races'].append(race_dict)

        self._update_stats()
        self._save_history()

    def _update_stats(self):
        """Update statistics"""
        races = self.history['races']

        # Count races by type
        type_counter = Counter(r['race_type'] for r in races)

        # Count races by function
        func_counter = Counter(r['function_name'] for r in races if r['function_name'])

        # Count races by severity (need to re-analyze)
        severity_counter = Counter()
        for r in races:
            if 'write-write' in f"{r['access1']['type']}-{r['access2']['type']}":
                severity_counter['HIGH'] += 1
            elif 'write' in f"{r['access1']['type']} {r['access2']['type']}":
                severity_counter['MEDIUM'] += 1
            else:
                severity_counter['LOW'] += 1

        # Count by address (hot spots)
        addr_counter = Counter(r['access1']['address'] for r in races)

        self.history['stats'] = {
            'total_races': len(races),
            'by_type': dict(type_counter.most_common()),
            'by_function': dict(func_counter.most_common(10)),
            'by_severity': dict(severity_counter),
            'hot_addresses': dict(addr_counter.most_common(5))
        }

    def get_statistics(self) -> dict:
        """Get current statistics"""
        return self.history.get('stats', {})

    def get_hot_spots(self) -> List[Tuple[str, int]]:
        """Get hot spots (addresses with most races)"""
        stats = self.get_statistics()
        return list(stats.get('hot_addresses', {}).items())

    def clear_history(self):
        """Clear analysis history"""
        self.history = {'races': [], 'stats': {}}
        self._save_history()


def analyze_text(text: str, update_history: bool = True) -> Tuple[List[DataRace], List[dict]]:
    """Analyze KCSAN report text and return races with analysis"""
    parser = KCSANParser()
    races = parser.parse_dmesg_output(text)

    analyzer = KCSANAnalyzer(parser)
    analyses = [analyzer.analyze_race(race) for race in races]

    if update_history and races:
        stats = KCSANStatistics()
        stats.add_races(races)

    return races, analyses


class SourceCodeViewer:
    """View source code for KCSAN reports"""

    def __init__(self, kernel_src: Optional[str] = None):
        self.kernel_src = self._find_kernel_src(kernel_src)

    def _find_kernel_src(self, provided_path: Optional[str]) -> Optional[Path]:
        """Find kernel source directory"""
        if provided_path:
            path = Path(provided_path)
            if path.exists():
                return path
            print(f"Warning: Kernel source path not found: {provided_path}", file=sys.stderr)
            return None

        # Try to auto-detect
        candidates = [
            Path("/lib/modules") / os.uname().release / "build",
            Path("/usr/src/linux-headers-" + os.uname().release),
            Path.cwd()  # Current directory
        ]

        for candidate in candidates:
            if candidate.exists() and (candidate / "kernel" / "sched" / "core.c").exists():
                return candidate

        return None

    def extract_file_line(self, stack_entry: str) -> Optional[Tuple[str, int]]:
        """Extract file path and line number from stack entry"""
        # Patterns like "kernel/sched/core.c:890" or "kernel/module.c:1234"
        match = re.search(r'([a-zA-Z0-9_/\-\.]+\.c):(\d+)', stack_entry)
        if match:
            file_path = match.group(1)
            line_num = int(match.group(2))
            return file_path, line_num
        return None

    def find_source_file(self, file_path: str) -> Optional[Path]:
        """Find source file in kernel tree"""
        if not self.kernel_src:
            return None

        # Try exact path relative to kernel source
        exact = self.kernel_src / file_path
        if exact.exists():
            return exact

        # Try to find by filename
        filename = Path(file_path).name
        try:
            for found in self.kernel_src.rglob(filename):
                if found.is_file():
                    return found
        except (PermissionError, OSError):
            pass

        return None

    def get_source_context(self, file_path: str, line_num: int, context_lines: int = 5) -> Optional[Dict]:
        """Get source code context around a line"""
        source_file = self.find_source_file(file_path)
        if not source_file:
            return None

        try:
            with open(source_file, 'r', errors='ignore') as f:
                lines = f.readlines()

            start = max(0, line_num - context_lines - 1)
            end = min(len(lines), line_num + context_lines)

            context = []
            for i in range(start, end):
                marker = ">>> " if i == line_num - 1 else "    "
                line_num_display = f"{i + 1:4d}"
                context.append(f"{marker}{line_num_display} {lines[i].rstrip()}")

            return {
                'file': str(source_file),
                'relative_path': file_path,
                'line': line_num,
                'context': context
            }
        except (IOError, OSError) as e:
            return None

    def get_race_sources(self, race: DataRace, context_lines: int = 5) -> Dict[str, Optional[Dict]]:
        """Get source code for both accesses in a race"""
        result = {'access1': None, 'access2': None}

        # Find file:line in stack traces
        for frame in race.access1.stack_trace:
            extracted = self.extract_file_line(frame)
            if extracted:
                result['access1'] = self.get_source_context(extracted[0], extracted[1], context_lines)
                break

        for frame in race.access2.stack_trace:
            extracted = self.extract_file_line(frame)
            if extracted:
                result['access2'] = self.get_source_context(extracted[0], extracted[1], context_lines)
                break

        return result

    def is_available(self) -> bool:
        """Check if source code is available"""
        return self.kernel_src is not None


class VariableResolver:
    """Resolve variable names from addresses and source code context"""

    def __init__(self, vmlinux_path: Optional[str] = None, kernel_src: Optional[str] = None):
        self.vmlinux_path = self._find_vmlinux(vmlinux_path)
        self.kernel_src = Path(kernel_src) if kernel_src else None
        self.addr2line = self._find_addr2line()

    def _find_vmlinux(self, provided_path: Optional[str]) -> Optional[Path]:
        """Find vmlinux binary with debug symbols"""
        if provided_path:
            path = Path(provided_path)
            if path.exists():
                return path
            return None

        # Common locations
        candidates = [
            Path("/usr/lib/debug/boot") / f"vmlinux-{os.uname().release}",
            Path("/boot") / f"vmlinux-{os.uname().release}",
            Path("/lib/modules") / os.uname().release / "build" / "vmlinux",
            Path(".o") / "vmlinux",  # Kernel build directory
        ]

        for candidate in candidates:
            if candidate.exists():
                return candidate

        return None

    def _find_addr2line(self) -> Optional[str]:
        """Find addr2line or llvm-addr2line"""
        import shutil

        # Try llvm-addr2line first (for LLVM-built kernels)
        for tool in ['llvm-addr2line', 'addr2line', 'llvm-addr2line-15', 'llvm-addr2line-14']:
            if shutil.which(tool):
                return tool

        return None

    def resolve_address(self, address: str) -> Optional[Dict]:
        """Resolve address to symbol and variable information"""
        if not self.vmlinux_path or not self.addr2line:
            return None

        try:
            import subprocess
            result = subprocess.run(
                [self.addr2line, '-e', str(self.vmlinux_path), '-f', '-C', address],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                if len(lines) >= 2:
                    return {
                        'function': lines[0],
                        'location': lines[1],
                        'address': address
                    }
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
            pass

        return None

    def extract_variable_from_source(self, source_context: Dict) -> Optional[str]:
        """Extract variable name from source code context using heuristics"""
        if not source_context or 'context' not in source_context:
            return None

        context = source_context['context']
        target_line_idx = None

        # Find the marked line (with >>>)
        for i, line in enumerate(context):
            if '>>>' in line:
                target_line_idx = i
                break

        if target_line_idx is None:
            return None

        target_line = context[target_line_idx]

        # Pattern 1: Direct variable access: varname
        # Pattern 2: Member access: ptr->field or struct.field
        # Pattern 3: Array access: array[index]
        # Pattern 4: Assignment: var = value or value = var

        # Extract the actual code (remove line number and marker)
        code_match = re.search(r'>>>?\s*\d+\s*(.+)$', target_line)
        if not code_match:
            code_match = re.search(r'\s*\d+\s*(.+)$', target_line)

        if not code_match:
            return None

        code = code_match.group(1).strip()

        # Remove comments
        code = re.sub(r'//.*$', '', code)
        code = re.sub(r'/\*.*?\*/', '', code)

        # Try to extract variable from common patterns
        var_patterns = [
            r'(\w+)\s*\+\+',           # var++
            r'(\w+)\s*--',              # var--
            r'\+\+\s*(\w+)',            # ++var
            r'--\s*(\w+)',              # --var
            r'(\w+)\s*[\+\-\*/%]=',     # var op= value
            r'(\w+)\s*=\s*[^=]',        # var = value
            r'=\s*(\w+)\s*[;,]',        # value = var
            r'(\w+)\s*\[[^\]]+\]',      # array[index]
            r'->\s*(\w+)\s*[;,)]',      # ptr->field
            r'\.\s*(\w+)\s*[;,)]',      # struct.field
            r'(\w+)\s*\)',              # function(var)
        ]

        for pattern in var_patterns:
            match = re.search(pattern, code)
            if match:
                var_name = match.group(1)
                # Filter out common non-variable keywords
                if var_name not in ['if', 'while', 'for', 'return', 'sizeof', 'typeof',
                                   'unlikely', 'likely', 'typeof', 'alignof']:
                    return var_name

        # Look at surrounding context for variable declarations
        # Check if there's a variable declaration nearby
        for i in range(max(0, target_line_idx - 3), min(len(context), target_line_idx + 2)):
            line = context[i]
            # Pattern: type varname;
            decl_match = re.search(r'(?:int|long|char|unsigned|struct|atomic|spinlock|void)\s+(\*?\s*\w+)', line)
            if decl_match:
                var_name = decl_match.group(1).strip().replace('*', '').strip()
                # Check if this variable appears in the target line
                if var_name in code:
                    return var_name

        return None

    def resolve_race_variable(self, race: DataRace, sources: Dict) -> Optional[Dict]:
        """Resolve the variable name involved in a data race"""
        result = {
            'address': race.access1.address,
            'variable_name': None,
            'confidence': 'low',
            'method': None,
            'symbol_info': None
        }

        # Try addr2line first
        if self.vmlinux_path and self.addr2line:
            symbol_info = self.resolve_address(race.access1.address)
            if symbol_info:
                result['symbol_info'] = symbol_info
                # Extract variable from symbol name if it contains global variable info
                # addr2line typically gives function name, not variable

        # Try source code analysis
        source_ctx1 = sources.get('access1') if sources else None
        source_ctx2 = sources.get('access2') if sources else None

        var_from_source1 = self.extract_variable_from_source(source_ctx1) if source_ctx1 else None
        var_from_source2 = self.extract_variable_from_source(source_ctx2) if source_ctx2 else None

        # If both sources point to the same variable, high confidence
        if var_from_source1 and var_from_source1 == var_from_source2:
            result['variable_name'] = var_from_source1
            result['confidence'] = 'high'
            result['method'] = 'source_analysis_both'
        elif var_from_source1:
            result['variable_name'] = var_from_source1
            result['confidence'] = 'medium'
            result['method'] = 'source_analysis_access1'
        elif var_from_source2:
            result['variable_name'] = var_from_source2
            result['confidence'] = 'medium'
            result['method'] = 'source_analysis_access2'

        return result if result['variable_name'] else None

    def is_available(self) -> bool:
        """Check if variable resolution is available"""
        return self.kernel_src is not None or (self.vmlinux_path is not None and self.addr2line is not None)