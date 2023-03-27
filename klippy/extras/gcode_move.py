# G-Code G1 movement commands (and associated coordinate manipulation)
#
# Copyright (C) 2016-2021  Kevin O'Connor <kevin@koconnor.net>
#
# This file may be distributed under the terms of the GNU GPLv3 license.
import logging
import math
import ast

DEG_TO_RAD = 0.01745329252
RAD_TO_DEG = 57.2958

class GCodeMove:
    def __init__(self, config):
        self.printer = printer = config.get_printer()


        printer.register_event_handler("klippy:ready", self._handle_ready)
        printer.register_event_handler(
            "klippy:shutdown", self._handle_shutdown)
        printer.register_event_handler("toolhead:set_position",
                                       self.reset_last_position)
        printer.register_event_handler("toolhead:manual_move",
                                       self.reset_last_position)
        printer.register_event_handler("gcode:command_error",
                                       self.reset_last_position)
        printer.register_event_handler("extruder:activate_extruder",
                                       self._handle_activate_extruder)
        printer.register_event_handler("homing:home_rails_end",
                                       self._handle_home_rails_end)
        self.is_printer_ready = False
        # Register g-code commands
        gcode = printer.lookup_object('gcode')
        handlers = [
            'G1', 'G20', 'G21',
            'M82', 'M83', 'G90', 'G91', 'G92', 'M220', 'M221',
            'SET_GCODE_OFFSET', 'SAVE_GCODE_STATE', 'RESTORE_GCODE_STATE',
        ]
        for cmd in handlers:
            func = getattr(self, 'cmd_' + cmd)
            desc = getattr(self, 'cmd_' + cmd + '_help', None)
            gcode.register_command(cmd, func, False, desc)
        gcode.register_command('G0', self.cmd_G1)
        gcode.register_command('M114', self.cmd_M114, True)
        gcode.register_command('GET_POSITION', self.cmd_GET_POSITION, True,
                               desc=self.cmd_GET_POSITION_help)
        gcode.register_command('LOAD_GCODE_STATE', self.cmd_LOAD_GCODE_STATE, True,
                               desc=self.cmd_LOAD_GCODE_STATE_help)
        gcode.register_command('RADIAL_SPEED_COMPENSATION', self.cmd_RADIAL_SPEED_COMPENSATION,
                               desc=self.cmd_RADIAL_SPEED_COMPENSATION_help)
        self.Coord = gcode.Coord
        # G-Code coordinate manipulation
        self.absolute_coord = self.absolute_extrude = True
        self.base_position = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        self.last_position = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        self.homing_position = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        self.radius = 0.
        self.square_corner_velocity = 5.
        self.radial_speed_compensation_enabled = False
        self.speed = self.rotary_speed = 25.
        self.speed_factor = 1. / 60.
        self.extrude_factor = 1.
        # Multiple coordinate systems
        self.wcs_offsets = []
        for wcs_index in range(6):
            wcs_conf = config.getsection('wcs_%d' % wcs_index)
            self.wcs_offsets.append([wcs_conf.getfloat(
                'x', 0.), wcs_conf.getfloat('y', 0.), wcs_conf.getfloat('z', 0.)])
        self.current_wcs = 0
        wcs_handlers = ['G10', 'G54', 'G55',
                        'G56', 'G57', 'G58', 'G59', 'GET_WCS', 'SET_WCS']
        for cmd in wcs_handlers:
            func = getattr(self, 'cmd_' + cmd)
            desc = getattr(self, 'cmd_' + cmd + '_help', None)
            gcode.register_command(cmd, func, False, desc)
        # Workpiece compensation
        workpiece_compensation_config = config.getsection(
            'workpiece_compensation')
        self.mm_per_arc_segment = workpiece_compensation_config.getfloat(
            'resolution', 1., above=0.0)
        self.compensation_enabled = False
        gcode.register_command('G43', self.cmd_ENABLE_WORKPIECE_COMPENSATION,
                               desc=self.cmd_ENABLE_WORKPIECE_COMPENSATION_help)
        gcode.register_command('G40', self.cmd_DISABLE_WORKPIECE_COMPENSATION,
                               desc=self.cmd_DISABLE_WORKPIECE_COMPENSATION_help)
        # Homing offsets
        homing_offset_conf = config.getsection('homing_offsets')
        for pos, axis in enumerate('xyzace'):
            offset = homing_offset_conf.getfloat(axis, 0.)
            self.base_position[pos] += offset
            self.homing_position[pos] = offset
        # G-Code state
        self.saved_states = {}
        self.move_transform = self.move_with_transform = None
        self.position_with_transform = (lambda: [0., 0., 0., 0., 0., 0.])

    def _handle_ready(self):
        self.is_printer_ready = True
        toolhead = self.printer.lookup_object('toolhead')
        if self.move_transform is None:
            self.move_with_transform = toolhead.move
            self.position_with_transform = toolhead.get_position
        self.square_corner_velocity = toolhead.square_corner_velocity
        self.reset_last_position()

    def _handle_shutdown(self):
        if not self.is_printer_ready:
            return
        self.is_printer_ready = False
        logging.info("gcode state: absolute_coord=%s absolute_extrude=%s"
                     " base_position=%s last_position=%s homing_position=%s"
                     " speed_factor=%s extrude_factor=%s speed=%s",
                     self.absolute_coord, self.absolute_extrude,
                     self.base_position, self.last_position,
                     self.homing_position, self.speed_factor,
                     self.extrude_factor, self.speed)

    def _handle_activate_extruder(self):
        self.reset_last_position()
        self.extrude_factor = 1.
        self.base_position[5] = self.last_position[5]

    def _handle_home_rails_end(self, homing_state, rails):
        self.reset_last_position()
        for axis in homing_state.get_axes():
            self.base_position[axis] = self.homing_position[axis]

    def set_move_transform(self, transform, force=False):
        if self.move_transform is not None and not force:
            raise self.printer.config_error(
                "G-Code move transform already specified")
        old_transform = self.move_transform
        if old_transform is None:
            old_transform = self.printer.lookup_object('toolhead', None)
        self.move_transform = transform
        self.move_with_transform = transform.move
        self.position_with_transform = transform.get_position
        return old_transform

    def _get_gcode_position(self):
        p = [lp - bp for lp, bp in zip(self.last_position, self.base_position)]
        p[5] /= self.extrude_factor
        return p

    def _get_gcode_speed(self):
        return self.speed / self.speed_factor #in mm/min

    def _get_gcode_speed_override(self):
        return self.speed_factor * 60.

    def get_status(self, eventtime=None):
        move_position = self._get_gcode_position()
        return {
            'speed_factor': self._get_gcode_speed_override(),
            'speed': self._get_gcode_speed(), #in mm/min
            'extrude_factor': self.extrude_factor,
            'absolute_coordinates': self.absolute_coord,
            'absolute_extrude': self.absolute_extrude,
            'homing_origin': self.Coord(*self.homing_position),
            'position': self.Coord(*self.last_position),
            'gcode_position': self.Coord(*move_position),
            'current_wcs': self.current_wcs,
            'wcs_offsets': [[a for a in line] for line in self.wcs_offsets],
            'base_position': self.Coord(*self.base_position),
            'compensation_enabled': self.compensation_enabled,
            'radial_speed_compensation_enabled': self.radial_speed_compensation_enabled,
        }

    def reset_last_position(self):
        if self.is_printer_ready:
            self.last_position = self.position_with_transform()
    # G-Code movement commands

    def manual_move(self, coord, speed):
        new_pos = []
        for i in range(len(coord)):
            if coord[i] is not None:
                new_pos.append(coord[i] + self.base_position[i])
            else:
                new_pos.append(coord[i])
        self.printer.lookup_object(
            'toolhead').manual_move(tuple(new_pos), speed)

    def cmd_G1(self, gcmd):
        if self.compensation_enabled:
            self.process_move_with_compensation(gcmd)
        else:
            # Move
            params = gcmd.get_command_parameters()
            try:
                for pos, axis in enumerate('XYZAC'):
                    if axis in params:
                        v = float(params[axis])
                        if not self.absolute_coord:
                            # value relative to position of last move
                            self.last_position[pos] += v
                        else:
                            # value relative to base coordinate position
                            self.last_position[pos] = v + \
                                self.base_position[pos]
                            if pos < 3:
                                self.last_position[pos] += self.wcs_offsets[self.current_wcs][pos]
                        if axis == 'Z':
                            self.radius = self._get_gcode_position()[2] - self.wcs_offsets[self.current_wcs][2]
                if 'E' in params:
                    v = float(params['E']) * self.extrude_factor
                    if not self.absolute_coord or not self.absolute_extrude:
                        # value relative to position of last move
                        self.last_position[5] += v
                    else:
                        # value relative to base coordinate position
                        self.last_position[5] = v + self.base_position[5]
                if 'F' in params:
                    # check need enable radial speed compensation.
                    with_rotation = 'C' in params
                    gcode_speed = float(params['F'])
                    if gcode_speed <= 0.:
                        raise gcmd.error("Invalid speed in '%s'"
                                         % (gcmd.get_commandline(),))
                    self.speed = gcode_speed * self.speed_factor
                if 'C' in params and self.radius > 0. and self.radial_speed_compensation_enabled:
                    self.rotary_speed = (RAD_TO_DEG * self.speed) / (self.radius * 3)
                    #self.rotary_speed = -0.5 * self.radius + 50.
                    if self.rotary_speed > self.speed:
                        self.rotary_speed = self.speed
                    if self.rotary_speed < self.square_corner_velocity:
                        self.rotary_speed = self.square_corner_velocity
            except ValueError as e:
                raise gcmd.error("Unable to parse move '%s'"
                                 % (gcmd.get_commandline(),))
            self.move_with_transform(self.last_position, \
                self.rotary_speed if self.radial_speed_compensation_enabled and with_rotation else self.speed)
    # G-Code coordinate manipulation

    def cmd_G20(self, gcmd):
        # Set units to inches
        raise gcmd.error('Machine does not support G20 (inches) command')

    def cmd_G21(self, gcmd):
        # Set units to millimeters
        pass

    def cmd_M82(self, gcmd):
        # Use absolute distances for extrusion
        self.absolute_extrude = True

    def cmd_M83(self, gcmd):
        # Use relative distances for extrusion
        self.absolute_extrude = False

    def cmd_G90(self, gcmd):
        # Use absolute coordinates
        self.absolute_coord = True

    def cmd_G91(self, gcmd):
        # Use relative coordinates
        self.absolute_coord = False

    def cmd_G92(self, gcmd):
        # Set position
        offsets = [gcmd.get_float(a, None) for a in 'XYZACE']
        for i, offset in enumerate(offsets):
            if offset is not None:
                if i == 5:
                    offset *= self.extrude_factor
                self.base_position[i] = self.last_position[i] - offset
        if offsets == [None, None, None, None, None, None]:
            self.base_position = list(self.last_position)

    def cmd_M114(self, gcmd):
        # Get Current Position
        p = self._get_gcode_position()
        gcmd.respond_raw(
            "X:%.3f Y:%.3f Z:%.3f A:%.3f C:%.3f E:%.3f" % tuple(p))

    def cmd_M220(self, gcmd):
        # Set speed factor override percentage
        value = gcmd.get_float('S', 100., above=0.) / (60. * 100.)
        self.speed = self._get_gcode_speed() * value
        self.speed_factor = value

    def cmd_M221(self, gcmd):
        # Set extrude factor override percentage
        new_extrude_factor = gcmd.get_float('S', 100., above=0.) / 100.
        last_e_pos = self.last_position[5]
        e_value = (last_e_pos - self.base_position[5]) / self.extrude_factor
        self.base_position[5] = last_e_pos - e_value * new_extrude_factor
        self.extrude_factor = new_extrude_factor
    cmd_SET_GCODE_OFFSET_help = "Set a virtual offset to g-code positions"

    def cmd_SET_GCODE_OFFSET(self, gcmd):
        move_delta = [0., 0., 0., 0., 0., 0.]
        for pos, axis in enumerate('XYZACE'):
            offset = gcmd.get_float(axis, None)
            if offset is None:
                offset = gcmd.get_float(axis + '_ADJUST', None)
                if offset is None:
                    continue
                offset += self.homing_position[pos]
            delta = offset - self.homing_position[pos]
            move_delta[pos] = delta
            self.base_position[pos] += delta
            self.homing_position[pos] = offset
            configfile = self.printer.lookup_object('configfile')
            configfile.set('homing_offsets', axis.lower(), offset)

        # Move the toolhead the given offset if requested
        if gcmd.get_int('MOVE', 0):
            speed = gcmd.get_float('MOVE_SPEED', self.speed, above=0.)
            for pos, delta in enumerate(move_delta):
                self.last_position[pos] += delta
            self.move_with_transform(self.last_position, speed)
    cmd_SAVE_GCODE_STATE_help = "Save G-Code coordinate state"

    def cmd_SAVE_GCODE_STATE(self, gcmd):
        state_name = gcmd.get('NAME', 'default')
        self.saved_states[state_name] = {
            'absolute_coord': self.absolute_coord,
            'absolute_extrude': self.absolute_extrude,
            'base_position': list(self.base_position),
            'last_position': list(self.last_position),
            'homing_position': list(self.homing_position),
            'speed': self.speed,
            'speed_factor': self.speed_factor,
            'extrude_factor': self.extrude_factor,
            'current_wcs': self.current_wcs,
        }
    cmd_RESTORE_GCODE_STATE_help = "Restore a previously saved G-Code state"

    def cmd_RESTORE_GCODE_STATE(self, gcmd):
        state_name = gcmd.get('NAME', 'default')
        state = self.saved_states.get(state_name)
        if state is None:
            raise gcmd.error("Unknown g-code state: %s" % (state_name,))
        # Restore state
        self.absolute_coord = state['absolute_coord']
        self.absolute_extrude = state['absolute_extrude']
        self.base_position = list(state['base_position'])
        self.homing_position = list(state['homing_position'])
        self.speed = state['speed']
        self.speed_factor = state['speed_factor']
        self.extrude_factor = state['extrude_factor']
        self.current_wcs = state['current_wcs']
        # Restore the relative E position
        e_diff = self.last_position[5] - state['last_position'][5]
        self.base_position[5] += e_diff
        # Move the toolhead back if requested
        if gcmd.get_int('MOVE', 0):
            speed = gcmd.get_float('MOVE_SPEED', self.speed, above=0.)
            self.last_position[:5] = state['last_position'][:5]
            self.move_with_transform(self.last_position, speed)
    cmd_GET_POSITION_help = (
        "Return information on the current location of the toolhead")

    def cmd_RADIAL_SPEED_COMPENSATION(self, gcmd):
        params = gcmd.get_int('ENABLE', 0)
        self.radial_speed_compensation_enabled = params > 0
        logging.info('Compensation the corner velocity ENABLE=%d' % self.radial_speed_compensation_enabled)
    cmd_RADIAL_SPEED_COMPENSATION_help = 'This command turn on compensation the corner velocity for the C axis'

    def cmd_LOAD_GCODE_STATE(self, gcmd):
        """
        Loads state from gcode file.
        """
        state_name = gcmd.get('NAME', 'default')
        params = gcmd.get('PARAMS', 'default')
        params_dict = ast.literal_eval(params)
        homing_position = [
                params_dict['gcode_move']['homing_origin'][0],
                params_dict['gcode_move']['homing_origin'][1],
                params_dict['gcode_move']['homing_origin'][2],
                params_dict['gcode_move']['homing_origin'][3],
                params_dict['gcode_move']['homing_origin'][4],
                params_dict['gcode_move']['homing_origin'][5]]
        last_position = [
                params_dict['gcode_move']['position'][0],
                params_dict['gcode_move']['position'][1],
                params_dict['gcode_move']['position'][2],
                params_dict['gcode_move']['position'][3],
                params_dict['gcode_move']['position'][4],
                params_dict['gcode_move']['position'][5]]
        base_position = [
                params_dict['gcode_move']['base_position'][0],
                params_dict['gcode_move']['base_position'][1],
                params_dict['gcode_move']['base_position'][2],
                params_dict['gcode_move']['base_position'][3],
                params_dict['gcode_move']['base_position'][4],
                params_dict['gcode_move']['base_position'][5]]
        self.saved_states[state_name] = {
            'absolute_coord': params_dict['gcode_move']['absolute_coordinates'],
            'absolute_extrude': params_dict['gcode_move']['absolute_extrude'],
            'base_position': list(base_position),
            'last_position': list(last_position),
            'homing_position': list(homing_position),
            'speed': params_dict['gcode_move']['speed'],
            'speed_factor': params_dict['gcode_move']['speed_factor'] / 60.,
            'extrude_factor': params_dict['gcode_move']['extrude_factor'],
            'current_wcs': params_dict['gcode_move']['current_wcs'],
        }
        logging.info('Realised cmd LOAD_GCODE_STATE, state: %s' % self.saved_states[state_name])
    cmd_LOAD_GCODE_STATE_help = 'Loading Print Status and Data from a params sended from STEAPP-server'

    def cmd_GET_POSITION(self, gcmd):
        toolhead = self.printer.lookup_object('toolhead', None)
        if toolhead is None:
            raise gcmd.error("Printer not ready")
        kin = toolhead.get_kinematics()
        steppers = kin.get_steppers()
        mcu_pos = " ".join(["%s:%d" % (s.get_name(), s.get_mcu_position())
                            for s in steppers])
        cinfo = [(s.get_name(), s.get_commanded_position()) for s in steppers]
        stepper_pos = " ".join(["%s:%.6f" % (a, v) for a, v in cinfo])
        kinfo = zip("XYZAC", kin.calc_position(dict(cinfo)))
        kin_pos = " ".join(["%s:%.6f" % (a, v) for a, v in kinfo])
        toolhead_pos = " ".join(["%s:%.6f" % (a, v) for a, v in zip(
            "XYZACE", toolhead.get_position())])
        gcode_pos = " ".join(["%s:%.6f" % (a, v)
                              for a, v in zip("XYZACE", self.last_position)])
        base_pos = " ".join(["%s:%.6f" % (a, v)
                             for a, v in zip("XYZACE", self.base_position)])
        homing_pos = " ".join(["%s:%.6f" % (a, v)
                               for a, v in zip("XYZAC", self.homing_position)])
        gcmd.respond_info("mcu: %s\n"
                          "stepper: %s\n"
                          "kinematic: %s\n"
                          "toolhead: %s\n"
                          "gcode: %s\n"
                          "gcode base: %s\n"
                          "gcode homing: %s"
                          % (mcu_pos, stepper_pos, kin_pos, toolhead_pos,
                             gcode_pos, base_pos, homing_pos))

    def cmd_G54(self, gcmd):
        self.current_wcs = 0

    def cmd_G55(self, gcmd):
        self.current_wcs = 1

    def cmd_G56(self, gcmd):
        self.current_wcs = 2

    def cmd_G57(self, gcmd):
        self.current_wcs = 3

    def cmd_G58(self, gcmd):
        self.current_wcs = 4

    def cmd_G59(self, gcmd):
        self.current_wcs = 5

    def cmd_G10(self, gcmd):
        offset_mode = gcmd.get_int('L', 2)
        n = gcmd.get_int('P', 0)
        relative = gcmd.get_int('R', 0)
        offsets = [gcmd.get_float(a, None) for a in 'XYZ']
        if n == 0:
            n = self.current_wcs
        else:
            n = n - 1
        if offset_mode == 20:
            pos = self._mcs_to_wcs(self.last_position)
            for i, offset in enumerate(offsets):
                if offset is not None:
                    self.wcs_offsets[n][i] -= offset - (pos[i] - self.homing_position[i])
        elif self.absolute_coord:
            if relative:
                for i, offset in enumerate(offsets):
                    if offset is not None:
                        self.wcs_offsets[n][i] += offset
            else:
                for i, offset in enumerate(offsets):
                    if offset is not None:
                        self.wcs_offsets[n][i] = offset
        else:
            for i, offset in enumerate(offsets):
                if offset is not None:
                    self.wcs_offsets[n][i] += offset
        configfile = self.printer.lookup_object('configfile')
        configfile.set('wcs_%d' % n, 'x', self.wcs_offsets[n][0])
        configfile.set('wcs_%d' % n, 'y', self.wcs_offsets[n][1])
        configfile.set('wcs_%d' % n, 'z', self.wcs_offsets[n][2])

    def get_wcs(self, wcs):
        if (wcs < 6):
            return self.wcs_offsets[wcs]
        else:
            return self.wcs_offsets[0]

    def _mcs_to_wcs(self, pos):
        return [
            pos[0] - self.wcs_offsets[self.current_wcs][0],
            pos[1] - self.wcs_offsets[self.current_wcs][1],
            pos[2] - self.wcs_offsets[self.current_wcs][2],
            pos[3],
            pos[4],
            pos[5]
        ]

    def cmd_GET_WCS(self, gcmd):
        current_wcs = " ".join(["%d" % (self.current_wcs)])
        wcs_offsets = " "
        for wcs_n in range(6):
            wcs_offsets = wcs_offsets + "%d " % (wcs_n) + " ".join(
                ["%s:%.3f" % (a, v) for a, v in zip("XYZ", self.wcs_offsets[wcs_n])])
            wcs_offsets += "\n"
        gcmd.respond_info("current_wcs: %s\n"
                          "wcs_offsets: \n"
                          "%s" % (current_wcs, wcs_offsets))

    def cmd_SET_WCS(self, gcmd):
        wcs = gcmd.get_int('WCS', 0)
        if (wcs < 6):
            self.current_wcs = wcs
        else:
            self.current_wcs = 0
        gcmd.respond_info("current_wcs: %d" % (self.current_wcs))

    def cmd_ENABLE_WORKPIECE_COMPENSATION(self, gcmd):
        self.compensation_enabled = True
    cmd_ENABLE_WORKPIECE_COMPENSATION_help = "Enable workpiece compensation"

    def cmd_DISABLE_WORKPIECE_COMPENSATION(self, gcmd):
        self.compensation_enabled = False
    cmd_DISABLE_WORKPIECE_COMPENSATION_help = "Disable workpiece compensation"

    def _plan_arc(self, current_pos, target_pos, offset):
        # Radius vector from center to current location
        linear_x = target_pos[0] - current_pos[0]
        linear_a = target_pos[3] - current_pos[3]
        linear_c = target_pos[4] - current_pos[4]

        r_Y = -offset[1]
        r_Z = -offset[2]

        # Determine angular travel
        center_Y = self.get_wcs(1)[1]  # current_pos[1] - r_Y
        center_Z = self.get_wcs(2)[2]  # current_pos[2] - r_Z

        angular_travel = DEG_TO_RAD * (target_pos[3] - current_pos[3])
        angular_target = DEG_TO_RAD * (target_pos[3] - self.base_position[3])
        linear_y = target_pos[1] - current_pos[1]
        linear_z = target_pos[2] - current_pos[2]

        cos_a_travel = math.cos(angular_travel)
        sin_a_travel = math.sin(angular_travel)

        compensated_target = list(target_pos)
        compensated_target.pop()
        compensated_target[1] = target_pos[1] * \
            cos_a_travel - target_pos[2] * sin_a_travel + \
            center_Y - cos_a_travel * center_Y + sin_a_travel * center_Z
        compensated_target[2] = target_pos[1] * \
            sin_a_travel + target_pos[2] * cos_a_travel + \
            center_Z - sin_a_travel * center_Y - cos_a_travel * center_Z

        radius = math.hypot(r_Y, r_Z)
        ellipse_length = math.sqrt(
            (radius + linear_y) ** 2 + (radius + linear_z) ** 2)
        mm_of_travel = math.hypot(
            (angular_travel / (2 * math.pi)) * ellipse_length, math.fabs(linear_x))
        segments = max(1., math.floor(mm_of_travel / self.mm_per_arc_segment))
        theta_per_segment = angular_travel / segments
        linear_per_segment = [linear_x / segments,
                              linear_y / segments,
                              linear_z / segments,
                              linear_a / segments,
                              linear_c / segments]
        coords = []
        for i in range(1, int(segments)):
            dist = [0., 0., 0., 0., 0.]
            for axis, linear in enumerate(linear_per_segment):
                dist[axis] = i * linear
            cos_Ti = math.cos(i * theta_per_segment)
            sin_Ti = math.sin(i * theta_per_segment)
            r_Y = (-offset[1] + dist[1]) * cos_Ti - (-offset[2] + dist[2]) * sin_Ti # + \
                #center_Y - cos_Ti * center_Y + sin_Ti * center_Z
            r_Z = (-offset[1] + dist[1]) * sin_Ti + (-offset[2] + dist[2]) * cos_Ti # + \
                #center_Z - sin_Ti * center_Y - cos_Ti * center_Z
            c = [current_pos[0] + dist[0],
                 center_Y + r_Y ,
                 center_Z + r_Z,
                 current_pos[3] + dist[3],
                 current_pos[4] + dist[4]]
            coords.append(c)

        coords.append(compensated_target)
        return coords

    def _calc_compensation(self, pos):
        angular_pos = DEG_TO_RAD * \
            (self.last_position[3] - self.base_position[3])
        cos_a = math.cos(angular_pos)
        sin_a = math.sin(angular_pos)
        cos_ma = math.cos(-angular_pos)
        sin_ma = math.sin(-angular_pos)

        wcs_1 = self.get_wcs(1)
        wcs_2 = self.get_wcs(2)

        inverted_last_pos = list(self.last_position)
        inverted_last_pos[1] = self.last_position[1] * \
            cos_ma - self.last_position[2] * sin_ma + \
            wcs_1[1] - cos_ma * wcs_1[1] + sin_ma * wcs_2[2]
        inverted_last_pos[2] = self.last_position[1] * \
            sin_ma + self.last_position[2] * cos_ma + \
            wcs_2[2] - sin_ma * wcs_1[1] - cos_ma * wcs_2[2]

        offset = [0., 0., 0.]
        offset_y = wcs_1[1] - self.last_position[1] #inverted_last_pos[1]
        offset_z = wcs_2[2] - self.last_position[2] #inverted_last_pos[2]
        offset[1] = offset_y # * cos_a - offset_z * sin_a + \
            #wcs_1[1] - cos_a * wcs_1[1] + sin_a * wcs_2[2]
        offset[2] = offset_z # offset_y * sin_a + offset_z * cos_a + \
            #wcs_2[2] - sin_a * wcs_1[1] - cos_a * wcs_2[2]

        inverted_pos = list(pos)
        inverted_pos[1] = pos[1] * \
            cos_a - pos[2] * sin_a + \
            wcs_1[1] - cos_a * wcs_1[1] + sin_a * wcs_2[2]
        inverted_pos[2] = pos[1] * \
            sin_a + pos[2] * cos_a + \
            wcs_2[2] - sin_a * wcs_1[1] - cos_a * wcs_2[2]

        coords = self._plan_arc(self.last_position, inverted_pos, offset)
        e_per_move = e_base = 0.
        if self.absolute_extrude:
            e_base = self.last_position[5]
        e_per_move = (pos[5] - e_base) / len(coords)

        for coord in coords:
            if e_per_move:
                coord.append(e_base + e_per_move)
                if self.absolute_extrude:
                    e_base += e_per_move
            else:
                coord.append(e_base)
        return coords

    def process_move_with_compensation(self, gcmd):
        params = gcmd.get_command_parameters()
        try:
            angular_pos = DEG_TO_RAD * \
                (self.last_position[3] - self.base_position[3])
            cos_a = math.cos(angular_pos)
            sin_a = math.sin(angular_pos)
            cos_ma = math.cos(-angular_pos)
            sin_ma = math.sin(-angular_pos)

            wcs_1 = self.get_wcs(1)
            wcs_2 = self.get_wcs(2)

            inverted_last_pos = list(self.last_position)
            inverted_last_pos[1] = self.last_position[1] * \
                cos_ma - self.last_position[2] * sin_ma + \
                wcs_1[1] - cos_ma * wcs_1[1] + sin_ma * wcs_2[2]
            inverted_last_pos[2] = self.last_position[1] * \
                sin_ma + self.last_position[2] * cos_ma + \
                wcs_2[2] - sin_ma * wcs_1[1] - cos_ma * wcs_2[2]
            new_position = list(inverted_last_pos)

            for pos, axis in enumerate('XYZAC'):
                if axis in params:
                    v = float(params[axis])
                    if not self.absolute_coord:
                        # value relative to position of last move
                        new_position[pos] += v
                    else:
                        # value relative to base coordinate position
                        new_position[pos] = v + self.base_position[pos]
                        if pos < 3:
                            new_position[pos] += self.wcs_offsets[self.current_wcs][pos]
            if 'E' in params:
                v = float(params['E']) * self.extrude_factor
                if not self.absolute_coord or not self.absolute_extrude:
                    # value relative to position of last move
                    new_position[5] += v
                else:
                    # value relative to base coordinate position
                    new_position[5] = v + self.base_position[5]
            if 'F' in params:
                gcode_speed = float(params['F'])
                if gcode_speed <= 0.:
                    raise gcmd.error("Invalid speed in '%s'"
                                     % (gcmd.get_commandline(),))
                self.speed = gcode_speed * self.speed_factor
        except ValueError as e:
            raise gcmd.error("Unable to parse move '%s'"
                             % (gcmd.get_commandline(),))
        positions = self._calc_compensation(new_position)
        for position in positions:
            self.move_with_transform(position, self.speed)
        self.last_position = positions[-1]


def load_config(config):
    return GCodeMove(config)
