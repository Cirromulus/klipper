This is an experimental branch
==============================

.. to enable fast PWM-Updates through the klipper stepcompress/_sync_channel_/move-queue system.
Currently, only HW-PWM is using the "fast track", because it breaks the heater pins then.*


Example configuration:
    
    [output_pin TOOL]
    pin: !ar9
    pwm: True
    hardware_pwm: True
    cycle_time: 0.001   # PWM-Frequency, limits the effective switching speed
    shutdown_value: 0
    host_acknowledge_timeout: 0     # Low Values currently may disrupt job

    [gcode_macro M3]
    default_parameter_S: 0
    gcode:
             SET_PIN PIN=TOOL VALUE={S|float / 255}

    [gcode_macro M5]
    gcode:
             SET_PIN PIN=TOOL VALUE=0
             
    [menu __main __control __toolonoff]
    type: input
    enable: {'output_pin TOOL' in printer}
    name: Fan: {'ON ' if menu.input else 'OFF'}
    input: {printer['output_pin TOOL'].value}
    input_min: 0
    input_max: 1
    input_step: 1
    gcode:
        M3 S{255 if menu.input else 0}

    [menu __main __control __toolspeed]
    type: input
    enable: {'output_pin TOOL' in printer}
    name: Tool speed: {'%3d' % (menu.input*100)}%
    input: {printer['output_pin TOOL'].value}
    input_min: 0
    input_max: 1
    input_step: 0.01
    gcode:
        M3 S{'%d' % (menu.input*255)}


*: Current Issue. Pin updates are not sent during moves, only in-between.
