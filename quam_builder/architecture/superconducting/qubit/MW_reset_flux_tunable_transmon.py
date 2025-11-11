from typing import Optional, Callable
from logging import getLogger

from quam.core import quam_dataclass
from qm.qua import (
    save,
    declare,
    fixed,
    assign,
    wait,
    while_,
    StreamType,
    if_,
    update_frequency,
    Math,
    Cast,
)

from quam_builder.architecture.superconducting.qubit.flux_tunable_transmon import (
    FluxTunableTransmon,
)
from quam_builder.architecture.superconducting.components.flux_line import FluxLine

__all__ = ["MWResetFluxTunableTransmon"]


@quam_dataclass
class MWResetFluxTunableTransmon(FluxTunableTransmon):
    """
    Flux tunable transmon qubit with MW reset capabilities.

    Attributes:
        resonator_frequency (float): The readout (lossy) resonator frequency, in Hz.
    """

    resonator_frequency: float = None

    def mw_reset(
        self,
        mw_pulse_name: str = "f0_g1_drive",
        pi_01_pulse_name: str = "GE_saturation",
        pi_12_pulse_name: str = "EF_saturation",
    ):
        """
        Perform MW reset of the qubit using microwave pulses.

        This function performs an MW reset by applying microwave pulses to drive the qubit
        to the ground state, followed by readout verification.

        Args:
            mw_pulse_name (str): The name of the MW reset pulse to use. Default is "mw_reset".
            readout_pulse_name (str): The name of the readout pulse to use. Default is "readout".
            max_attempts (int): The maximum number of reset attempts. Default is 10.
            save_qua_var (Optional[StreamType]): The QUA variable to save the number of attempts to.
        --------
        10/24
        TO add
        """


    def adaptive_reset(
        self,
        readout_pulse_name: str = "readout",
        pi_01_pulse_name: str = "x180",
        pi_12_pulse_name: str = "EF_x180",
    ):
        """
        Reset the qubit to the ground state ('g') using active reset with GEF state readout.

        This function performs an active reset of the qubit by repeatedly measuring its state
        and applying appropriate pulses to bring it back to the ground state ('g'). The process
        continues until the qubit is measured in the ground state twice in a row to ensure high
        confidence in the reset.

        Args:
            readout_pulse_name (str, optional): The name of the pulse to use for the readout. Defaults to "readout".
            pi_01_pulse_name (str, optional): The name of the pulse to use for the 0-1 transition. Defaults to "x180".
            pi_12_pulse_name (str, optional): The name of the pulse to use for the 1-2 transition. Defaults to "EF_x180".

        Returns:
            None
        --------
        10/24 
        Currently copied from reset_qubit_active_gef() 
        """
        res_ar = declare(int)
        success = declare(int)
        assign(success, 0)
        attempts = declare(int)
        assign(attempts, 0)
        self.align()
        with while_(success < 2):
            self.readout_state_gef(res_ar, readout_pulse_name)
            wait(self.rr.res_deplete_time // 4, self.xy.name)
            self.align()
            with if_(res_ar == 0):
                assign(
                    success, success + 1
                )  # we need to measure 'g' two times in a row to increase our confidence
            with if_(res_ar == 1):
                update_frequency(self.xy.name, int(self.xy.intermediate_frequency))
                self.xy.play(pi_01_pulse_name)
                assign(success, 0)
            with if_(res_ar == 2):
                update_frequency(
                    self.xy.name,
                    int(self.xy.intermediate_frequency - self.anharmonicity),
                )
                self.xy.play(pi_12_pulse_name)
                update_frequency(self.xy.name, int(self.xy.intermediate_frequency))
                self.xy.play(pi_01_pulse_name)
                assign(success, 0)
            self.align()
            assign(attempts, attempts + 1)