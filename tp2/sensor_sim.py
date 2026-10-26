"""Simulation of industrial sensor data (Python port of BasicSimulatorClass.cs).

Source: https://bitperfect.at/en/blog/simulation-von-sensordaten
Each new value moves a small random step away from the previous one; the
direction is biased back toward the mean the further the value drifts, which
gives a realistic, continuous, normally-distributed signal.
"""
import random

import paho.mqtt.client as mqtt


class Simulator:
    def __init__(self, seed, mean, standard_deviation):
        self._random = random.Random(seed)
        self._mean = mean
        self._standard_deviation = abs(standard_deviation)
        # step size factor used when calculating the next value
        self._step_size_factor = self._standard_deviation / 10
        # start value is not exactly the mean
        self._value = self._mean - self._random.random()

    def calculate_next_value(self):
        # how much the value will change
        value_change = self._random.random() * self._step_size_factor
        # whether the value is increased or decreased
        factor = (-1, 1)[self._decide_factor()]
        self._value += value_change * factor
        return self._value

    def _decide_factor(self):
        if self._value > self._mean:
            distance = self._value - self._mean
            continue_direction, change_direction = 1, 0
        else:
            distance = self._mean - self._value
            continue_direction, change_direction = 0, 1
        # 50/50 chance at the mean, less chance to keep drifting further away
        chance = (self._standard_deviation / 2) - (distance / 50)
        random_value = self._random.random() * self._standard_deviation
        return continue_direction if random_value < chance else change_direction


# Sensors used through the TPs: (seed, mean, standard deviation, unit)
SENSORS = {
    "temperature": (12345, 20.0, 5.0, "°C"),    # DHT
    "humidity":    (23456, 55.0, 10.0, "%"),    # DHT
    "pressure":    (34567, 1013.0, 8.0, "hPa"),
    "co2":         (45678, 450.0, 60.0, "ppm"), # MQ135 air quality
}


def generate_dataset(n=5000, seed=12345, mean=20.0, sd=5.0):
    sim = Simulator(seed, mean, sd)
    return [sim.calculate_next_value() for _ in range(n)]


def make_client(client_id, **kw):
    """paho-mqtt 1.x (Pi) and 2.x (PC) compatible client."""
    if hasattr(mqtt, "CallbackAPIVersion"):
        return mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=client_id, **kw)
    return mqtt.Client(client_id=client_id, **kw)
