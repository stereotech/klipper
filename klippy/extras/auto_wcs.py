import math


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
        self.tooling_radius_1 = 0.
        self.tooling_radius_2 = 0.
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
        self.gcode.register_command(
            'SET_PROBE_BACKLASH', self.cmd_SET_PROBE_BACKLASH,
            desc=self.cmd_SET_PROBE_BACKLASH_help)
        self.gcode.register_command(
            'CALC_WCS_TOOL', self.cmd_CALC_WCS_TOOL,
            desc=self.cmd_CALC_WCS_TOOL_help)

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
        y = (self.point_coords[5][1] + self.point_coords[6][1]) / 2. - thickness
        z = self.point_coords[4][2] - (len_thickness - adj)
        return x, y, z

    def calculate_probe_backlash(self, x1, y1, y2):
        self.probe_backlash_x = abs(self.point_coords[3][0] - (x1 + 55))
        self.probe_backlash_y = abs(self.point_coords[5][1] - y2)
        self.probe_backlash_y_2 = abs(self.point_coords[1][1] - (y1 - 5))

    def get_radius(self, gcmd):
        # calculate radius only whis probe_backlash_y
        x1, y1 = self.point_coords[1][0] + self.probe_backlash_y, self.point_coords[1][1]
        x2, y2 = self.point_coords[0][0], self.point_coords[0][1] + self.probe_backlash_y
        x3, y3 = self.point_coords[2][0] - self.probe_backlash_y, self.point_coords[2][1]
        c = (x1-x2)**2 + (y1-y2)**2
        a = (x2-x3)**2 + (y2-y3)**2
        b = (x3-x1)**2 + (y3-y1)**2
        s= 2*(a*b + b*c + c*a) - (a*a + b*b + c*c)
        centr_x = (a*(b+c-a)*x1 + b*(c+a-b)*x2 + c*(a+b-c)*x3) / s
        centr_y = (a*(b+c-a)*y1 + b*(c+a-b)*y2 + c*(a+b-c)*y3) / s
        ar = a**0.5
        br = b**0.5
        cr = c**0.5
        radius = ar*br*cr / ((ar+br+cr)*(-ar+br+cr)*(ar-br+cr)*(ar+br-cr))**0.5
        gcmd.respond_info('radius_tooling= %s,(only backlash_y) centr_tool(%s;%s)' % (
                radius, centr_x, centr_y))
        return radius

    def get_radius_1(self, gcmd):
        # calculate radius whis probe_backlash_y and probe_backlash_x
        x1, y1 = self.point_coords[1][0] + self.probe_backlash_x, self.point_coords[1][1]
        x2, y2 = self.point_coords[0][0], self.point_coords[0][1] + self.probe_backlash_y
        x3, y3 = self.point_coords[2][0] - self.probe_backlash_x, self.point_coords[2][1]
        c = (x1-x2)**2 + (y1-y2)**2
        a = (x2-x3)**2 + (y2-y3)**2
        b = (x3-x1)**2 + (y3-y1)**2
        s = 2*(a*b + b*c + c*a) - (a*a + b*b + c*c)
        px = (a*(b+c-a)*x1 + b*(c+a-b)*x2 + c*(a+b-c)*x3) / s
        py = (a*(b+c-a)*y1 + b*(c+a-b)*y2 + c*(a+b-c)*y3) / s
        ar = a**0.5
        br = b**0.5
        cr = c**0.5
        radius = ar*br*cr / ((ar+br+cr)*(-ar+br+cr)*(ar-br+cr)*(ar+br-cr))**0.5
        gcmd.respond_info('radius_tooling_1= %s,(backlash_y and X) centr_tool(%s;%s)' % (
            radius, px, py))
        return radius

    def get_radius_2(self, gcmd):
        # calculate radius whis probe_backlash_y_2 and probe_backlash_x
        x1, y1 = self.point_coords[1][0] + self.probe_backlash_x, self.point_coords[1][1]
        x2, y2 = self.point_coords[0][0], self.point_coords[0][1] + self.probe_backlash_y_2
        x3, y3 = self.point_coords[2][0] - self.probe_backlash_x, self.point_coords[2][1]
        c = (x1-x2)**2 + (y1-y2)**2
        a = (x2-x3)**2 + (y2-y3)**2
        b = (x3-x1)**2 + (y3-y1)**2
        s = 2*(a*b + b*c + c*a) - (a*a + b*b + c*c)
        px = (a*(b+c-a)*x1 + b*(c+a-b)*x2 + c*(a+b-c)*x3) / s
        py = (a*(b+c-a)*y1 + b*(c+a-b)*y2 + c*(a+b-c)*y3) / s
        ar = a**0.5
        br = b**0.5
        cr = c**0.5
        radius = ar*br*cr / ((ar+br+cr)*(-ar+br+cr)*(ar-br+cr)*(ar+br-cr))**0.5
        gcmd.respond_info('radius_tooling_2= %s,(backlash_y_2 and X) centr_tool(%s;%s)' % (
            radius, px, py))
        return radius

    cmd_CALC_WCS_TOOL_help = "command for calculate wcs coordinate for SPIRALL-FULL."
    def cmd_CALC_WCS_TOOL(self, gcmd):
        wcs =  gcmd.get_int('WCS')
        ind_axis = gcmd.get_int('AXIS')
        new_axis = (self.point_coords[0][ind_axis] + self.point_coords[1][ind_axis]) / 2.
        gcode_move = self.printer.lookup_object('gcode_move')
        old_axis = gcode_move.wcs_offsets[wcs][ind_axis]
        diff_axis = new_axis - old_axis
        self.wcs[wcs - 1][ind_axis] = new_axis
        gcmd.respond_info("""calculated wcs_%d_%d=%f,
            difference between tool and template=%f.""" % (wcs, ind_axis, new_axis, diff_axis))
        return new_axis

    cmd_GET_RADIUS_TOOLING_help = "command for get the tooling radius from measuring points."
    def cmd_GET_RADIUS_TOOLING(self, gcmd):
        advance =  gcmd.get_int('ADVANCE', 0)
        if not advance:
            self.tooling_radius = self.get_radius(gcmd)
            self.tooling_radius_1 = self.get_radius_1(gcmd)
            self.tooling_radius_2 = self.get_radius_2(gcmd)
        else:
            # if needed calculate advance radius
            gcode_move = self.printer.lookup_object('gcode_move')
            y2 = self.point_coords[0][1] + self.probe_backlash_y
            self.tooling_radius = gcode_move.wcs_offsets[1][1] - y2
            gcmd.respond_info('advance radius_tooling= %s' % self.tooling_radius)
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
                    "auto_wcs: improperly formatted entry for "
                    "point\n%s" % (gcmd.get_commandline()))
            for axis, coord in enumerate(coords):
                self.point_coords[point_idx][axis] = coord

    cmd_CALC_WCS_PARAMS_help = "Perform WCS calculation"
    def cmd_CALC_WCS_PARAMS(self, gcmd):
        #todo: get thickness default 10
        thickness =  gcmd.get_float('THICKNESS', 10.)
        adjustment_coeff = gcmd.get_float('ADJUSTMENT', .3)
        sensor_version = gcmd.get_int('SENSOR_VERSION', 0)
        if sensor_version:
            x, y, z = self._calc_wcs_new_sensor(thickness, adjustment_coeff, gcmd)
            x2, y2, z2 = self._calc_wcs_2_new_sensor(thickness, adjustment_coeff, gcmd)
            self.calculate_probe_backlash(x, y, y2)
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
            "wcs": self.wcs,
            "probe_backlash_x": self.probe_backlash_x,
            "probe_backlash_y": self.probe_backlash_y,
            "probe_backlash_y_2": self.probe_backlash_y_2,
            'tooling_radius': self.tooling_radius,
            'tooling_radius_1': self.tooling_radius_1,
            'tooling_radius_2': self.tooling_radius_2,
            'self.point_coords': self.point_coords
        }


def load_config(config):
    return AutoWcs(config)
