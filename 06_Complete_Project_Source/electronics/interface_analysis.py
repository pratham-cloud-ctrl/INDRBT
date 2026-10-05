"""Calculate low-voltage interface checks from BOM values and stated assumptions."""
from __future__ import annotations

import csv
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent


def calculate() -> dict:
    rows = list(csv.DictReader((ROOT / "bom.csv").open(encoding="utf-8")))
    bom = {row["Reference"]: row for row in rows}
    assumptions = json.loads((ROOT / "electrical_assumptions.json").read_text(encoding="utf-8"))

    def value(ref):
        match = re.match(r"([0-9.]+)([pnumkM]?)", bom[ref]["Value"])
        assert match is not None, f"No numeric value in {ref}"
        return float(match[1]) * {"": 1, "p": 1e-12, "n": 1e-9, "u": 1e-6, "m": 1e-3, "k": 1e3, "M": 1e6}[match[2]]

    rail = assumptions["logic_nominal_v"]
    limit_r, pullup_r, limit_c = value("R5"), value("R6"), value("C6")
    limit_low = rail * limit_r / (limit_r + pullup_r)
    assert limit_low < 0.8, "Limit divider cannot meet assumed low-level threshold"
    encoder_taus = {channel: value(f"R{2+i}") * value(f"C{3+i}") for i, channel in enumerate("ABZ")}
    assert all(tau <= 1.1e-7 for tau in encoder_taus.values())
    rt = value("R16") / assumptions["bus_end_terminator_count"]
    rp = value("R14") + value("R15")
    bias_v = rail * rt / (rp + rt)
    tol = assumptions["resistor_tolerance_fraction"]
    bias_worst = assumptions["bias_check_supply_min_v"] * (rt * (1-tol)) / (rp * (1+tol) + rt * (1-tol))
    assert bias_worst > assumptions["receiver_guaranteed_threshold_v"]
    assert bom["R14"]["Population"] == bom["R15"]["Population"] == "DNP by default"
    worst_input = assumptions["input_nominal_v"] * (1+assumptions["input_tolerance_fraction"])
    # Ignore diode drop for a conservative regulator dissipation bound.
    p_ldo = (worst_input - rail) * assumptions["logic_budget_a"]
    junction = assumptions["ambient_design_c"] + p_ldo * assumptions["ldo_datasheet_theta_ja_c_per_w"]
    return {
        "status": "CALCULATED", "no_measurements": True,
        "limit_closed_v": limit_low,
        "limit_release_tau_s": pullup_r * limit_c,
        "limit_closure_tau_s": limit_c * limit_r * pullup_r / (limit_r + pullup_r),
        "encoder_nominal_tau_s": encoder_taus,
        "optional_rs485_bias_nominal_v_two_terminators": bias_v,
        "optional_rs485_bias_worst_v_1pct_resistors_3v_supply": bias_worst,
        "optional_rs485_bias_idle_current_a": rail / (rp + rt),
        "optional_bias_threshold_check": "PASS; ideal DC network, excludes leakage/cable effects",
        "ldo_conservative_dissipation_bound_w": p_ldo,
        "ldo_conditional_junction_estimate_c": junction,
        "thermal_claim_boundary": "Datasheet theta_ja estimate only; PCB copper/airflow unspecified and no temperature verified",
        "pcb_status": assumptions["pcb_status"],
    }


if __name__ == "__main__":
    report = calculate()
    (ROOT / "interface_calculations.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
