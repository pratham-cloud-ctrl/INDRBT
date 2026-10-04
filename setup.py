"""Bundle the authoritative SI configuration in wheels, without a source duplicate."""

from pathlib import Path
from shutil import copyfile

from setuptools import setup
from setuptools.command.build_py import build_py


class BuildWithConfig(build_py):
    def run(self):
        super().run()
        target = Path(self.build_lib) / "robotarm" / "data" / "robot.yaml"
        target.parent.mkdir(parents=True, exist_ok=True)
        copyfile(Path(__file__).parent / "config" / "robot.yaml", target)


setup(cmdclass={"build_py": BuildWithConfig})
