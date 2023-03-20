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

    def _calc_wcs(self, thickness, adj, gcmd):
        thickness = thickness / 2.0
        x = (self.point_coords[2][0] + self.point_coords[3][0]) / 2
        y_probed = (self.point_coords[1][1] + self.point_coords[7][1]) / 2
        #y = math.tan(math.radians(15)) * (x - self.point_coords[1][0]) + y_probed
        y = (x - self.point_coords[1][0]) + y_probed
        y1 = (self.point_coords[5][1] + self.point_coords[6][1]) / 2 - thickness
        delta_y = y - y1
        delta_z = self.point_coords[0][2] - (self.point_coords[4][2] - (10 - adj))
        avg_delta = (delta_y + delta_z) / 2.0
        gcmd.respond_info("D_Y: %.3f, D_Z: %.3f, Avg_D: %.3f" % (delta_y, delta_z, avg_delta))
        y = y1 + delta_y
        z = self.point_coords[0][2]
        return x, y, z

    def _calc_wcs_2(self, thickness, adj, gcmd):
        thickness = thickness / 2.0
        x = (self.point_coords[2][0] + self.point_coords[3][0]) / 2
        # probe_backlash = (abs(self.point_coords[2][0] - self.point_coords[3][0]) - 110) / 2
        y = (self.point_coords[5][1] + self.point_coords[6][1]) / 2 - thickness
        #z = self.point_coords[4][2] - 60 # - probe_backlash
        y_probed = (self.point_coords[1][1] + self.point_coords[7][1]) / 2
        x0 = (self.point_coords[2][0] + self.point_coords[3][0]) / 2
        #y0 = math.tan(math.radians(15)) * (x0 - self.point_coords[1][0]) + y_probed
        y0 = (x0 - self.point_coords[1][0]) + y_probed
        delta_y = y0 - y
        delta_z = self.point_coords[0][2] - (self.point_coords[4][2] - (10 - adj))
        avg_delta = (delta_y + delta_z) / 2.0
        gcmd.respond_info("D_Y: %.3f, D_Z: %.3f, Avg_D: %.3f" % (delta_y, delta_z, avg_delta))
        z = self.point_coords[0][2] - delta_z
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
        #todo: get thickness default 10
        thickness =  gcmd.get_float('THICKNESS', 10.)
        adjustment_coeff = gcmd.get_float('ADJUSTMENT', .2)
        x, y, z = self._calc_wcs(thickness, adjustment_coeff, gcmd)
        x2, y2, z2 = self._calc_wcs_2(thickness, adjustment_coeff, gcmd)
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
