# Virtual SDCard print stat tracking
#
# Copyright (C) 2020  Eric Callahan <arksine.code@gmail.com>
#
# This file may be distributed under the terms of the GNU GPLv3 license.
import logging


class PrintStats:
    def __init__(self, config):
        self.printer = config.get_printer()
        self.gcode_move = self.printer.load_object(config, 'gcode_move')
        self.reactor = self.printer.get_reactor()
        self.reset()
        self.gcode = self.printer.lookup_object('gcode')
        # Register commands
        self.gcode.register_command(
            "SET_PRINT_STATS_INFO", self.cmd_SET_PRINT_STATS_INFO,
            desc=self.cmd_SET_PRINT_STATS_INFO_help)
    def _update_filament_usage(self, eventtime):
        gc_status = self.gcode_move.get_status(eventtime)
        cur_epos = gc_status['position'].e
        self.filament_used += (cur_epos - self.last_epos) \
            / gc_status['extrude_factor']
        self.last_epos = cur_epos
    def set_current_file(self, filename):
        self.reset()
        self.filename = filename
    def note_start(self):
        curtime = self.reactor.monotonic()
        if self.print_start_time is None:
            self.print_start_time = curtime
        elif self.last_pause_time is not None:
            # Update pause time duration
            pause_duration = curtime - self.last_pause_time
            self.prev_pause_duration += pause_duration
            self.last_pause_time = None
        # Reset last e-position
        gc_status = self.gcode_move.get_status(curtime)
        self.last_epos = gc_status['position'].e
        self.state = "printing"
        self.error_message = ""
    def note_pause(self):
        if self.last_pause_time is None:
            curtime = self.reactor.monotonic()
            self.last_pause_time = curtime
            # update filament usage
            self._update_filament_usage(curtime)
        if self.state != "error":
            self.state = "paused"
    def note_complete(self):
        self._note_finish("complete")
    def note_error(self, message):
        self._note_finish("error", message)
    def note_cancel(self):
        self._note_finish("cancelled")
    def _note_finish(self, state, error_message = ""):
        if self.print_start_time is None:
            return
        self.state = state
        self.error_message = error_message
        eventtime = self.reactor.monotonic()
        self.total_duration = eventtime - self.print_start_time
        if self.filament_used < 0.0000001:
            # No positive extrusion detected during print
            self.init_duration = self.total_duration - \
                self.prev_pause_duration
        self.print_start_time = None
    cmd_SET_PRINT_STATS_INFO_help = "Set info about current file."
    def cmd_SET_PRINT_STATS_INFO(self, gcmd):
        total_layer = gcmd.get_int("TOTAL_LAYER", 0)
        current_layer = gcmd.get_int("CURRENT_LAYER", 0)
        count_triggered_sensor = gcmd.get_int("COUNT_TRIGGERED_SENSOR", 0)
        if total_layer:
            self.info_total_layer = total_layer
            self.info_current_layer = 0
        if self.info_total_layer is not None and \
                current_layer is not None and \
                current_layer != self.info_current_layer:
            self.info_current_layer = min(current_layer, self.info_total_layer)
        if count_triggered_sensor:
            self.count_triggered_sensor = count_triggered_sensor

    def set_layer(self, total_layer=None, current_layer=None):
        if total_layer:
            try:
                total_layer = int(total_layer)
                self.info_total_layer = total_layer
            except Exception as e:
                logging.warning('Do not get total_layer\n %s' % e)
                self.info_total_layer = 0
        if current_layer:
            try:
                current_layer = int(current_layer)
                self.info_current_layer = current_layer
            except Exception as e:
                logging.warning('Do not get current_layer\n %s' % e)

    def reset(self):
        self.filename = self.error_message = ""
        self.state = "standby"
        self.prev_pause_duration = self.last_epos = 0.
        self.filament_used = self.total_duration = 0.
        self.print_start_time = self.last_pause_time = None
        self.init_duration = 0.
        self.count_triggered_sensor = 0
        self.info_total_layer = None
        self.info_current_layer = None
    def get_status(self, eventtime):
        time_paused = self.prev_pause_duration
        if self.print_start_time is not None:
            if self.last_pause_time is not None:
                # Calculate the total time spent paused during the print
                time_paused += eventtime - self.last_pause_time
            else:
                # Accumulate filament if not paused
                self._update_filament_usage(eventtime)
            self.total_duration = eventtime - self.print_start_time
            if self.filament_used < 0.0000001:
                # Track duration prior to extrusion
                self.init_duration = self.total_duration - time_paused
        print_duration = self.total_duration - self.init_duration - time_paused
        return {
            'filename': self.filename,
            'total_duration': self.total_duration,
            'print_duration': print_duration,
            'filament_used': self.filament_used,
            'state': self.state,
            'message': self.error_message,
            'count_triggered_sensor': self.count_triggered_sensor,
            'info': {'total_layer': self.info_total_layer,
                     'current_layer': self.info_current_layer}
        }

def load_config(config):
    return PrintStats(config)
