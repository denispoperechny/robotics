
default_arm_offsets = [180, 200, 96] # tip, middle, base height

import math

def calculate_angles(a, b, c):
    # Calculate the angle opposite to side a
    c1 = (b**2 + c**2 - a**2) / (2 * b * c)
    if c1 > 1:
        c1 = 1
    if c1 < -1:
        c1 = -1
    angle_A = math.degrees(math.acos(c1))
    # Calculate the angle opposite to side b
    c2 = (a**2 + c**2 - b**2) / (2 * a * c)
    if c2 > 1:
        c2 = 1
    if c2 < -1:
        c2 = -1
    angle_B = math.degrees(math.acos(c2))
    # Calculate the angle opposite to side c
    angle_C = 180 - (angle_A + angle_B)  # The sum of angles in a triangle is 180 degrees
    return angle_A, angle_B, angle_C


def calculate_angle_hypotenuse(adjacent, opposite):
    angle_radians = math.atan(opposite / adjacent)
    angle_degrees = math.degrees(angle_radians)
    hypotenuse = math.sqrt(math.pow(adjacent, 2) + math.pow(opposite, 2))
    return angle_degrees, hypotenuse

def decart_mm_to_degrees(x, y, z, arm_offsets=default_arm_offsets):
    deg_a = 0
    deg_b = 0
    deg_c = 0

    y = y - default_arm_offsets[2]
    deg_c, table_hypotenuse = calculate_angle_hypotenuse(x, z)
    vert_direction_angle, arm_ext_len = calculate_angle_hypotenuse(table_hypotenuse, y)
    deg_a, _, deg_b_part = calculate_angles(arm_ext_len, arm_offsets[1], arm_offsets[0])
    # print((deg_a, _, deg_b_part))
    deg_b = deg_b_part + vert_direction_angle

    # adjustments
    deg_a = 180 - deg_a
    deg_b = 90 - deg_b

    return deg_a, deg_b, deg_c

