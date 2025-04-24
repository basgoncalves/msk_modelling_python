## Slicer 


## Python
Use .\remesh.py for remeshing .stl files

```python
    import msk_modelling_python as msk

    msk_modelling_python.src.mri.hip_project.remesh
    subjects_to_run = []
    mode = "manual" # "manual", "semi-auto" or "batch"
```

## 3. Mesh lab
Cut meshes in mesh lab
### 3.1 Drag and drop meshes
![](./figures/MeshLab1.png)
### 3.2 Show femur 
![MeshLab Select Faces](./figures/MeshLab2.png)
### 3.3 Select faces 
#####  3.3.1 until narrrowest point of the neck
![MeshLab Select Faces](./figures/MeshLab3.png)
#####  3.3.2 acetabulum select only visible (hold ALT and select)
![MeshLab Select Faces](./figures/MeshLab4.png)
#### 3.4 Invert selection (CTRL + Shift + I)
![MeshLab Select Faces](./figures/MeshLab5.png)
![MeshLab Select Faces](./figures/MeshLab6.png)

### 3.5 Delete selected faces 
![MeshLab Select Faces](./figures/MeshLab7.png)

### 3.6 Export .stl file (CRLT + E) and untick binary encoding
![MeshLab Select Faces](./figures/MeshLab8.png)

### Invert Faces
Instructions on how to invert faces in MeshLab.

### Export Binary STL
Instructions on how to export a binary STL file in MeshLab.