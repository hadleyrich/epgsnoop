# By hads <hads@nice.net.nz>
# Released under the MIT license

import os
import signal
import subprocess
from time import sleep

from base import *

class TuningFailed(Exception):
    pass

class Tuner(object):
    def __init__(self, adapter, lnb_offset):
        self.adapter = adapter
        self.lnb_offset = int(lnb_offset)

    def tune(self, frequency, polarity, symbol_rate, flush=True):
        log.info('Tuning DVB card %s', self.adapter)
        freq = str((int(frequency) - self.lnb_offset) * 1000)
        self.tuner = subprocess.Popen(
            ['dvbtune', '-c', self.adapter, '-f', freq, '-s', symbol_rate, '-p', polarity, '-m', '-tone', '0'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        sleep(0.5) # Give dvbtune time to see if the card is available
        if self.tuner.poll() is not None:
            return False

        log.debug('dvbtune process running')
        if flush:
            self.flush()
        return True

    def free(self):
        # self.tuner.kill() was only introduced in 2.6
        os.kill(self.tuner.pid, signal.SIGTERM)

    def flush(self):
        """
        It seems that dvbsnoop can output data buffered from the previous tune.
        This makes sure we discard that data, 2000 is an arbitrary number.
        """
        log.info('Flushing stale EIT data...')
        self.dvbsnoop_flush = subprocess.Popen(
            ['dvbsnoop', '-adapter', self.adapter, '-n', '2000', '-nph', '0x12'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        (stdoutdata, stderrdata) = self.dvbsnoop_flush.communicate()
        log.info('Done.')

