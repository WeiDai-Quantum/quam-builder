from typing import Optional

from quam.core import quam_dataclass
from quam.components.channels import IQChannel, MWChannel

from quam_builder.tools.power_tools import (
    calculate_voltage_scaling_factor,
    set_output_power_mw_channel,
    get_output_power_mw_channel,
    set_output_power_iq_channel,
    get_output_power_iq_channel,
)


__all__ = ["XYDriveIQ", "XYDriveMW", "XYDriveMW_multiDUC"]


@quam_dataclass
class XYDriveBase:
    """
    QUAM component for a XY drive line.
    """

    @staticmethod
    def calculate_voltage_scaling_factor(
        fixed_power_dBm: float, target_power_dBm: float
    ):
        """
        Calculate the voltage scaling factor required to scale fixed power to target power.

        Parameters:
        fixed_power_dBm (float): The fixed power in dBm.
        target_power_dBm (float): The target power in dBm.

        Returns:
        float: The voltage scaling factor.
        """
        return calculate_voltage_scaling_factor(fixed_power_dBm, target_power_dBm)


@quam_dataclass
class XYDriveIQ(IQChannel, XYDriveBase):
    """
    QUAM component for a XY drive line through an IQ channel.
    """

    intermediate_frequency: int = "#./inferred_intermediate_frequency"

    @property
    def upconverter_frequency(self):
        """Returns the up-converter/LO frequency in Hz."""
        return self.LO_frequency

    def get_output_power(self, operation, Z=50) -> float:
        """
        Calculate the output power in dBm of the specified operation.

        Parameters:
            operation (str): The name of the operation to retrieve the amplitude.
            Z (float): The impedance in ohms. Default is 50 ohms.

        Returns:
            float: The output power in dBm.

        The function calculates the output power based on the amplitude of the specified operation and the gain of the
        frequency up-converter. It converts the amplitude to dBm using the specified impedance.
        """
        return get_output_power_iq_channel(self, operation, Z)

    def set_output_power(
        self,
        power_in_dbm: float,
        gain: Optional[int] = None,
        max_amplitude: Optional[float] = None,
        Z: int = 50,
        operation: Optional[str] = "readout",
    ):
        """
        Configure the output power for a specific operation by setting the gain or amplitude.
        Note that exactly one of `gain` or `amplitude` must be specified and the function calculates
        the other parameter specifically to meet the desired output power.

        Parameters:
            power_in_dbm (float): Desired output power in dBm.
            gain (Optional[int]): Optional gain in dB to set, must be within [-20, 20].
            max_amplitude (Optional[float]): Optional pulse amplitude in volts, must be within [-0.5, 0.5).
            Z (int): Impedance in ohms, default is 50.
            operation (Optional[str]): Name of the operation to configure, default is "readout".

        Raises:
            RuntimeError: If neither nor both `gain` and `amplitude` are specified.
            ValueError: If `gain` or `amplitude` is outside their valid ranges.

        """
        return set_output_power_iq_channel(
            self, power_in_dbm, gain, max_amplitude, Z, operation
        )


@quam_dataclass
class XYDriveMW(MWChannel, XYDriveBase):
    intermediate_frequency: float = "#./inferred_intermediate_frequency"

    @property
    def upconverter_frequency(self):
        """Returns the up-converter/LO frequency in Hz."""
        return self.opx_output.upconverter_frequency

    def get_output_power(self, operation, Z=50) -> float:
        """
        Calculate the output power in dBm of the specified operation.

        Parameters:
            operation (str): The name of the operation to retrieve the amplitude.
            Z (float): The impedance in ohms. Default is 50 ohms.

        Returns:
            float: The output power in dBm.

        The function calculates the output power based on the full-scale power in dBm and the amplitude of the
        specified operation.
        """
        return get_output_power_mw_channel(self, operation, Z)

    def set_output_power(
        self,
        power_in_dbm: float,
        full_scale_power_dbm: Optional[int] = None,
        max_amplitude: float = 1,
        operation: str = "readout",
    ):
        """
        Sets the power level in dBm for a specified operation, increasing the full-scale power
        in 3 dB steps if necessary until it covers the target power level, then scaling the
        given operation’s amplitude to match exactly the target power level.

        Parameters:
            power_in_dbm (float): The target power level in dBm for the operation.
            operation (str): The operation for which the power setting is applied.
            full_scale_power_dbm (Optional[int]): The full-scale power in dBm within [-41, 10] in 3 dB increments.
            max_amplitude (Optional[float]):
        """
        return set_output_power_mw_channel(
            self, power_in_dbm, operation, full_scale_power_dbm, max_amplitude
        )




