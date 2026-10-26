"""Generate the Node-RED flow (Dashboard 2.0) of the Raspberry Pi edge node -> node-red-flows.json."""
import json
import os

SENSORS = [("temperature", "Temperature", "°C", 0, 50, 30, "#3987e5"),
           ("humidity", "Humidity", "%", 0, 100, 80, "#d95926"),
           ("pressure", "Pressure", "hPa", 980, 1050, None, "#199e70"),
           ("co2", "Air quality CO₂", "ppm", 300, 800, 600, "#c98500")]
nodes = []
n_id = [0]


def nid(prefix):
    n_id[0] += 1
    return f"{prefix}{n_id[0]:04x}"


ui_y = [40]


def add(node):
    if node.get("x") == 900:
        node["y"] = ui_y[0]
        ui_y[0] += 50
    nodes.append(node)
    return node["id"]


TAB = add({"id": "tabedge01", "type": "tab", "label": "Edge dashboard", "disabled": False,
           "info": "Raspberry Pi edge node: raw sensor data vs filtered data, throughput, alerts, control."})
BROKER = add({"id": "brokeredge", "type": "mqtt-broker", "name": "Edge Mosquitto (localhost)", "broker": "localhost",
              "port": "1883", "clientid": "", "autoConnect": True, "usetls": False, "protocolVersion": "4",
              "keepalive": "60", "cleansession": True, "autoUnsubscribe": True})
BASE = add({"id": "uibase01", "type": "ui-base", "name": "Edge", "path": "/dashboard", "appIcon": "",
            "includeClientData": True, "acceptsClientConfig": ["ui-notification", "ui-control"],
            "showPathInSidebar": False, "showPageTitle": True, "navigationStyle": "default",
            "titleBarStyle": "default"})
THEME = add({"id": "uitheme01", "type": "ui-theme", "name": "Edge dark",
             "colors": {"surface": "#1c5cab", "primary": "#3987e5", "bgPage": "#121211", "groupBg": "#1a1a19",
                        "groupOutline": "#2f2f2b"},
             "sizes": {"density": "default", "pagePadding": "12px", "groupGap": "12px", "groupBorderRadius": "8px",
                       "widgetGap": "12px"}})
PAGE = add({"id": "uipage01", "type": "ui-page", "name": "Raspberry Pi edge node", "ui": BASE, "path": "/edge",
            "icon": "chip", "layout": "grid", "theme": THEME, "breakpoints": [{"name": "Default", "px": "0", "cols": "3"},
            {"name": "Tablet", "px": "576", "cols": "6"}, {"name": "Small Desktop", "px": "768", "cols": "9"},
            {"name": "Desktop", "px": "1024", "cols": "12"}],
            "order": 1, "className": "", "visible": "true", "disabled": "false"})


def group(name, width, order):
    return add({"id": nid("grp"), "type": "ui-group", "name": name, "page": PAGE, "width": str(width), "height": "1",
                "order": order, "showTitle": True, "className": "", "visible": "true", "disabled": "false",
                "groupType": "default"})


def chart(grp, name, order, colors, ylabel, width=6, height=5, points=600):
    return add({"id": nid("cht"), "type": "ui-chart", "z": TAB, "group": grp, "name": name, "label": name,
                "order": order, "chartType": "line", "category": "topic", "categoryType": "msg",
                "xAxisLabel": "", "xAxisProperty": "", "xAxisPropertyType": "timestamp", "xAxisType": "time",
                "xAxisFormat": "", "xAxisFormatType": "auto", "yAxisLabel": ylabel, "yAxisProperty": "payload",
                "yAxisPropertyType": "msg", "ymin": "", "ymax": "", "bins": 10, "action": "append",
                "stackSeries": False, "pointShape": "false", "pointRadius": 2, "showLegend": True,
                "removeOlder": "3", "removeOlderUnit": "60", "removeOlderPoints": str(points),
                "colors": colors + ["#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948", "#9085e9"][: 9 - len(colors)],
                "textColor": ["#c3c2b7"], "textColorDefault": False, "gridColor": ["#2f2f2b"],
                "gridColorDefault": False, "width": width, "height": height, "className": "",
                "interpolation": "linear", "x": 900, "y": 0, "wires": [[]]})


