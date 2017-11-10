from __future__ import absolute_import, division, print_function

import subprocess

from ..helpers import BaseSTIS, download_file_cgi


class TestInttag(BaseSTIS):
    """
    This is a temprorary test for the inttag function.

    """
    subdir = 'inttag_temp'

    def test_ex1(self):
        timetag_file = 'od8k51igq_tag.fits'

        # Prepare input files.
        self.get_input_file(timetag_file)

        # Run CALSTIS (equivalent to stistools.calstis.calstis)
        subprocess.call(['inttag.e', timetag_file, 'out_i1.fits', '-v'])

        # Compare results
        outputs = [('out_i1.fits', 'out_inttag1.fits')]
        self.compare_outputs(outputs)

    def test_ex3(self):
        timetag_file = 'od8k51igq_tag.fits'

        # Prepare input files.
        self.get_input_file(timetag_file)

        # Run CALSTIS (equivalent to stistools.calstis.calstis)
        subprocess.call(['inttag.e', timetag_file, 'out_i3.fits',
                         '10.0', '-v'])

        # Compare results
        outputs = [('out_i3.fits', 'out_inttag3.fits')]
        self.compare_outputs(outputs)
        
    def test_ex7(self):
        timetag_file = 'od8k51igq_tag.fits'

        # Prepare input files.
        self.get_input_file(timetag_file)

        # Run CALSTIS (equivalent to stistools.calstis.calstis)
        subprocess.call(['inttag.e', timetag_file, 'out_i7.fits',
                         '-h', '-v'])

        # Compare results
        outputs = [('out_i7.fits', 'out_inttag7.fits')]
        self.compare_outputs(outputs)