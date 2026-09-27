"""Construit docs/data/countries.js à partir de Natural Earth 1:50m (domaine public).
Usage : python tools/build_countries.py chemin/vers/ne_50m_admin_0_countries.geojson
Rarement nécessaire : le fichier généré est déjà fourni."""
import json
import sys


def rdp(points, eps):
    if len(points) < 3:
        return points
    (x1, y1), (x2, y2) = points[0], points[-1]
    dx, dy = x2 - x1, y2 - y1
    norm = (dx * dx + dy * dy) ** 0.5
    dmax, idx = 0.0, 0
    for i in range(1, len(points) - 1):
        px, py = points[i]
        if norm == 0:
            d = ((px - x1) ** 2 + (py - y1) ** 2) ** 0.5
        else:
            d = abs(dy * px - dx * py + x2 * y1 - y2 * x1) / norm
        if d > dmax:
            dmax, idx = d, i
    if dmax > eps:
        left = rdp(points[: idx + 1], eps)
        right = rdp(points[idx:], eps)
        return left[:-1] + right
    return [points[0], points[-1]]


def simplify_ring(ring, eps):
    pts = rdp(ring, eps)
    pts = [[round(x, 3), round(y, 3)] for x, y in pts]
    if len(pts) < 4:
        return None
    if pts[0] != pts[-1]:
        pts.append(pts[0])
    return pts


def simplify_polygon(poly, eps):
    out = []
    for i, ring in enumerate(poly):
        r = simplify_ring(ring, eps)
        if r is None:
            if i == 0:
                return None
            continue
        out.append(r)
    return out


def main(src, dst="docs/data/countries.js", eps=0.04):
    data = json.load(open(src, encoding="utf-8"))
    feats = []
    for f in data["features"]:
        p = f["properties"]
        iso2 = p["ISO_A2_EH"] if p["ISO_A2_EH"] not in ("-99", None) else p["ADM0_A3"]
        iso3 = p["ISO_A3_EH"] if p["ISO_A3_EH"] not in ("-99", None) else p["ADM0_A3"]
        g = f["geometry"]
        polys = [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]
        simp = [s for s in (simplify_polygon(pl, eps) for pl in polys) if s]
        if not simp:
            # micro-États : on garde un petit carré autour du point d'étiquette
            x, y = p["LABEL_X"], p["LABEL_Y"]
            d = 0.08
            simp = [[[[x - d, y - d], [x + d, y - d], [x + d, y + d], [x - d, y + d], [x - d, y - d]]]]
        feats.append({
            "type": "Feature",
            "properties": {
                "iso2": iso2, "iso3": iso3, "fips": p.get("FIPS_10") or "",
                "name_en": p["NAME_EN"], "name_fr": p["NAME_FR"],
                "continent": p["CONTINENT"], "region": p["SUBREGION"],
                "label": [round(p["LABEL_X"], 3), round(p["LABEL_Y"], 3)],
            },
            "geometry": {"type": "MultiPolygon", "coordinates": simp},
            "_pop": p.get("POP_EST") or 0,
        })
    # un même code ISO peut couvrir plusieurs entités (ex. Australie + îles Ashmore) : on fusionne
    merged = {}
    for f in feats:
        k = f["properties"]["iso2"]
        if k in merged:
            merged[k]["geometry"]["coordinates"].extend(f["geometry"]["coordinates"])
            if f["_pop"] > merged[k]["_pop"]:
                merged[k]["properties"], merged[k]["_pop"] = f["properties"], f["_pop"]
        else:
            merged[k] = f
    feats = list(merged.values())
    for f in feats:
        f.pop("_pop", None)
    fc = {"type": "FeatureCollection", "features": feats}
    with open(dst, "w", encoding="utf-8") as fh:
        fh.write("window.VS_COUNTRIES = ")
        json.dump(fc, fh, ensure_ascii=False, separators=(",", ":"))
        fh.write(";\n")
    print(len(feats), "pays écrits dans", dst)


if __name__ == "__main__":
    main(sys.argv[1])
