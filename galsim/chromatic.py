# Copyright 2012, 2013 The GalSim developers:
# https://github.com/GalSim-developers
#
# This file is part of GalSim: The modular galaxy image simulation toolkit.
#
# GalSim is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# GalSim is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with GalSim.  If not, see <http://www.gnu.org/licenses/>
#
"""@file chromatic.py
Definitions for GalSim classes implementing wavelength-dependence.

This file extends the base GalSim classes by allowing them to be wavelength dependent.  This allows
one to implement wavelength-dependent PSFs or galaxies with color gradients.
"""

import numpy

import galsim
import galsim.integ
import galsim.dcr

class ChromaticObject(object):
    """Base class for defining wavelength dependent objects.
    """
    def draw(self, bandpass, image=None, scale=None, gain=1.0, wmult=1.0,
             add_to_image=False, use_true_center=True, offset=None,
             integrator=None, **kwargs):
        # default integrator is Riemann sum
        if integrator is None:
            integrator = galsim.integ.midpoint_int_image
        # setup output image
        prof0 = self.evaluateAtWavelength(bandpass.bluelim) * bandpass(bandpass.bluelim)
        prof0 = prof0._fix_center(image, scale, offset, use_true_center, reverse=False)
        image = prof0._draw_setup_image(image, scale, wmult, add_to_image)

        # integrand returns an image at each wavelength
        def f_image(w):
            prof = self.evaluateAtWavelength(w) * bandpass(w)
            tmpimage = image.copy()
            tmpimage.setZero()
            prof.draw(image=tmpimage, gain=gain, wmult=wmult,
                      add_to_image=False, use_true_center=use_true_center, offset=offset)
            return tmpimage

        # wavelength integral
        integral = integrator(f_image, bandpass.bluelim, bandpass.redlim, **kwargs)

        # clear image unless add_to_image is True
        if not add_to_image:
            image.setZero()
        image += integral
        return image

    def __add__(self, other):
        return galsim.ChromaticSum([self, other])

class Chromatic(ChromaticObject):
    """Construct chromatic versions of the galsim GSObjects.

    This class extends the base GSObjects in basy.py by adding SEDs.  Useful to consistently generate
    the same galaxy observed through different filters, or, with the ChromaticSum class, to construct
    multi-component galaxies, each with a different SED. For example, a bulge+disk galaxy could be
    constructed:

    >>> bulge_SED = user_function_to_get_bulge_spectrum()
    >>> disk_SED = user_function_to_get_disk_spectrum()
    >>> bulge_mono = galsim.DeVaucouleurs(half_light_radius=1.0)
    >>> bulge = galsim.Chromatic(mono, bulge_SED)
    >>> disk_mono = galsim.Exponential(half_light_radius=2.0)
    >>> disk = galsim.Chromatic(disk_mono, disk_SED)
    >>> gal = galsim.ChromaticSum([bulge, disk])

    The SED is specified as a galsim.SED object.  The normalization is set via the SED.  I.e., the
    SED implicitly has units of counts per nanometer.  The drawn flux will be an intregral over this
    distribution.
    """
    def __init__(self, gsobj, SED):
        """Initialize Chromatic.

        @param gsobj    An GSObject instance to be chromaticized.
        @param SED      A SED object.
        """
        self.SED = SED
        self.gsobj = gsobj
        # Chromaticized GSObjects are separable into spatial (x,y) and spectral (lambda) factors.
        self.separable = True

    # Make op* and op*= work to adjust the flux of an object
    def __imul__(self, other):
        self.gsobj.scaleFlux(other)
        return self

    def __mul__(self, other):
        ret = self.copy()
        ret *= other
        return ret

    def __rmul__(self, other):
        ret = self.copy()
        ret *= other
        return ret

    # Make a copy of an object
    # Not sure if `SED` and `gsobj` copy cleanly here or not...
    def copy(self):
        cls = self.__class__
        ret = cls.__new__(cls)
        ret.__dict__.update(self.__dict__)
        return ret

    def applyShear(self, *args, **kwargs):
        self.gsobj.applyShear(*args, **kwargs)

    def applyDilation(self, *args, **kwargs):
        self.gsobj.applyDilation(*args, **kwargs)

    def applyShift(self, *args, **kwargs):
        self.gsobj.applyShift(*args, **kwargs)

    def applyExpansion(self, *args, **kwargs):
        self.gsobj.applyExpansion(*args, **kwargs)

    def applyMagnification(self, *args, **kwargs):
        self.gsobj.applyMagnification(*args, **kwargs)

    def applyLensing(self, *args, **kwargs):
        self.gsobj.applyLensing(*args, **kwargs)

    def applyRotation(self, *args, **kwargs):
        self.gsobj.applyRotation(*args, **kwargs)

    def evaluateAtWavelength(self, wave):
        """
        @param wave  Wavelength in nanometers.
        @returns     GSObject for profile at specified wavelength
        """
        return self.SED(wave) * self.gsobj

