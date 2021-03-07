# Code to configure miscellaneous chips
#
# Copyright (C) 2017-2020  Kevin O'Connor <kevin@koconnor.net>
#
# This file may be distributed under the terms of the GNU GPLv3 license.

PIN_MIN_TIME = 0.100

class PrinterOutputPin:
    def __init__(self, config):
        self.printer = config.get_printer()
        ppins = self.printer.lookup_object('pins')
        self.is_pwm = config.getboolean('pwm', False)
        if self.is_pwm:
            self.mcu_pin = ppins.setup_pin('pwm', config.get('pin'))
            cycle_time = config.getfloat('cycle_time', 0.100, above=0.)
            hardware_pwm = config.getboolean('hardware_pwm', False)
            self.mcu_pin.setup_cycle_time(cycle_time, hardware_pwm)
            self.scale = config.getfloat('scale', 1., above=0.)
            self.last_cycle_time = self.default_cycle_time = cycle_time
        else:
            self.mcu_pin = ppins.setup_pin('digital_out', config.get('pin'))
            self.scale = 1.
            self.last_cycle_time = self.default_cycle_time = 0.
        self.last_print_time = 0.
        static_value = config.getfloat('static_value', None,
                                       minval=0., maxval=self.scale)
        if static_value is not None:
            self.mcu_pin.setup_max_duration(0.)
            self.last_value = static_value / self.scale
            self.mcu_pin.setup_start_value(
                self.last_value, self.last_value, True)
        else:
            self.reactor = self.printer.get_reactor()
            self.safety_timeout = config.getfloat('safety_timeout', 5,
                                        minval=0.)
            self.mcu_pin.setup_max_duration(self.safety_timeout)
            self.resend_timer = self.reactor.register_timer(
                self._resend_current_val)

            self.last_value = config.getfloat(
                'value', 0., minval=0., maxval=self.scale) / self.scale
            self.shutdown_value = config.getfloat(
                'shutdown_value', 0., minval=0., maxval=self.scale) / self.scale
            self.mcu_pin.setup_start_value(self.last_value, self.shutdown_value)
            pin_name = config.get_name().split()[1]
            gcode = self.printer.lookup_object('gcode')
            gcode.register_mux_command("SET_PIN", "PIN", pin_name,
                                       self.cmd_SET_PIN,
                                       desc=self.cmd_SET_PIN_help)
    def get_status(self, eventtime):
        return {'value': self.last_value}
    def _set_pin(self, print_time, value, cycle_time, is_resend=False):
        if value == self.last_value and cycle_time == self.last_cycle_time:
            if not is_resend:
                return
        print_time = max(print_time, self.last_print_time + PIN_MIN_TIME)
        print("Setting pin at " + str(print_time))
        if self.is_pwm:
            self.mcu_pin.set_pwm(print_time, value, cycle_time)
        else:
            self.mcu_pin.set_digital(print_time, value)
        self.last_value = value
        self.last_cycle_time = cycle_time
        self.last_print_time = print_time
        if self.safety_timeout != 0 and not is_resend:
            if value != self.shutdown_value:
                print("Starting resend timer at " + str(self.reactor.monotonic()))
                self.reactor.update_timer(
                    self.resend_timer, self.reactor.monotonic())
    cmd_SET_PIN_help = "Set the value of an output pin"
    def cmd_SET_PIN(self, gcmd):
        value = gcmd.get_float('VALUE', minval=0., maxval=self.scale)
        value /= self.scale
        cycle_time = gcmd.get_float('CYCLE_TIME', self.default_cycle_time,
                                    above=0.)
        if not self.is_pwm and value not in [0., 1.]:
            raise gcmd.error("Invalid pin value")
        toolhead = self.printer.lookup_object('toolhead')
        toolhead.register_lookahead_callback(
            lambda print_time: self._set_pin(print_time, value, cycle_time))

    def _resend_current_val(self, eventtime):
        # TODO: Split moves into smaller segments to enforce resend?
        print("Resend timer at " + str(eventtime))
        print("Scheduling set_pin at " + str(eventtime + 0.25 * self.safety_timeout))
        print("Re-running at " + str(eventtime + 0.5 * self.safety_timeout))
        toolhead = self.printer.lookup_object('toolhead')
        toolhead.register_lookahead_callback(lambda print_time:
            self._set_pin(eventtime + 0.25 * self.safety_timeout,
                           self.last_value, self.last_cycle_time, True)
            )
        if self.last_value != self.shutdown_value:
            return eventtime + 0.5 * self.safety_timeout    #every 0.5 t/o
        return self.reactor.NEVER

def load_config_prefix(config):
    return PrinterOutputPin(config)
