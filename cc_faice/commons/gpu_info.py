class InsufficientGPUError(Exception):
    pass


class GPUDevice:
    """
    Represents a GPU Device
    """
    def __init__(self, device_id, vram):
        """
        :param vram: The vram of this GPU in bytes
        """
        self.device_id = device_id
        self.vram = vram


class GPURequirement:
    """
    Represents a GPU Requirement
    """
    def __init__(self, min_vram=None):
        """
        :param min_vram: The minimal vram needed for this device in bytes
                         If None, no vram limitation is used.
        """
        self.min_vram = min_vram

    def is_sufficient(self, device):
        """
        Returns whether the device is sufficient for this requirement.

        :param device: A GPUDevice instance.
        :type device: GPUDevice
        :return: True if the requirement is fulfilled otherwise False
        """

        sufficient = True
        if (self.min_vram is not None) and (device.vram < self.min_vram):
            sufficient = False

        return sufficient


def get_cuda_devices():
    """
    Imports pycuda at runtime and reads GPU information.
    :return: A list of available cuda GPUs.
    """

    devices = []

    try:
        import pycuda.autoinit
        import pycuda.driver as cuda

        for device_id in range(cuda.Device.count()):
            vram = cuda.Device(device_id).total_memory()

            devices.append(GPUDevice(device_id, vram))
    except ImportError:
        # TODO: raise an exception here, indicating that pycuda could not be imported
        return []

    return devices


def no_devices():
    """
    Returns an empty list
    :return: []
    """
    return []


""" maps docker engines to functions returning gpu devices """
DEVICE_INFORMATION_MAP = {
    'docker': no_devices,
    'nvidia-docker': get_cuda_devices
}


def get_devices(engine):
    """
    Returns GPU device information.

    :param engine: The used docker engine.
    :return: A list of available devices
    """

    return DEVICE_INFORMATION_MAP[engine]()


def search_device(requirement, devices):
    """
    Returns a sufficient device or None

    :param requirement: The requirement to fulfill
    :param devices: The list of available devices
    :return: A device from the list
    """

    for device in devices:
        if requirement.is_sufficient(device):
            return device
    return None


def get_gpus(engine, requirements=[GPURequirement()]):
    """
    Determines sufficient GPUs for the given requirements and returns a list of Device IDs.
    If no GPUs could be found or if there aren't sufficient GPUs a InsufficientGPUException is thrown.

    :param engine: The used docker engine; one of 'docker' or 'nvidia-docker'
    :param requirements: A list of GPURequirements

    :return: A list of sufficient devices
    """

    if not requirements:
        return []

    available_devices = get_devices(engine)

    used_devices = []

    for req in requirements:
        dev = search_device(req, available_devices)
        if dev:
            used_devices.append(dev)
            available_devices.remove(dev)
        else:
            raise InsufficientGPUError("Not all GPU requirements could be fulfilled.")

    return used_devices
