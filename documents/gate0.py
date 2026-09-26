"""Memory-pressure gate. Prints one line, gate=GREEN|YELLOW|RED. Runs refuse to start unless GREEN, and red_sentinel.sh
kills a running job on RED. RED = kernel pressure level critical, or swap above KEV_GATE_SWAP_GB (default 8)."""
import os, re, subprocess
lvl = int(subprocess.run(["sysctl", "-n", "kern.memorystatus_vm_pressure_level"], capture_output=True, text=True).stdout.strip() or 1)
sw = subprocess.run(["sysctl", "-n", "vm.swapusage"], capture_output=True, text=True).stdout
used = re.search(r"used = ([\d.]+)([MG])", sw); used_gb = float(used.group(1)) / (1024 if used.group(2) == "M" else 1) if used else 0.0
lim = float(os.environ.get("KEV_GATE_SWAP_GB", 8))
g = "RED" if lvl >= 4 or used_gb > lim else ("YELLOW" if lvl == 2 else "GREEN")
print(f"gate={g} pressure_level={lvl} swap_used={used_gb:.1f}GB")
