from pathlib import Path
import re
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import geopandas as gpd
import xarray as xr
from tqdm import tqdm
from rasterio.features import rasterize
from affine import Affine

# ====== 路径 ======
ROOT = Path(__file__).resolve().parents[1]
SHAPE_PATH = ROOT / "data/shapes/ne_110m_admin_0_countries.shp"
MODIS_DIR  = ROOT / "data/modis"
OUT_CSV    = ROOT / "data/ndvi_country_2024.csv"

SCALE = 1e-4  # MODIS NDVI scale
jday_pat = re.compile(r"A2024(\d{3})")  # e.g., MOD13C2.A2024032...

# ====== 读取国家边界（EPSG:4326）======
gdf = gpd.read_file(SHAPE_PATH).to_crs(4326)
for cand in ["ISO_A3", "ADM0_A3", "iso_a3", "ISO3"]:
    if cand in gdf.columns:
        gdf["iso3"] = gdf[cand]
        break
assert "iso3" in gdf.columns, "shapefile 里没有 ISO3 字段"
gdf = gdf[["iso3", "geometry"]].reset_index(drop=True)
n_regions = len(gdf)

# ====== 找到所有月文件 ======
files = sorted(MODIS_DIR.glob("*.hdf"))
assert files, f"没找到 {MODIS_DIR} 下的 HDF 文件"

rows = []

# ====== 辅助：从第一个文件确定网格大小并预生成“国家标签”栅格 ======
# 读取首个 HDF，拿到维度（通常是 YDim..., XDim...）
f0 = files[0]
ds0 = xr.open_dataset(f0, engine="netcdf4", mask_and_scale=False)
var0 = [k for k in ds0.data_vars if "ndvi" in k.lower()]
assert var0, f"{f0.name} 中找不到 NDVI 变量，变量有：{list(ds0.data_vars)}"
da0 = ds0[var0[0]].astype("float32") * SCALE

# 识别行列维度名并构造中心坐标（0.05° 全局网格）
lat_dim = next((d for d in da0.dims if d.lower() in ("lat","latitude","y","ydim") or "ydim" in d.lower()), None)
lon_dim = next((d for d in da0.dims if d.lower() in ("lon","longitude","x","xdim") or "xdim" in d.lower()), None)
assert lat_dim and lon_dim, f"无法识别经纬度维度名，dims={da0.dims}"

nlat, nlon = da0.sizes[lat_dim], da0.sizes[lon_dim]
# 像元中心坐标
lats = np.linspace(90 - 0.025, -90 + 0.025, nlat)          # 北->南
lons = np.linspace(-180 + 0.025, 180 - 0.025, nlon)        # 西->东
# 建立仿射变换（像元左上角为 (-180, 90)，像元大小 0.05°）
transform = Affine.translation(-180, 90) * Affine.scale(0.05, -0.05)

# 预生成国家标签栅格（int32，-1 表示海洋/无国界）
shapes = [(geom, idx) for idx, geom in enumerate(gdf.geometry)]
labels = rasterize(
    shapes=shapes,
    out_shape=(nlat, nlon),
    transform=transform,
    fill=-1,
    dtype="int32"
)

# ====== 逐月统计 ======
for f in tqdm(files, desc="Processing HDFs"):
    m = jday_pat.search(f.name)
    if not m:
        print(f"跳过文件（未识别儒略日）: {f.name}")
        continue
    jday = int(m.group(1))
    date = datetime(2024, 1, 1) + timedelta(days=jday - 1)
    month = date.month

    ds = xr.open_dataset(f, engine="netcdf4", mask_and_scale=False)
    var_candidates = [k for k in ds.data_vars if "ndvi" in k.lower()]
    if not var_candidates:
        print(f"{f.name} 中找不到 NDVI 变量，变量有: {list(ds.data_vars)}")
        continue
    da = ds[var_candidates[0]].astype("float32")

    fv = da.attrs.get("_FillValue", None)
    if fv is not None:
        da = da.where(da != fv)

    da = da * SCALE

    # 确保维度顺序与 labels 匹配（lat_dim, lon_dim）
    if da.dims != (lat_dim, lon_dim):
        da = da.transpose(lat_dim, lon_dim)

    arr = da.values  # (nlat, nlon)
    valid = np.isfinite(arr)

    # 将标签偏移 +1，使 -1 -> 0（海洋），国家 0..N-1 -> 1..N
    lab = labels + 1
    lab_valid = lab[valid]
    val_valid = arr[valid]

    # 计算各标签的加权和与计数
    # minlength 取 n_regions + 1（含海洋）
    sums = np.bincount(lab_valid.ravel(), weights=val_valid.ravel(), minlength=n_regions + 1)
    cnts = np.bincount(lab_valid.ravel(), minlength=n_regions + 1)

    means = np.full(n_regions, np.nan, dtype="float32")
    nonzero = cnts[1:] > 0
    means[nonzero] = (sums[1:][nonzero] / cnts[1:][nonzero]).astype("float32")

    # 写入行
    for idx, iso3 in enumerate(gdf["iso3"]):
        v = means[idx]
        if np.isfinite(v):
            rows.append({"iso3": iso3, "month": month, "ndvi_mean": float(np.round(v, 4))})

# ====== 导出 CSV ======
out = pd.DataFrame(rows).sort_values(["iso3", "month"])
OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
out.to_csv(OUT_CSV, index=False)
print(f"✅ Saved: {OUT_CSV}  rows={len(out)}  countries≈{out['iso3'].nunique()}")
