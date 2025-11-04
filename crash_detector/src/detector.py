"""
Crash Detector - Monitors logcat for crashes, ANRs, and freezes
"""
import re
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)


class CrashType(str, Enum):
    """Types of crashes/errors"""
    FATAL = "fatal"
    ANR = "anr"
    EXCEPTION = "exception"
    NATIVE_CRASH = "native_crash"
    FREEZE = "freeze"
    OOM = "out_of_memory"


@dataclass
class CrashEvent:
    """Represents a crash event"""
    timestamp: str
    crash_type: CrashType
    package_name: str
    message: str
    stack_trace: List[str]
    pid: Optional[int] = None
    severity: str = "high"
    
    def to_dict(self):
        return asdict(self)


class CrashDetector:
    """Detects and analyzes crashes from logcat"""
    
    def __init__(self):
        self.crash_patterns = {
            CrashType.FATAL: [
                r'FATAL EXCEPTION',
                r'AndroidRuntime.*FATAL',
            ],
            CrashType.ANR: [
                r'ANR in',
                r'Application Not Responding',
                r'Input dispatching timed out',
            ],
            CrashType.EXCEPTION: [
                r'Exception',
                r'Error',
            ],
            CrashType.NATIVE_CRASH: [
                r'signal \d+ \(SIG',
                r'Native crash',
                r'backtrace:',
            ],
            CrashType.OOM: [
                r'OutOfMemoryError',
                r'Failed to allocate',
            ]
        }
        
        self.crashes: List[CrashEvent] = []
        self.last_check_time = None
        
    def analyze_logcat(self, logcat_output: str, package_filter: Optional[str] = None) -> List[CrashEvent]:
        """Analyze logcat output for crashes"""
        new_crashes = []
        lines = logcat_output.split('\n')
        
        i = 0
        while i < len(lines):
            line = lines[i]
            
            # Check for crash patterns
            for crash_type, patterns in self.crash_patterns.items():
                for pattern in patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        crash = self._extract_crash_info(
                            lines, i, crash_type, package_filter
                        )
                        if crash:
                            new_crashes.append(crash)
                            self.crashes.append(crash)
                            logger.warning(f"Detected {crash_type}: {crash.message}")
                        break
            
            i += 1
        
        return new_crashes
    
    def _extract_crash_info(
        self, 
        lines: List[str], 
        start_idx: int, 
        crash_type: CrashType,
        package_filter: Optional[str]
    ) -> Optional[CrashEvent]:
        """Extract detailed crash information"""
        try:
            crash_line = lines[start_idx]
            
            # Extract timestamp
            timestamp_match = re.search(r'(\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d+)', crash_line)
            timestamp = timestamp_match.group(1) if timestamp_match else datetime.now().isoformat()
            
            # Extract PID
            pid_match = re.search(r'\(\s*(\d+)\)', crash_line)
            pid = int(pid_match.group(1)) if pid_match else None
            
            # Extract package name
            package_name = "unknown"
            for i in range(max(0, start_idx - 10), min(len(lines), start_idx + 10)):
                pkg_match = re.search(r'([a-z][a-z0-9_]*(\.[a-z0-9_]+)+)', lines[i])
                if pkg_match:
                    package_name = pkg_match.group(1)
                    break
            
            # Filter by package if specified
            if package_filter and package_filter not in package_name:
                return None
            
            # Extract message
            message = crash_line.strip()
            
            # Extract stack trace
            stack_trace = []
            for i in range(start_idx, min(len(lines), start_idx + 50)):
                line = lines[i].strip()
                if not line:
                    break
                if 'at ' in line or 'Caused by:' in line or 'Exception' in line:
                    stack_trace.append(line)
            
            # Determine severity
            severity = self._determine_severity(crash_type, message)
            
            return CrashEvent(
                timestamp=timestamp,
                crash_type=crash_type,
                package_name=package_name,
                message=message,
                stack_trace=stack_trace,
                pid=pid,
                severity=severity
            )
            
        except Exception as e:
            logger.error(f"Error extracting crash info: {e}")
            return None
    
    def _determine_severity(self, crash_type: CrashType, message: str) -> str:
        """Determine crash severity"""
        if crash_type in [CrashType.FATAL, CrashType.ANR, CrashType.NATIVE_CRASH]:
            return "critical"
        elif crash_type == CrashType.OOM:
            return "high"
        elif "NullPointerException" in message or "IllegalStateException" in message:
            return "high"
        else:
            return "medium"
    
    def detect_freeze(self, logcat_output: str, anr_timeout: int = 10) -> Optional[CrashEvent]:
        """Detect if app has frozen"""
        # Look for Input dispatching timeout
        freeze_patterns = [
            r'Input event dispatching timed out',
            r'Skipped \d+ frames',
        ]
        
        for pattern in freeze_patterns:
            if re.search(pattern, logcat_output, re.IGNORECASE):
                return CrashEvent(
                    timestamp=datetime.now().isoformat(),
                    crash_type=CrashType.FREEZE,
                    package_name="unknown",
                    message="App appears to be frozen or unresponsive",
                    stack_trace=[],
                    severity="high"
                )
        
        return None
    
    def get_crash_statistics(self) -> Dict:
        """Get crash statistics"""
        if not self.crashes:
            return {
                "total_crashes": 0,
                "by_type": {},
                "by_severity": {},
                "critical_count": 0
            }
        
        by_type = {}
        by_severity = {}
        
        for crash in self.crashes:
            # Count by type
            crash_type = crash.crash_type
            by_type[crash_type] = by_type.get(crash_type, 0) + 1
            
            # Count by severity
            severity = crash.severity
            by_severity[severity] = by_severity.get(severity, 0) + 1
        
        return {
            "total_crashes": len(self.crashes),
            "by_type": by_type,
            "by_severity": by_severity,
            "critical_count": by_severity.get("critical", 0) + by_severity.get("high", 0),
            "recent_crashes": [crash.to_dict() for crash in self.crashes[-5:]]
        }
    
    def save_crash_report(self, output_path: str):
        """Save crash report to file"""
        try:
            report = {
                "generated_at": datetime.now().isoformat(),
                "statistics": self.get_crash_statistics(),
                "crashes": [crash.to_dict() for crash in self.crashes]
            }
            
            with open(output_path, 'w') as f:
                json.dump(report, f, indent=2)
                
            logger.info(f"Crash report saved to {output_path}")
            
        except Exception as e:
            logger.error(f"Error saving crash report: {e}")
    
    def clear_crashes(self):
        """Clear crash history"""
        self.crashes.clear()
        logger.info("Crash history cleared")
