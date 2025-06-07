from enum import Enum
from typing import Dict, List, Union, Literal
from fasthtml.common import *
from fasthtml.components import Uk_chart
from monsterui.all import *
from monsterui.core import stringify
import json
from copy import deepcopy

class ChartT(str, Enum):
    line = "line"
    area = "area"
    bar = "bar"
    column = "column"
    histogram = "histogram"
    pie = "pie"
    donut = "donut"
    radar = "radar"
    scatter = "scatter"
    bubble = "bubble"
    candlestick = "candlestick"
    heatmap = "heatmap"
    radialBar = "radialBar"
    rangeBar = "rangeBar"
    rangeArea = "rangeArea"
    treemap = "treemap"
    polarArea = "polarArea"
    boxPlot = "boxPlot"
    waterfall = "waterfall"
    timeline = "timeline"

def _deep_merge(a: Dict, b: Dict) -> Dict:
    out = deepcopy(a)
    for k, v in b.items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = deepcopy(v)
    return out

def Apex_Chart(
    *,
    series: Union[List[Dict], List[float]],  # Data to plot. For axis charts, pass a list of series-objects; for pie/donut/radialBar, pass a flat list of values. See Apex “Working with Data” docs. :contentReference[oaicite:turn0search11]{index=0}
    chart_type: ChartT = ChartT.line,        # One of Apex’s supported chart types (line, area, bar, pie, donut, heatmap, etc.). :contentReference[oaicite:turn0search1]{index=1}
    categories: List[str] | None = None,     # X-axis categories for axis charts (ignored by pie/donut). :contentReference[oaicite:turn0search2]{index=2}
    enable_zoom: bool | None = None,         # Toggle interactive zoom (None = Apex default). :contentReference[oaicite:turn0search3]{index=3}
    show_toolbar: bool = False,              # Show the chart toolbar (download, zoom buttons). :contentReference[oaicite:turn0search4]{index=4}
    data_labels: bool = False,               # Show numeric labels on points/bars. :contentReference[oaicite:turn0search5]{index=5}
    show_yaxis_labels: bool = False,         # Render y-axis tick labels. :contentReference[oaicite:turn0search6]{index=6}
    show_tooltip_title: bool = False,        # Display the tooltip title section. :contentReference[oaicite:turn0search7]{index=7}
    distributed: bool = False,               # Color each bar individually (bar/column charts only). :contentReference[oaicite:turn0search8]{index=8}
    curve: Literal["smooth", "straight", "stepline"] = "smooth",  # Stroke curve style for line/area. :contentReference[oaicite:turn0search9]{index=9}
    stroke_width: int = 2,                   # Width (px) of line/area strokes. :contentReference[oaicite:turn0search9]{index=10}
    colors: List[str] | None = None,         # Palette array or callback for series/points. :contentReference[oaicite:turn0search10]{index=11}
    cls: str = '',                           # Extra CSS classes for the outer <div>. (Utility parameter, no Apex reference.)
    **extra_options,                         # Arbitrary ApexCharts options to deep-merge over the defaults.
) -> Div:
    """
    Build a Div that renders an ApexCharts graph.
    All boolean parameters default to *False* (or *None*) to avoid surprising side-effects; pass ``True`` to opt-in.
    Any key you pass via ``extra_options`` overrides the baked-in defaults without losing the design-system styles.   
    """
    base = {
        "series": series,
        "chart": {
            "type": chart_type,
            # If caller leaves enable_zoom=None we fall back to Apex default
            **({"zoom": {"enabled": enable_zoom}} if enable_zoom is not None else {}),
            "toolbar": {"show": show_toolbar},
        },
        "dataLabels": {"enabled": data_labels},
        "stroke": {"curve": curve, "width": stroke_width},
        "colors": colors or [f"hsl(var(--chart-{i+1}))" for i in range(len(series))],
        "grid": {"row": {"colors": []}, "borderColor": "hsl(var(--border))"},
        "tooltip": {"title": {"show": show_tooltip_title}},
        "yaxis": {"labels": {"show": show_yaxis_labels}},
    }

    # Axis scaffolding only when caller passes categories
    if categories is not None:
        base["xaxis"] = {
            "categories": categories,
            "tooltip": {"enabled": False},
            "labels": {"style": {"colors": "hsl(var(--muted-foreground))"}},
            "axisBorder": {"show": False},
            "axisTicks": {"show": False},
        }

    # Per-bar colouring option for bar/column charts
    if distributed and chart_type in ("bar", "column"):
        base.setdefault("plotOptions", {}).setdefault("bar", {})["distributed"] = True

    merged = _deep_merge(base, extra_options)
    return Div(Uk_chart(Script(json.dumps(merged, separators=(",", ":")), type="application/json")), cls=stringify(cls))