class ChromaticSum(ChromaticObject):
    """Sum ChromaticObjects and/or GSObjects together.  GSObjects are treated as having flat spectra.
    """
    def __init__(self, objlist):
        self.objlist = objlist

    def evaluateAtWavelength(self, wave):
        """
        @param wave  Wavelength in nanometers.
        @returns     GSObject for profile at specified wavelength
        """
        return galsim.Sum([obj.evaluateAtWavelength(wave) for obj in self.objlist])

    def draw(self, bandpass, image=None, scale=None, gain=1.0, wmult=1.0,
             add_to_image=False, use_true_center=True, offset=None,
             integrator=None, **kwargs):
        # is the most efficient method to just add up one component at a time...?
        image = self.objlist[0].draw(bandpass, image=image, scale=scale, gain=gain, wmult=wmult,
                                     add_to_image=add_to_image, use_true_center=use_true_center,
                                     offset=offset, integrator=integrator, **kwargs)
        for obj in self.objlist[1:]:
            image = obj.draw(bandpass, image=image, scale=scale, gain=gain, wmult=wmult,
                             add_to_image=True, use_true_center=use_true_center,
                             offset=offset, integrator=integrator, **kwargs)

    def applyShear(self, *args, **kwargs):
        for obj in self.objlist:
            obj.applyShear(*args, **kwargs)

    def applyDilation(self, *args, **kwargs):
        for obj in self.objlist:
            obj.applyDilation(*args, **kwargs)

    def applyShift(self, *args, **kwargs):
        for obj in self.objlist:
            obj.applyShift(*args, **kwargs)

    def applyExpansion(self, *args, **kwargs):
        for obj in self.objlist:
            obj.applyExpansion(*args, **kwargs)

    def applyMagnification(self, *args, **kwargs):
        for obj in self.objlist:
            obj.applyMagnification(*args, **kwargs)

    def applyLensing(self, *args, **kwargs):
        for obj in self.objlist:
            obj.applyLensing(*args, **kwargs)

    # Does this work?  About which point is the rotation applied?
    def applyRotation(self, *args, **kwargs):
        for obj in self.objlist:
            obj.applyRotation(*args, **kwargs)

