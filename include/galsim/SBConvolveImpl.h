/* -*- c++ -*-
 * Copyright (c) 2012-2016 by the GalSim developers team on GitHub
 * https://github.com/GalSim-developers
 *
 * This file is part of GalSim: The modular galaxy image simulation toolkit.
 * https://github.com/GalSim-developers/GalSim
 *
 * GalSim is free software: redistribution and use in source and binary forms,
 * with or without modification, are permitted provided that the following
 * conditions are met:
 *
 * 1. Redistributions of source code must retain the above copyright notice, this
 *    list of conditions, and the disclaimer given in the accompanying LICENSE
 *    file.
 * 2. Redistributions in binary form must reproduce the above copyright notice,
 *    this list of conditions, and the disclaimer given in the documentation
 *    and/or other materials provided with the distribution.
 */

#ifndef GalSim_SBConvolveImpl_H
#define GalSim_SBConvolveImpl_H

#include "SBProfileImpl.h"
#include "SBConvolve.h"

namespace galsim {

    class SBConvolve::SBConvolveImpl: public SBProfileImpl
    {
    public:

        SBConvolveImpl(const std::list<SBProfile>& slist, bool real_space,
                       const GSParamsPtr& gsparams);
        ~SBConvolveImpl() {}

        std::list<SBProfile> getObjs() const { return _plist; }
        bool isRealSpace() const { return _real_space; }

        void add(const SBProfile& rhs);

        // Do the real-space convolution to calculate this.
        double xValue(const Position<double>& p) const;

        std::complex<double> kValue(const Position<double>& k) const;

        bool isAxisymmetric() const { return _isStillAxisymmetric; }
        bool hasHardEdges() const { return false; }
        bool isAnalyticX() const { return _real_space; }
        bool isAnalyticK() const { return true; }    // convolvees must all meet this
        double maxK() const { return _minMaxK; }
        double stepK() const { return _netStepK; }

        void getXRange(double& xmin, double& xmax, std::vector<double>& splits) const
        {
            // Getting the splits correct would require a bit of work.
            // So if we ever do real-space convolutions where one of the elements
            // is (or includes) another convolution, we might want to rework this a
            // bit.  But I don't think this is really every going to be used, so
            // I didn't try to get that right.  (Note: ignoring the splits won't be
            // wrong -- just not optimal.)
            std::vector<double> splits0;
            ConstIter pptr = _plist.begin();
            pptr->getXRange(xmin,xmax,splits0);
            for (++pptr; pptr!=_plist.end(); ++pptr) {
                double xmin_1, xmax_1;
                pptr->getXRange(xmin_1,xmax_1,splits0);
                xmin += xmin_1;
                xmax += xmax_1;
            }
        }

        void getYRange(double& ymin, double& ymax, std::vector<double>& splits) const
        {
            std::vector<double> splits0;
            ConstIter pptr = _plist.begin();
            pptr->getYRange(ymin,ymax,splits0);
            for (++pptr; pptr!=_plist.end(); ++pptr) {
                double ymin_1, ymax_1;
                pptr->getYRange(ymin_1,ymax_1,splits0);
                ymin += ymin_1;
                ymax += ymax_1;
            }
        }

        void getYRangeX(double x, double& ymin, double& ymax, std::vector<double>& splits) const
        {
            std::vector<double> splits0;
            ConstIter pptr = _plist.begin();
            pptr->getYRangeX(x,ymin,ymax,splits0);
            for (++pptr; pptr!=_plist.end(); ++pptr) {
                double ymin_1, ymax_1;
                pptr->getYRangeX(x,ymin_1,ymax_1,splits0);
                ymin += ymin_1;
                ymax += ymax_1;
            }
        }

        Position<double> centroid() const
        { return Position<double>(_x0, _y0); }

        double getFlux() const { return _fluxProduct; }

        double getPositiveFlux() const;
        double getNegativeFlux() const;
        /**
         * @brief Shoot photons through this SBConvolve.
         *
         * SBConvolve will add the displacements of photons generated by each convolved component.
         * Their fluxes are multiplied (modulo factor of N).
         * @param[in] N Total number of photons to produce.
         * @param[in] ud UniformDeviate that will be used to draw photons from distribution.
         * @returns PhotonArray containing all the photons' info.
         */
        boost::shared_ptr<PhotonArray> shoot(int N, UniformDeviate ud) const;

        // Overrides for better efficiency
        void fillKValue(tmv::MatrixView<std::complex<double> > val,
                        double kx0, double dkx, int izero,
                        double ky0, double dky, int jzero) const;
        void fillKValue(tmv::MatrixView<std::complex<double> > val,
                        double kx0, double dkx, double dkxy,
                        double ky0, double dky, double dkyx) const;

        std::string serialize() const;

    private:
        typedef std::list<SBProfile>::iterator Iter;
        typedef std::list<SBProfile>::const_iterator ConstIter;

