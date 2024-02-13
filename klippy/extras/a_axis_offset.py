# Helper script to automate a axis offset calculation

import math
import logging


RAD_TO_DEG = 57.295779513


class AAxisOffsetCalculation:
    def __init__(self, config):
        self.printer = config.get_printer()
        self.gcode_move = self.printer.load_object(config, 'gcode_move')
        self.gcode = self.printer.lookup_object('gcode')
        self.calc_offset = 0.
        self.max_repeat_probe = config.getint('max_repeat_probe', 5)
        self.threshold_value = config.getfloat('threshold_value', 0.02)
        self.point_coords = [
            [0., 0., 0., 0., 0., 0.],
            [0., 0., 0., 0., 0., 0.],
            [0., 0., 0., 0., 0., 0.],
            [0., 0., 0., 0., 0., 0.]
        ]
        self.gcode.register_command(
            'CALCULATE_ALIGN_A_AXIS', self.cmd_CALCULATE_ALIGN_A_AXIS,
            desc=self.cmd_CALCULATE_ALIGN_A_AXIS_help)
        self.gcode.register_command(
            'SAVE_A_AXIS_POINT', self.cmd_SAVE_A_AXIS_POINT,
            desc=self.cmd_SAVE_A_AXIS_POINT_help)
        self.gcode.register_command(
            'APPLY_ALIGN_A_AXIS', self.cmd_APPLY_ALIGN_A_AXIS,
            desc=self.cmd_APPLY_ALIGN_A_AXIS_help)

    def _calc_a_axis_offset(self):
        """
                  . b
               .  .
             .    .
         a  . . . . c
        """
        bc = self.point_coords[1][2] - self.point_coords[0][2]
        ac = self.point_coords[1][1] - self.point_coords[0][1]
        ab =  math.hypot(ac, bc)
        asin_a =  math.asin(bc / ab)
        self.calc_offset = RAD_TO_DEG * asin_a
        logging.info("calculate offset for the axis A: %f." % self.calc_offset)

    def _apply_offset_a(self):
        homing_origin_a = self.gcode_move.get_status()['homing_origin'].a
        if (homing_origin_a + self.calc_offset) > 0.0:
            logging.warning("A-axis offset is positive")
            self.calc_offset = 0.0
        offset_gcmd = self.gcode.create_gcode_command(
            'SET_GCODE_OFFSET', 'SET_GCODE_OFFSET', {'A_ADJUST': self.calc_offset})
        self.gcode_move.cmd_SET_GCODE_OFFSET(offset_gcmd)

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

    cmd_CALCULATE_ALIGN_A_AXIS_help = "Calculate A axis offset"
    def cmd_CALCULATE_ALIGN_A_AXIS(self, gcmd):
        self._calc_a_axis_offset()

    cmd_APPLY_ALIGN_A_AXIS_help = "Apply calculated offsets for A-axis"
    def cmd_APPLY_ALIGN_A_AXIS(self, gcmd):
        self._apply_offset_a()

    def get_status(self, eventtime=None):
        return {
            "calc_offset": self.calc_offset,
            "max_repeat_probe": self.max_repeat_probe,
            "threshold_value": self.threshold_value
        }


def load_config(config):
    return AAxisOffsetCalculation(config)
