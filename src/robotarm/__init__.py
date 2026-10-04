"""ASTER-6 digital-only robotics engineering model. Internal units are SI."""

from .config import load_config
from .kinematics import IKError, IKResult, RobotArm

__version__ = "0.9.0"
__all__ = ["RobotArm", "IKError", "IKResult", "load_config"]