class ChromaticConvolution(ChromaticObject):
    """Convolve ChromaticObjects and/or GSObjects together.  GSObjects are treated as having flat
    spectra.
    """
    def __init__(self, objlist):
        self.objlist = objlist

    def evaluateAtWavelength(self, wave):
        """
        @param wave  Wavelength in nanometers.
        @returns     GSObject for profile at specified wavelength
        """
        return galsim.Convolve([obj.evaluateAtWavelength(wave) for obj in self.objlist])

    def draw(self, bandpass, image=None, scale=None, gain=1.0, wmult=1.0,
             add_to_image=False, use_true_center=True, offset=None,
             integrator=None, **kwargs):
        if integrator is None:
            integrator = galsim.integ.midpoint_int_image
        # Only make temporary changes to objlist...
        objlist = list(self.objlist)

        # expand any `ChromaticConvolution`s in the object list
        L = len(objlist)
        i = 0
        while i < L:
            if isinstance(objlist[i], ChromaticConvolution):
                # found a ChromaticConvolution object, so unpack its obj.objlist to end of objlist,
                # delete obj from objlist, and update list length `L` and list index `i`.
                L += len(objlist[i].objlist) - 1
                # appending to the end of the objlist means we don't have to recurse in order to
                # expand a hierarchy of `ChromaticSum`s; we just have to keep going until the end of
                # the ever-expanding list.
                # I.e., `*` marks progress through list...
                # {{{A, B}, C}, D}  i = 0, length = 2
                #  *
                # {D, {A, B}, C}    i = 1, length = 3
                #     *
                # {D, C, A, B}      i = 2, length = 4
                #        *
                # {D, C, A, B}      i = 3, length = 4
                #           *
                # Done!
                objlist.extend(objlist[i].objlist)
                del objlist[i]
                i -= 1
            i += 1

        # Now split up any `ChromaticSum`s:
        # This is the tricky part.  Some notation first:
        #     I(f(x,y,lambda)) denotes the integral over wavelength of a chromatic surface brightness
        #         profile f(x,y,lambda).
        #     C(f1, f2) denotes the convolution of surface brightness profiles f1 & f2.
        #     A(f1, f2) denotes the addition of surface brightness profiles f1 & f2.
        #
        # In general, chromatic s.b. profiles can be classified as either separable or inseparable,
        # depending on whether they can be factored into spatial and spectral components or not.
        # Write separable profiles as g(x,y) * h(lambda), and leave inseparable profiles as
        # f(x,y,lambda).
        # We will suppress the arguments `x`, `y`, `lambda`, hereforward, but generally an `f` refers
        # to an inseparable profile, a `g` refers to the spatial part of a separable profile, and an
        # `h` refers to the spectral part of a separable profile.
        #
        # Now, analyze a typical scenario, a bulge+disk galaxy model (each of which is separable,
        # e.g., an SED times an exponential profile for the disk, and a different SED times a DeV
        # profile for the bulge).  Suppose the PSF is inseparable.  (Chromatic PSF's will generally
        # be inseparable since we usually think of the spatial part of the PSF being normalized to
        # unit integral for any fixed wavelength.)  Say there's also an achromatic pixel to
        # convolve with.
        # The formula for this might look like:
        #
        # img = I(C(A(bulge, disk), PSF, pix))
        #     = I(C(A(g1*h1, g2*h2), f3, g4))                # note pix is lambda-independent
        #     = I(A(C(g1*h1, f3, g4)), C(A(g2*h2, f3, g4)))  # distribute the A over the C
        #     = A(I(C(g1*h1, f3, g4)), I(C(g2*h2, f3, g4)))  # distribute the A over the I
        #     = A(C(g1,I(h1*f3),g4), C(g2,I(h2*f3),g4))      # move lambda-indep terms out of I
        #
        # The result is that the integral is now inside the convolution, meaning we only have to
        # compute two convolutions instead of a convolution for each wavelength at which we evaluate
        # the integrand.  This technique, making an `effective` PSF profile for each of the bulge and
        # disk, is a significant time savings in most cases.
        # In general, we make effective profiles by splitting up `ChromaticSum`s and collecting the
        # inseparable terms on which to do integration first, and then finish with convolution last.

        # Here is the logic to turn I(C(A(...))) into A(C(..., I(...)))
        returnme = False
        for i, obj in enumerate(objlist):
            if isinstance(obj, ChromaticSum):
                # say obj.objlist = [A,B,C], where obj is a ChromaticSum object
                returnme = True
                del objlist[i] # remove the add object from objlist
                tmplist = list(objlist) # collect remaining items to be convolved with each of A,B,C
                tmplist.append(obj.objlist[0]) # add A to this convolve list
                tmpobj = ChromaticConvolution(tmplist) # draw image
                image = tmpobj.draw(bandpass, image=image, gain=gain, wmult=wmult,
                                    add_to_image=add_to_image, use_true_center=use_true_center,
                                    offset=offset, **kwargs)
                for summand in obj.objlist[1:]: # now do the same for B and C
                    tmplist = list(objlist)
                    tmplist.append(summand)
                    tmpobj = ChromaticConvolution(tmplist)
                    # add to previously started image
                    image = tmpobj.draw(bandpass, image=image, gain=gain, wmult=wmult,
                                        add_to_image=True, use_true_center=use_true_center,
                                        offset=offset, **kwargs)
        if returnme:
            return image

        # If program gets this far, the objects in objlist should be atomic (non-ChromaticSum
        # and non-ChromaticConvolution).
        # Sort these atomic objects into separable and inseparable lists, and collect
        # the spectral parts of the separable profiles.
        sep_profs = []
        insep_profs = []
        sep_SED = []
        for obj in objlist:
            if obj.separable:
                if isinstance(obj, galsim.GSObject):
                    sep_profs.append(obj) # The g(x,y)'s (see above)
                else:
                    sep_profs.append(obj.gsobj) # more g(x,y)'s
                sep_SED.append(obj.SED) # The h(lambda)'s (see above)
            else:
                insep_profs.append(obj) # The f(x,y,lambda)'s (see above)

        # check if there are any inseparable profiles
        if insep_profs == []:
            def f(w):
                term = bandpass(w)
                for s in sep_SED:
                    term *= s(w)
                return term
            multiplier = galsim.integ.int1d(f, bandpass.bluelim, bandpass.redlim)
        else:
            multiplier = 1.0
            # setup image for effective profile
            mono_prof0 = galsim.Convolve([p.evaluateAtWavelength(bandpass.bluelim)
                                          for p in insep_profs])
            mono_prof0 = mono_prof0._fix_center(image=None, scale=None, offset=None,
                                                use_true_center=True, reverse=False)
            mono_prof_image = mono_prof0._draw_setup_image(image=None, scale=None, wmult=wmult,
                                                           add_to_image=False)
            # integrand for effective profile
            def f_image(w):
                mono_prof = galsim.Convolve([insp.evaluateAtWavelength(w) for insp in insep_profs])
                mono_prof *= bandpass(w)
                for s in sep_SED:
                    mono_prof *= s(w)
                tmpimage = mono_prof_image.copy()
                tmpimage.setZero()
                mono_prof.draw(image=tmpimage, wmult=wmult)
                # print 'f_image {} {}'.format(w, mono_prof.getFlux()* 2.2)
                return tmpimage
            # wavelength integral
            effective_prof_image = integrator(f_image, bandpass.bluelim, bandpass.redlim, **kwargs)
            # Image -> InterpolatedImage
            effective_prof = galsim.InterpolatedImage(effective_prof_image)
            # append effective profile to separable profiles (which are all GSObjects)
            sep_profs.append(effective_prof)
        # finally, convolve and draw.
        final_prof = multiplier * galsim.Convolve(sep_profs)
        return final_prof.draw(image=image, gain=gain, wmult=wmult, add_to_image=add_to_image,
                               use_true_center=use_true_center, offset=offset)

