# Helper script to automate a axis offset calculation

import math

RAD_TO_DEG = 57.295779513


class CAxisAlignCalculation:
    def __init__(self, config):
        self.printer = config.get_printer()
        self.gcode_move = self.printer.load_object(config, 'gcode_move')
        self.gcode = self.printer.lookup_object('gcode')
        self.point_coords = [
            [0., 0., 0., 0., 0., 0.],
            [0., 0., 0., 0., 0., 0.]
        ]
        self.gcode.register_command('CALC_C_AXIS_ALIGN',
                                    self.cmd_CALC_C_AXIS_ALIGN,
                                    desc=self.cmd_CALC_C_AXIS_ALIGN_help)
        self.gcode.register_command(
            'SAVE_C_AXIS_POINT', self.cmd_SAVE_C_AXIS_POINT,
            desc=self.cmd_SAVE_C_AXIS_POINT_help)

    def cmd_SAVE_C_AXIS_POINT(self, gcmd):
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
                    "2032: a_axis_offset: improperly formatted entry for "
                    "point\n%s" % (gcmd.get_commandline()))
            for axis, coord in enumerate(coords):
                self.point_coords[point_idx][axis] = coord

    cmd_SAVE_C_AXIS_POINT_help = "Save point for C axis align"

    def _calc_c_axis_align(self, point_0, point_1):
        offset = math.atan((point_1[1] - point_0[1]) / 90) * RAD_TO_DEG / 3
        return offset

    def cmd_CALC_C_AXIS_ALIGN(self, gcmd):
        offset = self._calc_c_axis_align(
            self.point_coords[0], self.point_coords[1])
        align_gcmd = self.gcode.create_gcode_command(
            'G0', 'G0', {'C': offset})
        self.gcode_move.cmd_G1(align_gcmd)
        self.gcode_move.cmd_G92(self.gcode.create_gcode_command(
            'G92', 'G92', {'C': 0}))

    cmd_CALC_C_AXIS_ALIGN_help = "Calculate C axis align"


def load_config(config):
    CAxisAlignCalculation(config)
