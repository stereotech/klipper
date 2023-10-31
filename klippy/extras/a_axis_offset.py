# Helper script to automate a axis offset calculation

import math

RAD_TO_DEG = 57.295779513


class AAxisOffsetCalculation:
    def __init__(self, config):
        self.printer = config.get_printer()
        self.gcode_move = self.printer.load_object(config, 'gcode_move')
        self.gcode = self.printer.lookup_object('gcode')
        self.point_coords = [
            [0., 0., 0., 0., 0., 0.],
            [0., 0., 0., 0., 0., 0.],
            [0., 0., 0., 0., 0., 0.],
            [0., 0., 0., 0., 0., 0.]
        ]
        self.gcode.register_command('CALC_A_AXIS_OFFSET',
                                    self.cmd_CALC_A_AXIS_OFFSET,
                                    desc=self.cmd_CALC_A_AXIS_OFFSET_help)
        self.gcode.register_command(
            'SAVE_A_AXIS_POINT', self.cmd_SAVE_A_AXIS_POINT,
            desc=self.cmd_SAVE_A_AXIS_POINT_help)

    cmd_SAVE_A_AXIS_POINT_help = "Save point for A axis offset"
    def cmd_SAVE_A_AXIS_POINT(self, gcmd):
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
                    "2046: a_axis_offset: improperly formatted entry for "
                    "point \n%s" % (gcmd.get_commandline()))
            for axis, coord in enumerate(coords):
                self.point_coords[point_idx][axis] = coord

    def _calc_a_axis_offset(self, point_0, point_1):
        offset = RAD_TO_DEG * math.asin((point_1[2] - point_0[2]) / math.hypot(
            point_1[1] - point_0[1], point_1[2] - point_0[2]))
        return offset

    cmd_CALC_A_AXIS_OFFSET_help = "Calculate A axis offset"
    def cmd_CALC_A_AXIS_OFFSET(self, gcmd):
        offset = self._calc_a_axis_offset(
            self.point_coords[0], self.point_coords[1])
        homing_origin_a = self.gcode_move.get_status()['homing_origin'].a
        if homing_origin_a + offset > 0.0:
            offset = 0.0
        offset_gcmd = self.gcode.create_gcode_command(
            'SET_GCODE_OFFSET', 'SET_GCODE_OFFSET', {'A_ADJUST': offset})
        self.gcode_move.cmd_SET_GCODE_OFFSET(offset_gcmd)
        gcmd.respond_info("calculate offset for the axis A: %f." % offset)

    # cmd_CALC_A_AXIS_OFFSET_TOOL_help = "Calculate A axis offset by tool"
    # def cmd_CALC_A_AXIS_OFFSET_TOOL(self, gcmd):
    #     # get average value axis Z
    #     self.point_coords[0][2] = (self.point_coords[0][2] + self.point_coords[2][2]) / 2.
    #     self.point_coords[1][2] = (self.point_coords[1][2] + self.point_coords[3][2]) / 2.
    #     # calculate offset
    #     offset = self._calc_a_axis_offset(
    #         self.point_coords[0], self.point_coords[1])
    #     homing_origin_a = self.gcode_move.get_status()['homing_origin'].a
    #     if homing_origin_a + offset > 0.0:
    #         offset = 0.0
    #     offset_gcmd = self.gcode.create_gcode_command(
    #         'SET_GCODE_OFFSET', 'SET_GCODE_OFFSET', {'A_ADJUST': offset})
    #     self.gcode_move.cmd_SET_GCODE_OFFSET(offset_gcmd)
    #     gcmd.respond_info("calculate offset for the axis A: %f." % offset)


def load_config(config):
    return AAxisOffsetCalculation(config)
