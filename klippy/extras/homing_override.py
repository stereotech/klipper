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

    def check_axis_a(self, gcmd, status_kin):
        # Function to move the A-axis 45 degrees before parking the Z-axis
        if self.kin is not None:
            if 'za' in status_kin['homed_axes']:
                # the axes Z, A in home state
                retract_z = self.kin.rails[2].homing_retract_dist
                retract_a = self.kin.rails[3].homing_retract_dist
                axis_z = status_kin['axis_maximum'][2] - retract_z
                axis_a = status_kin['axis_maximum'][3] - retract_a
                if 'Z' in gcmd._params:
                    axis_a = status_kin['axis_maximum'][3] / 2.
                elif 'A' in gcmd._params:
                    axis_z = status_kin['axis_maximum'][2] / 2.
                return [None, None, axis_z, axis_a, None, None]

    def check_position_z(self, status_kin):
        # The function checks the position axis Z before move by axis X or Y
        if 'z' in status_kin['homed_axes']:
            # the axes Z in home state
            pos_z = status_kin['position'][2]
            danger_zone = status_kin['axis_maximum'][2] / 6.
            if pos_z < danger_zone:
                axis_z = status_kin['axis_maximum'][2] / 2.
                return [None, None, axis_z, None, None, None]

    def check_module(self, curtime):
        # The function checks module 5d is installed
        self.button = self.printer.lookup_objects('gcode_button')
        button = [i[1] for i in self.button if i[0] == 'gcode_button five_axis_module']
        state = True if button[0].get_status(curtime)['state'] == 'PRESSED' else False
        return state

    def check_axes_before_parking(self, gcmd):
        # The function do checks before parking
        curtime = self.printer.get_reactor().monotonic()
        if self.check_module(curtime) and self.toolhead is not None:
            # if the module 5d is installed
            status_kin = self.toolhead.get_status(curtime)
            move_pos = []
            if self.rotate_a and ('Z' in gcmd._params or 'A' in gcmd._params):
                move_pos = self.check_axis_a(gcmd, status_kin)
            if 'X' in gcmd._params or 'Y' in gcmd._params:
                move_pos = self.check_position_z(status_kin)
            # do move
            if move_pos:
                self.toolhead.manual_move(move_pos, 25.0)

    def cmd_G28(self, gcmd):
        if self.in_script:
            self.check_axes_before_parking(gcmd)
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
            self.check_axes_before_parking(gcmd)
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