# Wei Dai added 2025-10-24
@quam_dataclass
class XYDriveMW_multiDUC(MWChannel, XYDriveBase):
    """
    QUAM component for a XY drive line with multi-upconverter support.
    
    This class extends XYDriveMW to support multiple upconverters on the same
    physical port, enabling multi-frequency drive capabilities.
    """
    
    intermediate_frequency: float = "#./inferred_intermediate_frequency"

    def __post_init__(self):
        """Validate DUC frequency zone constraints after initialization."""
        super().__post_init__()
        
        # Validate frequencies if they are available
        if hasattr(self, 'RF_frequency') and self.RF_frequency is not None:
            if hasattr(self, 'intermediate_frequency') and self.intermediate_frequency is not None:
                self._validate_duc_frequency_zone(self.RF_frequency, self.intermediate_frequency)

    def _validate_duc_frequency_zone(self, rf_frequency: float, intermediate_frequency: float) -> None:
        """Validate DUC (Digital Upconverter) frequency zone constraints.
        
        Args:
            rf_frequency (float): RF frequency in Hz
            intermediate_frequency (float): Intermediate frequency in Hz
            
        Raises:
            ValueError: If frequencies are outside valid ranges
        """
        # Validate RF frequency band [50 MHz, 10.5 GHz]
        if not (50e6 <= rf_frequency <= 10.5e9):
            raise ValueError(
                f"RF frequency {rf_frequency/1e9:.3f} GHz is outside the MW FEM bandwidth "
                f"[50 MHz, 10.5 GHz]"
            )
        
        # Validate intermediate frequency [-400 MHz, 400 MHz]
        if not (-400e6 <= intermediate_frequency <= 400e6):
            raise ValueError(
                f"Intermediate frequency {intermediate_frequency/1e6:.1f} MHz is outside "
                f"the valid range [-400 MHz, 400 MHz]"
            )
        
        # Validate upconverter frequency (RF - IF)
        upconverter_frequency = rf_frequency - intermediate_frequency
        if not (50e6 <= upconverter_frequency <= 10.5e9):
            raise ValueError(
                f"Upconverter frequency {upconverter_frequency/1e9:.3f} GHz is outside "
                f"the MW FEM bandwidth [50 MHz, 10.5 GHz]"
            )

    @property
    def upconverter_frequency(self):
        """Returns the up-converter/LO frequency in Hz for the specified upconverter."""
        return self.opx_output.upconverter_frequency

    def get_output_power(self, operation, Z=50) -> float:
        """
        Calculate the output power in dBm of the specified operation.

        Parameters:
            operation (str): The name of the operation to retrieve the amplitude.
            Z (float): The impedance in ohms. Default is 50 ohms.

        Returns:
            float: The output power in dBm.

        The function calculates the output power based on the full-scale power in dBm and the amplitude of the
        specified operation.
        """
        return get_output_power_mw_channel(self, operation, Z)

    def set_output_power(
        self,
        power_in_dbm: float,
        full_scale_power_dbm: Optional[int] = None,
        max_amplitude: float = 1,
        operation: str = "readout",
    ):
        """
        Sets the power level in dBm for a specified operation, increasing the full-scale power
        in 3 dB steps if necessary until it covers the target power level, then scaling the
        given operation's amplitude to match exactly the target power level.

        Parameters:
            power_in_dbm (float): The target power level in dBm for the operation.
            operation (str): The operation for which the power setting is applied.
            full_scale_power_dbm (Optional[int]): The full-scale power in dBm within [-41, 10] in 3 dB increments.
            max_amplitude (Optional[float]):
        """
        return set_output_power_mw_channel(
            self, power_in_dbm, operation, full_scale_power_dbm, max_amplitude
        )