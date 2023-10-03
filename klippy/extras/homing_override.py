# Run user defined actions in place of a normal G28 homing command
#
# Copyright (C) 2018  Kevin O'Connor <kevin@koconnor.net>
#
# This file may be distributed under the terms of the GNU GPLv3 license.

class HomingOverride:
    def __init__(self, config):
        self.printer = config.get_printer()
        self.start_pos = [config.getfloat('set_position_' + a, None)
                          for a in 'xyzac']
        self.axes = config.get('axes', 'XYZAC').upper()
        # rotate axis A on 45 degrees
        self.rotate_a = config.getboolean('rotate_a', False)
        gcode_macro = self.printer.load_object(config, 'gcode_macro')
        self.template = gcode_macro.load_template(config, 'gcode')
        self.in_script = False
        self.printer.load_object(config, 'homing')
        self.gcode = self.printer.lookup_object('gcode')
        self.prev_G28 = self.gcode.register_command("G28", None)
        self.gcode.register_command("G28", self.cmd_G28)
        self.toolhead = None
        self.kin = None
        self.gcode_move = self.printer.load_object(config, 'gcode_move')
        self.printer.register_event_handler("klippy:ready",
                                            self._handle_ready)

    def _handle_ready(self):
        self.toolhead = self.printer.lookup_object('toolhead')
        self.kin = self.toolhead.get_kinematics()
        self.axes_max = self.kin.axes_max

    def check_axes_for_homing(self, gcmd):
        # Function to move the A-axis 45 degrees before parking the Z-axis
        curtime = self.printer.get_reactor().monotonic()
        if self.kin is not None and self.toolhead is not None:
            kin_status = self.kin.get_status(curtime)
            if 'za' in kin_status['homed_axes'] and (
                'Z' in gcmd._params or 'A' in gcmd._params):
                # so the 5d module is enabled and axes Z, A in home state
                retract_z = self.kin.rails[2].homing_retract_dist
                retract_a = self.kin.rails[3].homing_retract_dist
                axis_z = self.axes_max[2] - retract_z
                axis_a = self.axes_max[3] - retract_a
                if 'Z' in gcmd._params:
                    axis_a = (self.axes_max[3] / 2)
                elif 'A' in gcmd._params:
                    axis_z = self.axes_max[2] / 2
                self.toolhead.manual_move(
                        [None, None, axis_z, axis_a, None, None], 25.0)

    def cmd_G28(self, gcmd):
        if self.in_script:
            if self.rotate_a:
                self.check_axes_for_homing(gcmd)
            # Was called recursively - invoke the real G28 command
            self.prev_G28(gcmd)
            return
        # if no axis is given as parameter we assume the override
        no_axis = True
        for axis in 'XYZAC':
            if gcmd.get(axis, None) is not None:
                no_axis = False
                break
        if no_axis:
            override = True
        else:
            # check if we home an axis which needs the override
            override = False
            for axis in self.axes:
                if gcmd.get(axis, None) is not None:
                    override = True
        if not override:
            if self.rotate_a:
                self.check_axes_for_homing(gcmd)
            self.prev_G28(gcmd)
            return

        # Calculate forced position (if configured)
        toolhead = self.printer.lookup_object('toolhead')
        pos = toolhead.get_position()
        homing_axes = []
        for axis, loc in enumerate(self.start_pos):
            if loc is not None:
                pos[axis] = loc
                homing_axes.append(axis)
        toolhead.set_position(pos, homing_axes=homing_axes)
        # Perform homing
        context = self.template.create_template_context()
        context['params'] = gcmd.get_command_parameters()
        try:
            self.in_script = True
            self.template.run_gcode_from_command(context)
        finally:
            self.in_script = False


def load_config(config):
    return HomingOverride(config)
