import struct

def decode_double(n):
    b = struct.pack('Q', n)
    return struct.unpack('d', b)[0]

cal1 = decode_double(4662947039282284463)
cal2 = decode_double(4669525647103385491)
cal3 = decode_double(4660518447848644499)

print(f"Calibration 1: {cal1}")
print(f"Calibration 2: {cal2}")
print(f"Calibration 3: {cal3}")



# Test different metadata values
test_values = {
    'Focus': 4602317050157652502,
    'NA': 4596373779694328218,
    'WD': 4626322717216342016
}

for name, value in test_values.items():
    decoded = decode_double(value)
    print(f"{name}: {decoded}")