        std::list<SBProfile> _plist; ///< list of profiles to convolve
        double _x0; ///< Centroid position in x.
        double _y0; ///< Centroid position in y.
        bool _isStillAxisymmetric; ///< Is output SBProfile shape still circular?
        double _minMaxK; ///< Minimum maxK() of the convolved SBProfiles.
        double _netStepK; ///< Minimum stepK() of the convolved SBProfiles.
        double _sumMinX; ///< sum of minX() of the convolved SBProfiles.
        double _sumMaxX; ///< sum of maxX() of the convolved SBProfiles.
        double _sumMinY; ///< sum of minY() of the convolved SBProfiles.
        double _sumMaxY; ///< sum of maxY() of the convolved SBProfiles.
        double _fluxProduct; ///< Flux of the product.
        bool _real_space; ///< Whether to do convolution as an integral in real space.

        void initialize();

        // Copy constructor and op= are undefined.
        SBConvolveImpl(const SBConvolveImpl& rhs);
        void operator=(const SBConvolveImpl& rhs);
    };

    class SBAutoConvolve::SBAutoConvolveImpl: public SBProfileImpl
    {
    public:

        SBAutoConvolveImpl(const SBProfile& s, bool real_space, const GSParamsPtr& gsparams);

        ~SBAutoConvolveImpl() {}

        SBProfile getObj() const { return _adaptee; }
        bool isRealSpace() const { return _real_space; }

        double xValue(const Position<double>& p) const;

        std::complex<double> kValue(const Position<double>& k) const
        { return SQR(_adaptee.kValue(k)); }

        bool isAxisymmetric() const { return _adaptee.isAxisymmetric(); }
        bool hasHardEdges() const { return false; }
        bool isAnalyticX() const { return _real_space; }
        bool isAnalyticK() const { return true; }
        double maxK() const { return _adaptee.maxK(); }
        double stepK() const { return _adaptee.stepK() / sqrt(2.); }

        Position<double> centroid() const { return _adaptee.centroid() * 2.; }

        double getFlux() const { return SQR(_adaptee.getFlux()); }

        double getPositiveFlux() const;
        double getNegativeFlux() const;

        boost::shared_ptr<PhotonArray> shoot(int N, UniformDeviate ud) const;

        // Overrides for better efficiency
        void fillKValue(tmv::MatrixView<std::complex<double> > val,
                        double kx0, double dkx, int izero,
                        double ky0, double dky, int jzero) const;
        void fillKValue(tmv::MatrixView<std::complex<double> > val,
                        double kx0, double dkx, double dkxy,
                        double ky0, double dky, double dkyx) const;

        const SBProfile& getAdaptee() const { return _adaptee; }

        std::string serialize() const;

    private:
        SBProfile _adaptee;
        bool _real_space;

        template <typename T>
        static T SQR(T x) { return x*x; }

        // Copy constructor and op= are undefined.
        SBAutoConvolveImpl(const SBAutoConvolveImpl& rhs);
        void operator=(const SBAutoConvolveImpl& rhs);
    };

    class SBAutoCorrelate::SBAutoCorrelateImpl: public SBProfileImpl
    {
    public:

        SBAutoCorrelateImpl(const SBProfile& s, bool real_space, const GSParamsPtr& gsparams);

        ~SBAutoCorrelateImpl() {}

        SBProfile getObj() const { return _adaptee; }
        bool isRealSpace() const { return _real_space; }

        double xValue(const Position<double>& p) const;

        std::complex<double> kValue(const Position<double>& k) const
        { return NORM(_adaptee.kValue(k)); }

        bool isAxisymmetric() const { return _adaptee.isAxisymmetric(); }
        bool hasHardEdges() const { return false; }
        bool isAnalyticX() const { return _real_space; }
        bool isAnalyticK() const { return true; }
        double maxK() const { return _adaptee.maxK(); }
        double stepK() const { return _adaptee.stepK() / sqrt(2.); }

        Position<double> centroid() const { return Position<double>(0., 0.); }

        double getFlux() const { return SQR(_adaptee.getFlux()); }

        double getPositiveFlux() const;
        double getNegativeFlux() const;

        boost::shared_ptr<PhotonArray> shoot(int N, UniformDeviate ud) const;

        // Overrides for better efficiency
        void fillKValue(tmv::MatrixView<std::complex<double> > val,
                        double kx0, double dkx, int izero,
                        double ky0, double dky, int jzero) const;
        void fillKValue(tmv::MatrixView<std::complex<double> > val,
                        double kx0, double dkx, double dkxy,
                        double ky0, double dky, double dkyx) const;

        const SBProfile& getAdaptee() const { return _adaptee; }

        std::string serialize() const;

    private:
        SBProfile _adaptee;
        bool _real_space;

        template <typename T>
        static T SQR(T x) { return x*x; }
        template <typename T>
        static T NORM(std::complex<T> x) { return std::norm(x); }

        // Copy constructor and op= are undefined.
        SBAutoCorrelateImpl(const SBAutoCorrelateImpl& rhs);
        void operator=(const SBAutoCorrelateImpl& rhs);
    };

}

#endif
