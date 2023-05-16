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
            [0., 0., 0., 0., 0., 0.],
            [0., 0., 0., 0., 0., 0.],
            [0., 0., 0., 0., 0., 0.]
        ]
        self.wcs = [
            [0., 0., 0.],
            [0., 0., 0.]
        ]
        self.tooling_radius = 0.
        self.probe_backlash_x = 0.
        self.probe_backlash_y = 0.
        self.probe_backlash_y_2 = 0
        self.tooling_radius_2 = 0
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
            'GET_RADIUS_TOOLING', self.cmd_GET_RADIUS_TOOLING,
            desc=self.cmd_GET_RADIUS_TOOLING_help)

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
        z = self.point_coords[0][2] - delta_z
        return x, y, z

    def _calc_wcs_new_sensor(self, thickness, adj, gcmd):
        thickness = thickness / 2.
        x = (self.point_coords[2][0] + self.point_coords[3][0]) / 2.
        y = (self.point_coords[1][1] + self.point_coords[7][1]) / 2.
        z = self.point_coords[0][2]
        return x, y, z

    def _calc_wcs_2_new_sensor(self, thickness, adj, gcmd):
        thickness = thickness / 2.
        len_thickness = 10.
        x = (self.point_coords[8][0] + self.point_coords[9][0]) / 2.
        y = ((self.point_coords[5][1] + self.point_coords[6][1]) / 2.) - thickness
        z = self.point_coords[4][2] - (len_thickness - adj)

        y1 = ((self.point_coords[1][1] + self.point_coords[7][1]) / 2.) - 5
        self.probe_backlash_y_2 = abs(self.point_coords[1][1] - y1)

        x1 = (self.point_coords[2][0] + self.point_coords[3][0]) / 2.
        self.probe_backlash_x = abs(self.point_coords[3][0] - (x1 + 55))

        self.probe_backlash_y = abs(self.point_coords[5][1] - y)

        return x, y, z

    def cmd_GET_RADIUS_TOOLING(self, gcmd):
        save_variables = self.printer.lookup_object('save_variables')
        probe_backlash_x = save_variables.allVariables['probe_backlash_x']
        probe_backlash_y = save_variables.allVariables['probe_backlash_y']
        x1, y1 = self.point_coords[1][0] + probe_backlash_x, self.point_coords[1][1]
        x2, y2 = self.point_coords[0][0], self.point_coords[0][1] + probe_backlash_y
        x3, y3 = self.point_coords[2][0] - probe_backlash_x, self.point_coords[2][1]
        c = (x1-x2)**2 + (y1-y2)**2
        a = (x2-x3)**2 + (y2-y3)**2
        b = (x3-x1)**2 + (y3-y1)**2
        s = 2*(a*b + b*c + c*a) - (a*a + b*b + c*c)
        px = (a*(b+c-a)*x1 + b*(c+a-b)*x2 + c*(a+b-c)*x3) / s
        py = (a*(b+c-a)*y1 + b*(c+a-b)*y2 + c*(a+b-c)*y3) / s
        ar = a**0.5
        br = b**0.5
        cr = c**0.5
        r = ar*br*cr / ((ar+br+cr)*(-ar+br+cr)*(ar-br+cr)*(ar+br-cr))**0.5
        self.tooling_radius = r
        gcmd.respond_info('---------------radius_tooling= %s' % self.tooling_radius)
        self.get_radius_2(gcmd)
        return px, py, r
    cmd_GET_RADIUS_TOOLING_help = "command for get the tooling radius from measuring points."

    def get_radius_2(self, gcmd):
            save_variables = self.printer.lookup_object('save_variables')
            probe_backlash_x = save_variables.allVariables['probe_backlash_x']
            probe_backlash_y_2 = save_variables.allVariables['probe_backlash_y_2']
            x1, y1 = self.point_coords[1][0] + probe_backlash_x, self.point_coords[1][1]
            x2, y2 = self.point_coords[0][0], self.point_coords[0][1] + probe_backlash_y_2
            x3, y3 = self.point_coords[2][0] - probe_backlash_x, self.point_coords[2][1]
            c = (x1-x2)**2 + (y1-y2)**2
            a = (x2-x3)**2 + (y2-y3)**2
            b = (x3-x1)**2 + (y3-y1)**2
            s = 2*(a*b + b*c + c*a) - (a*a + b*b + c*c)
            px = (a*(b+c-a)*x1 + b*(c+a-b)*x2 + c*(a+b-c)*x3) / s
            py = (a*(b+c-a)*y1 + b*(c+a-b)*y2 + c*(a+b-c)*y3) / s
            ar = a**0.5
            br = b**0.5
            cr = c**0.5
            r = ar*br*cr / ((ar+br+cr)*(-ar+br+cr)*(ar-br+cr)*(ar+br-cr))**0.5
            self.tooling_radius_2 = r
            gcmd.respond_info('---------------radius_tooling_2= %s' % self.tooling_radius_2)
            return px, py, r

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
        adjustment_coeff = gcmd.get_float('ADJUSTMENT', .3)
        sensor_version = gcmd.get_int('SENSOR_VERSION', 0)
        if sensor_version:
            x, y, z = self._calc_wcs_new_sensor(thickness, adjustment_coeff, gcmd)
            x2, y2, z2 = self._calc_wcs_2_new_sensor(thickness, adjustment_coeff, gcmd)
            delta_y = y - y2
            delta_z = z - z2
            avg_delta = (delta_y + delta_z) / 2.0
            gcmd.respond_info("D_Y: %.3f, D_Z: %.3f, Avg_D: %.3f" % (delta_y, delta_z, avg_delta))
        else:
            x, y, z = self._calc_wcs_old_sensor(thickness, adjustment_coeff, gcmd)
            x2, y2, z2 = self._calc_wcs_2_old_sensor(thickness, adjustment_coeff, gcmd)
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
            "wcs": self.wcs,
            "probe_backlash_x": self.probe_backlash_x,
            "probe_backlash_y": self.probe_backlash_y,
            "probe_backlash_y_2": self.probe_backlash_y_2,
            'point_coords': self.point_coords,
            'tooling_radius': self.tooling_radius,
            'tooling_radius_2': self.tooling_radius_2
        }

def load_config(config):
    return AutoWcs(config)
