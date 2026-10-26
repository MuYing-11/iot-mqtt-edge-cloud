"""IoT sensor simulator (PyQt6) for TP1/TP2 - PC side.

    PC simulator --MQTT--> Raspberry Pi (Mosquitto + edge filter) --MQTT--> EC2 cloud broker

* generates realistic sensor data (bitperfect Simulator model) for 4 sensors
* publishes it to the edge broker, periodically or with Poisson arrivals (lambda)
* listens to what the Pi sends out (edge/<s>/filtered) and to what reaches the
  cloud (cloud/<s> on EC2) and overlays the three curves
* 3D view, animated data-flow view, edge filter remote control
* separate "Throughput" window: bytes/s and msg/s at each hop

usage: python iot_simulator.py
"""
import collections
import json
import math
import os
import queue
import random
import sys
import threading
import time

from PyQt6 import QtCore, QtGui, QtWidgets

import pyqtgraph as pg
import pyqtgraph.opengl as gl
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tp2"))
import cloud_env  # noqa: E402
from sensor_sim import SENSORS, Simulator, make_client  # noqa: E402

COLORS = {"temperature": "#3987e5", "humidity": "#d95926", "pressure": "#199e70", "co2": "#c98500"}
RAW, EDGE, CLOUD = "#8a8981", "#3987e5", "#d95926"
# live-sensor plots use the same look as the TP2 figures (matplotlib default colours)
PLOT_RAW, PLOT_REDUCED = "#1f77b4", "#ff7f0e"
MEAN_TYPES = [("sampling", "Sampling (mean per period)"),
              ("moving", "Centred moving average"),
              ("passthrough", "Pass-through (no reduction)")]
HISTORY = 6000

pg.setConfigOptions(antialias=True, background="#161615", foreground="#c3c2b7")


def mqtt_size(topic, payload):
    remaining = 2 + len(topic.encode()) + len(payload)
    return 1 + (1 if remaining < 128 else 2) + remaining


class Publisher(threading.Thread):
    """Generates sensor values and publishes them (periodic or Poisson arrivals)."""

    def __init__(self, client, sensors, rate, poisson, events):
        super().__init__(daemon=True)
        self.client, self.sensors, self.rate, self.poisson = client, sensors, rate, poisson
        self.events = events
        self.running = threading.Event()
        self.running.set()
        self.sims = {n: Simulator(seed, mean, sd) for n, (seed, mean, sd, _) in SENSORS.items()}
        self.seq = collections.Counter()
        self.spike_until = 0.0

    def interval(self):
        if self.poisson:
            return -math.log(1.0 - random.random()) / self.rate
        return 1.0 / self.rate

    def run(self):
        now = time.time()
        due = {n: now + random.random() / self.rate for n in self.sensors}
        while self.running.is_set():
            name = min(due, key=due.get)
            wait = due[name] - time.time()
            if wait > 0:
                time.sleep(min(wait, 0.05))
                continue
            value = self.sims[name].calculate_next_value()
            if time.time() < self.spike_until and name in ("temperature", "co2"):
                value += 15 if name == "temperature" else 250
            payload = json.dumps({"seq": self.seq[name], "ts": round(time.time(), 3),
                                  "value": round(value, 3), "unit": SENSORS[name][3]}).encode()
            topic = f"sensors/{name}/raw"
            self.client.publish(topic, payload)
            self.seq[name] += 1
            self.events.put(("pub", name, time.time(), value, mqtt_size(topic, payload)))
            due[name] += self.interval()
            if due[name] < time.time() - 1:  # fell behind: resync
                due[name] = time.time()

    def stop(self):
        self.running.clear()


