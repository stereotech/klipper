import math
import logging


RAD_TO_DEG = 57.295779513

class AutoWcs:
    def __init__(self, config):
        self.printer = config.get_printer()
        self.center_x = 0.0
        self.center_y = 0.0
        self.point_coords = [
            [0., 0., 0., 0., 0., 0.],
            [0., 0., 0., 0., 0., 0.],
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
        self.probe_backlash_x = 0.
        self.probe_backlash_y = 0.
        self.probe_backlash_y_2 = 0.
        self.tooling_radius = 3.
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
        self.gcode.register_command(
            'CALC_TOOL_RADIUS', self.cmd_CALC_TOOL_RADIUS,
            desc=self.cmd_CALC_TOOL_RADIUS_help)
        self.gcode.register_command(
            'SET_PROBE_BACKLASH', self.cmd_SET_PROBE_BACKLASH,
            desc=self.cmd_SET_PROBE_BACKLASH_help)

    def _calc_wcs_old_sensor(self, thickness, adj, gcmd):
        thickness = thickness / 2.0
        x = (self.point_coords[2][0] + self.point_coords[3][0]) / 2.
        y_probed = (self.point_coords[1][1] + self.point_coords[7][1]) / 2.
        #y = math.tan(math.radians(15)) * (x - self.point_coords[1][0]) + y_probed
        y = (x - self.point_coords[1][0]) + y_probed
        y1 = (self.point_coords[5][1] + self.point_coords[6][1]) / 2. - thickness
        delta_y = y - y1
        delta_z = self.point_coords[0][2] - (self.point_coords[4][2] - (55 - adj))
        avg_delta = (delta_y + delta_z) / 2.0
        gcmd.respond_info("D_Y: %.3f, D_Z: %.3f, Avg_D: %.3f" % (delta_y, delta_z, avg_delta))
        y = y1 + delta_y
        z = self.point_coords[0][2]
        return x, y, z

    def _calc_wcs_2_old_sensor(self, thickness, adj, gcmd):
        thickness = thickness / 2.0
        x = (self.point_coords[2][0] + self.point_coords[3][0]) / 2.
        # probe_backlash = (abs(self.point_coords[2][0] - self.point_coords[3][0]) - 110) / 2
        y = (self.point_coords[5][1] + self.point_coords[6][1]) / 2. - thickness
        #z = self.point_coords[4][2] - 60 # - probe_backlash
        y_probed = (self.point_coords[1][1] + self.point_coords[7][1]) / 2.
        x0 = (self.point_coords[2][0] + self.point_coords[3][0]) / 2.
        #y0 = math.tan(math.radians(15)) * (x0 - self.point_coords[1][0]) + y_probed
        y0 = (x0 - self.point_coords[1][0]) + y_probed
        delta_y = y0 - y
        delta_z = self.point_coords[0][2] - (self.point_coords[4][2] - (55 - adj))
        avg_delta = (delta_y + delta_z) / 2.0
        gcmd.respond_info("D_Y: %.3f, D_Z: %.3f, Avg_D: %.3f" % (delta_y, delta_z, avg_delta))
        z = self.point_coords[4][2] - 10.
        return x, y, z

    def _calc_wcs_new_sensor(self):
        x = (self.point_coords[2][0] + self.point_coords[3][0]) / 2.
        y = (self.point_coords[1][1] + self.point_coords[7][1]) / 2.
        z = self.point_coords[0][2]
        return x, y, z

    def _calc_wcs_2_new_sensor(self, len_thickness):
        thickness = len_thickness / 2.
        x = (self.point_coords[8][0] + self.point_coords[9][0]) / 2.
        y = (self.point_coords[5][1] + self.point_coords[6][1]) / 2. - thickness
        z = self.point_coords[4][2] - 10.
        return x, y, z

    def calculate_probe_backlash(self, x1, y1, y2):
        self.probe_backlash_x = abs(self.point_coords[3][0] - (x1 + 55))
        self.probe_backlash_y = abs(self.point_coords[5][1] - y2)
        self.probe_backlash_y_2 = abs(self.point_coords[1][1] - (y1 - 5))
        logging.info("""Probe backlash is set:\nprobe_backlash_x=%f,
            probe_backlash_y=%f, probe_backlash_y_2=%f""" % (self.probe_backlash_x,
                                                             self.probe_backlash_y,
                                                             self.probe_backlash_y_2))

    def get_radius(self, gcmd):
        probe_backlash_z = 0.9
        # sensor tip radius
        tip_radius = 0.3
        x1, z1 =  self.point_coords[1][0] +  self.probe_backlash_x, \
            (self.point_coords[1][2] + (tip_radius + probe_backlash_z))
        x2, z2 =  self.point_coords[0][0],  self.point_coords[0][2]
        x3, z3 =  self.point_coords[2][0] -  self.probe_backlash_x, \
            (self.point_coords[2][2] + (tip_radius + probe_backlash_z))
        c = (x1 - x2)**2 + (z1 - z2)**2
        a = (x2 - x3)**2 + (z2 - z3)**2
        b = (x3 - x1)**2 + (z3 - z1)**2
        ar = a**0.5
        br = b**0.5
        cr = c**0.5
        radius = ar*br*cr / ((ar + br + cr)*(-ar + br + cr) * (ar - br + cr) * (ar + br - cr))**0.5
        gcmd.respond_info('radius_tooling= %s' % radius)
        return radius

    cmd_CALC_TOOL_RADIUS_help = "command for get the tooling radius from measuring points."
    def cmd_CALC_TOOL_RADIUS(self, gcmd):
        self.tooling_radius = self.get_radius(gcmd)
        gcmd.respond_info('radius_tooling= %s' % self.tooling_radius)
        return self.tooling_radius

    cmd_SAVE_WCS_CALC_POINT_help = "Save point for WCS calculation"
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
                    "2045: auto_wcs: improperly formatted entry for "
                    "point \n%s" % (gcmd.get_commandline()))
            for axis, coord in enumerate(coords):
                self.point_coords[point_idx][axis] = coord

    cmd_CALC_WCS_PARAMS_help = "Perform WCS calculation"
    def cmd_CALC_WCS_PARAMS(self, gcmd):
        #todo: get thickness default 10
        sensor_version = gcmd.get_int('SENSOR_VERSION', 0)
        thickness =  gcmd.get_float('THICKNESS', 10.)
        if sensor_version:
            x, y, z = self._calc_wcs_new_sensor()
            x2, y2, z2 = self._calc_wcs_2_new_sensor(thickness)
            self.calculate_probe_backlash(x, y, y2)
            delta_y = y - y2
            delta_z = z - z2
            avg_delta = (delta_y + delta_z) / 2.0
            gcmd.respond_info("D_Y: %.3f, D_Z: %.3f, Avg_D: %.3f" % (delta_y, delta_z, avg_delta))
        else:
            adjustment_coeff = gcmd.get_float('ADJUSTMENT', .3)
            x, y, z = self._calc_wcs_old_sensor(thickness, adjustment_coeff, gcmd)
            x2, y2, z2 = self._calc_wcs_2_old_sensor(thickness, adjustment_coeff, gcmd)
        out = "Calculated WCS 1 center: X:%.6f, Y:%.6f, Z:%.6f\n" % (
            x, y, z)
        out += "Calculated WCS 2 center: X:%.6f, Y:%.6f, Z:%.6f\n" % (
            x2, y2, z2)
        self.wcs[0] = [x, y, z]
        self.wcs[1] = [x2, y2, z2]
        gcmd.respond_info(out)

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
                    "2047: auto_wcs: improperly formatted entry for "
                    "point \n%s" % (gcmd.get_commandline()))
            for axis, coord in enumerate(coords):
                self.wcs[point_idx][axis] = coord

    cmd_SET_PROBE_BACKLASH_help = "Set the sensor backlash for the current sensor."
    def cmd_SET_PROBE_BACKLASH(self, gcmd):
        self.probe_backlash_x = gcmd.get_float('BACKLASH_X', self.probe_backlash_x)
        self.probe_backlash_y = gcmd.get_float('BACKLASH_Y', self.probe_backlash_y)
        self.probe_backlash_y_2 = gcmd.get_float('BACKLASH_Y_2', self.probe_backlash_y_2)
        gcmd.respond_info(
            'Probe backlash is set:\nprobe_backlash_x=%f, probe_backlash_y=%f, probe_backlash_y_2=%f' % (
                self.probe_backlash_x, self.probe_backlash_y, self.probe_backlash_y_2)
            )

    def get_status(self, eventtime=None):
        return {
            "points": self.point_coords,
            "wcs": self.wcs,
            "probe_backlash_x": self.probe_backlash_x,
            "probe_backlash_y": self.probe_backlash_y,
            "probe_backlash_y_2": self.probe_backlash_y_2,
            'tooling_radius': self.tooling_radius
        }


def load_config(config):
    return AutoWcs(config)
