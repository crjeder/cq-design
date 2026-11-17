## REMOVED Requirements

### Requirement: Preview tile supports deterministic feature callouts
**Reason**: Numbered badges on the 2x2 tile are superseded by the name-labeled five-view preview (`labeled-preview`), which shows names directly instead of numbers to look up.
**Migration**: Stop passing `--callout` and `--unlocated-name` to `render_preview.py` and `run_cadquery_model.py`; use `preview/<name>_preview_labeled.png` for feature identification.

### Requirement: Callout legend maps badges to plan names
**Reason**: The badge-number legend has no badges to map; the labeled preview carries its own name legend.
**Migration**: Read feature names from the legend of the labeled preview.

### Requirement: Callouts are placed only where the feature is visible
**Reason**: Visibility-based placement moves into the labeled preview's anchor computation (`labeled-preview`).
**Migration**: None; visibility is handled per view by `render_labeled.py`.

### Requirement: Hidden callouts are marked in the legend
**Reason**: Replaced by the `NAME (hidden)` legend rule in `labeled-preview`.
**Migration**: None.

### Requirement: Coincident badges merge
**Reason**: Labels are de-overlapped by offset instead of merged into one badge.
**Migration**: None.