class FlowView(QtWidgets.QWidget):
    """Animated view of the data path PC -> Pi -> EC2."""

    NODES = [("PC", "Sensor simulator", "PyQt6 · paho-mqtt"),
             ("Raspberry Pi", "Edge broker + filter", "192.168.174.133:1883"),
             ("EC2", "Cloud broker", "13.60.75.46:1883")]

    def __init__(self):
        super().__init__()
        self.packets = []  # [hop, progress, color]
        self.counts = [0, 0]
        self.rates = [0.0, 0.0]
        self.last = ["", ""]
        self.setMinimumHeight(360)
        timer = QtCore.QTimer(self)
        timer.timeout.connect(self.step)
        timer.start(30)

    def add(self, hop, text):
        self.counts[hop] += 1
        self.last[hop] = text
        if len(self.packets) < 120:
            self.packets.append([hop, 0.0, QtGui.QColor(EDGE if hop == 0 else CLOUD)])

    def step(self):
        for p in self.packets:
            p[1] += 0.025
        self.packets = [p for p in self.packets if p[1] < 1.0]
        self.update()

    def node_rects(self):
        w, h = self.width(), self.height()
        bw, bh = min(220, w / 4.2), 110
        xs = [w * 0.04, (w - bw) / 2, w * 0.96 - bw]
        return [QtCore.QRectF(x, h / 2 - bh / 2 - 20, bw, bh) for x in xs]

    def paintEvent(self, _):
        qp = QtGui.QPainter(self)
        qp.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        qp.fillRect(self.rect(), QtGui.QColor("#161615"))
        rects = self.node_rects()
        for hop in range(2):
            a, b = rects[hop], rects[hop + 1]
            y = a.center().y()
            x1, x2 = a.right(), b.left()
            qp.setPen(QtGui.QPen(QtGui.QColor("#3a3a35"), 3))
            qp.drawLine(QtCore.QPointF(x1, y), QtCore.QPointF(x2, y))
            qp.setPen(QtGui.QColor("#c3c2b7"))
            label = ["sensors/+/raw  (raw data)", "cloud/+  (reduced data)"][hop]
            qp.drawText(QtCore.QRectF(x1, y - 46, x2 - x1, 20), QtCore.Qt.AlignmentFlag.AlignCenter, label)
            qp.setPen(QtGui.QColor("#f0efec"))
            qp.drawText(QtCore.QRectF(x1, y + 12, x2 - x1, 20), QtCore.Qt.AlignmentFlag.AlignCenter,
                        f"{self.rates[hop]:.1f} msg/s · total {self.counts[hop]}")
            qp.setPen(QtGui.QColor("#8a8981"))
            qp.setFont(QtGui.QFont("Consolas", 8))
            qp.drawText(QtCore.QRectF(rects[0].left(), self.height() - 70 + hop * 22, self.width() * 0.92, 20),
                        QtCore.Qt.AlignmentFlag.AlignLeft,
                        ("last PC → Pi : " if hop == 0 else "last Pi → EC2: ") + self.last[hop][:150])
            qp.setFont(QtGui.QFont())
            for p in self.packets:
                if p[0] != hop:
                    continue
                x = x1 + (x2 - x1) * p[1]
                qp.setPen(QtCore.Qt.PenStyle.NoPen)
                qp.setBrush(p[2])
                qp.drawEllipse(QtCore.QPointF(x, y), 6, 6)
        for rect, (title, sub, addr) in zip(rects, self.NODES):
            qp.setPen(QtGui.QPen(QtGui.QColor("#3a3a35"), 1.5))
            qp.setBrush(QtGui.QColor("#22221f"))
            qp.drawRoundedRect(rect, 12, 12)
            qp.setPen(QtGui.QColor("#f0efec"))
            f = QtGui.QFont()
            f.setPointSize(12)
            f.setBold(True)
            qp.setFont(f)
            qp.drawText(rect.adjusted(0, 14, 0, 0), QtCore.Qt.AlignmentFlag.AlignHCenter, title)
            qp.setFont(QtGui.QFont())
            qp.setPen(QtGui.QColor("#c3c2b7"))
            qp.drawText(rect.adjusted(0, 46, 0, 0), QtCore.Qt.AlignmentFlag.AlignHCenter, sub)
            qp.setPen(QtGui.QColor("#8a8981"))
            qp.drawText(rect.adjusted(0, 70, 0, 0), QtCore.Qt.AlignmentFlag.AlignHCenter, addr)


