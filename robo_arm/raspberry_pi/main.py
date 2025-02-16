import serial
import time
from arm_coordinates_mapping import decart_mm_to_degrees

ser = serial.Serial('/dev/ttyUSB0', 115200)  # Replace '/dev/ttyUSB0' with your serial port and 115200 with your baud rate

angle_val = 45
increment = +5

try:
    # ser.write(b'0;90;0\n')

    # deg_a, deg_b, deg_c = decart_mm_to_degrees(160, 210, -50)
    deg_a, deg_b, deg_c = decart_mm_to_degrees(120, 96, 0)

    # data_str = f"{int(deg_a)};{int(deg_b)};{int(deg_c)};\n"

    
    data_str = f"{100};{0};{0};\n"

    ser.write(bytes(data_str, "utf-8"))
    # print(data_str)


    # while True:
    #     angle_val += increment
    #     if angle_val > 0:
    #         increment = increment * -1
    #     if angle_val < 90:
    #         increment = increment * -1
        
    #     data_str = f"{0};{angle_val};0;\n"
    #     # ser.write(b"Data from Python\n")
    #     ser.write(bytes(data_str, "utf-8"))
    #     # print("Data sent to UART")
    #     time.sleep(1/5)
except KeyboardInterrupt:
    print("\nExiting...")
finally:
    ser.close()
    print("Serial port closed")

