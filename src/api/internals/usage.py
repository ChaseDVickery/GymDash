import psutil
import shutil
import os
from pydantic import BaseModel

# Detailed usage statistics measure the usage
# of this process against the total resources
# of the system
class UsageStatsDetailed(BaseModel):
    cpus_percent:       list[float] = []
    cpu_percent_proc:   float       = 0
    cpu_count:          int         = 0
    memory_phys_proc:   int         = 0
    memory_virt_proc:   int         = 0
    memory_total:       int         = 0
    memory_available:   int         = 0
    disk_total:         int         = 0
    disk_available:     int         = 0

# Simple usage statistics measure the general
# usage of the system, not specific to this
# process
class UsageStatsSimple(BaseModel):
    cpu_percent:        float   = 0       
    memory_total:       int     = 0
    memory_available:   int     = 0
    disk_total:         int     = 0
    disk_available:     int     = 0

def get_usage_detailed():
    # Get the process with os.getpid by default
    p = psutil.Process()
    # Speedup data retrievel with oneshot context
    with p.oneshot():
        return UsageStatsDetailed(
            cpus_percent = psutil.cpu_percent(interval=None, percpu=True),
            cpu_percent_proc = p.cpu_percent(interval=None),
            cpu_count = psutil.cpu_count(),
            memory_phys_proc = p.memory_info().rss,
            memory_virt_proc = p.memory_info().vms,
            memory_total = psutil.virtual_memory().total,
            memory_available = psutil.virtual_memory().available,
            disk_total = shutil.disk_usage(__file__).total,
            disk_available = shutil.disk_usage(__file__).free
        )
    
def get_usage_simple():
    return UsageStatsSimple(
        cpu_percent = psutil.cpu_percent(interval=None, percpu=False),
        memory_total = psutil.virtual_memory().total,
        memory_available = psutil.virtual_memory().available,
        disk_total = shutil.disk_usage(__file__).total,
        disk_available = shutil.disk_usage(__file__).free
    )