# SubLayout
KiCad plugin to merge (or create) a sub-pcb-layout into (or from) a top-level board.

Inspired by [SaveRestoreLayout](https://github.com/MitjaNemec/SaveRestoreLayout) and [HierarchicalPcb](https://github.com/gauravmm/HierarchicalPcb), but this plugin only uses the board layout file and does not require a schematic or any project structure.
Compatible with schematic-less flows as long as the requirements below are met.

## Features
- Select and save the layout of a hierarchical block to a .kicad_pcb file.
  - Selection includes traces, vias, and zones of internal nets.
  - Selection expands to layout groups enclosing the footprints.
  - This file can be edited.
- Restore a saved layout to a hierarchical block of a board.
  - This includes footprint positions, traces, vias, and zones.
  - Optionally delete existing internal traces and groups (if applicable) before restoring
- Replicate a layout of a hierarchical block to other instances of that block in the same board. 
- Best-effort restore when the footprints or netlists do not match, allowing partial restores when the hierarhical sheet schematic has changed.

## Workflow
1. Select ONE anchor footprint.
   - For saving: select any footprint in the hierarchical block to be saved.
   - For restoring: select the footprint in the hierarchical block where the layout will be restored around.
   - For replicating: select the footprint of the source hierarchical block corresponding to the footprints of the instances where the layouts will be replicated around.
2. Invoke the plugin from the plugin menu or toolbar.
3. If needed, change the level of hierarchy to operate on.
   By default, the lowest (leafmost) hierarchical block is selected.
4. Optionally, select multiple instances of the hierarchical block to replicate or restore.
5. Click 'Save', 'Replicate' or 'Restore' to perform the operation.

## Board Requirements
- Sublayouts work on hierarchical sheets.
  - For non-schematic flows (e.g., hardware description language to netlist to layout), netlists must encode hierarchy in footprint tstamp (component unique id) data and provide Sheetfile and Sheetname.
- Component unique IDs must match when restoring or replicating sublayouts.
  - For non-schematic flows, this means footprint tstamp data must match.
  - Note, in the future, there may be an option to match components on refdes.
- Sheetname inference may fail if there are hierarchical sheets with no direct footprints.
  This may result in not finding other instances of a hierarhical sheet and is a limitation of the data available in the board layout file.
