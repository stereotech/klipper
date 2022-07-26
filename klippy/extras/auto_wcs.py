import math

RAD_TO_DEG = 57.295779513

class AutoWcs:
    def __init__(self, config):
        self.printer = config.get_printer()
        self.center_x = 0.0
        self.center_y = 0.0
        self.radius = 0.0
        self.point_coords = [
            [0., 0., 0., 0., 0., 0.],
            [0., 0., 0., 0., 0., 0.],
            [0., 0., 0., 0., 0., 0.],
            [0., 0., 0., 0., 0., 0.],
            [0., 0., 0., 0., 0., 0.],
            [0., 0., 0., 0., 0., 0.]
        ]
        self.wcs = [
            [0., 0., 0.],
            [0., 0., 0.]
        ]
        self.adjust_angle = 10 / RAD_TO_DEG
        self.gcode = self.printer.lookup_object('gcode')
        self.gcode.register_command(
            'SAVE_WCS_CALC_POINT', self.cmd_SAVE_WCS_CALC_POINT,
            desc=self.cmd_SAVE_WCS_CALC_POINT_help)
        self.gcode.register_command(
            'CALC_WCS_PARAMS', self.cmd_CALC_WCS_PARAMS,
            desc=self.cmd_CALC_WCS_PARAMS_help)
        self.gcode.register_command(
            'SET_AUTO_WCS', self.cmd_SET_AUTO_WCS,
            desc=self.cmd_CALC_WCS_PARAMS_help)

    def _calc_circle(self):
        x0 = self.point_coords[0][0]
        y0 = self.point_coords[0][1]
        x1 = self.point_coords[1][0]
        y1 = self.point_coords[1][1]
        x2 = self.point_coords[2][0]
        y2 = self.point_coords[2][1]
        a = x1 - x0
        b = y1 - y0
        c = x2 - x0
        d = y2 - y0
        e = a * (x0 + x1) + b * (y0 + y1)
        f = c * (x0 + x2) + d * (y0 + y2)
        g = 2 * (a * (y2 - y1) - b * (x2 - x1))
        if g == 0.0:
            return
        self.center_x = (d * e - b * f) / g
        self.center_y = (a * f - c * e) / g
        self.radius =  math.hypot(x0 - self.center_x, y0 - self.center_y)

    def _calc_wcs(self):
        probe_backlash = (abs(self.point_coords[2][0] - self.point_coords[3][0]) - 110) / 2
        x = (self.point_coords[2][0] + self.point_coords[3][0]) / 2
        y = self.point_coords[1][1] + 10 + probe_backlash
        z = self.point_coords[0][2]
        return x, y, z

    def _calc_wcs_2(self):
        x = (self.point_coords[2][0] + self.point_coords[3][0]) / 2
        probe_backlash = (abs(self.point_coords[2][0] - self.point_coords[3][0]) - 110) / 2
        y = self.point_coords[5][1] + probe_backlash
        z = self.point_coords[4][2] - 60 # - probe_backlash
        return x, y, z

    def cmd_SAVE_WCS_CALC_POINT(self, gcmd):
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
                    "auto_wcs: improperly formatted entry for "
                    "point\n%s" % (gcmd.get_commandline()))
            for axis, coord in enumerate(coords):
                self.point_coords[point_idx][axis] = coord

    cmd_SAVE_WCS_CALC_POINT_help = "Save point for WCS calculation"


    def cmd_CALC_WCS_PARAMS(self, gcmd):
        x, y, z = self._calc_wcs()
        x2, y2, z2 = self._calc_wcs_2()
        out = "Calculated WCS 1 center: X:%.6f, Y:%.6f, Z:%.6f\n" % (
            x, y, z)
        out += "Calculated WCS 2 center: X:%.6f, Y:%.6f, Z:%.6f\n" % (
            x2, y2, z2)
        self.wcs[0] = [x, y, z]
        self.wcs[1] = [x2, y2, z2]
        gcmd.respond_info(out)

    cmd_CALC_WCS_PARAMS_help = "Perform WCS calculation"

    def cmd_SET_AUTO_WCS(self, gcmd):
        point_idx = gcmd.get_int('WCS', 0)
        coords = gcmd.get('COORDS', None)
        if coords is not None:
            try:
                coords = coords.strip().split(",", 2)
                coords = [float(l.strip()) for l in coords]
                if len(coords) != 3:
                    raise Exception
            except Exception:
                raise gcmd.error(
                    "auto_wcs: improperly formatted entry for "
                    "point\n%s" % (gcmd.get_commandline()))
            for axis, coord in enumerate(coords):
                self.wcs[point_idx][axis] = coord

    cmd_CALC_WCS_PARAMS_help = "Perform WCS calculation"

    def get_status(self, eventtime=None):
        return {
            "wcs": self.wcs
        }

def load_config(config):
    return AutoWcs(config)
