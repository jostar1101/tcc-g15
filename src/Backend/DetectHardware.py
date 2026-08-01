from typing import Optional
from wmi import WMI # type: ignore

class DetectHardware:
    CPUFanIdx = 0
    GPUFanIdx = 1

    def __init__(self) -> None:
        self._wmi = WMI()

    def getHardwareName(self, fanIdx: int) -> Optional[str]:
        try:
            if fanIdx == self.CPUFanIdx:
                wmiClass = self._wmi.Win32_Processor
                wmiInst = wmiClass()[0]
                return wmiInst.Name.strip() if hasattr(wmiInst, 'Name') else None
            elif fanIdx == self.GPUFanIdx:
                wmiClass = self._wmi.Win32_VideoController
                gpus = wmiClass()
                if not gpus:
                    return None
                gpuInst = max(gpus, key=lambda inst: (inst.AdapterRAM & 0xFFFFFFFF) if isinstance(getattr(inst, 'AdapterRAM', None), int) else 0) # Assume the one with the largest memory is the main GPU
                return gpuInst.Name.strip() if hasattr(gpuInst, 'Name') else None
        except Exception as ex:
            print(f'DetectHardware: {ex}')
        return None