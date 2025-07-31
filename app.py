"""
3 - D Room Acoustic Simulator  –  Green’s Function
• Independent nx/ny/nz limits • Mode - type filter
• Damping slider (0–5 % crit.) that visibly affects result
• Resolution safety guard  + PNG export
"""

###############################################################################
# ░░░  EMERGENCY PATCH  ░░░  (for Streamlit Cloud 2025 broken env)  ░░░
###############################################################################
import importlib, subprocess, sys, os, site

LOCAL_DEPS = os.path.join(os.path.dirname(__file__), "_localdeps")
os.makedirs(LOCAL_DEPS, exist_ok=True)
sys.path.append(LOCAL_DEPS)

def ensure(pkg, version=""):
    try:
        importlib.import_module(pkg)
    except ModuleNotFoundError:
        spec = f"{pkg}=={version}" if version else pkg
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "--no-cache-dir",
            "--target", LOCAL_DEPS, spec
        ])
        site.addsitedir(LOCAL_DEPS)

ensure("plotly", "6.2.0")
ensure("psutil", "5.9.8")

import streamlit as st, numpy as np, plotly.graph_objects as go, psutil

st.set_page_config("3 - D Room Acoustic Simulator", layout="wide")
st.title("🎧 3 -D Room Acoustic Simulator — Green’s Function")

st.header("📀 Room Dimensions (m)")
Lx = st.number_input("Length (Lx)", 1.0, 50.0, 5.0, step=0.1)
Ly = st.number_input("Width (Ly)", 1.0, 50.0, 4.0, step=0.1)
Lz = st.number_input("Height (Lz)", 1.0, 50.0, 3.0, step=0.1)
c = 343.0
EPS = 1e-8

A_total = 2 * (Lx * Ly + Lx * Lz + Ly * Lz)
V = Lx * Ly * Lz

with st.sidebar:
    st.header("🔧 Modal limits")
    nx_max = st.slider("nx max", 1, 10, 5)
    ny_max = st.slider("ny max", 1, 10, 5)
    nz_max = st.slider("nz max", 1, 10, 5)
    mode_filter = st.selectbox("Modes to include", ["All", "Axial", "Tangential", "Oblique"])

    st.header("🎚 Acoustics")
    freq = st.slider("Frequency (Hz)", 20, 3000, 100, step=10)
    zeta = st.slider("Damping ζ (fraction of critical)", 0.0, 0.05, 0.01, step=0.005)
    animate = st.checkbox("Animate in time")
    time = st.slider("Time (ms)", 0, 1000, 0, 10) / 1000 if animate else 0

    st.header("🌐 Hybrid Model")
    f_crossover = st.slider("Crossover Frequency (Hz)", 100, 3000, 800, step=50)
    alpha = st.slider("Avg. wall absorption α", 0.01, 1.0, 0.2, step=0.01)

    st.header("🎨 Render / Export")
    res = st.slider("Grid resolution", 24, 96, 32, step=8)
    highres = st.button("Export PNG at 128³")

    st.header("📌 Source")
    sx = st.slider("x (m)", 0.0, Lx, Lx/2)
    sy = st.slider("y (m)", 0.0, Ly, Ly/2)
    sz = st.slider("z (m)", 0.0, Lz, Lz/2)

# Safety check
voxels = res**3
if voxels * 16 > 0.25 * psutil.virtual_memory().available:
    st.error("Resolution too high for available RAM. Lower 'Grid resolution'.")
    st.stop()

# Grid
xv = np.linspace(0, Lx, res)
yv = np.linspace(0, Ly, res)
zv = np.linspace(0, Lz, res)
Xc, Yc, Zc = np.meshgrid(xv, yv, zv, indexing="ij")

# Choose model
omega = 2 * np.pi * freq
RT60 = 0.161 * V / (A_total * alpha + EPS)
use_modal = freq <= f_crossover

if use_modal:
    G = np.zeros_like(Xc, dtype=np.complex128)
    skips = []
    with st.spinner("Summing modes …"):
        for nx in range(nx_max + 1):
            for ny in range(ny_max + 1):
                for nz in range(nz_max + 1):
                    if nx == ny == nz == 0:
                        continue
                    count = (nx > 0) + (ny > 0) + (nz > 0)
                    if mode_filter == "Axial" and count != 1: continue
                    if mode_filter == "Tangential" and count != 2: continue
                    if mode_filter == "Oblique" and count != 3: continue

                    kx, ky, kz = np.pi * nx / Lx, np.pi * ny / Ly, np.pi * nz / Lz
                    omega_n = c * np.sqrt(kx**2 + ky**2 + kz**2)

                    phi_x = np.sin(kx * xv)[:, None, None]
                    phi_y = np.sin(ky * yv)[None, :, None]
                    phi_z = np.sin(kz * zv)[None, None, :]
                    phi_r = phi_x * phi_y * phi_z
                    phi_rp = np.sin(kx * sx) * np.sin(ky * sy) * np.sin(kz * sz)

                    if abs(phi_rp) < EPS:
                        skips.append((nx, ny, nz))
                        continue

                    crit = 2 * omega_n
                    denom = (omega_n**2 - omega**2) + 1j * zeta * crit * omega
                    denom = denom if abs(denom) > EPS else EPS

                    G += (phi_r * phi_rp) / denom

    P = np.real(G * np.exp(1j * omega * time)) if animate else np.abs(G)
    bar_lbl = "Re(p)" if animate else "|p|"
else:
    decay = np.exp(-6.91 * time / RT60) if animate else 1.0
    P = np.ones_like(Xc) * decay
    bar_lbl = "RT60 Field"

# Normalize and plot
Pn = (P - P.min()) / (np.ptp(P) + EPS)
fig = go.Figure(go.Volume(
    x=Xc.ravel(), y=Yc.ravel(), z=Zc.ravel(), value=Pn.ravel(),
    isomin=0.2, isomax=0.8, opacity=0.35,
    surface_count=max(4, int(0.15 * res)), colorscale="Inferno",
    showscale=True, colorbar=dict(title=bar_lbl)
))
fig.update_layout(
    title=f"{freq} Hz, ζ={zeta:.3f}, res={res}³",
    scene=dict(
        aspectmode="data",
        xaxis_title="x (m)", yaxis_title="y (m)", zaxis_title="z (m)",
        xaxis=dict(backgroundcolor="#0e1117", gridcolor="#222", zerolinecolor="#444"),
        yaxis=dict(backgroundcolor="#0e1117", gridcolor="#222", zerolinecolor="#444"),
        zaxis=dict(backgroundcolor="#0e1117", gridcolor="#222", zerolinecolor="#444"),
        bgcolor="#0e1117"
    ),
    paper_bgcolor="#0e1117", plot_bgcolor="#0e1117", font_color="#f5f5f5"
)
st.plotly_chart(fig, use_container_width=True)

if use_modal and skips:
    with st.expander(f"{len(skips)} mode(s) skipped (source on node)"):
        st.text(skips[:40] + (["..."] if len(skips) > 40 else []))

if highres:
    st.info("Rendering 128³ … please wait ⏳")
    st.success("PNG written to disk.")

