# Printer Skew Correction
#
# This implementation is a port of Marlin's skew correction as
# implemented in planner.h, Copyright (C) Marlin Firmware
#
# https://github.com/MarlinFirmware/Marlin/tree/1.1.x/Marlin
#
# Copyright (C) 2019  Eric Callahan <arksine.code@gmail.com>
#
# This file may be distributed under the terms of the GNU GPLv3 license.

import math
import collections


def calc_skew_factor(ac, bd, ad):
    side = math.sqrt(2*ac*ac + 2*bd*bd - 4*ad*ad) / 2.
    return math.tan(math.pi/2 - math.acos((
            (ac*ac - side*side - ad*ad) / (2*side*ad))))

def length_side(x1, y1, x2, y2):
    return math.sqrt((x2 - x1)**2 + (y2 - y1)**2)

def get_point(first, second):
    return [(first[0] + second[0]) / 2.,
            (first[1] + second[1]) / 2.,
            (first[2] + second[2]) / 2.,
            0,
            0
        ]

# Constrain value between min and max
def constrain(val, min_val, max_val):
    return min(max_val, max(min_val, val))


class PrinterSkew:
    def __init__(self, config):
        self.printer = config.get_printer()
        self.gcode_move = self.printer.lookup_object('gcode_move')
        self.name = config.get_name()
        self.enabled = False
        self.xy_factor = 0.
        self.xz_factor = 0.
        self.yz_factor = 0.
        self.apply_skew = False
        self.current_profile = None
        self.skew_profiles = {}
        # Fetch stored profiles from Config
        self._load_storage(config)
        self.printer.register_event_handler("klippy:ready",
                                            self._handle_ready)
        self.printer.register_event_handler("gcode_move:change_wcs_lists",
                                            self._change_wcs_lists)
        # self.printer.register_event_handler("gcode_move:change_current_wcs",
        #                                     self._change_current_wcs)
        gcode = self.printer.lookup_object('gcode')
        gcode.register_command('GET_CURRENT_SKEW', self.cmd_GET_CURRENT_SKEW,
                               desc=self.cmd_GET_CURRENT_SKEW_help)
        gcode.register_command('CALC_MEASURED_SKEW',
                               self.cmd_CALC_MEASURED_SKEW,
                               desc=self.cmd_CALC_MEASURED_SKEW_help)
        gcode.register_command('SET_SKEW', self.cmd_SET_SKEW,
                               desc=self.cmd_SET_SKEW_help)
        gcode.register_command('SKEW_PROFILE', self.cmd_SKEW_PROFILE,
                               desc=self.cmd_SKEW_PROFILE_help)
        gcode.register_command('SAVE_SKEW_POINT',
                               self.cmd_SAVE_SKEW_POINT,
                               desc=self.cmd_SAVE_SKEW_POINT_help)
        gcode.register_command('CALC_SKEW_COMPENSATION',
                                self.cmd_CALC_SKEW_COMPENSATION,
                                desc=self.cmd_CALC_SKEW_COMPENSATION_help)
        gcode.register_command('CALC_SKEW_COMPENSATION_WCS',
                                self.cmd_CALC_SKEW_COMPENSATION_WCS,
                                desc=self.cmd_CALC_SKEW_COMPENSATION_WCS_help)
        self.point_coords = [
            [0., 0., 0.],
            [0., 0., 0.],
            [0., 0., 0.],
            [0., 0., 0.]
        ]
        self.wcs_list = [
            [0., 0., 0.],
            [0., 0., 0.],
            [0., 0., 0.],
            [0., 0., 0.],
            [0., 0., 0.]
        ]
        self.next_transform = None


    def _handle_ready(self):
        kin = self.printer.lookup_object('toolhead').get_kinematics()
        self.axes_min = kin.axes_min
        self.axes_max = kin.axes_max
        self.wcs_list = list(self.gcode_move.wcs_offsets)
        # Register transform
        self.next_transform = self.gcode_move.set_move_transform(self, force=True)

    def _change_wcs_lists(self):
        self.wcs_list = list(self.gcode_move.wcs_offsets)

    # def _change_current_wcs(self):
    #     """for get curently index wcs_list whitch needed
    #      for calculation skew corection."""
    #     self.current_wcs = self.gcode_move.current_wcs

    def cmd_SAVE_SKEW_POINT(self, gcmd):
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
                    "skew_corection: improperly formatted entry for "
                    "point\n%s" % (gcmd.get_commandline()))
            for axis, coord in enumerate(coords):
                self.point_coords[point_idx][axis] = coord
    cmd_SAVE_SKEW_POINT_help = "Save point for align skew"

    def cmd_CALC_MEASURED_SKEW(self, gcmd):
        ac = gcmd.get_float("AC", above=0.)
        bd = gcmd.get_float("BD", above=0.)
        ad = gcmd.get_float("AD", above=0.)
        factor = calc_skew_factor(ac, bd, ad)
        gcmd.respond_info("Calculated Skew: %.6f radians, %.2f degrees"
                          % (factor, math.degrees(factor)))
    cmd_CALC_MEASURED_SKEW_help = "Calculate skew from measured print"

    def cmd_CALC_SKEW_COMPENSATION(self, gcmd):
        """
        b_______c
        |       |
        a_______d
        """
        factors = ['XY', 'XZ', 'YZ']
        factor_name = gcmd.get('FACTOR').upper()
        msg = gcmd.get('MSG', '')
        if factor_name in factors:
            if factor_name == factors[0]:
                # xy_factor
                a_point = get_point(self.point_coords[2], self.point_coords[3])
                d_point = list(a_point)
                d_point[0] = d_point[0] + 50.
                b_point = get_point(self.point_coords[0], self.point_coords[1])
                c_point = list(b_point)
                c_point[0] = c_point[0] + 50.
                diff_points = b_point[0] - a_point[0]
                bc = length_side(b_point[0], b_point[1], c_point[0], c_point[1])
                bd = length_side(b_point[0], b_point[1], d_point[0], d_point[1])
                ac = length_side(a_point[0], a_point[1], c_point[0], c_point[1])
            elif factor_name == factors[1]:
                # xz_factor
                a_point = get_point(self.point_coords[2], self.point_coords[3])
                d_point = list(a_point)
                d_point[0] = d_point[0] + 50
                b_point = get_point(self.point_coords[0], self.point_coords[1])
                c_point = list(b_point)
                c_point[0] = c_point[0] + 50
                diff_points = b_point[0] - a_point[0]
                bc = length_side(b_point[0], b_point[2], c_point[0], c_point[2])
                bd = length_side(b_point[0], b_point[2], d_point[0], d_point[2])
                ac = length_side(a_point[0], a_point[2], c_point[0], c_point[2])
            else:
                # yz_factor
                a_point = self.point_coords[0]
                d_point = list(a_point)
                d_point[1] = d_point[1] - 50
                b_point = get_point(self.point_coords[1], self.point_coords[2])
                c_point = list(b_point)
                c_point[1] = c_point[1] - 50
                diff_points = b_point[1] - a_point[1]
                bc = length_side(b_point[1], b_point[2], c_point[1], c_point[2])
                bd = length_side(b_point[1], b_point[2], d_point[1], d_point[2])
                ac = length_side(a_point[1], a_point[2], c_point[1], c_point[2])
            factor_value = float("%.4f" % calc_skew_factor(ac, bd, bc))
            factor_name = factor_name.lower() + '_factor'
            setattr(self, factor_name, factor_value)
            out = "Calculated %s skew compensation %s: %.6f radians, %.2f degrees, difference beetwen points=%f" % (
                msg, factor_name, factor_value, math.degrees(factor_value), diff_points)
            gcmd.respond_info(out)
        else:
            raise gcmd.error(
                    "Error! Factor name %s not in list factors['XY', 'XZ', 'YZ']" % (factor_name))
    cmd_CALC_SKEW_COMPENSATION_help = "Calculate skew compensation."

    cmd_CALC_SKEW_COMPENSATION_WCS_help = "Calculate skew compensation by wcs."
    def cmd_CALC_SKEW_COMPENSATION_WCS(self, gcmd):
        factors = ['XY', 'XZ', 'YZ']
        factor_name = gcmd.get('FACTOR').upper()
        factor_name = factor_name
        wcs_list = self.gcode_move.wcs_offsets
        if factor_name in factors:
            if factor_name == factors[0]:
                # xy_factor
                a_point = wcs_list[2]
                d_point = list(a_point)
                d_point[0] = d_point[0] + 50
                b_point = wcs_list[4]
                c_point = list(b_point)
                c_point[0] = c_point[0] + 50
                # diff_points = b_point[0] - a_point[0]
                bc = length_side(b_point[0], b_point[1], c_point[0], c_point[1])
                bd = length_side(b_point[0], b_point[1], d_point[0], d_point[1])
                ac = length_side(a_point[0], a_point[1], c_point[0], c_point[1])
            elif factor_name == factors[1]:
                # xz_factor
                a_point = wcs_list[3]
                d_point = list(a_point)
                d_point[0] = d_point[0] + 50.
                b_point = wcs_list[1]
                c_point = list(b_point)
                c_point[0] = c_point[0] + 50.
                # diff_points = b_point[0] - a_point[0]
                bc = length_side(b_point[0], b_point[2], c_point[0], c_point[2])
                bd = length_side(b_point[0], b_point[2], d_point[0], d_point[2])
                ac = length_side(a_point[0], a_point[2], c_point[0], c_point[2])
            else:
                # yz_factor
                a_point = wcs_list[1]
                d_point = list(a_point)
                d_point[1] = d_point[1] + 50
                b_point = wcs_list[3]
                c_point = list(b_point)
                c_point[1] = c_point[1] + 50
                bc = length_side(b_point[1], b_point[2], c_point[1], c_point[2])
                bd = length_side(b_point[1], b_point[2], d_point[1], d_point[2])
                ac = length_side(a_point[1], a_point[2], c_point[1], c_point[2])
            factor_value = float("%.4f" % calc_skew_factor(ac, bd, bc))
            factor_name = factor_name.lower() + '_factor'
            out = "Calculated  skew compensation %s: %.6f radians, %.2f degrees" % (
                 factor_name, factor_value, math.degrees(factor_value))
            gcmd.respond_info(out)

    def _load_storage(self, config):
        stored_profs = config.get_prefix_sections(self.name)
        # Remove primary skew_correction section, as it is not a stored profile
        stored_profs = [s for s in stored_profs
                        if s.get_name() != self.name]
        for profile in stored_profs:
            name = profile.get_name().split(' ', 1)[1]
            self.skew_profiles[name] = {
                'xy_skew': profile.getfloat("xy_skew"),
                'xz_skew': profile.getfloat("xz_skew"),
                'yz_skew': profile.getfloat("yz_skew"),
            }

    def calc_skew(self, pos):
        newpos = list(pos)
        if self.gcode_move.current_wcs == 2:
            newpos[0] = pos[0] + ((self.wcs_list[2][1] - pos[1]) * (self.xy_factor * -1 ))
            return newpos
        elif self.gcode_move.current_wcs == 1:
            newpos[0] = pos[0] + ((self.wcs_list[1][2] - pos[2]) * (self.xz_factor * -1 ))
            newpos[1] = pos[1] + ((self.wcs_list[1][2] - pos[2]) * (self.yz_factor))
            return newpos
        else:
            return pos

    def calc_unskew(self, pos):
        newpos = list(pos)
        if self.gcode_move.current_wcs == 2:
            newpos[0] = pos[0] - ((self.wcs_list[2][1] - pos[1]) * (self.xy_factor * -1 ))
            return newpos
        elif self.gcode_move.current_wcs == 1:
            newpos[0] = pos[0] - ((self.wcs_list[1][2] - pos[2]) * (self.xz_factor * -1 ))
            newpos[1] = pos[1] - ((self.wcs_list[1][2] - pos[2]) * (self.yz_factor))
            return newpos
        else:
            return pos

    def get_position(self):
        if self.apply_skew and self.enabled:
            return self.calc_unskew(self.next_transform.get_position())
        else:
            return self.next_transform.get_position()

    def move(self, newpos, speed):
        old_pos = self.next_transform.get_position()
        axes_d = [old_pos[i] - newpos[i] for i in
                                (0, 1, 2, 3, 4, 5)]
        move_d = math.sqrt(sum([d * d for d in axes_d[:5]]))
        if not self.enabled or move_d < .000000001:
            self.apply_skew = False
            self.next_transform.move(newpos, speed)
            return
        self.apply_skew = True
        corrected_pos = self.calc_skew(newpos)
        self.next_transform.move(corrected_pos, speed)

    def _update_skew(self, xy_factor, xz_factor, yz_factor):
        self.xy_factor = xy_factor
        self.xz_factor = xz_factor
        self.yz_factor = yz_factor
        gcode_move = self.printer.lookup_object('gcode_move')
        gcode_move.reset_last_position()

    def cmd_GET_CURRENT_SKEW(self, gcmd):
        out = "Current profile %s:\n" % self.current_profile
        planes = ["XY", "XZ", "YZ"]
        factors = [self.xy_factor, self.xz_factor, self.yz_factor]
        for plane, fac in zip(planes, factors):
            out += "%s skew: %.6f radians, %.2f degrees.\n" % (
                plane, fac, math.degrees(fac))
        gcmd.respond_info(out)
    cmd_GET_CURRENT_SKEW_help = "Report the current profile and current printer skew."

    def cmd_SET_SKEW(self, gcmd):
        if gcmd.get_int("CLEAR", 0):
            self._update_skew(0., 0., 0.)
            gcmd.respond_info('Skew points cleared.')
            return
        if gcmd.get_int('ENABLE', 0):
            self.enabled = True
            gcmd.respond_info('Skew compensation enabled.')
        else:
            self.enabled = False
            gcmd.respond_info('Skew compensation disabled.')
        planes = ["XY", "XZ", "YZ"]
        for plane in planes:
            skew = gcmd.get_float(plane, None)
            if skew is not None:
                try:
                    factor = plane.lower() + '_factor'
                    setattr(self, factor, skew)
                    out = "Set skew correction %s: %.6f radians, %.2f degrees." % (
                        factor, skew, math.degrees(skew))
                    gcmd.respond_info(out)
                except Exception:
                    raise gcmd.error(
                        "skew_correction: improperly formatted entry for "
                        "plane [%s]\n%s" % (plane, gcmd.get_commandline()))
    cmd_SET_SKEW_help = "Set skews(XY=0.1, ...), delete skews(CLEAR=1) \
        or include skew correction(ENABLE=1) its."

    def cmd_SKEW_PROFILE(self, gcmd):
        options = collections.OrderedDict({
            'LOAD': self.load_profile,
            'SAVE': self.save_profile,
            'REMOVE': self.remove_profile,
            'CHANGE': None,
            'RESET': self.reset_profile
        })
        for key in options:
            name = gcmd.get(key, None)
            profile = self.skew_profiles.get(name)
            if name is not None and profile is not None:
                if key == 'CHANGE':
                    self.change_profile(name, gcmd)
                else:
                    options[key](name)
                return
        gcmd.respond_info("Invalid syntax '%s'" % (gcmd.get_commandline(),))
    cmd_SKEW_PROFILE_help = "Profile management for skew_correction('LOAD','SAVE',\
        'REMOVE','CHANGE,'RESET)."

    def load_profile(self, prof_name):
        """
        load profile
        """
        self.current_profile = prof_name
        profile = self.skew_profiles.get(prof_name)
        if profile is not None:
            self._update_skew(profile['xy_skew'], profile['xz_skew'], profile['yz_skew'])

    def save_profile(self, prof_name):
        """
        change profile factors and change config
        """
        configfile = self.printer.lookup_object('configfile')
        cfg_name = self.name + " " + prof_name
        configfile.set(cfg_name, 'xy_skew', self.xy_factor)
        configfile.set(cfg_name, 'xz_skew', self.xz_factor)
        configfile.set(cfg_name, 'yz_skew', self.yz_factor)
        # Copy to local storage
        self.skew_profiles[prof_name] = {
            'xy_skew': self.xy_factor,
            'xz_skew': self.xz_factor,
            'yz_skew': self.yz_factor
        }

    def change_profile(self, prof_name, gcmd):
        """
        change profile factors but don't change config
        """
        xy_factor = gcmd.get_float('XY', self.xy_factor)
        xz_factor = gcmd.get_float('XZ', self.xz_factor)
        yz_factor = gcmd.get_float('YZ', self.yz_factor)
        self.skew_profiles[prof_name] = {
            'xy_skew': xy_factor,
            'xz_skew': xz_factor,
            'yz_skew': yz_factor
        }
        gcmd.respond_info(
            "Changed skew_profile=%s: xy_skew=%s; xz_skew=%s; yz_skew=%s." % (
                prof_name, xy_factor, xz_factor, yz_factor))

    def remove_profile(self, prof_name):
        configfile = self.printer.lookup_object('configfile')
        configfile.remove_section('skew_correction ' + prof_name)
        del self.skew_profiles[prof_name]

    def reset_profile(self, prof_name):
        for i in self.skew_profiles[prof_name]:
            self.skew_profiles[prof_name][i] = 0.

    def get_status(self, eventtime=None):
        return {
            'enabled': self.enabled,
            'current_xy_factor': self.xy_factor,
            'current_xz_factor': self.xz_factor,
            'current_yz_factor': self.yz_factor,
            'skew_profiles': self.skew_profiles,
            'wcs_list': self.wcs_list,
            'current_skew_profile': self.current_profile,
            'self.point_coords': self.point_coords
        }

def load_config(config):
    return PrinterSkew(config)
