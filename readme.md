# Flight Computer

This repository contains all the code running our main flight computer on the rocket. It can be either run on an android smartphone or on any full "desktop" computer (e.g. a raspberry pi)

## File structure

- `kivy_wrapper` and `standalone` are the two executables available. Standalone has not much additional stuff, whilst kivy has some platform specific addtional code (e.g. for android sensors, etc.)
- `core` has all of the rest of the code and is structured as such:
  - At the top level there is the `api_client` to do the server handshake (this has to happen before the flight starts). This api client has also some  api methods for during the flight, like for commands, etc. There is also the flight executor which has the main loop and related things
  - `models` are api models used by the `api_client`
  - `logic` is a bit of a mess currently. It contains the `rocket_definition` and the base command definition some abstract base part defintions like `measurmetn_sink` and a bunch of helpers. This should be re-organized at some point
  - `helper` contains a bunch of other helper methods used in the parts and elsewhere
  - `content` contains all the actual parts and related code
    - `common_sensor_interfaces` are interfaces that many parts might be implementing. This is quite new and not very far developed yet
    - `flight_director` contains everything related to the flight director. The flight director is handling the flight and makes high level calls on changing into other flight phases (e.g. from countdown to launch, etc.)
    - `general_commands` some commands common to many parts
    - `measurement_sinks` specialized parts that store or send away measurements
    - `microcontroller` any code related to communicating with an arduino  
    - `motor_commands` commands related to motors (currently just open/close)
    - `sensors` contains all sensor parts that are not implemented over the serial connection
    - `testing` has parts useful for e.g. lab-bench testing of the code or electronics