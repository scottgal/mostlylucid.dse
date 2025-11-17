#!/usr/bin/env python3
"""
Platform Information Tool

Gathers comprehensive information about the underlying platform including:
- Operating system and platform details
- CPU information (cores, frequency, usage)
- Memory information (total, available, usage)
- GPU information (if available)
- Disk information
- Running processes (optional)
- Network interfaces (optional)

Usage:
    echo '{"detail_level": "standard"}' | python platform_info.py

Input (JSON via stdin):
    detail_level:       Level of detail (basic, standard, detailed, full). Default: standard
    include_processes:  Include running processes information. Default: false
    include_network:    Include network interface information. Default: false

Examples:
    echo '{"detail_level": "basic"}' | python platform_info.py
    echo '{"detail_level": "standard"}' | python platform_info.py
    echo '{"detail_level": "detailed", "include_processes": true}' | python platform_info.py
    echo '{"detail_level": "full"}' | python platform_info.py
"""

import sys
import json
import platform
import os
from typing import Dict, Any, List, Optional
from datetime import datetime


class PlatformInfoGatherer:
    """Gathers comprehensive platform information."""

    def __init__(self):
        self.info = {}

    def get_basic_info(self) -> Dict[str, Any]:
        """Get basic platform information."""
        return {
            "platform": platform.system(),
            "platform_release": platform.release(),
            "platform_version": platform.version(),
            "architecture": platform.machine(),
            "hostname": platform.node(),
            "processor": platform.processor(),
            "python_version": platform.python_version(),
        }

    def get_cpu_info(self, detailed: bool = False) -> Dict[str, Any]:
        """Get CPU information."""
        cpu_info = {}

        try:
            import psutil

            # Basic CPU info
            cpu_info["physical_cores"] = psutil.cpu_count(logical=False)
            cpu_info["logical_cores"] = psutil.cpu_count(logical=True)

            if detailed:
                # CPU frequency
                cpu_freq = psutil.cpu_freq()
                if cpu_freq:
                    cpu_info["frequency_mhz"] = {
                        "current": round(cpu_freq.current, 2),
                        "min": round(cpu_freq.min, 2) if cpu_freq.min else None,
                        "max": round(cpu_freq.max, 2) if cpu_freq.max else None,
                    }

                # CPU usage per core
                cpu_percent = psutil.cpu_percent(interval=0.1, percpu=True)
                cpu_info["usage_per_core"] = [round(x, 2) for x in cpu_percent]
                cpu_info["usage_total"] = round(psutil.cpu_percent(interval=0.1), 2)

                # CPU stats
                cpu_stats = psutil.cpu_stats()
                cpu_info["stats"] = {
                    "ctx_switches": cpu_stats.ctx_switches,
                    "interrupts": cpu_stats.interrupts,
                    "soft_interrupts": cpu_stats.soft_interrupts if hasattr(cpu_stats, 'soft_interrupts') else None,
                    "syscalls": cpu_stats.syscalls if hasattr(cpu_stats, 'syscalls') else None,
                }
            else:
                cpu_info["usage_percent"] = round(psutil.cpu_percent(interval=0.1), 2)

        except ImportError:
            # Fallback without psutil
            cpu_info["cores"] = os.cpu_count()
            cpu_info["note"] = "Install psutil for detailed CPU information"

        return cpu_info

    def get_memory_info(self, detailed: bool = False) -> Dict[str, Any]:
        """Get memory information."""
        memory_info = {}

        try:
            import psutil

            # Virtual memory
            vmem = psutil.virtual_memory()
            memory_info["total_gb"] = round(vmem.total / (1024**3), 2)
            memory_info["available_gb"] = round(vmem.available / (1024**3), 2)
            memory_info["used_gb"] = round(vmem.used / (1024**3), 2)
            memory_info["usage_percent"] = round(vmem.percent, 2)
            memory_info["free_gb"] = round(vmem.free / (1024**3), 2)

            if detailed:
                memory_info["buffers_gb"] = round(vmem.buffers / (1024**3), 2) if hasattr(vmem, 'buffers') else None
                memory_info["cached_gb"] = round(vmem.cached / (1024**3), 2) if hasattr(vmem, 'cached') else None
                memory_info["shared_gb"] = round(vmem.shared / (1024**3), 2) if hasattr(vmem, 'shared') else None

                # Swap memory
                swap = psutil.swap_memory()
                memory_info["swap"] = {
                    "total_gb": round(swap.total / (1024**3), 2),
                    "used_gb": round(swap.used / (1024**3), 2),
                    "free_gb": round(swap.free / (1024**3), 2),
                    "usage_percent": round(swap.percent, 2),
                }

        except ImportError:
            memory_info["note"] = "Install psutil for memory information"

        return memory_info

    def get_gpu_info(self) -> Dict[str, Any]:
        """Get GPU information if available."""
        gpu_info = {"available": False, "devices": []}

        # Try NVIDIA GPUs first
        try:
            import pynvml

            pynvml.nvmlInit()
            device_count = pynvml.nvmlDeviceGetCount()
            gpu_info["available"] = device_count > 0
            gpu_info["vendor"] = "NVIDIA"

            for i in range(device_count):
                handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                name = pynvml.nvmlDeviceGetName(handle)
                # Handle both string and bytes return types
                if isinstance(name, bytes):
                    name = name.decode('utf-8')

                memory_info = pynvml.nvmlDeviceGetMemoryInfo(handle)

                device_info = {
                    "index": i,
                    "name": name,
                    "memory_total_gb": round(memory_info.total / (1024**3), 2),
                    "memory_used_gb": round(memory_info.used / (1024**3), 2),
                    "memory_free_gb": round(memory_info.free / (1024**3), 2),
                    "memory_usage_percent": round((memory_info.used / memory_info.total) * 100, 2),
                }

                try:
                    utilization = pynvml.nvmlDeviceGetUtilizationRates(handle)
                    device_info["gpu_utilization_percent"] = utilization.gpu
                    device_info["memory_utilization_percent"] = utilization.memory
                except:
                    pass

                try:
                    temperature = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
                    device_info["temperature_c"] = temperature
                except:
                    pass

                gpu_info["devices"].append(device_info)

            pynvml.nvmlShutdown()
            return gpu_info

        except (ImportError, Exception):
            pass

        # Try GPUtil as alternative
        try:
            import GPUtil

            gpus = GPUtil.getGPUs()
            if gpus:
                gpu_info["available"] = True
                for gpu in gpus:
                    device_info = {
                        "index": gpu.id,
                        "name": gpu.name,
                        "memory_total_gb": round(gpu.memoryTotal / 1024, 2),
                        "memory_used_gb": round(gpu.memoryUsed / 1024, 2),
                        "memory_free_gb": round(gpu.memoryFree / 1024, 2),
                        "memory_usage_percent": round(gpu.memoryUtil * 100, 2),
                        "gpu_utilization_percent": round(gpu.load * 100, 2),
                        "temperature_c": gpu.temperature,
                    }
                    gpu_info["devices"].append(device_info)
                return gpu_info
        except (ImportError, Exception):
            pass

        gpu_info["note"] = "No GPU detected or GPU libraries not installed (pynvml/GPUtil)"
        return gpu_info

    def get_disk_info(self, detailed: bool = False) -> Dict[str, Any]:
        """Get disk information."""
        disk_info = {"partitions": []}

        try:
            import psutil

            partitions = psutil.disk_partitions()
            for partition in partitions:
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    partition_info = {
                        "device": partition.device,
                        "mountpoint": partition.mountpoint,
                        "fstype": partition.fstype,
                        "total_gb": round(usage.total / (1024**3), 2),
                        "used_gb": round(usage.used / (1024**3), 2),
                        "free_gb": round(usage.free / (1024**3), 2),
                        "usage_percent": round(usage.percent, 2),
                    }

                    if detailed:
                        partition_info["opts"] = partition.opts

                    disk_info["partitions"].append(partition_info)
                except PermissionError:
                    # Skip partitions we can't access
                    continue

            if detailed:
                # Disk I/O stats
                try:
                    disk_io = psutil.disk_io_counters()
                    if disk_io:
                        disk_info["io_stats"] = {
                            "read_count": disk_io.read_count,
                            "write_count": disk_io.write_count,
                            "read_bytes_gb": round(disk_io.read_bytes / (1024**3), 2),
                            "write_bytes_gb": round(disk_io.write_bytes / (1024**3), 2),
                        }
                except:
                    pass

        except ImportError:
            disk_info["note"] = "Install psutil for disk information"

        return disk_info

    def get_process_info(self, top_n: int = 10) -> Dict[str, Any]:
        """Get information about running processes."""
        process_info = {"count": 0, "top_processes": []}

        try:
            import psutil

            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'status']):
                try:
                    pinfo = proc.info
                    processes.append(pinfo)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

            process_info["count"] = len(processes)

            # Sort by CPU usage
            processes_by_cpu = sorted(
                [p for p in processes if p.get('cpu_percent', 0) > 0],
                key=lambda x: x.get('cpu_percent', 0),
                reverse=True
            )[:top_n]

            # Sort by memory usage
            processes_by_mem = sorted(
                processes,
                key=lambda x: x.get('memory_percent', 0),
                reverse=True
            )[:top_n]

            process_info["top_by_cpu"] = [
                {
                    "pid": p['pid'],
                    "name": p['name'],
                    "cpu_percent": round(p.get('cpu_percent', 0), 2),
                    "memory_percent": round(p.get('memory_percent', 0), 2),
                    "status": p.get('status', 'unknown')
                }
                for p in processes_by_cpu
            ]

            process_info["top_by_memory"] = [
                {
                    "pid": p['pid'],
                    "name": p['name'],
                    "cpu_percent": round(p.get('cpu_percent', 0), 2),
                    "memory_percent": round(p.get('memory_percent', 0), 2),
                    "status": p.get('status', 'unknown')
                }
                for p in processes_by_mem
            ]

        except ImportError:
            process_info["note"] = "Install psutil for process information"

        return process_info

    def get_network_info(self) -> Dict[str, Any]:
        """Get network interface information."""
        network_info = {"interfaces": []}

        try:
            import psutil

            # Network interfaces
            if_addrs = psutil.net_if_addrs()
            if_stats = psutil.net_if_stats()

            for interface_name, addresses in if_addrs.items():
                interface_info = {
                    "name": interface_name,
                    "addresses": []
                }

                for addr in addresses:
                    addr_info = {
                        "family": str(addr.family),
                        "address": addr.address,
                    }
                    if addr.netmask:
                        addr_info["netmask"] = addr.netmask
                    if addr.broadcast:
                        addr_info["broadcast"] = addr.broadcast
                    interface_info["addresses"].append(addr_info)

                # Add interface stats
                if interface_name in if_stats:
                    stats = if_stats[interface_name]
                    interface_info["is_up"] = stats.isup
                    interface_info["speed_mbps"] = stats.speed

                network_info["interfaces"].append(interface_info)

            # Network I/O stats
            try:
                net_io = psutil.net_io_counters()
                network_info["io_stats"] = {
                    "bytes_sent_gb": round(net_io.bytes_sent / (1024**3), 2),
                    "bytes_recv_gb": round(net_io.bytes_recv / (1024**3), 2),
                    "packets_sent": net_io.packets_sent,
                    "packets_recv": net_io.packets_recv,
                    "errors_in": net_io.errin,
                    "errors_out": net_io.errout,
                    "drop_in": net_io.dropin,
                    "drop_out": net_io.dropout,
                }
            except:
                pass

        except ImportError:
            network_info["note"] = "Install psutil for network information"

        return network_info

    def get_boot_time(self) -> Optional[str]:
        """Get system boot time."""
        try:
            import psutil
            from datetime import datetime

            boot_time = psutil.boot_time()
            return datetime.fromtimestamp(boot_time).isoformat()
        except ImportError:
            return None

    def gather_info(
        self,
        detail_level: str = "standard",
        include_processes: bool = False,
        include_network: bool = False
    ) -> Dict[str, Any]:
        """
        Gather platform information based on detail level.

        Args:
            detail_level: One of 'basic', 'standard', 'detailed', 'full'
            include_processes: Include running process information
            include_network: Include network interface information

        Returns:
            Dictionary with platform information
        """
        result = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "detail_level": detail_level,
        }

        # All levels include basic platform info
        result["platform"] = self.get_basic_info()

        if detail_level == "basic":
            # Just platform and basic CPU/memory
            result["cpu"] = {"cores": os.cpu_count()}
            try:
                import psutil
                vmem = psutil.virtual_memory()
                result["memory"] = {
                    "total_gb": round(vmem.total / (1024**3), 2),
                    "available_gb": round(vmem.available / (1024**3), 2),
                    "usage_percent": round(vmem.percent, 2),
                }
            except ImportError:
                result["memory"] = {"note": "Install psutil for memory information"}

        elif detail_level == "standard":
            # Platform, CPU, memory, and disk
            result["cpu"] = self.get_cpu_info(detailed=False)
            result["memory"] = self.get_memory_info(detailed=False)
            result["disk"] = self.get_disk_info(detailed=False)
            result["gpu"] = self.get_gpu_info()

        elif detail_level == "detailed":
            # Everything in standard plus more details
            result["cpu"] = self.get_cpu_info(detailed=True)
            result["memory"] = self.get_memory_info(detailed=True)
            result["disk"] = self.get_disk_info(detailed=True)
            result["gpu"] = self.get_gpu_info()
            boot_time = self.get_boot_time()
            if boot_time:
                result["boot_time"] = boot_time

        elif detail_level == "full":
            # Everything
            result["cpu"] = self.get_cpu_info(detailed=True)
            result["memory"] = self.get_memory_info(detailed=True)
            result["disk"] = self.get_disk_info(detailed=True)
            result["gpu"] = self.get_gpu_info()
            boot_time = self.get_boot_time()
            if boot_time:
                result["boot_time"] = boot_time

            # Full always includes processes and network
            include_processes = True
            include_network = True

        # Optional additions
        if include_processes:
            result["processes"] = self.get_process_info()

        if include_network:
            result["network"] = self.get_network_info()

        # Add helpful summary for decision making
        result["summary"] = self._generate_summary(result)

        return result

    def _generate_summary(self, info: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a helpful summary for decision making."""
        summary = {
            "platform_type": info["platform"]["platform"],
            "is_windows": info["platform"]["platform"] == "Windows",
            "is_linux": info["platform"]["platform"] == "Linux",
            "is_macos": info["platform"]["platform"] == "Darwin",
        }

        # Memory status
        if "memory" in info and "usage_percent" in info["memory"]:
            mem_usage = info["memory"]["usage_percent"]
            summary["memory_status"] = (
                "critical" if mem_usage > 90
                else "high" if mem_usage > 75
                else "moderate" if mem_usage > 50
                else "low"
            )
            summary["low_memory"] = mem_usage > 75

        # GPU availability
        if "gpu" in info:
            summary["has_gpu"] = info["gpu"].get("available", False)
            summary["gpu_count"] = len(info["gpu"].get("devices", []))

        # CPU cores
        if "cpu" in info:
            cores = info["cpu"].get("logical_cores") or info["cpu"].get("cores")
            if cores:
                summary["cpu_cores"] = cores
                summary["low_cpu_cores"] = cores < 4

        return summary


def main():
    """Main entry point."""
    try:
        # Read input from stdin
        input_data = json.load(sys.stdin)

        # Get parameters with defaults
        detail_level = input_data.get("detail_level", "standard")
        include_processes = input_data.get("include_processes", False)
        include_network = input_data.get("include_network", False)

        # Validate detail level
        if detail_level not in ["basic", "standard", "detailed", "full"]:
            detail_level = "standard"

        gatherer = PlatformInfoGatherer()
        result = gatherer.gather_info(
            detail_level=detail_level,
            include_processes=include_processes,
            include_network=include_network
        )

        print(json.dumps(result, indent=2))

    except json.JSONDecodeError as e:
        print(json.dumps({
            "error": "Invalid JSON input",
            "detail": str(e)
        }), file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(json.dumps({
            "error": str(e),
            "type": type(e).__name__
        }), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
