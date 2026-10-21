## Purpose

Verify the Pico W, its MicroPython firmware, and the host toolchain by blinking the onboard LED without any external components.

## ADDED Requirements

### Requirement: Blink the onboard LED
The experiment SHALL toggle the Pico W onboard LED indefinitely with a visible on/off cycle.

#### Scenario: LED blinks after start
- **WHEN** `experiments/pico-1-w-led-blink/main.py` runs on the Pico W
- **THEN** the onboard LED alternates between on and off approximately every 0.5 seconds

#### Scenario: LED identifier matches the hardware
- **WHEN** the program initialises the LED
- **THEN** it uses the board's `"LED"` identifier rather than GPIO 25, because the Pico W LED is connected to `WL_GPIO0` on the wireless chip

### Requirement: No external wiring
The experiment SHALL work with only the Pico W connected over USB.

#### Scenario: Run with bare board
- **WHEN** the board is powered over USB and no components are attached
- **THEN** the LED blink is observable

### Requirement: Clean interruption
The experiment SHALL turn the LED off and exit cleanly when interrupted.

#### Scenario: Interrupt stops the blink
- **WHEN** the running program receives a keyboard interrupt
- **THEN** the LED is left off and the program exits without an error traceback
