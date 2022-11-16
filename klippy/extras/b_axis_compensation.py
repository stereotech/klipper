# B axis compensation correction

import math

from mathutil import matrix3x3_apply, matrix3x3_mul, matrix3x3_transpose

RAD_TO_DEG = 57.295779513

# Constrain value between min and max
def constrain(val, min_val, max_val):
    return min(max_val, max(min_val, val))

class BAxisCompensation:
    def __init__(self, config):
        self.printer = config.get_printer()
        self.gcode_move = self.printer.load_object(config, 'gcode_move')
        self.gcode = self.printer.lookup_object('gcode')
        self.b_angle = config.getfloat(
            'b_angle', default=0.
        )
        sin_b = math.sin(self.b_angle)
        cos_b = math.cos(self.b_angle)
        self.rot_matrix = [cos_b, 0., sin_b, 0., 1., 0., -sin_b, 0., cos_b]
        self.rot_center_x = config.getfloat('rot_center_x', default=0.)
        self.rot_center_z = config.getfloat('rot_center_z', default=0.)
        self.enabled = False
        self.point_coords = [
            [0., 0., 0., 0., 0., 0.],
            [0., 0., 0., 0., 0., 0.],
            [0., 0., 0., 0., 0., 0.],
            [0., 0., 0., 0., 0., 0.],
            [0., 0., 0., 0., 0., 0.],
            [0., 0., 0., 0., 0., 0.]
        ]
        self.adjust_angle = 10 / RAD_TO_DEG
        self.gcode.register_command('CALC_B_AXIS_COMPENSATION',
                                    self.cmd_CALC_B_AXIS_COMPENSATION,
                                    desc=self.cmd_CALC_B_AXIS_COMPENSATION_help)
        self.gcode.register_command('CALC_B_AXIS_CENTER',
                                    self.cmd_CALC_B_AXIS_CENTER,
                                    desc=self.cmd_CALC_B_AXIS_CENTER_help)
        self.gcode.register_command('CALC_B_ANGLE',
                                    self.cmd_CALC_B_ANGLE,
                                    desc=self.cmd_CALC_B_ANGLE_help)
        self.gcode.register_command(
            'SAVE_B_AXIS_POINT', self.cmd_SAVE_B_AXIS_POINT,
            desc=self.cmd_SAVE_B_AXIS_POINT_help)
        self.gcode.register_command(
            'B_AXIS_COMPENSATION_VARS', self.cmd_B_AXIS_COMPENSATION_VARS,
            desc=self.cmd_B_AXIS_COMPENSATION_VARS_help
        )
        self.printer.register_event_handler("klippy:connect",
                                            self._handle_connect)
        # Register transform
        self.printer.lookup_object('bed_mesh').next_transform = self
        self.next_transform = None

    def _handle_connect(self):
        kin = self.printer.lookup_object('toolhead').get_kinematics()
        self.axes_min = kin.axes_min
        self.axes_max = kin.axes_max

    def get_position(self):
        if not self.enabled:
            return self.next_transform.get_position()
        return self.calc_untransformed(self.next_transform.get_position())

    def move(self, newpos, speed):
        axes_d = [self.next_transform.get_position()[i] - newpos[i] for i in
                                (0, 1, 2, 3, 4, 5)]
        move_d = math.sqrt(sum([d * d for d in axes_d[:5]]))
        if not self.enabled or move_d < .000000001:
            self.next_transform.move(newpos, speed)
            return
        corrected_pos = self.calc_tranformed(newpos)
        self.next_transform.move(corrected_pos, speed)

    def calc_tranformed(self, pos):
        gcode_move = self.printer.lookup_object('gcode_move')
        base_position = gcode_move.base_position
        a = math.radians(pos[3] - base_position[3])
        sin_a = math.sin(a)
        cos_a = math.cos(a)
        a_rot_matrix = [1., 0., 0, 0., cos_a, -sin_a, 0., sin_a, cos_a]
        newpos = list(pos)
        newpos[0] -= self.rot_center_x
        newpos[2] -= self.rot_center_z
        m = matrix3x3_mul(matrix3x3_mul(
            a_rot_matrix, self.rot_matrix), matrix3x3_transpose(a_rot_matrix))
        newpos = matrix3x3_apply(newpos, m)
        newpos[0] += self.rot_center_x
        newpos[2] += self.rot_center_z
        newpos = [constrain(newpos[axis], self.axes_min[axis], self.axes_max[axis]) for axis in range(5)]
        newpos.append(pos[5])
        return newpos

    def calc_untransformed(self, pos):
        gcode_move = self.printer.lookup_object('gcode_move')
        base_position = gcode_move.base_position
        a = math.radians(pos[3] - base_position[3])
        sin_a = math.sin(a)
        cos_a = math.cos(a)
        a_rot_matrix = [1., 0., 0, 0., cos_a, -sin_a, 0., sin_a, cos_a]
        newpos = list(pos)
        newpos[0] -= self.rot_center_x
        newpos[2] -= self.rot_center_z
        m = matrix3x3_mul(matrix3x3_mul(
            a_rot_matrix, self.rot_matrix), matrix3x3_transpose(a_rot_matrix))
        m = matrix3x3_transpose(m)
        newpos = matrix3x3_apply(newpos, m)
        newpos[0] += self.rot_center_x
        newpos[2] += self.rot_center_z
        newpos = [constrain(newpos[axis], self.axes_min[axis], self.axes_max[axis]) for axis in range(5)]
        newpos.append(pos[5])
        return newpos

    def cmd_SAVE_B_AXIS_POINT(self, gcmd):
        point_idx = gcmd.get_int('POINT', 0)
        coords = gcmd.get('COORDS', None)
        if coords is not None:
            try:
                coords = coords.strip().split(",", 2)
                coords = [float(l.strip()) for l in coords]
                if len(coords) != 3:
                    raise Exception
            except Exception:
                raise gcmd.error(
                    "b_axis_compensation: improperly formatted entry for "
                    "point\n%s" % (gcmd.get_commandline()))
            for axis, coord in enumerate(coords):
                self.point_coords[point_idx][axis] = coord

    cmd_SAVE_B_AXIS_POINT_help = "Save point for B axis compensation"

    def _calc_b_axis_compensation(self, point_0, point_1, point_2, point_3, point_4, point_5):
        b_angle = self._calc_b_axis_angle(point_2, point_3)
        rot_center_x, rot_center_z = self._calc_b_axis_center(point_0, point_1, point_4, point_5)
        return b_angle, rot_center_x, rot_center_z

    def _calc_b_axis_center(self, point_0, point_1, point_2, point_3):
        probe_backlash = (abs(point_2[0] - point_3[0]) - 110) / 2
        rot_center_x = (point_2[0] + point_3[0]) / 2
        o_cz_1 = (point_0[2] - (point_1[2] + probe_backlash *
                                math.sin(self.adjust_angle))) / math.tan(self.adjust_angle)
        o2_o1 = 45 - o_cz_1
        h = abs(o2_o1 / math.tan(self.adjust_angle / 2))
        rot_center_z = point_0[2] - h
        return rot_center_x, rot_center_z

    def _calc_b_axis_angle(self, point_0, point_1):
        b_angle = math.pi / 2 - math.atan((point_1[0] - point_0[0]) / (point_0[2] - point_1[2]))
        if b_angle > math.pi / 2:
            b_angle -= math.pi
        return b_angle

    def _update_compensation(self, b_angle, rot_center_x, rot_center_z):
        self.b_angle = b_angle
        self.rot_center_x = rot_center_x
        self.rot_center_z = rot_center_z
        sin_b = math.sin(b_angle)
        cos_b = math.cos(b_angle)
        self.rot_matrix = [cos_b, 0., sin_b, 0., 1., 0., -sin_b, 0., cos_b]
        gcode_move = self.printer.lookup_object('gcode_move')
        gcode_move.reset_last_position()

    def _save_compensation(self, b_angle, rot_center_x, rot_center_z):
        configfile = self.printer.lookup_object('configfile')
        configfile.set('b_axis_compensation', 'b_angle', b_angle)
        configfile.set('b_axis_compensation',
                       'rot_center_x', rot_center_x)
        configfile.set('b_axis_compensation',
                       'rot_center_z', rot_center_z)

    def cmd_CALC_B_AXIS_COMPENSATION(self, gcmd):
        b_angle, rot_center_x, rot_center_z = self._calc_b_axis_compensation(
            self.point_coords[0], self.point_coords[1], self.point_coords[2],
            self.point_coords[3], self.point_coords[4], self.point_coords[5])
        self._update_compensation(b_angle, rot_center_x, rot_center_z)
        enable = gcmd.get_int('ENABLE', 0)
        if enable:
            self.enabled = True
            gcmd.respond_info('B_axis_compesation  enabled.')
        else:
            self.enabled = False
            gcmd.respond_info('B_axis_compesation disabled.')
        save = gcmd.get_int('SAVE', 0)
        if save:
            self._save_compensation(b_angle, rot_center_x, rot_center_z)
        out = "Calculated B axis angle: %.6f radians, %.2f degrees\n" % (
            b_angle, math.degrees(b_angle))
        out += "B axis rotation center: X%.3f Y%.3f Z%.3f" % (
            rot_center_x, 0, rot_center_z)
        gcmd.respond_info(out)

    cmd_CALC_B_AXIS_COMPENSATION_help = "Calculate B axis compensation"

    def cmd_CALC_B_AXIS_CENTER(self, gcmd):
        rot_center_x, rot_center_z = \
        self._calc_b_axis_center(self.point_coords[0], self.point_coords[1],
                                 self.point_coords[4], self.point_coords[5])
        gcmd.respond_info("B axis rotation center: X%.3f Y%.3f Z%.3f" % (
            rot_center_x, 0, rot_center_z))

    cmd_CALC_B_AXIS_CENTER_help = "Calculate B axis center"

    def cmd_CALC_B_ANGLE(self, gcmd):
        b_angle = self._calc_b_axis_angle(self.point_coords[2], self.point_coords[3])
        gcmd.respond_info("B axis angle: %.3f" % (b_angle))

    cmd_CALC_B_ANGLE_help = "Calculate B axis angle"

    def cmd_B_AXIS_COMPENSATION_VARS(self, gcmd):
        b_angle = gcmd.get_float('B', self.b_angle)
        rot_center_x = gcmd.get_float('X', self.rot_center_x)
        rot_center_z = gcmd.get_float('Z', self.rot_center_z)
        self._update_compensation(b_angle, rot_center_x, rot_center_z)
        enable = gcmd.get_int('ENABLE', 0)
        if enable:
            self.enabled = True
        else:
            self.enabled = False
        save = gcmd.get_int('SAVE', 0)
        if save:
            self._save_compensation(b_angle, rot_center_x, rot_center_z)

    cmd_B_AXIS_COMPENSATION_VARS_help = "Set B axis compensation parameters directly"

    def get_status(self, eventtime=None):
        return {
            'b_angle': self.b_angle,
            'rot_center_x': self.rot_center_x,
            'rot_center_z': self.rot_center_z,
            'enable': self.enabled
        }

def load_config(config):
    return BAxisCompensation(config)
