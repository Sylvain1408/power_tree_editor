from __future__ import annotations
import math
import uuid
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional

@dataclass
class PowerStage:
    """Data model for a power stage (INPUT, LDO, DCDC, LOAD)."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    stage_type: str = "LDO"  # INPUT / LDO / DCDC / LOAD
    name: str = "Stage"
    ic_name: str = ""
    vin_min: float = 0.0
    vin_max: float = 20.0
    vin_nom: float = 12.0
    vout: float = 12
    iout_user: float = 0.0        # current actually requested by descendants
    iout_max_ic: float = 1.0
    efficiency_user: float = 0.9
    iq: float = 0.0
    notes: str = ""
    upstream: Optional[str] = None   # id of the upstream node (source)
    
    color:str = "ffffff"
    
    # Effective/calculated values (updated by compute())
    vin_effective: float = 0.0
    eff_effective: float = 1.0
    p_out: float = 0.0
    p_in: float = 0.0
    p_diss: float = 0.0
    p_iq: float = 0.0
    p_tot: float = 0.0
    i_in: float = 0.0

    # LOAD-specific
    load_current: float = 0.0

    errors: List[str] = field(default_factory=list)

    def compute(self, upstream_vout: Optional[float]) -> None:
        """Compute effective electrical values and populate errors.

        upstream_vout: voltage provided by upstream stage (if any). If None,
        vin_nom (nominal input voltage) is used as the input reference.
        """
        self.errors.clear()

        # Determine effective input voltage
        vin = upstream_vout if upstream_vout is not None else self.vin_nom
        self.vin_effective = vin

        stype = self.stage_type.upper()

        # INPUT stage: it is a source -> check output range only and nothing else
        if stype == "INPUT":
            #Only here, vin_min/max serve as vout_min/max to avoid creating specific rows
            if not (self.vin_min <= self.vout <= self.vin_max):
                self.errors.append(f"[{self.name}] Output {self.vout:.3g} V is outside source range ({self.vin_min:.3g}-{self.vin_max:.3g} V)")
            # INPUT provides power; its computed values are minimal
            self.p_out = self.vout * self.iout_user
            self.p_in = self.p_out
            self.i_in = self.iout_user
            return

        # LOAD stage: consumes power at the bus voltage
        if stype == "LOAD":
            # For loads, input equals bus voltage
            self.vin_nom = upstream_vout if upstream_vout is not None else self.vin_nom
            self.vout = self.vin_nom
            self.p_out = abs(self.vout) * self.load_current
            self.p_in = self.p_out
            self.i_in = self.load_current
            return

        # LDO / DCDC calculations
        if stype in ("LDO", "DCDC"):
            if stype == "LDO":
                # LDO cannot step up: input must be > output + 0.1V of dropout voltage (at least)
                if abs(self.vin_effective) <= abs(self.vout) + 0.1:
                    self.errors.append(f"[{self.name}] Vin {self.vin_effective:.3g} V must be > Vout {self.vout:.3g} V for an LDO")
                # LDO effective efficiency approximated by Vout/Vin
                eff = (abs(self.vout) / abs(self.vin_effective)) if self.vin_effective != 0 else 0.0
            else:  # DCDC
                eff = max(0.0, min(1.0, self.efficiency_user))

            eff = max(0.0, min(1.0, eff))
            self.eff_effective = eff

            # Output power is Vout * requested current
            self.p_out = abs(self.vout) * self.iout_user

            # Input power depends on efficiency
            self.p_in = self.p_out / eff if eff > 0 else float("inf")
            self.i_in = (self.p_in / abs(self.vin_effective)) if self.vin_effective != 0 else float("inf")

            # Quiescent power
            self.p_iq = (self.iq / 1e6) * self.vin_effective

            # Dissipated power = Pin - Pout
            self.p_diss = (self.p_in - self.p_out) if math.isfinite(self.p_in) else float("inf")
            self.p_tot = (self.p_diss if math.isfinite(self.p_diss) else 0.0) + self.p_iq

            # Basic checks
            if self.iout_max_ic < self.iout_user:
                self.errors.append(f"[{self.name}] IC max current {self.iout_max_ic:.3g} A < requested Iout {self.iout_user:.3g} A")

            if not (self.vin_min*1.05 <= self.vin_effective <= self.vin_max*0.95):
                self.errors.append(f"[{self.name}] Vin {self.vin_effective:.3g} V is close/outside Vin_min/Vin_max range ({self.vin_min*1.1:.3g};{self.vin_max*0.9:.3g} V)")

    def to_dict(self) -> Dict:
        return asdict(self)

    @staticmethod
    def from_dict(data: Dict) -> "PowerStage":
        ps = PowerStage()
        for key, val in data.items():
            setattr(ps, key, val)
        return ps
