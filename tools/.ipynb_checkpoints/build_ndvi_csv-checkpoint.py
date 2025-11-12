from pathlib import Path
import re
import pandas as pd
import geopandas as gpd
import numpy as np
import xarray as xr
import regionmask
from tqdm import tqdm

# ====== 路径 ======
ROOT = Path(__file__).resolve().parents[1]
SHAPE_PATH = ROOT / "data/shapes/ne_110m_admin_0_countries.shp"
MODIS_DIR  = ROOT / "data/modis"
OUT_CSV    = ROOT / "data/ndvi_country_2024.csv"

SCALE = 1e-4  # MODIS NDVI 缩放因子
month_pat = re.compile(r"A2024(\d{3})")  # 从文件名识别儒略日

# ====== 读取国家边界 ======
gdf = gpd.read_file(SHAPE_PATH).to_crs(4326)
for cand in ["ISO_A3", "ADM0_A3", "iso_a3", "ISO3"]:
    if cand in gdf.columns:
        gdf["iso3"] = gdf[cand]
        break
assert "iso3" in gdf.columns, "shapefile 里没有 ISO3 字段"

gdf = gdf[["iso3", "geometry"]]
regions = regionmask.Regions(
    numbers=list(range(len(gdf))),
    names=list(gdf["iso3"]),
    outlines=list(gdf["geometry"].values)
)

rows = []

files = sorted(MODIS_DIR.glob("*.hdf"))
assert files, f"没找到 {MODIS_DIR} 下的 HDF 文件"

for f in tqdm(files, desc="Processing HDFs"):
    # 从文件名推月份
    m = month_pat.search(f.name)
    if not m:
        print(f"跳过文件（未识别月份）: {f.name}")
        continue
    day_of_year = int(m.group(1))
    month = int(np.ceil(day_of_year / 30.5))

    ds = xr.open_dataset(f, engine="netcdf4", mask_and_scale=False)
    # 寻找 NDVI 波段
    var_candidates = [k for k in ds.data_vars if "ndvi" in k.lower()]
    if not var_candidates:
        print(f"{f.name} 中找不到 NDVI 波段，变量有: {list(ds.data_vars)}")
        continue
    da = ds[var_candidates[0]].astype("float32")
    fv = da.attrs.get("_FillValue", None)
    if fv is not None:
        da = da.where(da != fv)
    da = da * SCALE

    lat_name = next(c for c in da.coords if c.lower().startswith("lat"))
    lon_name = next(c for c in da.coords if c.lower().startswith("lon"))

    mask = regions.mask(da, lon_name=lon_name, lat_name=lat_name)
    grouped = da.groupby(mask).mean(skipna=True)

    for idx, iso3 in enumerate(gdf["iso3"]):
        try:
            v = grouped.sel(mask=idx).item()
        except Exception:
            v = np.nan
        if np.isfinite(v):
            rows.append({"iso3": iso3, "month": month, "ndvi_mean": round(float(v), 4)})

out = pd.DataFrame(rows).sort_values(["iso3", "month"])
OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
out.to_csv(OUT_CSV, index=False)
print(f"✅ Saved: {OUT_CSV}  rows={len(out)} countries≈{out['iso3'].nunique()}")