class ChromaticShiftAndDilate(ChromaticObject):
    """Class representing chromatic profiles whose wavelength dependence consists of shifting and
    dilating a fiducial profile.

    By simply shifting and dilating a fiducial PSF, a variety of physical wavelength dependencies can
    be effected.  For instance, differential chromatic refraction is just shifting the PSF center as
    a function of wavelength.  The wavelength-dependence of seeing, and the wavelength-dependence of
    the diffraction limit are dilations.  This class can compactly represent all of these effects.
    See tests/test_chromatic.py for an example.
    """
    def __init__(self, gsobj,
                 shift_fn=None, dilate_fn=None):
        """
        @param gsobj      Fiducial profile (as a GSObject instance) to shift and dilate.
        @param shift_fn   Function that takes wavelength in nanometers and returns a
                          galsim.Position object, or parameters which can be transformed into a
                          galsim.Position object (dx, dy).
        @param dilate_fn  Function that takes wavelength in nanometers and returns a dilation
                          scale factor.
        """
        self.gsobj = gsobj
        if shift_fn is None:
            self.shift_fn = lambda x: (0,0)
        else:
            self.shift_fn = shift_fn
        if dilate_fn is None:
            self.dilate_fn = lambda x: 1.0
        else:
            self.dilate_fn = dilate_fn
        self.separable = False

    def applyShear(self, *args, **kwargs):
        self.gsobj.applyShear(*args, **kwargs)

    def evaluateAtWavelength(self, wave):
        """
        @param wave  Wavelength in nanometers.
        @returns     GSObject for profile at specified wavelength
        """
        profile = self.gsobj.copy()
        profile.applyDilation(self.dilate_fn(wave))
        profile.applyShift(self.shift_fn(wave))
        return profile

class ChromaticAtmosphere(ChromaticObject):
    def __init__(self, base_obj, base_wavelength, zenith_angle, alpha=-0.2,
                 parallactic_angle=0*galsim.radians, **kwargs):
        self.base_obj = base_obj
        self.base_wavelength = base_wavelength
        self.zenith_angle = zenith_angle
        self.alpha = alpha
        self.kwargs = kwargs
        self.parallactic_angle = parallactic_angle

        self.base_refraction = galsim.dcr.get_refraction(base_wavelength, zenith_angle, **kwargs)
        self.separable = False

    def evaluateAtWavelength(self, wave):
        profile = self.base_obj.copy()
        dilation = (wave/self.base_wavelength)**self.alpha
        shift_magnitude = galsim.dcr.get_refraction(wave, self.zenith_angle, **self.kwargs)
        shift_magnitude -= self.base_refraction
        shift_magnitude = shift_magnitude / galsim.arcsec
        shift = (shift_magnitude*numpy.sin(self.parallactic_angle.rad()),
                 shift_magnitude*numpy.cos(self.parallactic_angle.rad()))
        profile.applyDilation(dilation)
        profile.applyShift(shift)
        return profile

