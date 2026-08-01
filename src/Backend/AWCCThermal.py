from typing import Optional, NewType
from Backend.AWCCWmiWrapper import AWCCWmiWrapper
from wmi import WMI # type: ignore
import ctypes
import time

class NoAWCCWMIClass(Exception):
    def __init__(self) -> None:
        super().__init__("AWCC WMI class not found in the system")

class CannotInstAWCCWMI(Exception):
    def __init__(self) -> None:
        super().__init__("Couldn't instantiate AWCC WMI class")

class AWCCThermal:
    Mode = AWCCWmiWrapper.ThermalMode
    ModeType = NewType("ModeType", AWCCWmiWrapper.ThermalMode)
    CPUFanIdx = 0
    GPUFanIdx = 1

    def __init__(self, awcc: Optional[AWCCWmiWrapper] = None) -> None:
        if awcc is None:
            try:
                awccClass = WMI(namespace="root\\WMI").AWCCWmiMethodFunction
            except Exception as ex:
                print(ex)
                raise NoAWCCWMIClass()
            try:
                awcc = AWCCWmiWrapper(awccClass()[0])
            except Exception as ex:
                print(ex)
                raise CannotInstAWCCWMI()
        self._awcc = awcc
        self._fanIdsAndRelatedSensorsIds = self._awcc.GetFanIdsAndRelatedSensorsIds()
        self._fanIds = [ id for id, _ in self._fanIdsAndRelatedSensorsIds ]
        self._sensorIds = [ id for _, ids in self._fanIdsAndRelatedSensorsIds for id in ids ]

    def getAllTemp(self) -> list[Optional[int]]:
        return [ self._awcc.GetSensorTemperature(sensorId) for sensorId in self._sensorIds ]

    def getAllFanRPM(self) -> list[Optional[int]]:
        return [ self._awcc.GetFanRPM(fanId) for fanId in self._fanIds ]

    def setAllFanSpeed(self, speed: int) -> bool:
        res = True
        for fanId in self._fanIds:
            if not self._awcc.SetAddonSpeedPercent(fanId, speed):
                res = False
        return res


    def getFanRelatedTemp(self, fanIdx: int) -> Optional[int]:
        if fanIdx >= len(self._fanIdsAndRelatedSensorsIds):
            return None
        return self._awcc.GetSensorTemperature(self._fanIdsAndRelatedSensorsIds[fanIdx][1][0])

    def getGPUTemp(self) -> Optional[int]:
        # GPU core temperature via NVML (same source as Task Manager).
        # The AWCC driver often reports bogus GPU temp on Dell G15.
        # Using ctypes against nvml.dll avoids spawning a subprocess every
        # second (which kept the CPU at full frequency on idle).
        if not hasattr(self, "_nvml"):
            self._nvml = None
            try:
                nvml = ctypes.WinDLL("nvml.dll")
                if nvml.nvmlInit() == 0:
                    nvml.nvmlDeviceGetHandleByIndex.argtypes = [ctypes.c_uint, ctypes.POINTER(ctypes.c_void_p)]
                    nvml.nvmlDeviceGetHandleByIndex.restype = ctypes.c_int
                    nvml.nvmlDeviceGetTemperature.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.POINTER(ctypes.c_uint)]
                    nvml.nvmlDeviceGetTemperature.restype = ctypes.c_int
                    self._nvml = nvml
            except Exception:
                self._nvml = None
        if self._nvml is not None:
            try:
                handle = ctypes.c_void_p()
                if self._nvml.nvmlDeviceGetHandleByIndex(0, ctypes.byref(handle)) == 0:
                    temp = ctypes.c_uint()
                    if self._nvml.nvmlDeviceGetTemperature(handle, 0, ctypes.byref(temp)) == 0:
                        return int(temp.value)
            except Exception:
                pass
        return self.getFanRelatedTemp(self.GPUFanIdx)

    def getFanRPM(self, fanIdx: int) -> Optional[int]:
        if fanIdx >= len(self._fanIdsAndRelatedSensorsIds):
            return None
        return self._awcc.GetFanRPM(self._fanIdsAndRelatedSensorsIds[fanIdx][0])

    def setFanSpeed(self, fanIdx: int, speed: int) -> bool:
        if fanIdx >= len(self._fanIdsAndRelatedSensorsIds):
            return False
        return self._awcc.SetAddonSpeedPercent(self._fanIdsAndRelatedSensorsIds[fanIdx][0], speed)

    def setMode(self, mode: ModeType) -> bool:
        return self._awcc.ApplyThermalMode(mode)
