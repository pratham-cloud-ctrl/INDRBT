"""Opposed-thread screw gripper: symmetric jaw coordinates and ideal work balance."""

from __future__ import annotations

import numpy as np

from robotarm.config import load_config, validate_config


class ParallelGripper:
    def __init__(self, config: dict | None = None):
        self.config = load_config() if config is None else config
        if config is not None:
            validate_config(config)
        self.parameters = self.config["gripper"]
        self.max_opening = self.parameters["max_opening"]

    def jaw_positions(self, opening: float) -> np.ndarray:
        """Inner jaw faces along local Y, metres; opening is full jaw gap."""
        if not np.isfinite(opening) or not 0 <= opening <= self.max_opening:
            raise ValueError("Opening lies outside the configured gripper range.")
        return np.array([-opening / 2, opening / 2])

    def screw_revolutions(self, start: float, end: float) -> float:
        self.jaw_positions(start)
        self.jaw_positions(end)
        return (end - start) / (2 * self.parameters["screw_lead"])

    def required_torque(self, total_normal_force: float | None = None) -> float:
        """N=sum of both jaw contact normal forces; tau=N*lead/(2*pi*eta).

        Each opposed nut travels one lead per revolution. The full gap changes
        by TWO leads; summing both jaws' work prevents a factor-of-two mistake.
        """
        force = (
            self.parameters["total_normal_force_target"]
            if total_normal_force is None
            else total_normal_force
        )
        if not np.isfinite(force) or force < 0:
            raise ValueError("Normal force must be nonnegative and finite.")
        return (
            force
            * self.parameters["screw_lead"]
            / (2 * np.pi * self.parameters["screw_efficiency"])
        )

    def ideal_total_normal_force(self) -> float:
        return (
            2
            * np.pi
            * self.parameters["screw_efficiency"]
            * self.parameters["motor_torque"]
            / self.parameters["screw_lead"]
        )

    def metrics(self) -> dict:
        gravity = self.config["targets"]["gravity"]
        force = self.parameters["total_normal_force_target"]
        return {
            "opening_m": self.max_opening,
            "travel_per_jaw_m": self.max_opening / 2,
            "full_stroke_screw_revolutions": abs(self.screw_revolutions(0, self.max_opening)),
            "target_total_normal_force_N": force,
            "required_motor_torque_Nm": self.required_torque(),
            "ideal_force_at_assumed_motor_torque_N": self.ideal_total_normal_force(),
            "friction_limited_payload_kg_with_safety_factor": self.parameters[
                "friction_coefficient"
            ]
            * force
            / (gravity * self.parameters["grip_safety_factor"]),
            "status": "CALCULATED from assumed screw efficiency and friction; no contact simulation",
        }
