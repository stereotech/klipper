# Helper script to automate a axis offset calculation

import math
import logging


RAD_TO_DEG = 57.295779513


class CAxisAlignCalculation:
    def __init__(self, config):
        self.printer = config.get_printer()
        self.gcode_move = self.printer.load_object(config, 'gcode_move')
        self.gcode = self.printer.lookup_object('gcode')
        self.max_repeat_probe = config.getint('max_repeat_probe', 5)
        self.threshold_value = config.getfloat('threshold_value', 0.02)
        self.point_coords = [
            [0., 0., 0., 0., 0., 0.],
            [0., 0., 0., 0., 0., 0.]
        ]
        self.gcode.register_command(
            'ALIGN_C_AXIS', self.cmd_ALIGN_C_AXIS,
            desc=self.cmd_ALIGN_C_AXIS_help)
        self.gcode.register_command(
            'SAVE_C_AXIS_POINT', self.cmd_SAVE_C_AXIS_POINT,
            desc=self.cmd_SAVE_C_AXIS_POINT_help)

    cmd_SAVE_C_AXIS_POINT_help = "Save point for C axis align"

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
                    "2032: c_axis_align: improperly formatted entry for "
                    "point \n%s" % (gcmd.get_commandline()))
            for axis, coord in enumerate(coords):
                self.point_coords[point_idx][axis] = coord

    cmd_ALIGN_C_AXIS_help = "Calculate and apply correction for align the C axis"

    def cmd_ALIGN_C_AXIS(self, gcmd):
        for i in range(self.max_repeat_probe):
            self.gcode.run_script_from_command("MOVE_ALIGN_C_AXIS")
            offset = self._calc_c_axis_align(
                self.point_coords[0], self.point_coords[1])
            if (self.threshold_value * -1) <= offset <= self.threshold_value:
                logging.info("align the axis C completed")
                break
            else:
                self._apply_offset_c(offset)

    def _calc_c_axis_align(self, point_0, point_1):
        offset = math.atan((point_1[1] - point_0[1]) / 90) * RAD_TO_DEG / 3
        logging.info("calculate offset for the axis C: %f." % offset)
        return offset

    def _apply_offset_c(self, offset):
        logging.info("an offset has been applied to correct the C axis")
        align_gcmd = self.gcode.create_gcode_command(
            'G0', 'G0', {'C': offset})
        self.gcode_move.cmd_G1(align_gcmd)
        self.gcode_move.cmd_G92(self.gcode.create_gcode_command(
            'G92', 'G92', {'C': 0}))


def load_config(config):
    CAxisAlignCalculation(config)
