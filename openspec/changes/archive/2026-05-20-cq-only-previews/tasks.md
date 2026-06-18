## 1. Rewrite preview.py

- [x] 1.1 Remove all `pyrender`, `trimesh`, and OpenGL imports from `src/preview.py`
- [x] 1.2 Add matplotlib import (Agg backend, set before pyplot import) and CadQuery imports
- [x] 1.3 Implement `_tessellate(workplane_or_shape, tolerance=0.05)` helper that calls `result.val().tessellate()` and returns vertex/face arrays ready for matplotlib
- [x] 1.4 Implement `_render_cq_view(workplane, elev, azim, width, height)` using `matplotlib.figure.Figure` with `Axes3D` and `Poly3DCollection`; returns PIL Image
- [x] 1.5 Rewrite `render_single(workplane, output_path, title, width, height)` to use `_render_cq_view`; preserve footer with bbox/volume/face-count info from CQ bounding box
- [x] 1.6 Rewrite `render_multi_view(workplane, output_path, title, subtitle, view_size)` to render six views using `_render_cq_view` and compose them with Pillow (same 3x2 grid layout as before)
- [x] 1.7 Remove `_build_scene`, `_build_grid`, `_render_frame`, `_rotation_matrix`, `load_mesh` call, and all other pyrender-specific helpers
- [x] 1.8 Remove `mesh_io` import from `preview.py` (mesh loading no longer needed here)

## 2. Add render_preview.py subprocess entry point

- [x] 2.1 Create `src/render_preview.py` with argparse CLI: `--script`, `--output`, `--views (iso|multi, default multi)`, `--title`, `--subtitle`
- [x] 2.2 Implement script loading: read the model script, compile it, and run it in an isolated dict namespace with `PYTHONPATH` set to `src/` so block imports resolve
- [x] 2.3 Extract `result` from the namespace; exit with code 1 and diagnostic message if `result` is absent or not a CadQuery object
- [x] 2.4 Call `preview.render_multi_view(result, output_path)` or `preview.render_single(result, output_path)` depending on `--views`
- [x] 2.5 Exit 0 on success; catch and print exceptions then exit 1 on failure

## 3. Update run_cadquery_model.py

- [x] 3.1 Remove the in-process `import preview` call and the `_process_stls` render path that passes a trimesh object to `preview.render_multi_view`
- [x] 3.2 In the `--preview` branch, replace the in-process render with a subprocess call to `render_preview.py`: `[sys.executable, os.path.join(skill_root, "render_preview.py"), "--script", script_path, "--output", preview_path, "--views", args.views]`
- [x] 3.3 Capture stdout/stderr from the render subprocess and append any error output to `result["stderr"]` if the subprocess fails
- [x] 3.4 Move preview PNG to the script directory and populate `result["previews"]` and `result["preview"]` as before

## 4. Update dependencies

- [x] 4.1 Remove `pyrender>=0.1.45,<0.2` from `requirements.txt`
- [x] 4.2 Add `matplotlib>=3.7,<4` to `requirements.txt` with a comment explaining it is used for headless preview rendering
- [x] 4.3 Verify `numpy` bound in `requirements.txt` is compatible with the chosen matplotlib version (numpy is already listed)

## 5. Update tests

- [x] 5.1 Update `tests/test_run_wrapper.py` preview tests: mock `subprocess.run` for the `render_preview.py` call instead of patching `preview.render_multi_view` directly
- [x] 5.2 Add a unit test in `tests/test_run_wrapper.py` that verifies the preview subprocess is invoked with `render_preview.py` in the command
- [x] 5.3 Add `tests/test_preview.py` (or extend existing) with a test that calls `preview.render_multi_view(workplane, tmp_path)` using a simple CadQuery box and verifies a PNG is produced
- [x] 5.4 Verify `tests/test_run_wrapper.py` existing preview-related tests still pass after the mock update

## 6. Cleanup

- [x] 6.1 Remove the `PYOPENGL_PLATFORM` environment variable setup block at the top of `preview.py` (Linux EGL workaround, no longer needed)
- [x] 6.2 Confirm `mesh_io.py` import is still used elsewhere (by `run_cadquery_model.py` geometry check); if `preview.py` was its only other caller, note this but do not remove `mesh_io.py`
- [x] 6.3 Run `ruff check --fix src/preview.py src/render_preview.py src/run_cadquery_model.py` and resolve any lint issues
- [x] 6.4 Run `pytest tests/test_run_wrapper.py tests/test_orchestrate.py` (fast subset) to confirm no regressions
