# B axis compensation correction

import math

from mathutil import matrix3x3_apply, matrix3x3_mul, matrix3x3_transpose

RAD_TO_DEG = 57.295779513


class BAxisCompensation:
    def __init__(self, config):
        self.printer = config.get_printer()
        self.gcode_move = self.printer.load_object(config, 'gcode_move')
        self.gcode = self.printer.lookup_object('gcode')
        self.calibration_template_size = config.getfloat(
            'calibration_template_size', default=50., above=0.)
        self.b_angle = config.getfloat(
            'b_angle', default=0.
        )
        sin_b = math.sin(self.b_angle)
        cos_b = math.cos(self.b_angle)
        self.rot_matrix = [cos_b, 0., sin_b, 0., 1., 0., -sin_b, 0., cos_b]
        self.rot_center_x = config.getfloat('rot_center_x', default=0.)
        self.rot_center_z = config.getfloat('rot_center_z', default=0.)
        self.point_coords = [
            [0., 0., 0., 0., 0., 0.],
            [0., 0., 0., 0., 0., 0.]
        ]
        self.gcode.register_command('CALC_B_AXIS_COMPENSATION',
                                    self.cmd_CALC_B_AXIS_COMPENSATION,
                                    desc=self.cmd_CALC_B_AXIS_COMPENSATION_help)
        self.gcode.register_command(
            'SAVE_B_AXIS_POINT', self.cmd_SAVE_B_AXIS_POINT,
            desc=self.cmd_SAVE_B_AXIS_POINT_help)
        self.gcode.register_command(
            'B_AXIS_COMPENSATION_VARS', self.cmd_B_AXIS_COMPENSATION_VARS,
            desc=self.cmd_B_AXIS_COMPENSATION_VARS_help
        )
        self.printer.register_event_handler("klippy:connect",
                                            self._handle_connect)
        self.next_transform = None

    def _handle_connect(self):
        gcode_move = self.printer.lookup_object('gcode_move')
        self.next_transform = gcode_move.set_move_transform(self, force=True)

    def get_position(self):
        return self.calc_untransformed(self.next_transform.get_position())

    def move(self, newpos, speed):
        corrected_pos = self.calc_tranformed(newpos)
        self.next_transform.move(corrected_pos, speed)

    def calc_tranformed(self, pos):
        a = pos[3]
        sin_a = math.sin(a)
        cos_a = math.cos(a)
        a_rot_matrix = [1., 0., 0, 0., cos_a, -sin_a, 0., sin_a, cos_a]
        pos[0] -= self.rot_center_x
        pos[2] -= self.rot_center_z
        m = matrix3x3_mul(matrix3x3_mul(
            a_rot_matrix, self.rot_matrix), matrix3x3_transpose(a_rot_matrix))
        newpos = matrix3x3_apply(pos, m)
        newpos[0] += self.rot_center_x
        newpos[2] += self.rot_center_z
        return newpos

    def calc_untransformed(self, pos):
        a = pos[3]
        sin_a = math.sin(a)
        cos_a = math.cos(a)
        a_rot_matrix = [1., 0., 0, 0., cos_a, -sin_a, 0., sin_a, cos_a]
        pos[0] -= self.rot_center_x
        pos[2] -= self.rot_center_z
        m = matrix3x3_mul(matrix3x3_mul(
            a_rot_matrix, self.rot_matrix), matrix3x3_transpose(a_rot_matrix))
        m = matrix3x3_transpose(m)
        newpos = matrix3x3_apply(pos, m)
        newpos[0] += self.rot_center_x
        newpos[2] += self.rot_center_z
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

    def _calc_b_axis_compensation(self, point_0, point_1):
        b_angle = - \
            math.asin((point_1[2] - point_0[2])/self.calibration_template_size)
        sin_b = math.sin(b_angle)
        cos_b = math.cos(b_angle)
        rot_center_x = point_0[0] + \
            self.calibration_template_size * sin_b
        rot_center_z = point_0[2] - \
            self.calibration_template_size * cos_b
        return b_angle, rot_center_x, rot_center_z

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
            self.point_coords[0], self.point_coords[1])
        enable = gcmd.get_int('ENABLE', 0)
        if enable:
            self._update_compensation(b_angle, rot_center_x, rot_center_z)
        save = gcmd.get_int('SAVE', 0)
        if save:
            self._save_compensation(b_angle, rot_center_x, rot_center_z)

    cmd_CALC_B_AXIS_COMPENSATION_help = "Calculate B axis compensation"

    def cmd_B_AXIS_COMPENSATION_VARS(self, gcmd):
        b_angle = gcmd.get_float('B', self.b_angle)
        rot_center_x = gcmd.get_float('X', self.rot_center_x)
        rot_center_z = gcmd.get_float('Z', self.rot_center_z)
        self._update_compensation(b_angle, rot_center_x, rot_center_z)
        save = gcmd.get_int('SAVE', 0)
        if save:
            self._save_compensation(b_angle, rot_center_x, rot_center_z)

    cmd_B_AXIS_COMPENSATION_VARS_help = "Set B axis compensation parameters directly"


def load_config(config):
    BAxisCompensation(config)