class ThroughputWindow(QtWidgets.QWidget):
    """Separate window: throughput of the generated data at each hop."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Throughput monitor - sensors → edge → cloud")
        self.resize(1000, 720)
        self.setStyleSheet("background:#121211; color:#f0efec;")
        lay = QtWidgets.QVBoxLayout(self)
        self.summary = QtWidgets.QLabel("waiting for data…")
        self.summary.setStyleSheet("font-size:14px; padding:6px;")
        lay.addWidget(self.summary)
        self.bytes_plot = pg.PlotWidget(title="Bytes per second (MQTT PUBLISH packets)", axisItems={"bottom": pg.DateAxisItem()})
        self.msgs_plot = pg.PlotWidget(title="Messages per second", axisItems={"bottom": pg.DateAxisItem()})
        for p, unit in ((self.bytes_plot, "B/s"), (self.msgs_plot, "msg/s")):
            p.showGrid(x=False, y=True, alpha=0.25)
            p.setLabel("left", unit)
            p.addLegend(offset=(10, 5))
            lay.addWidget(p)
        series = [("Published by the PC simulator", "#8a8981"), ("Received by the Pi edge", EDGE), ("Received by EC2 cloud", CLOUD)]
        self.curves = {}
        for key, plot in (("bytes", self.bytes_plot), ("msgs", self.msgs_plot)):
            self.curves[key] = [plot.plot([], [], name=n, pen=pg.mkPen(c, width=2), stepMode=None) for n, c in series]
        self.data = {k: [collections.deque(maxlen=300) for _ in range(3)] for k in ("bytes", "msgs")}
        self.t = collections.deque(maxlen=300)

    def add(self, ts, pub, edge, cloud):
        """pub / edge / cloud = (bytes, msgs) measured during the last second."""
        self.t.append(ts)
        for i, (b, m) in enumerate((pub, edge, cloud)):
            self.data["bytes"][i].append(b)
            self.data["msgs"][i].append(m)
        t = list(self.t)
        for key in ("bytes", "msgs"):
            for i in range(3):
                self.curves[key][i].setData(t, list(self.data[key][i]))
        n = min(30, len(t))
        avg = [sum(list(self.data["bytes"][i])[-n:]) / n for i in range(3)]
        gain = 100 * (1 - avg[2] / avg[0]) if avg[0] else 0
        self.summary.setText(
            f"<b>last 30 s</b> &nbsp; PC → Pi: <b>{avg[0]:.0f} B/s</b> &nbsp;|&nbsp; Pi received: <b>{avg[1]:.0f} B/s</b>"
            f" &nbsp;|&nbsp; arriving at EC2: <b style='color:{CLOUD}'>{avg[2]:.0f} B/s</b> &nbsp;|&nbsp; "
            f"bandwidth saved by the edge: <b style='color:#3fcf8e'>{gain:.1f} %</b>")


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("IoT Sensor Simulator - TP Edge computing (PC → Raspberry Pi → EC2)")
        self.resize(1400, 860)
        self.events = queue.Queue()
        self.publisher = None
        self.edge_client = None
        self.cloud_client = None
        self.env = cloud_env.load()
        self.series = {n: {k: collections.deque(maxlen=HISTORY) for k in ("raw", "edge", "cloud")} for n in SENSORS}
        self.second = {"pub": [0, 0], "edge": [0, 0], "cloud": [0, 0]}
        self.edge_stats = None
        self.edge_config = None
        self.t0 = time.time()
        self.flow_rate_win = [collections.deque(maxlen=5), collections.deque(maxlen=5)]

        central = QtWidgets.QWidget()
        root = QtWidgets.QHBoxLayout(central)
        controls = QtWidgets.QScrollArea()
        controls.setWidget(self.build_controls())
        controls.setWidgetResizable(True)
        controls.setFixedWidth(320)
        controls.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        root.addWidget(controls, 0)
        self.tabs = QtWidgets.QTabWidget()
        root.addWidget(self.tabs, 1)
        self.setCentralWidget(central)
        self.build_live_tab()
        self.build_3d_tab()
        self.flow = FlowView()
        self.tabs.addTab(self.flow, "Data flow PC → Pi → EC2")
        self.log = QtWidgets.QPlainTextEdit(readOnly=True)
        self.log.setMaximumBlockCount(500)
        self.log.setStyleSheet("font-family:Consolas; font-size:11px;")
        self.tabs.addTab(self.log, "MQTT messages")

        self.throughput = ThroughputWindow()
        self.statusBar().showMessage("Not connected")

        drain = QtCore.QTimer(self)
        drain.timeout.connect(self.drain)
        drain.start(50)
        tick = QtCore.QTimer(self)
        tick.timeout.connect(self.every_second)
        tick.start(1000)
        redraw = QtCore.QTimer(self)
        redraw.timeout.connect(self.redraw)
        redraw.start(250)
        self.connect_brokers()

    # ---------- UI ----------
    def build_controls(self):
        box = QtWidgets.QWidget()
        box.setFixedWidth(300)
        lay = QtWidgets.QVBoxLayout(box)

        g = QtWidgets.QGroupBox("Brokers")
        f = QtWidgets.QFormLayout(g)
        self.edge_host = QtWidgets.QLineEdit("192.168.174.133")
        self.cloud_host = QtWidgets.QLineEdit(self.env["CLOUD_HOST"])
        f.addRow("Edge (Pi)", self.edge_host)
        f.addRow("Cloud (EC2)", self.cloud_host)
        btn = QtWidgets.QPushButton("Reconnect")
        btn.clicked.connect(self.connect_brokers)
        f.addRow(btn)
        self.conn_label = QtWidgets.QLabel("–")
        self.conn_label.setMinimumHeight(40)
        f.addRow(self.conn_label)
        lay.addWidget(g)

        g = QtWidgets.QGroupBox("Sensors")
        v = QtWidgets.QVBoxLayout(g)
        self.sensor_checks = {}
        for n, (_, mean, sd, unit) in SENSORS.items():
            c = QtWidgets.QCheckBox(f"{n}  (μ={mean:g} {unit}, σ={sd:g})")
            c.setChecked(True)
            c.setStyleSheet(f"color:{COLORS[n]}")
            self.sensor_checks[n] = c
            v.addWidget(c)
        lay.addWidget(g)

        g = QtWidgets.QGroupBox("Publication")
        f = QtWidgets.QFormLayout(g)
        self.mode = QtWidgets.QComboBox()
        self.mode.addItems(["Poisson (random arrivals)", "Periodic"])
        self.rate = QtWidgets.QDoubleSpinBox(minimum=0.2, maximum=200, value=10, decimals=1, suffix=" msg/s")
        f.addRow("Arrivals", self.mode)
        f.addRow("λ per sensor", self.rate)
        row = QtWidgets.QHBoxLayout()
        self.start_btn = QtWidgets.QPushButton("▶ Start")
        self.start_btn.setStyleSheet("background:#1c5cab; color:white; padding:6px; font-weight:bold;")
        self.start_btn.clicked.connect(self.toggle)
        spike = QtWidgets.QPushButton("⚡ Anomaly 10 s")
        spike.setToolTip("Adds +15 °C / +250 ppm for 10 s so the edge raises an alert")
        spike.clicked.connect(self.spike)
        row.addWidget(self.start_btn)
        row.addWidget(spike)
        f.addRow(row)
        self.pub_label = QtWidgets.QLabel("0 messages published")
        f.addRow(self.pub_label)
        lay.addWidget(g)

        g = QtWidgets.QGroupBox("Edge filter on the Raspberry Pi")
        f = QtWidgets.QFormLayout(g)
        self.edge_mode = QtWidgets.QComboBox()
        for code, label in MEAN_TYPES:
            self.edge_mode.addItem(label, code)
        self.edge_period = QtWidgets.QDoubleSpinBox(minimum=0.1, maximum=30, value=2.0, decimals=1, suffix=" s")
        self.edge_window = QtWidgets.QSpinBox(minimum=1, maximum=500, value=30, suffix=" samples")
        self.edge_mode.currentIndexChanged.connect(
            lambda: self.edge_window.setEnabled(self.edge_mode.currentData() == "moving"))
        f.addRow("Mean type", self.edge_mode)
        f.addRow("Period", self.edge_period)
        f.addRow("Window", self.edge_window)
        self.plot_span = QtWidgets.QSpinBox(minimum=10, maximum=600, value=60, suffix=" s")
        f.addRow("Plot span", self.plot_span)
        apply_btn = QtWidgets.QPushButton("Apply to edge (edge/control)")
        apply_btn.clicked.connect(self.apply_edge)
        f.addRow(apply_btn)
        self.edge_label = QtWidgets.QLabel("–")
        self.edge_label.setWordWrap(True)
        f.addRow(self.edge_label)
        lay.addWidget(g)

        tp = QtWidgets.QPushButton("📈 Open throughput window")
        tp.clicked.connect(lambda: (self.throughput.show(), self.throughput.raise_()))
        lay.addWidget(tp)
        dash = QtWidgets.QPushButton("🌐 Open cloud dashboard (EC2)")
        dash.clicked.connect(lambda: QtGui.QDesktopServices.openUrl(QtCore.QUrl(f"http://{self.cloud_host.text()}/")))
        lay.addWidget(dash)
        nr = QtWidgets.QPushButton("🟥 Open Node-RED dashboard (Pi)")
        nr.clicked.connect(lambda: QtGui.QDesktopServices.openUrl(QtCore.QUrl(f"http://{self.edge_host.text()}:1880/dashboard")))
        lay.addWidget(nr)
        lay.addStretch(1)
        return box

    def build_live_tab(self):
        """Original sensor data vs reduced data received by the cloud, one plot per sensor (TP2 figures)."""
        w = pg.GraphicsLayoutWidget()
        w.setBackground("w")
        self.plots, self.curves = {}, {}
        for i, (n, (_, _, _, unit)) in enumerate(SENSORS.items()):
            p = w.addPlot(row=i // 2, col=i % 2)
            for side in ("left", "bottom", "top", "right"):
                p.showAxis(side)
                ax = p.getAxis(side)
                ax.setPen(pg.mkPen("k"))
                ax.setTextPen(pg.mkPen("k"))
                if side in ("top", "right"):
                    ax.setStyle(showValues=False)
            p.setLabel("left", f"{n} ({unit})", color="k")
            p.setLabel("bottom", "time (s)", color="k")
            p.showGrid(x=True, y=True, alpha=0.15)
            p.addLegend(offset=(8, 8), labelTextColor="k", labelTextSize="9pt",
                        brush=pg.mkBrush(255, 255, 255, 230), pen=pg.mkPen("#c8c8c8"))
            self.curves[n] = {
                "raw": p.plot([], [], name="Original (sensor -> edge)", pen=pg.mkPen(PLOT_RAW, width=1)),
                "cloud": p.plot([], [], name="Reduced (edge -> cloud)", pen=pg.mkPen(PLOT_REDUCED, width=2.5),
                                symbol="o", symbolSize=5, symbolBrush=PLOT_REDUCED, symbolPen=None),
            }
            self.plots[n] = p
        self.update_titles(None)
        self.tabs.addTab(w, "Live sensors")

    def update_titles(self, cfg):
        if not cfg:
            desc = "waiting for the edge configuration"
        elif cfg["mode"] == "sampling":
            desc = f"sampling reduction (mean every {float(cfg['period']):g} s)"
        elif cfg["mode"] == "moving":
            desc = f"centred moving average (window {cfg['window']} samples, sent every {float(cfg['period']):g} s)"
        else:
            desc = "pass-through (no reduction)"
        for n, p in self.plots.items():
            p.setTitle(f"{n} - {desc} vs sensor data", color="k", size="10pt")

    def build_3d_tab(self):
        container = QtWidgets.QWidget()
        lay = QtWidgets.QVBoxLayout(container)
        lay.addWidget(QtWidgets.QLabel("3D trajectory of the raw sensor state: x = temperature, y = humidity, "
                                       "z = CO₂ (normalised). Colour = age (bright = recent). Drag to rotate."))
        self.gl = gl.GLViewWidget()
        self.gl.setBackgroundColor("#161615")
        self.gl.setCameraPosition(distance=40, elevation=22, azimuth=40)
        for axis_rot in ((0, 0, 0, 0), (90, 1, 0, 0), (90, 0, 1, 0)):
            grid = gl.GLGridItem()
            grid.setSize(20, 20)
            grid.setSpacing(2, 2)
            grid.setColor((80, 80, 75, 120))
            if axis_rot[0]:
                grid.rotate(*axis_rot)
            grid.translate(*( (0, 0, -10) if not axis_rot[0] else ((0, -10, 0) if axis_rot[1] else (-10, 0, 0)) ))
            self.gl.addItem(grid)
        self.gl.addItem(gl.GLAxisItem(size=QtGui.QVector3D(12, 12, 12)))
        self.traj_line = gl.GLLinePlotItem(width=2, antialias=True)
        self.traj_pts = gl.GLScatterPlotItem(size=6)
        self.gl.addItem(self.traj_line)
        self.gl.addItem(self.traj_pts)
        lay.addWidget(self.gl, 1)
        self.tabs.addTab(container, "3D view")
        self.azimuth = 40

    # ---------- MQTT ----------
    def connect_brokers(self):
        for c in (self.edge_client, self.cloud_client):
            if c:
                c.loop_stop()
                c.disconnect()
        self.edge_client = make_client(f"pc-simulator-{os.getpid()}")
        self.edge_client.on_connect = lambda c, u, f, rc, p=None: (
            c.subscribe([("edge/+/filtered", 0), ("edge/stats", 0), ("edge/config", 0), ("edge/alerts", 0)]),
            self.events.put(("status", "edge", str(rc))))
        self.edge_client.on_message = lambda c, u, m: self.events.put(("edge_msg", m.topic, m.payload, time.time()))
        self.edge_client.on_disconnect = lambda *a: self.events.put(("status", "edge", "disconnected"))
        self.cloud_client = make_client(f"pc-cloud-monitor-{os.getpid()}")
        self.cloud_client.username_pw_set(self.env["VIEWER_USER"], self.env["VIEWER_PASS"])
        self.cloud_client.on_connect = lambda c, u, f, rc, p=None: (
            c.subscribe("cloud/#"), self.events.put(("status", "cloud", str(rc))))
        self.cloud_client.on_message = lambda c, u, m: self.events.put(("cloud_msg", m.topic, m.payload, time.time()))
        self.cloud_client.on_disconnect = lambda *a: self.events.put(("status", "cloud", "disconnected"))
        self.conn_status = {"edge": "connecting…", "cloud": "connecting…"}
        try:
            self.edge_client.connect_async(self.edge_host.text(), 1883)
            self.edge_client.loop_start()
            self.cloud_client.connect_async(self.cloud_host.text(), int(self.env["CLOUD_PORT"]))
            self.cloud_client.loop_start()
        except OSError as e:
            QtWidgets.QMessageBox.warning(self, "MQTT", str(e))

    def toggle(self):
        if self.publisher:
            self.publisher.stop()
            self.publisher = None
            self.start_btn.setText("▶ Start")
            return
        sensors = [n for n, c in self.sensor_checks.items() if c.isChecked()]
        if not sensors:
            return
        for s in self.series.values():  # each run starts a fresh time axis at 0 s
            for d in s.values():
                d.clear()
        self.t0 = time.time()
        self.publisher = Publisher(self.edge_client, sensors, self.rate.value(), self.mode.currentIndex() == 0, self.events)
        self.publisher.start()
        self.start_btn.setText("■ Stop")
        self.throughput.show()

    def spike(self):
        if self.publisher:
            self.publisher.spike_until = time.time() + 10

    def apply_edge(self):
        cfg = {"mode": self.edge_mode.currentData(), "period": self.edge_period.value(), "window": self.edge_window.value()}
        self.edge_client.publish("edge/control", json.dumps(cfg))

    # ---------- event processing (GUI thread) ----------
    def drain(self):
        for _ in range(2000):
            try:
                ev = self.events.get_nowait()
            except queue.Empty:
                break
            kind = ev[0]
            if kind == "pub":
                _, name, ts, value, size = ev
                self.series[name]["raw"].append((ts, value))
                self.second["pub"][0] += 1
                self.second["pub"][1] += size
                self.flow.add(0, f"sensors/{name}/raw {value:.2f}")
            elif kind == "status":
                self.conn_status[ev[1]] = "connected" if ev[2] in ("0", "Success") else ev[2]
                self.conn_label.setText(f"Edge: {self.conn_status['edge']}\nCloud: {self.conn_status['cloud']}")
            elif kind in ("edge_msg", "cloud_msg"):
                self.on_mqtt(kind, *ev[1:])

    def on_mqtt(self, kind, topic, payload, ts):
        try:
            data = json.loads(payload)
        except ValueError:
            return
        parts = topic.split("/")
        if kind == "edge_msg":
            if topic == "edge/stats":
                self.edge_stats = data
            elif topic == "edge/config":
                self.edge_label.setText(f"current: {data['mode']}, period {data['period']} s, window {data['window']}")
                if data != self.edge_config:  # new mean type: restart the reduced curve
                    for s in self.series.values():
                        s["cloud"].clear()
                self.edge_config = data
                self.update_titles(data)
                idx = self.edge_mode.findData(data["mode"])
                if idx >= 0:
                    self.edge_mode.setCurrentIndex(idx)
                self.edge_period.setValue(float(data["period"]))
                self.edge_window.setValue(int(data["window"]))
            elif topic == "edge/alerts":
                self.log.appendPlainText(f"[ALERT from edge] {payload.decode()}")
            elif len(parts) == 3 and parts[2] == "filtered" and parts[1] in self.series:
                self.series[parts[1]]["edge"].append((data["ts"], data["value"]))
            return
        # cloud side
        self.second["cloud"][0] += 1
        self.second["cloud"][1] += mqtt_size(topic, payload)
        if len(parts) == 2 and parts[1] in self.series:
            # a centred moving average is plotted at the centre of its window (ts_center comes from the
            # raw timestamps, i.e. the PC clock); a period mean is plotted when it reaches the PC, so a
            # drifting Raspberry Pi clock cannot push the point outside the plot
            self.series[parts[1]]["cloud"].append((data.get("ts_center", ts), data["value"]))
            self.flow.add(1, f"{topic} {payload.decode()}")
            self.log.appendPlainText(f"{time.strftime('%H:%M:%S')}  EC2 ← {topic}  {payload.decode()}")
        elif topic == "cloud/alerts":
            self.flow.add(1, f"{topic} {payload.decode()}")

    def every_second(self):
        ts = time.time()
        edge_b = self.edge_stats["in_bytes_s"] if self.edge_stats and ts - self.edge_stats["ts"] < 3 else 0
        edge_m = self.edge_stats["in_msgs_s"] if self.edge_stats and ts - self.edge_stats["ts"] < 3 else 0
        self.throughput.add(ts, (self.second["pub"][1], self.second["pub"][0]), (edge_b, edge_m),
                            (self.second["cloud"][1], self.second["cloud"][0]))
        self.flow_rate_win[0].append(self.second["pub"][0])
        self.flow_rate_win[1].append(self.second["cloud"][0])
        self.flow.rates = [sum(d) / len(d) for d in self.flow_rate_win]
        total = sum(self.publisher.seq.values()) if self.publisher else None
        if total is not None:
            self.pub_label.setText(f"{total} messages published")
        self.statusBar().showMessage(
            f"PC → Pi: {self.second['pub'][0]} msg/s ({self.second['pub'][1]} B/s)   |   "
            f"EC2 received: {self.second['cloud'][0]} msg/s ({self.second['cloud'][1]} B/s)   |   "
            f"edge reduction: {self.edge_stats['reduction_pct'] if self.edge_stats else '–'} %")
        self.second = {"pub": [0, 0], "edge": [0, 0], "cloud": [0, 0]}

    def redraw(self):
        now = time.time()
        span = self.plot_span.value()
        for n, s in self.series.items():
            for k in ("raw", "cloud"):
                pts = [(t - self.t0, v) for t, v in s[k] if t >= now - span]
                if pts:
                    xs, ys = zip(*pts)
                    self.curves[n][k].setData(xs, ys)
                else:
                    self.curves[n][k].setData([], [])
            self.plots[n].setXRange(max(0.0, now - self.t0 - span), max(span, now - self.t0), padding=0.02)
        if self.tabs.currentIndex() == 1:
            self.redraw_3d()

    def redraw_3d(self):
        keys = ["temperature", "humidity", "co2"]
        raws = [list(self.series[k]["raw"])[-400:] for k in keys]
        n = min(len(r) for r in raws)
        if n < 2:
            return
        cols = []
        for k, r in zip(keys, raws):
            v = np.array([p[1] for p in r[-n:]])
            mean, sd = SENSORS[k][1], SENSORS[k][2]
            cols.append((v - mean) / sd * 4)
        pos = np.stack(cols, axis=1).astype(np.float32)
        age = np.linspace(0.15, 1.0, n)
        color = np.stack([0.22 * age + 0.1, 0.53 * age + 0.1, 0.9 * age + 0.1, 0.3 + 0.7 * age], axis=1)
        self.traj_line.setData(pos=pos, color=color)
        self.traj_pts.setData(pos=pos[-1:], color=(1.0, 0.55, 0.2, 1.0), size=14)
        self.azimuth = (self.azimuth + 0.4) % 360
        self.gl.setCameraPosition(azimuth=self.azimuth)

    def closeEvent(self, e):
        if self.publisher:
            self.publisher.stop()
        self.throughput.close()
        super().closeEvent(e)


def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setStyle("Fusion")
    pal = QtGui.QPalette()
    for role, c in ((QtGui.QPalette.ColorRole.Window, "#1a1a19"), (QtGui.QPalette.ColorRole.WindowText, "#f0efec"),
                    (QtGui.QPalette.ColorRole.Base, "#121211"), (QtGui.QPalette.ColorRole.Text, "#f0efec"),
                    (QtGui.QPalette.ColorRole.Button, "#26261f"), (QtGui.QPalette.ColorRole.ButtonText, "#f0efec"),
                    (QtGui.QPalette.ColorRole.Highlight, "#3987e5"), (QtGui.QPalette.ColorRole.AlternateBase, "#22221f")):
        pal.setColor(role, QtGui.QColor(c))
    app.setPalette(pal)
    win = MainWindow()
    win.show()
    if "--start" in sys.argv:
        QtCore.QTimer.singleShot(1500, win.toggle)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
