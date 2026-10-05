# Contributing

From the organized repository root, enter `06_Complete_Project_Source`. Use Python 3.12 or later and install `python -m pip install -e ".[cad,dev]"`. Keep geometry, masses, motion constraints and demonstration settings in `config/robot.yaml`.

Run `python scripts/run_validation.py` before proposing a change. For geometry or parameters, also regenerate `python scripts/generate_cad.py`, `python scripts/generate_results.py` and affected inspection reports. Use `python -m ruff format src analysis scripts tests cad/build123d electronics` and `python -m ruff check src analysis scripts tests cad/build123d electronics`.

Claims must identify whether they are ASSUMED, TARGET, CALCULATED, SIMULATED or VERIFIED DIGITALLY. Record actual failures/fixes in the journal. A zero ERC count does not validate electronic component suitability or physical operation. Collision evidence must state its exact pair and sampling scope. Avoid adding an empty PCB or fabricated FEA/contact results.

Run `python scripts/sync_presentation.py` after refreshing verified source artifacts so the numbered presentation folders and readable reports match. Useful further extensions include continuous swept collision checks, coupled inverse dynamics and nonlinear/contact-aware gripper models. Hardware work is outside this digital project.
