import serial
import numpy as np

from arm_coordinates_mapping import decart_mm_to_degrees

data = {
    "ref_values": (),
    "entries": [],
    "velocity": (0.0, 0.0, 0.0),
    "calculated_position": (200.0, 100.0, 0.0),
    "aggregated_position": (),
    "orientation": np.eye(3)
}

def compute_rotation_matrix(gyro, dt):
    # Assuming gyro = [gx, gy, gz] in radians/second
    angle = np.linalg.norm(gyro) * dt
    if angle == 0:
        return np.eye(3)
    axis = gyro / np.linalg.norm(gyro)
    cos_angle = np.cos(angle)
    sin_angle = np.sin(angle)
    one_minus_cos = 1 - cos_angle
    
    # Rodrigues' rotation formula
    x, y, z = axis
    rotation_matrix = np.array([
        [cos_angle + x**2 * one_minus_cos, x*y*one_minus_cos - z*sin_angle, x*z*one_minus_cos + y*sin_angle],
        [y*x*one_minus_cos + z*sin_angle, cos_angle + y**2 * one_minus_cos, y*z*one_minus_cos - x*sin_angle],
        [z*x*one_minus_cos - y*sin_angle, z*y*one_minus_cos + x*sin_angle, cos_angle + z**2 * one_minus_cos]
    ])
    return rotation_matrix

# Continuous loop to update orientation
def update_orientation(gyro_readings, dt, current_orientation):
    rotation_matrix = compute_rotation_matrix(gyro_readings, dt)
    return np.dot(current_orientation, rotation_matrix)


def rotation_matrix_to_euler_angles(rotation_matrix):
    # Extract the individual elements of the matrix
    r11, r12, r13 = rotation_matrix[0]
    r21, r22, r23 = rotation_matrix[1]
    r31, r32, r33 = rotation_matrix[2]
    
    # Calculate pitch (θ)
    pitch = -np.arcsin(r31)  # Limited to the range [-π/2, π/2]
    
    # Handle gimbal lock cases (cos(pitch) close to zero)
    if np.isclose(np.cos(pitch), 0):
        roll = np.arctan2(-r23, r22)  # Use ZYX convention (alternative calculation)
        yaw = 0  # Yaw is indeterminate in this case
    else:
        # Calculate roll (φ)
        roll = np.arctan2(r32, r33)
        # Calculate yaw (ψ)
        yaw = np.arctan2(r21, r11)

    return np.degrees(yaw), np.degrees(pitch), np.degrees(roll) 


# Function to process each new entry
# def process_input(new_entry):
#     print(f"Processing: {new_entry}")

# Setup the serial connection
ser = serial.Serial('/dev/ttyUSB0', 115200, timeout=1)  # Adjust baud rate and timeout as needed

calibrate_ct_left = 25

gyro_bias_x = -0.01
gyro_bias_y = -0.02
gyro_bias_z = -0.00

try:
    while True:
        if ser.in_waiting > 0:
            new_entry = ser.readline().decode('utf-8').strip()
            # print(new_entry)

            parts = new_entry.split(';')
            if len(parts) >= 6:

                gyro_reading = np.array([float(parts[3])+gyro_bias_x, float(parts[4])+gyro_bias_y, float(parts[5])+gyro_bias_z])  # Example gyroscope reading in radians/second
                dt = 0.1  # Time step in seconds
                data['orientation'] = update_orientation(gyro_reading, dt, data['orientation'])
                print(rotation_matrix_to_euler_angles(data['orientation']))

                data["entries"].append((float(parts[0]), float(parts[1]), float(parts[2])))

                calibrate_ct_left -= 1
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
                    # print(data["velocity"])
                    ser.write(bytes(f"{angles[0]};{angles[1]};{angles[2]};\n", "utf-8"))




            # process_input(new_entry)
except KeyboardInterrupt:
    print("Stopped by user")
finally:
    ser.close()