def gauge(grp, title, units, order, lo, hi, limit, color, width=3):
    segs = [{"from": str(lo), "color": color}]
    if limit is not None:
        segs.append({"from": str(limit), "color": "#d03b3b"})
    return add({"id": nid("gau"), "type": "ui-gauge", "z": TAB, "group": grp, "name": title, "gtype": "gauge-half",
                "gstyle": "rounded", "title": title, "units": units, "icon": "", "order": order, "value": "payload",
                "valueType": "msg", "width": width, "height": 3, "min": lo, "max": hi, "sizeThickness": 16,
                "sizeGap": 4, "sizeKeyThickness": 8, "styleRounded": True, "styleGlow": False, "segments": segs,
                "className": "", "x": 900, "y": 0, "wires": []})


def text(grp, label, order, width=3):
    return add({"id": nid("txt"), "type": "ui-text", "z": TAB, "group": grp, "order": order, "width": width,
                "height": 1, "name": label, "label": label, "format": "{{msg.payload}}", "layout": "row-spread",
                "style": False, "font": "", "fontSize": 16, "color": "#f0efec", "className": "",
                "x": 900, "y": 0, "wires": []})


def mqtt_in(topic, wires, y):
    return add({"id": nid("min"), "type": "mqtt in", "z": TAB, "name": topic, "topic": topic, "qos": "0",
                "datatype": "json", "broker": BROKER, "nl": False, "rap": True, "rh": 0, "inputs": 0,
                "x": 140, "y": y, "wires": [wires]})


def function(name, code, outputs, wires, y, x=420):
    return add({"id": nid("fn"), "type": "function", "z": TAB, "name": name, "func": code, "outputs": outputs,
                "timeout": 0, "noerr": 0, "initialize": "", "finalize": "", "libs": [], "x": x, "y": y,
                "wires": wires})


# ---- sensor groups: one chart (raw vs filtered) + one gauge per sensor
sensor_targets = []
for i, (key, label, unit, lo, hi, limit, color) in enumerate(SENSORS):
    g = group(f"{label} ({unit})", 6, i + 1)
    c = chart(g, f"{label}: raw vs edge-filtered", 1, [color, "#8a8981"], unit, width=4, height=4, points=1200)
    ga = gauge(g, f"{label} (filtered)", unit, 2, lo, hi, limit, color, width=2)
    sensor_targets.append((c, ga))

route_code = """// split raw / filtered messages per sensor -> [chart, gauge] outputs.
// The chart colours its series by order of first appearance, so every raw point is
// sent right after the value currently held at the edge output (filtered first).
const sensors = %s;
const parts = msg.topic.split('/');
const i = sensors.indexOf(parts[1]);
if (i < 0 || typeof msg.payload.value !== 'number') return null;
const out = new Array(sensors.length * 2).fill(null);
const v = Math.round(msg.payload.value * 100) / 100;
if (parts[2] === 'filtered') {
    context.set(parts[1], v);
    out[2 * i + 1] = { payload: v };
    return out;
}
const held = context.get(parts[1]);
if (held === undefined) return null;
out[2 * i] = [{ topic: 'filtered (edge → cloud)', payload: held }, { topic: 'raw (sensor → edge)', payload: v }];
return out;""" % json.dumps([s[0] for s in SENSORS])

wires = []
for c, ga in sensor_targets:
    wires += [[c], [ga]]
ROUTE = function("route per sensor", route_code, len(SENSORS) * 2, wires, 160, x=560)
# raw data is decimated (1 point out of 2 per sensor) to keep the browser fluid
DECIM = function("decimate raw", "const k = msg.topic;\nconst n = (context.get(k) || 0) + 1;\ncontext.set(k, n);\nreturn n % 2 ? msg : null;", 1, [[ROUTE]], 80, x=360)
mqtt_in("sensors/+/raw", [DECIM], 80)
mqtt_in("edge/+/filtered", [ROUTE], 160)

