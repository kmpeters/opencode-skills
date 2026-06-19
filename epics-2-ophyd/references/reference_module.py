"""
Style reference for the epics-2-ophyd skill.

This is the BASELINE style — used only when the target instrument has no
existing modules to copy. When the instrument's own ``<instrument>/devices/``
modules establish a different convention (imports, base classes, docstring
style, ophyd flavor), those take precedence and this file is ignored.

Conventions to mirror when this is the baseline:

- One symbol per import line; stdlib grouped above third-party.
- ``MotorBundle`` for a group of motors; subclass ``EpicsMotor`` to add
  record-field signals (e.g. ``.PROC``, ``.STUP``) declared as
  ``Component(EpicsSignal, ".FIELD", kind="omitted")``.
- A ``Component``'s PV is the suffix: a full PV when the device prefix is
  empty, or a relative field like ``.PROC`` when it appends to the parent
  prefix.
- ``labels=(...)`` passed as a tuple; ``kind="omitted"`` for helper /
  diagnostic signals that shouldn't appear in normal reads.
- Bluesky plans may be defined as device methods using ``yield from
  bps.mv(...)``, with keyword-only args, input validation, and numpydoc-style
  docstrings.
- Class-level configuration constants as typed attributes with defaults (not
  Components).
- Module + class docstrings in the compact ``name`` — description style; type
  hints via ``typing``. (Confirms classic threaded ophyd, not ophyd-async.)
"""

from typing import Optional

from bluesky import plan_stubs as bps
from ophyd import Component
from ophyd import EpicsMotor
from ophyd import EpicsSignal
from ophyd import MotorBundle


class UsaxsSlitDevice(MotorBundle):
    """USAXS sample slit just before the sample position.

    ``x``, ``y``          — slit center position (mm).
    ``h_size``, ``v_size``— horizontal and vertical aperture (mm).
    """

    h_size = Component(EpicsMotor, "usxLAX:m58:c1:m8", labels=("uslit",))
    x = Component(EpicsMotor, "usxLAX:m58:c1:m6", labels=("uslit",))
    v_size = Component(EpicsMotor, "usxLAX:m58:c1:m7", labels=("uslit",))
    y = Component(EpicsMotor, "usxLAX:m58:c1:m5", labels=("uslit",))

    def set_size(self, *, h: Optional[float] = None, v: Optional[float] = None):
        """Bluesky plan: move horizontal and vertical aperture to *h* × *v* mm.

        Both *h* and *v* are required keyword-only arguments.

        Parameters
        ----------
        h : float
            Target horizontal aperture in mm.
        v : float
            Target vertical aperture in mm.

        Raises
        ------
        ValueError
            If either *h* or *v* is not provided.

        Yields
        ------
        Bluesky messages.
        """
        if h is None:
            raise ValueError("must define horizontal size")
        if v is None:
            raise ValueError("must define vertical size")
        yield from bps.mv(self.h_size, h, self.v_size, v)


class GuardSlitMotor(EpicsMotor):
    """EpicsMotor with additional ``.PROC`` and ``.STUP`` signals.

    ``process_record`` (``.PROC``) — process the record manually.
    ``status_update``  (``.STUP``) — request a status update from the motor.
    """

    process_record = Component(EpicsSignal, ".PROC", kind="omitted")
    status_update = Component(EpicsSignal, ".STUP", kind="omitted")


class GSlitDevice(MotorBundle):
    """Guard slit with four individual blade motors and aperture summary signals.

    Blade motors (``bot``, ``inb``, ``outb``, ``top``) use :class:`GuardSlitMotor`.
    ``x``, ``y`` — guard slit centre position (mm).
    ``h_size``, ``v_size`` — calculated aperture read from soft IOC records.
    ``h_sync_proc``, ``v_sync_proc`` — trigger recalculation of aperture.

    Class-level tuning parameters (mm unless noted):

    ``gap_tolerance``             — required closeness of actual to desired gap.
    ``scale_factor``              — guard slit aperture as multiple of beam size.
    ``h_step_away`` / ``v_step_away`` — step away from beam during tuning.
    ``h_step_into`` / ``v_step_into`` — step to block beam during tuning.
    ``tuning_intensity_threshold``    — minimum count rate to consider beam present.
    """

    bot = Component(GuardSlitMotor, "usxLAX:m58:c1:m4", labels=("gslit",))
    inb = Component(GuardSlitMotor, "usxLAX:m58:c1:m2", labels=("gslit",))
    outb = Component(GuardSlitMotor, "usxLAX:m58:c1:m1", labels=("gslit",))
    top = Component(GuardSlitMotor, "usxLAX:m58:c1:m3", labels=("gslit",))
    x = Component(EpicsMotor, "usxLAX:m58:c0:m7", labels=("gslit",))
    y = Component(EpicsMotor, "usxLAX:m58:c0:m6", labels=("gslit",))

    h_size = Component(EpicsSignal, "usxLAX:GSlit1H:size")
    v_size = Component(EpicsSignal, "usxLAX:GSlit1V:size")

    h_sync_proc = Component(EpicsSignal, "usxLAX:GSlit1H:sync.PROC")
    v_sync_proc = Component(EpicsSignal, "usxLAX:GSlit1V:sync.PROC")

    gap_tolerance: float = 0.02
    scale_factor: float = 1.2
    h_step_away: float = 0.2
    v_step_away: float = 0.1
    h_step_into: float = 1.1
    v_step_into: float = 0.4
    tuning_intensity_threshold: int = 500
