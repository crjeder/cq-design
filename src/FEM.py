import subprocess, numpy as np, gmsh
from pathlib import Path

CCX = r"C:\path\to\ccx.exe"   # z.B. aus der FreeCAD-Installation (bin/)
WORK = Path("fem_job"); WORK.mkdir(exist_ok=True)

# Orthotrop, Z = schwache Richtung (Startwerte, ggf. kalibrieren)
MAT = dict(E1=1700, E2=1700, E3=1400, nu12=0.38, nu13=0.38, nu23=0.38,
           G12=616, G13=500, G23=500)
Z_STRENGTH = 25.0   # MPa, konservativ
SAFETY = 2.5

def mesh(step_file, size=2.0):
    gmsh.initialize()
    gmsh.option.setNumber("General.Terminal", 0)
    gmsh.model.occ.importShapes(step_file)
    gmsh.model.occ.synchronize()
    gmsh.option.setNumber("Mesh.MeshSizeMax", size)
    gmsh.option.setNumber("Mesh.ElementOrder", 2)
    gmsh.model.mesh.generate(3)
    tags, xyz, _ = gmsh.model.mesh.getNodes()
    xyz = xyz.reshape(-1, 3)
    _, en = gmsh.model.mesh.getElementsByType(11)      # 10-Knoten-Tet
    en = en.reshape(-1, 10)[:, [0,1,2,3,4,5,6,7,9,8]]  # gmsh -> ccx Knotenreihenfolge
    gmsh.finalize()
    return dict(zip(tags.astype(int), xyz)), en.astype(int)

def write_inp(nodes, elems, fixed_ids, load_ids, force, path):
    with open(path, "w") as f:
        f.write("*NODE\n")
        for i, (x, y, z) in nodes.items():
            f.write(f"{i},{x},{y},{z}\n")
        f.write("*ELEMENT, TYPE=C3D10, ELSET=EALL\n")
        for k, e in enumerate(elems, 1):
            f.write(f"{k}," + ",".join(map(str, e)) + "\n")
        f.write("*NSET, NSET=FIX\n" + ",".join(map(str, fixed_ids)) + "\n")
        f.write("*MATERIAL, NAME=PETG\n*ELASTIC, TYPE=ENGINEERING CONSTANTS\n")
        m = MAT
        f.write(f"{m['E1']},{m['E2']},{m['E3']},{m['nu12']},{m['nu13']},{m['nu23']},{m['G12']},\n{m['G13']},{m['G23']}\n")
        f.write("*SOLID SECTION, ELSET=EALL, MATERIAL=PETG\n")
        f.write("*STEP\n*STATIC\n*BOUNDARY\nFIX,1,3\n*CLOAD\n")
        fx = np.array(force) / len(load_ids)
        for i in load_ids:
            for d in range(3):
                if fx[d]: f.write(f"{i},{d+1},{fx[d]}\n")
        f.write("*NODE PRINT, NSET=FIX\nRF\n*EL PRINT, ELSET=EALL\nS\n*END STEP\n")

def run(job="job"):
    subprocess.run([CCX, job], cwd=WORK, check=True)

def max_von_mises(dat):
    vm = 0.0
    for line in Path(dat).read_text().splitlines():
        p = line.split()
        if len(p) == 8:
            try:
                s = list(map(float, p[2:]))
            except ValueError:
                continue
            sx, sy, sz, txy, txz, tyz = s
            v = np.sqrt(0.5*((sx-sy)**2 + (sy-sz)**2 + (sz-sx)**2)
                        + 3*(txy**2 + txz**2 + tyz**2))
            vm = max(vm, v)
    return vm

if __name__ == "__main__":
    nodes, elems = mesh("part.step", size=2.0)
    xyz = np.array(list(nodes.values())); ids = list(nodes.keys())
    tol = 1e-3
    fixed = [i for i, p in nodes.items() if p[0] < xyz[:,0].min() + tol]  # Fläche x_min
    load  = [i for i, p in nodes.items() if p[0] > xyz[:,0].max() - tol]  # Fläche x_max
    write_inp(nodes, elems, fixed, load, force=(0, 0, -50), path=WORK/"job.inp")
    run()
    vm = max_von_mises(WORK/"job.dat")
    print(f"max von Mises: {vm:.1f} MPa | zulässig: {Z_STRENGTH/SAFETY:.1f} MPa")