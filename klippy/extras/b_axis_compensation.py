# B axis compensation correction

import math

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
            'B_AXIS_COMPENSATION_PROFILE', self.cmd_B_AXIS_COMPENSATION_PROFILE,
            desc=self.cmd_B_AXIS_COMPENSATION_PROFILE_help
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
        return pos

    def calc_untransformed(self, pos):
        return pos

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
        configfile = self.printer.lookup_object('configfile')
        configfile.set('b_axis_compensation', 'b_angle', self.b_angle)
        configfile.set('b_axis_compensation',
                       'rot_center_x', self.rot_center_x)
        configfile.set('b_axis_compensation',
                       'rot_center_z', self.rot_center_z)

    def _update_compensation(self, b_angle, rot_center_x, rot_center_z):
        self.b_angle = b_angle
        self.rot_center_x = rot_center_x
        self.rot_center_z = rot_center_z
        gcode_move = self.printer.lookup_object('gcode_move')
        gcode_move.reset_last_position()

    def cmd_CALC_B_AXIS_COMPENSATION(self, gcmd):
        self._calc_b_axis_compensation(
            self.point_coords[0], self.point_coords[1])
        enable = gcmd.get_int('ENABLE', 0)
        if enable:
            # TODO: enable comp

    cmd_CALC_B_AXIS_COMPENSATION_help = "Calculate B axis compensation"


def load_config(config):
    BAxisCompensation(config)
