import re
from concurrent.futures import ThreadPoolExecutor

import requests

from .cache import cached_by_location

SOILGRIDS_URL = "https://rest.isric.org/soilgrids/v2.0/properties/query"
# Same SoilGrids maps served one pixel at a time; used when the REST API is down
SOILGRIDS_WMS_URL = "https://maps.isric.org/mapserv"
SOIL_PROPERTIES = ["phh2o", "clay", "sand", "silt", "soc", "bdod", "nitrogen", "cec"]

TEXTURE_MAP = {
    (0,  15):  "clay",
    (15, 25):  "clay loam",
    (25, 40):  "silty clay loam",
    (40, 60):  "silt loam",
    (60, 100): "sandy loam",
}

def _classify_texture(clay_pct: float, sand_pct: float) -> str:
    if clay_pct >= 40:
        return "clay"
    if clay_pct >= 27 and sand_pct <= 20:
        return "silty clay"
    if clay_pct >= 27:
        return "clay loam"
    if clay_pct >= 18 and sand_pct <= 15:
        return "silt loam"
    if sand_pct >= 70:
        return "sandy loam"
    return "loam"


# Rice roots and the plough layer sit in the top 30 cm: (SoilGrids depth label, thickness cm)
ROOT_ZONE = [("0-5cm", 5), ("5-15cm", 10), ("15-30cm", 15)]


def _root_zone_median(layer: dict):
    """Thickness-weighted average of the median (Q0.5) over the root-zone depths.

    The median, not the mean: SoilGrids' predictions for Panabo have a long upper tail
    (soil carbon Q0.95 reaches 550 g/kg, peat level), which drags the mean to ~11% soil
    carbon on mineral paddy soils while the median is ~2%.
    """
    total = weight = 0.0
    thickness = dict(ROOT_ZONE)
    for depth in layer.get("depths", []):
        value = depth.get("values", {}).get("Q0.5")
        cm = thickness.get(depth.get("label"))
        if value is not None and cm:
            total += value * cm
            weight += cm
    return total / weight if weight else None


_WMS_VALUE = re.compile(r'id="value">\s*(-?\d+(?:\.\d+)?)\s*<')


def _wms_median(prop: str, depth: str, lat: float, lon: float):
    """One property's median at one depth from the SoilGrids WMS (None for no-data pixels)."""
    layer, d = f"{prop}_{depth}_Q0.5", 0.0005
    params = {
        "map": f"/map/{prop}.map", "SERVICE": "WMS", "VERSION": "1.1.1", "REQUEST": "GetFeatureInfo",
        "LAYERS": layer, "QUERY_LAYERS": layer, "SRS": "EPSG:4326", "STYLES": "",
        "BBOX": f"{lon - d},{lat - d},{lon + d},{lat + d}", "WIDTH": 3, "HEIGHT": 3, "X": 1, "Y": 1,
        "INFO_FORMAT": "text/html", "FORMAT": "image/png",
    }
    resp = requests.get(SOILGRIDS_WMS_URL, params=params, timeout=15)
    resp.raise_for_status()
    match = _WMS_VALUE.search(resp.text)
    value = float(match.group(1)) if match else None
    return value if value and value > 0 else None


def _wms_layers(lat: float, lon: float) -> list:
    """Root-zone medians for every property via WMS, in the REST API's `layers` shape."""
    jobs = [(prop, label) for prop in SOIL_PROPERTIES for label, _ in ROOT_ZONE]
    with ThreadPoolExecutor(max_workers=8) as ex:
        futures = [ex.submit(_wms_median, prop, label, lat, lon) for prop, label in jobs]
    values, errors = {}, []
    for (prop, label), fut in zip(jobs, futures):
        try:
            values[(prop, label)] = fut.result()
        except requests.RequestException as e:
            errors.append(e)
    if errors and len(errors) == len(jobs):
        raise errors[0]                 # WMS is down too: let the scan use its fallback
    return [{"name": prop, "depths": [{"label": label, "values": {"Q0.5": values.get((prop, label))}}
                                      for label, _ in ROOT_ZONE]}
            for prop in SOIL_PROPERTIES]


# Soil properties do not change between scans.
# v3: organic matter in % (was 10x too high). v4: root-zone median instead of 0-5 cm mean.
@cached_by_location("soilgrids:soil:v4", ttl=30 * 24 * 60 * 60)
def get_soil_data(lat: float, lon: float) -> dict:
    params = {
        "lon":      lon,
        "lat":      lat,
        "property": SOIL_PROPERTIES,
        "depth":    [label for label, _ in ROOT_ZONE],
        "value":    "Q0.5",
    }
    try:
        # SoilGrids is a free research service and often takes 20-40 s to answer
        resp = requests.get(SOILGRIDS_URL, params=params, timeout=40)
        resp.raise_for_status()
        layers = resp.json().get("properties", {}).get("layers", [])
    except requests.RequestException:
        # The REST API is paused at times; the WMS serves the same maps
        layers = _wms_layers(lat, lon)

    props = {p["name"]: _root_zone_median(p) for p in layers}
    if layers and not any(v is not None for v in props.values()):
        # A degraded REST API answers with nulls for pixels the WMS still has. Built-up
        # areas and water are null in both, and the defaults below fill them in.
        try:
            props = {p["name"]: _root_zone_median(p) for p in _wms_layers(lat, lon)}
        except Exception:
            pass
    # SoilGrids has no values for built-up areas and water; the defaults below fill the gaps
    from_soilgrids = any(v is not None for v in props.values())

    ph        = round((props.get("phh2o") or 62)  / 10, 1)   # SoilGrids pH×10; 62 = pH 6.2
    clay      = round((props.get("clay")  or 350) / 10, 1)   # g/kg → %
    sand      = round((props.get("sand")  or 300) / 10, 1)
    silt      = round((props.get("silt")  or 350) / 10, 1)
    # Each fraction's median is predicted separately, so rescale them to add up to 100 %
    fractions = clay + sand + silt
    if fractions:
        clay, sand = round(clay * 100 / fractions, 1), round(sand * 100 / fractions, 1)
        silt = round(100 - clay - sand, 1)
    # SOC in dg/kg -> % (÷100), then organic matter = SOC × 1.724 (Van Bemmelen factor).
    # The suitability rule scores organic matter in % (S1 ≥ 3, S2 ≥ 2, S3 ≥ 1).
    # 145 dg/kg (SOC 1.45%) gives the old 2.5% organic matter default.
    soc       = round((props.get("soc")   or 145) / 100 * 1.724, 2)
    bulk_dens = round((props.get("bdod")  or 130) / 100, 2)  # cg/cm³ → g/cm³
    nitrogen  = round((props.get("nitrogen") or 1500) / 100, 1)  # cg/kg → mg/kg
    cec       = round((props.get("cec")  or 200) / 10, 1)    # mmol/kg → cmol/kg

    texture = _classify_texture(clay, sand)

    return {
        "ph":              ph,
        "texture":         texture,
        "clay_pct":        clay,
        "sand_pct":        sand,
        "silt_pct":        silt,
        "organic_matter":  soc,
        "bulk_density":    bulk_dens,
        "nitrogen_ppm":    nitrogen,
        "cec":             cec,
        "drainage":        "poorly drained" if clay > 35 else "moderately drained",
        "from_soilgrids":  from_soilgrids,  # False: every value is a default, not a measurement
    }
