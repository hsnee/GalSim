import unittest
import numpy as np
import os
import galsim
from galsim.lsst import LSSTWCS
from galsim.celestial import CelestialCoord


class WcsTestClass(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        path, filename = os.path.split(__file__)
        file_name = os.path.join(path, 'random_data', 'galsim_afwCameraGeom_data.txt')
        dtype = np.dtype([('ra', np.float), ('dec', np.float), ('chipName', str, 100),
                           ('xpix', np.float), ('ypix', np.float),
                           ('xpup', np.float), ('ypup', np.float)])

        cls.camera_data = np.genfromtxt(file_name, dtype=dtype, delimiter='; ')


    def test_pupil_coordinates(self):
        """
        Test the conversion between (RA, Dec) and pupil coordinates.
        Results are checked against the routine provided by PALPY.
        """

        def palpyPupilCoords(star, pointing):
            """
            This is just a copy of the PALPY method Ds2tp, which
            I am taking to be the ground truth for projection from
            a sphere onto the tangent plane

            inputs
            ------------
            star is a CelestialCoord corresponding to the point being projected

            pointing is a CelestialCoord corresponding to the pointing of the
            'telescope'

            outputs
            ------------
            The x and y coordinates in the focal plane (radians)
            """

            ra = star.ra/galsim.radians
            dec = star.dec/galsim.radians
            ra_pointing = pointing.ra/galsim.radians
            dec_pointing = pointing.dec/galsim.radians

            cdec = np.cos(dec)
            sdec = np.sin(dec)
            cdecz = np.cos(dec_pointing)
            sdecz = np.sin(dec_pointing)
            cradif = np.cos(ra - ra_pointing)
            sradif = np.sin(ra - ra_pointing)

            denom = sdec * sdecz + cdec * cdecz * cradif
            xx = cdec * sradif/denom
            yy = (sdec * cdecz - cdec * sdecz * cradif)/denom
            return xx*galsim.radians, yy*galsim.radians


        np.random.seed(42)
        n_pointings = 10
        ra_pointing_list = np.random.random_sample(n_pointings)*2.0*np.pi
        dec_pointing_list = 0.5*(np.random.random_sample(n_pointings)-0.5)*np.pi
        rotation_angle_list = np.random.random_sample(n_pointings)*2.0*np.pi

        for ra, dec, rotation in zip(ra_pointing_list, dec_pointing_list, rotation_angle_list):

            pointing = CelestialCoord(ra*galsim.radians, dec*galsim.radians)
            wcs = LSSTWCS(pointing, rotation*galsim.radians)

            dra_list = (np.random.random_sample(100)-0.5)*0.5
            ddec_list = (np.random.random_sample(100)-0.5)*0.5

            star_list = np.array([CelestialCoord((ra+dra)*galsim.radians, (dec+ddec)*galsim.radians)
                                 for dra, ddec in zip(dra_list, ddec_list)])

            xTest, yTest = wcs._get_pupil_coordinates(star_list)
            xControl = []
            yControl = []
            for star in star_list:
                xx, yy = palpyPupilCoords(star, pointing)
                xx *= -1.0
                xControl.append(xx*np.cos(rotation) - yy*np.sin(rotation))
                yControl.append(yy*np.cos(rotation) + xx*np.sin(rotation))

            xControl = np.array(xControl)
            yControl = np.array(yControl)

            np.testing.assert_array_almost_equal((xTest/galsim.arcsec) - (xControl/galsim.arcsec), np.zeros(len(xControl)),  7)
            np.testing.assert_array_almost_equal((yTest/galsim.arcsec) - (yControl/galsim.arcsec), np.zeros(len(yControl)), 7)


    def test_get_chip_name(self):
        """
        Test the method which associates positions on the sky with names of chips
        """

        ra = 112.064181578541
        dec = -33.015167519966
        rotation = 27.0

        pointing = CelestialCoord(ra*galsim.degrees, dec*galsim.degrees)
        wcs = LSSTWCS(pointing, rotation*galsim.degrees)

        # test case of a mapping a single location
        for rr, dd, control_name in \
            zip(self.camera_data['ra'], self.camera_data['dec'], self.camera_data['chipName']):

            point = CelestialCoord(rr*galsim.degrees, dd*galsim.degrees)
            test_name = wcs._get_chip_name(point)

            try:
                if control_name != 'None':
                    self.assertEqual(test_name, control_name)
                else:
                    self.assertEqual(test_name, None)
            except AssertionError as aa:
                print 'triggering error: ',aa.args[0]
                raise AssertionError("The LSST WCS chipName outputs are no longer consistent\n"
                                     "with the LSST Stack.  Contact Scott Daniel at scottvalscott@gmail.com\n"
                                     "to make sure you have the correct version\n")

        # test case of mapping a list of celestial coords
        point_list = []
        for rr, dd in zip(self.camera_data['ra'], self.camera_data['dec']):
            point_list.append(CelestialCoord(rr*galsim.degrees, dd*galsim.degrees))

        test_name_list = wcs._get_chip_name(point_list)
        for test_name, control_name in zip(test_name_list, self.camera_data['chipName']):
            try:
                if control_name != 'None':
                    self.assertEqual(test_name, control_name)
                else:
                    self.assertEqual(test_name, None)
            except AssertionError as aa:
                print 'triggering error: ',aa.args[0]
                raise AssertionError("The LSST WCS chipName outputs are no longer consistent\n"
                                     "with the LSST Stack.  Contact Scott Daniel at scottvalscott@gmail.com\n"
                                     "to make sure you have the correct version\n")

