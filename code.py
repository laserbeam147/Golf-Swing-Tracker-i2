import time
import board
import busio
import math

# Bluetooth libraries
from adafruit_ble import BLERadio
from adafruit_ble.advertising.standard import ProvideServicesAdvertisement
from adafruit_ble.services.nordic import UARTService

# BNO085 libraries
from adafruit_bno08x.i2c import BNO08X_I2C
from adafruit_bno08x import BNO_REPORT_LINEAR_ACCELERATION, BNO_REPORT_GAME_ROTATION_VECTOR

# --- 1. SETUP BLUETOOTH ---
ble = BLERadio()
uart = UARTService()
advertisement = ProvideServicesAdvertisement(uart)

# --- 2. SETUP SENSOR ---
i2c = busio.I2C(board.SCL, board.SDA)
bno = BNO08X_I2C(i2c)
bno.enable_feature(BNO_REPORT_LINEAR_ACCELERATION)
bno.enable_feature(BNO_REPORT_GAME_ROTATION_VECTOR)

print("Starting up... Waiting for connection.")

# Main loop to keep the board running forever
while True:
    # Start broadcasting Bluetooth
    ble.start_advertising(advertisement)
    print("Advertising...")
    
    # Wait here until something (iPad or LightBlue) connects
    while not ble.connected:
        time.sleep(0.1)
        
    ble.stop_advertising()
    print("Connected! Waiting for a swing...")

    # Reset variables on new connection
    is_swinging = False
    max_mph = 0.0
    contact_angle = 0.0
    current_velocity_ms = 0.0
    last_time = time.monotonic()

    # The loop that runs while the app is connected
    while ble.connected:
        try:
            current_time = time.monotonic()
            dt = current_time - last_time
            last_time = current_time

            # --- 3. READ SENSOR DATA ---
            accel_x, accel_y, accel_z = bno.linear_acceleration
            
            # (Insert your specific club face angle math here)
            # Example: current_angle = your_angle_calculation()
            current_angle = 85.0 

            # --- 4. CALCULATE SPEED ---
            # Get total acceleration magnitude
            total_accel = math.sqrt(accel_x**2 + accel_y**2 + accel_z**2)
            
            # If acceleration spikes, a swing has started!
            if total_accel > 5.0:  
                if not is_swinging:
                    print("Swing started...")
                is_swinging = True
                
            if is_swinging:
                # Integrate acceleration to get velocity
                current_velocity_ms += (total_accel * dt)
                current_mph = current_velocity_ms * 2.23694 # Convert to MPH
                
                # --- 5. THE "IMPACT" LOGIC ---
                # Every time the club gets faster, save the speed AND the angle
                if current_mph > max_mph:
                    max_mph = current_mph
                    contact_angle = current_angle # This grabs the angle at the absolute fastest moment!
                    
                # --- 6. END OF SWING & TRANSMIT ---
                # If acceleration drops back down, the swing is over
                if total_accel < 2.0 and max_mph > 2.0: 
                    
                    # Package it as ONE string so LightBlue doesn't split it up!
                    # We also add \r\n to the end so it prints correctly.
                    message = f"RESULT | Max MPH: {max_mph:.1f} | Angle at Hit: {contact_angle:.1f}\r\n"
                    
                    # Send it over Bluetooth
                    uart.write(message.encode("utf-8"))
                    
                    # Print it to the Serial Monitor for your own reference
                    print(message.strip())
                    print("-----------------------------------------")
                    
                    # Reset variables for the next swing
                    is_swinging = False
                    max_mph = 0.0
                    contact_angle = 0.0
                    current_velocity_ms = 0.0
                    
                    # Tiny pause so it doesn't immediately trigger a second swing
                    time.sleep(1) 
                    
        except Exception as e:
            print("Error reading sensor:", e)
            time.sleep(0.1)

    # If the app disconnects, the loop breaks and it goes back to advertising
    print("Disconnected. Going back to advertising...")