# ---- throughput group
gt = group("Throughput: before / after the edge filter", 8, 5)
tp_chart = chart(gt, "Bytes per second", 1, ["#3987e5", "#d95926"], "B/s", width=8, height=4, points=300)
gk = group("Data reduction", 4, 6)
red_gauge = gauge(gk, "Bandwidth saved", "%", 1, 0, 100, None, "#199e70", width=4)
mode_text = text(gk, "Edge filter", 2, width=4)
in_text = text(gk, "Raw ingress", 3, width=4)
out_text = text(gk, "Reduced egress", 4, width=4)
stats_code = """const s = msg.payload;
return [
  [{ topic: 'raw in (sensors → edge)', payload: s.in_bytes_s }, { topic: 'reduced out (edge → cloud)', payload: s.out_bytes_s }],
  { payload: s.reduction_pct },
  { payload: `${s.mode} · ${s.period}s · window ${s.window}` },
  { payload: `${s.in_msgs_s} msg/s · ${s.in_bytes_s} B/s` },
  { payload: `${s.out_msgs_s} msg/s · ${s.out_bytes_s} B/s` },
];"""
STATS = function("stats", stats_code, 5, [[tp_chart], [red_gauge], [mode_text], [in_text], [out_text]], 340)
mqtt_in("edge/stats", [STATS], 340)

# ---- Pi system + control group
gs = group("Raspberry Pi & edge control", 12, 7)
cpu_g = gauge(gs, "CPU", "%", 1, 0, 100, 85, "#3987e5", width=3)
mem_g = gauge(gs, "Memory", "%", 2, 0, 100, 85, "#d95926", width=3)
SYS = function("system", "const s = msg.payload;\nreturn [{payload: s.cpu_pct}, {payload: s.mem_used_pct}];", 2,
               [[cpu_g], [mem_g]], 480)
mqtt_in("edge/system", [SYS], 480)

CTRL_OUT = add({"id": nid("mout"), "type": "mqtt out", "z": TAB, "name": "edge/control", "topic": "edge/control",
                "qos": "0", "retain": "false", "respTopic": "", "contentType": "", "userProps": "", "correl": "",
                "expiry": "", "broker": BROKER, "x": 660, "y": 600, "wires": []})
CTRL = function("to control JSON", "msg.payload = JSON.stringify({ mode: msg.payload });\nreturn msg;", 1, [[CTRL_OUT]], 600)
add({"id": nid("btn"), "type": "ui-button-group", "z": TAB, "name": "Edge filter mode", "group": gs,
     "order": 3, "width": 6, "height": 1, "label": "Edge filter mode", "className": "", "rounded": True,
     "useThemeColors": True, "passthru": False, "topic": "topic", "topicType": "msg",
     "options": [{"label": "Moving average", "icon": "", "value": "moving", "valueType": "str", "color": "#3987e5"},
                 {"label": "Sampling (period mean)", "icon": "", "value": "sampling", "valueType": "str", "color": "#3987e5"},
                 {"label": "Pass-through", "icon": "", "value": "passthrough", "valueType": "str", "color": "#3987e5"}],
     "x": 160, "y": 600, "wires": [[CTRL]]})

# ---- alerts -> notification
NOTIF = add({"id": nid("ntf"), "type": "ui-notification", "z": TAB, "ui": BASE, "position": "top right",
             "colorDefault": False, "color": "#d03b3b", "displayTime": "6", "showCountdown": True, "outputs": 1,
             "allowDismiss": True, "dismissText": "Close", "allowConfirm": False, "confirmText": "Confirm",
             "raw": False, "className": "", "name": "edge alert", "x": 660, "y": 680, "wires": [[]]})
ALERT = function("format alert", "const a = msg.payload;\nmsg.payload = `${a.state === 'ALARM' ? '⚠ ALARM' : '✓ back to normal'}: ${a.sensor} = ${a.value} (limit ${a.limit})`;\nreturn msg;", 1, [[NOTIF]], 680)
mqtt_in("edge/alerts", [ALERT], 680)

out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "node-red-flows.json")
with open(out, "w", encoding="utf-8") as f:
    json.dump(nodes, f, indent=1, ensure_ascii=False)
print(f"{len(nodes)} nodes -> {out}")