class SED(object):
    """Very simple SED object."""
    def __init__(self, wave=None, flambda=None, fnu=None, fphotons=None):
        """ Initialize SED with a wavelength array and a flux density array.  The flux density
        can be represented in one of three ways.
        @param wave     Array of wavelengths at which the SED is sampled.
        @param flambda  Array of flux density samples.  Units proprotional to erg/nm
        @param fnu      Array of flux density samples.  Units proprotional to erg/Hz
        @param fphotons Array of photon density samples.  Units proportional to photons/nm
        """
        self.wave = wave
        if flambda is not None:
            self.fphotons = flambda * wave
        elif fnu is not None:
            self.fphotons = fnu / wave
        elif fphotons is not None:
            self.fphotons = fphotons

        self.needs_new_interp=True

    def __call__(self, wave, force_new_interp=False):
        """ Uses a galsim.LookupTable to interpolate the photon density at the requested wavelength.
        The LookupTable is cached for future use.

        @param force_new_interp     Force rebuild of LookupTable.

        @returns photon density, Units proportional to photons/nm
        """
        interp = self._get_interp(force_new_interp=force_new_interp)
        return interp(wave)

    def _get_interp(self, force_new_interp=False):
        """ Return LookupTable, rebuild if requested.
        """
        if force_new_interp or self.needs_new_interp:
            self.interp = galsim.LookupTable(self.wave, self.fphotons)
            self.needs_new_interp=False
        return self.interp

    def setNormalization(self, base_wavelength, normalization):
        """ Set photon density normalization at specified wavelength
        """
        current_fphoton = self(base_wavelength)
        self.fphotons *= normalization/current_fphoton
        self.needs_new_interp = True

    def setMagnitude(self, bandpass, mag_norm):
        """ Set relative AB magnitude of SED when observed through given bandpass.
        """
        current_mag = self.getMagnitude(bandpass)
        multiplier = 10**(-0.4 * (mag_norm - current_mag))
        self.fphotons *= multiplier
        self.needs_new_interp = True

    def setFlux(self, bandpass, flux_norm):
        """ Set relative flux of SED when observed through given bandpass.
        """
        current_flux = self.getFlux(bandpass)
        multiplier = flux_norm/current_flux
        self.fphotons *= multiplier
        self.needs_new_interp = True

    def setRedshift(self, redshift):
        self.wave *= (1.0 + redshift)
        self.interp = galsim.LookupTable(self.wave, self.fphotons)
        self.needs_new_interp=True

    def getFlux(self, bandpass):
        interp = self._get_interp()
        return galsim.integ.int1d(lambda w:bandpass(w)*interp(w), bandpass.bluelim, bandpass.redlim)

    def getMagnitude(self, bandpass):
        flux = self.getFlux(bandpass)
        return -2.5 * numpy.log10(flux) - bandpass.AB_zeropoint()

class Bandpass(object):
    """Very simple Bandpass filter object."""
    def __init__(self, wave, throughput):
        self.wave = numpy.array(wave)
        self.throughput = numpy.array(throughput)
        self.bluelim = self.wave[0]
        self.redlim = self.wave[-1]
        self.interp = galsim.LookupTable(wave, throughput)

    def __call__(self, wave):
        """ Return throughput of bandpass at given wavelength.
        """
        return self.interp(wave)

    def truncate(self, rel_throughput=None, bluelim=None, redlim=None):
        """ Truncate filter wavelength range.

        @param   bluelim   Truncate blue side of bandpass here.
        @param   redlim    Truncate red side of bandpass here.
        @param   rel_throughput  Truncate wavelength ranges which
                                 have relative throughput less than this value.
        """
        if bluelim is None:
            bluelim = self.bluelim
        if redlim is None:
            redlim = self.redlim
        if rel_throughput is not None:
            mx = self.throughput.max()
            w = (self.throughput > mx*rel_throughput).nonzero()
            bluelim = max([min(self.wave[w]), bluelim])
            redlim = min([max(self.wave[w]), redlim])
        w = (self.wave >= bluelim) & (self.wave <= redlim)
        self.wave = self.wave[w]
        self.throughput = self.throughput[w]
        self.bluelim = self.wave[0]
        self.redlim = self.wave[-1]
        self.interp = galsim.LookupTable(self.wave, self.throughput)

    def AB_zeropoint(self, force_new_zeropoint=False):
        if not (hasattr(self, 'zp') or force_new_zeropoint):
            AB_source = 3631e-23 # 3631 Jy -> erg/s/Hz/cm^2
            c = 29979245800.0 # speed of light in cm/s
            nm_to_cm = 1.0e-7
            # convert AB source from erg/s/Hz/cm^2*cm/s/nm^2 -> erg/s/cm^2/nm
            AB_flambda = AB_source * c / self.wave**2 / nm_to_cm
            AB_photons = galsim.LookupTable(self.wave, AB_flambda * self.wave * self.throughput)
            AB_flux = galsim.integ.int1d(AB_photons, self.bluelim, self.redlim)
            self.zp = -2.5 * numpy.log10(AB_flux)
        return self.zp
