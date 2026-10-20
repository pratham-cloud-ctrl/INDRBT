# ASTER-6 · KiCad electronics source

[Illustrated electronics tour](../docs/electronics_tour.md) · [Project home](../../README.md) · [Engineering design chapter](../docs/05_electronics.md)

This is the authoritative source for the **100 × 100 mm, four-layer joint/sensor interface**: 44 schematic components and 48 PCB footprints, including four mounting holes. An external 3.3 V controller connects to encoder/limit inputs, a separate motor drive and RS-485. The PCB implements logic interfacing; the controller, motor power stage and embedded firmware are external to this design.

[Inspect the PCB online](https://aster-six-engineering-showcase.warmkiwi64.chatgpt.site/#pcb), [rotate the 3D board](https://aster-six-engineering-showcase.warmkiwi64.chatgpt.site/#pcb3d) or [zoom the schematic](https://aster-six-engineering-showcase.warmkiwi64.chatgpt.site/#schematic) without installing KiCad or downloading files. The native project steps below are optional for offline editing.

![Native KiCad 3D board export](exports/pcb_3d.png)

| Browse without KiCad | Open |
|---|---|
| Circuit | [Schematic PDF](exports/joint_interface.pdf) |
| Layout | [Top view](exports/pcb_top.png) and [six-page layer PDF](exports/pcb_layers.pdf) |
| Parts | [BOM CSV](bom.csv) and [component guide](../docs/electronics_components.md) |
| Manufacturing package | [Gerber/drill/assembly ZIP](fabrication/joint_interface_fabrication.zip) |
| Checked evidence | [Independent review](../results/validation/final_electronics_review.json), [ERC](erc_report.json), [DRC](pcb_drc_report.json) and [source/export hashes](pcb_verification.json) |

## Open the editable project

For optional offline editing, download and extract the **complete repository** using **Code → Download ZIP**, or clone it. With KiCad 10 and its standard libraries installed, open [joint_interface.kicad_pro](joint_interface.kicad_pro), then its [schematic](joint_interface.kicad_sch) or [PCB](joint_interface.kicad_pcb). GitHub shows native files as source; PDF/PNG links above provide readable previews.

Keep this folder intact. [fp-lib-table](fp-lib-table) resolves the project-local [F1 footprint](ASTER_Interface.pretty/PTC_Bourns_MF-NSMF025X_1206.kicad_mod) through `${KIPRJMOD}`; [sym-lib-table](sym-lib-table) resolves stock symbols. Downloading a single native file omits this library context. On Windows, [OPEN_PCB_LAYOUT.cmd](../../OPEN_PCB_LAYOUT.cmd) at the repository root opens the downloaded layout.

Supply regulated **5 V**, with 3.3 V GPIO and a shared 150 mA logic-load design budget. Read the [tour](../docs/electronics_tour.md) for connector roles and the [design chapter](../docs/05_electronics.md) for complete pin contracts, calculations, assumptions and reproduction commands. Saved native rules/connectivity checks pass within their documented scope; no physical board was built or qualified.
