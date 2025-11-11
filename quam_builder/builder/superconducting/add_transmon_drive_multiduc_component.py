from typing import Dict, Union
from quam_builder.builder.qop_connectivity.channel_ports import (
    iq_out_channel_ports,
    mw_out_channel_ports,
)
from quam_builder.architecture.superconducting.components.xy_drive import (
    XYDriveIQ,
    XYDriveMW,
    XYDriveMW_multiDUC,
)
from quam_builder.builder.qop_connectivity.get_digital_outputs import (
    get_digital_outputs,
)
from quam_builder.architecture.superconducting.qubit import (
    FixedFrequencyTransmon,
    FluxTunableTransmon,
)
from qualang_tools.addons.calibration.calibrations import unit


u = unit(coerce_to_integer=True)


def get_band_from_freq(freq: float) -> int:
    """Determine the MW fem DAC band corresponding to a given frequency.
    
    Args:
        freq (float): The frequency in Hz.
        
    Returns:
        int: The Nyquist band number.
            - 1 if 50 MHz <= freq < 5.5 GHz
            - 2 if 4.5 GHz <= freq < 7.5 GHz
            - 3 if 6.5 GHz <= freq <= 10.5 GHz
            
    Raises:
        ValueError: If the frequency is outside the MW fem bandwidth [50 MHz, 10.5 GHz].
    """
    if 50e6 <= freq < 5.5e9:
        return 1
    elif 4.5e9 <= freq < 7.5e9:
        return 2
    elif 6.5e9 <= freq <= 10.5e9:
        return 3
    else:
        raise ValueError(f"The specified frequency {freq} Hz is outside of the MW fem bandwidth [50 MHz, 10.5 GHz]")


def add_transmon_drive_multiduc_component(
    transmon: Union[FixedFrequencyTransmon, FluxTunableTransmon],
    wiring_path: str,
    ports: Dict[str, str],
    upconverter_id: int = 2,
    component_name: str = "xy2",
):
    """Adds a multi-upconverter drive component to a transmon qubit.
    
    This function adds a second drive component that shares the same physical port
    as the existing xy drive but uses a different upconverter. This enables
    multi-frequency drive capabilities on the same physical line.
    
    Args:
        transmon (Union[FixedFrequencyTransmon, FluxTunableTransmon]): The transmon qubit 
            to which the multi-upconverter drive component will be added.
        wiring_path (str): The path to the wiring configuration.
        ports (Dict[str, str]): A dictionary mapping port names to their respective configurations.
            Required keys: 'opx_output'
        upconverter_id (int): The upconverter ID to use for this component (default: 2).
        component_name (str): The name of the component attribute to add to the transmon (default: "xy2").
        
    Raises:
        ValueError: If the port keys do not match any implemented mapping or if required
            configuration is missing.
        RuntimeError: If the existing xy component doesn't support multi-upconverter setup.
    """
    digital_outputs = get_digital_outputs(wiring_path, ports)
    
    if all(key in ports for key in mw_out_channel_ports):
        # Check if transmon already has an xy component
        if not hasattr(transmon, 'xy') or transmon.xy is None:
            raise RuntimeError(
                f"Cannot add multi-upconverter component to {transmon.name}: "
                "No existing xy component found. Multi-upconverter setup requires "
                "an existing xy component to share the port."
            )
        
        # Check if existing xy component is MW-based
        if not isinstance(transmon.xy, XYDriveMW):
            raise RuntimeError(
                f"Cannot add multi-upconverter component to {transmon.name}: "
                "Existing xy component must be XYDriveMW type for multi-upconverter setup."
            )
        
        # Create the multi-upconverter drive component using the same wiring path as existing xy component
        # This ensures proper port sharing for multi-upconverter functionality
        multiduc_component = XYDriveMW_multiDUC(
            opx_output=f"{wiring_path}/opx_output",  # Use the same wiring path as existing xy component
            digital_outputs=digital_outputs,
            RF_frequency=None,
            upconverter=upconverter_id,  # Specify which upconverter to use
            intermediate_frequency=None,  # Will be inferred
        )
        
        # Add the component to the transmon
        setattr(transmon, component_name, multiduc_component)
        
        print(f"✓ Multi-upconverter component '{component_name}' added to {transmon.name}")
        print(f"  - Uses upconverter {upconverter_id}")
        print(f"  - Shares port with existing xy component")
        
    else:
        raise ValueError(
            f"Unimplemented mapping of port keys to channel for ports: {ports}. "
            "Multi-upconverter setup currently only supports MW output channels."
        )
