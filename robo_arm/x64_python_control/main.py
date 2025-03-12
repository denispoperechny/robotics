import serial

from arm_coordinates_mapping import decart_mm_to_degrees

data = {
    "ref_values": (),
    "entries": [],
    "velocity": (0.0, 0.0, 0.0),
    "calculated_position": (200.0, 100.0, 0.0),
    "aggregated_position": ()
}



# Function to process each new entry
# def process_input(new_entry):
#     print(f"Processing: {new_entry}")

# Setup the serial connection
ser = serial.Serial('COM7', 115200, timeout=1)  # Adjust baud rate and timeout as needed

calibrate_ct_left = 25

try:
    while True:
        if ser.in_waiting > 0:
            new_entry = ser.readline().decode('utf-8').strip()
            # print(new_entry)

            parts = new_entry.split(';')
            if len(parts) >= 6:
                calibrate_ct_left -= 1

                data["entries"].append((float(parts[0]), float(parts[1]), float(parts[2])))
                if calibrate_ct_left == 0:
                    data["ref_values"] = (
                        sum([x[0] for x in data["entries"]]) / len(data["entries"]),
                        sum([x[1] for x in data["entries"]]) / len(data["entries"]),
                        sum([x[2] for x in data["entries"]]) / len(data["entries"]),
                    )
                    data["aggregated_position"] = (0,0,0)
                if calibrate_ct_left < 0:
                    data["velocity"] = (
                        data["velocity"][0] + data["entries"][-1][0] - data["ref_values"][0],
                        data["velocity"][1] + data["entries"][-1][1] - data["ref_values"][1],
                        data["velocity"][2] + data["entries"][-1][2] - data["ref_values"][2]
                    )

                    # data["aggregated_position"] = (
                    #     data["aggregated_position"][0] + data["entries"][-1][0] - data["ref_values"][0],
                    #     data["aggregated_position"][1] + data["entries"][-1][1] - data["ref_values"][1],
                    #     data["aggregated_position"][2] + data["entries"][-1][2] - data["ref_values"][2]
                    # )

                    data["calculated_position"] = (
                        data["calculated_position"][0] + data["velocity"][0],
                        data["calculated_position"][1] + data["velocity"][1],
                        data["calculated_position"][2] + data["velocity"][2]
                    )

                    # print(data["calculated_position"])
                    angles = decart_mm_to_degrees(
                        data["calculated_position"][1] /1,
                        data["calculated_position"][2] /1,
                        data["calculated_position"][0] /1,
                    )

                    # print(angles)
                    print(data["velocity"])
                    ser.write(bytes(f"{angles[0]};{angles[1]};{angles[2]};\n", "utf-8"))




            # process_input(new_entry)
except KeyboardInterrupt:
    print("Stopped by user")
finally:
    ser.close()
