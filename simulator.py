#!/usr/bin/env python3
"""Simple Modbus TCP simulator for testing modbus-cli.

Run this in one terminal:
    python simulator.py

Then test in another terminal:
    modbus read localhost 40001 --count 10
    modbus write localhost 40001 999
    modbus scan localhost --range 1-5
    modbus watch localhost 40001 --count 8
    modbus dump localhost 40001 40050
"""

import random
import threading
import time

from pymodbus.datastore import (
    ModbusSequentialDataBlock,
    ModbusDeviceContext,
    ModbusServerContext,
)
from pymodbus.server import StartTcpServer


def create_context():
    """Create a datastore pre-loaded with realistic-looking IoT sensor data."""
    # Holding registers (40001+): simulate sensor readings
    # Think: temperature, pressure, flow rate, voltage, battery, etc.
    holding_values = [
        237,    # 40001: temperature (23.7 C * 10)
        1024,   # 40002: pressure (mbar)
        58,     # 40003: flow rate (L/min)
        900,    # 40004: RPM
        2315,   # 40005: voltage (231.5V * 10)
        4850,   # 40006: battery mV
        95,     # 40007: signal strength %
        1,      # 40008: device status (1=online)
        3742,   # 40009: total runtime hours
        156,    # 40010: error count
        12045,  # 40011: flow totalizer
        8821,   # 40012: energy kWh
        2200,   # 40013: frequency (Hz * 100)
        485,    # 40014: current (mA)
        32767,  # 40015: max int16
        0,      # 40016: zero
    ]
    # Pad to 100 registers
    holding_values.extend([random.randint(0, 1000) for _ in range(84)])

    # Input registers (30001+): read-only sensor data
    input_values = [random.randint(100, 5000) for _ in range(100)]

    # Coils (00001+): digital outputs
    coil_values = [random.choice([True, False]) for _ in range(32)]

    # Discrete inputs (10001+): digital inputs
    discrete_values = [random.choice([True, False]) for _ in range(32)]

    store = ModbusDeviceContext(
        hr=ModbusSequentialDataBlock(0, holding_values),
        ir=ModbusSequentialDataBlock(0, input_values),
        co=ModbusSequentialDataBlock(0, coil_values),
        di=ModbusSequentialDataBlock(0, discrete_values),
    )

    # Create multiple slave IDs (1-3) so scan has something to find
    slaves = {1: store, 2: store, 3: store}
    return ModbusServerContext(devices=slaves, single=False)


def drift_values(context):
    """Background thread that slowly changes register values to simulate live data."""
    while True:
        time.sleep(0.5)
        try:
            store = context[1]  # slave 1
            # Read current holding registers
            values = store.getValues(3, 0, count=16)  # function code 3 = holding

            # Drift temperature (register 0 / address 40001)
            temp = values[0] + random.randint(-3, 3)
            temp = max(200, min(280, temp))
            store.setValues(3, 0, [temp])

            # Drift pressure (register 1 / address 40002)
            pressure = values[1] + random.randint(-10, 10)
            pressure = max(900, min(1100, pressure))
            store.setValues(3, 1, [pressure])

            # Drift flow rate (register 2 / address 40003)
            flow = values[2] + random.randint(-2, 2)
            flow = max(40, min(80, flow))
            store.setValues(3, 2, [flow])

            # Drift RPM (register 3 / address 40004)
            rpm = values[3] + random.randint(-20, 20)
            rpm = max(800, min(1000, rpm))
            store.setValues(3, 3, [rpm])

            # Drift voltage (register 4 / address 40005)
            voltage = values[4] + random.randint(-5, 5)
            voltage = max(2200, min(2400, voltage))
            store.setValues(3, 4, [voltage])

            # Drift battery (register 5 / address 40006)
            batt = values[5] - random.randint(0, 2)
            batt = max(3000, min(5000, batt))
            store.setValues(3, 5, [batt])

            # Increment totalizer (register 10 / address 40011)
            total = values[10] + random.randint(0, 3)
            store.setValues(3, 10, [total % 65535])

        except Exception:
            pass


def main():
    print()
    print("  \033[1;36mmodbus-cli simulator\033[0m")
    print("  \033[2m" + "-" * 40 + "\033[0m")
    print()
    print("  \033[1;32mListening on localhost:5020\033[0m")
    print("  Slave IDs: 1, 2, 3")
    print("  Holding registers: 100 (drifting values)")
    print("  Input registers:   100")
    print("  Coils:             32")
    print("  Discrete inputs:   32")
    print()
    print("  \033[1;33mTest commands (run in another terminal):\033[0m")
    print()
    print("    modbus read localhost 40001 -c 10 -p 5020")
    print("    modbus read localhost 40001 -c 10 -p 5020 -f hex")
    print("    modbus write localhost 40001 999 -p 5020")
    print("    modbus scan localhost --range 1-5 -p 5020")
    print("    modbus watch localhost 40001 -c 8 -p 5020")
    print("    modbus dump localhost 40001 40050 -p 5020")
    print("    modbus dump localhost 40001 40050 -p 5020 --csv test.csv")
    print()
    print("  \033[2mCtrl+C to stop\033[0m")
    print()

    context = create_context()

    # Start background value drifter
    drifter = threading.Thread(target=drift_values, args=(context,), daemon=True)
    drifter.start()

    # Start Modbus TCP server on port 5020 (non-privileged)
    StartTcpServer(context=context, address=("localhost", 5020))


if __name__ == "__main__":
    main()
