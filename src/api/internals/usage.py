import psutil
import shutil
import os
import GPUtil
from pydantic import BaseModel

mega2bytes = pow(2, 20)
usage_interval = None

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

class UsageStatsGPU(BaseModel):
    gpu_count:          int     = 0
    load:               float   = 0
    memory_total:       int     = 0
    memory_available:   int     = 0

def get_usage_detailed():
    # Get the process with os.getpid by default
    p = psutil.Process()
    # Speedup data retrievel with oneshot context
    with p.oneshot():
        return UsageStatsDetailed(
            cpus_percent        = psutil.cpu_percent(interval=usage_interval, percpu=True),
            cpu_percent_proc    = p.cpu_percent(interval=usage_interval),
            cpu_count           = psutil.cpu_count(),
            memory_phys_proc    = p.memory_info().rss,
            memory_virt_proc    = p.memory_info().vms,
            memory_total        = psutil.virtual_memory().total,
            memory_available    = psutil.virtual_memory().available,
            disk_total          = shutil.disk_usage(__file__).total,
            disk_available      = shutil.disk_usage(__file__).free
        )
    
def get_usage_simple():
    return UsageStatsSimple(
        cpu_percent         = psutil.cpu_percent(interval=usage_interval, percpu=False),
        memory_total        = psutil.virtual_memory().total,
        memory_available    = psutil.virtual_memory().available,
        disk_total          = shutil.disk_usage(__file__).total,
        disk_available      = shutil.disk_usage(__file__).free
    )

def get_usage_gpu():
    gpus = GPUtil.getGPUs()
    count           = len(gpus)
    mem_total       = 0
    mem_available   = 0
    gpu_load        = 0
    for gpu in gpus:
        mem_total       += gpu.memoryTotal
        mem_available   += gpu.memoryFree
        gpu_load        += gpu.load
    gpu_load *= 100.0
    gpu_load /= count if count != 0 else 1
    return UsageStatsGPU(
        gpu_count           = count,
        load                = gpu_load,
        memory_total        = mega2bytes * mem_total,
        memory_available    = mega2bytes * mem_available
    )