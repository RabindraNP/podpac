"""
OGC-compliant datasources over HTTP
"""

from __future__ import division, unicode_literals, print_function, absolute_import

import os
import re
from copy import deepcopy
from io import BytesIO

import numpy as np
import traitlets as tl

from podpac.core.settings import settings
from podpac.core.utils import common_doc, cached_property
from podpac.core.data.datasource import DataSource
from podpac.core.interpolation.interpolation import InterpolationMixin
from podpac.core.node import Node, NodeException
from podpac.core.coordinates import Coordinates
from podpac.core.coordinates import StackedCoordinates, Coordinates1d, UniformCoordinates1d, ArrayCoordinates1d

# Optional dependencies
from lazy_import import lazy_module, lazy_class

bs4 = lazy_module("bs4")
lxml = lazy_module("lxml")  # used by bs4 so want to check if it's available
owslib_wcs = lazy_module("owslib.wcs")
rasterio = lazy_module("rasterio")


# TODO time coordinates (need to find a WCS source for this)
# TODO crs
# TODO tests
# TODO max_size (or is this something a particular composited data source should handle?)


class WCSError(NodeException):
    pass


class WCSBase(DataSource):
    source = tl.Unicode().tag(attr=True)
    layer = tl.Unicode().tag(attr=True)
    version = tl.Unicode(default_value="1.0.0").tag(attr=True)  # TODO 1.0.0 deprecated?

    # max_size = tl.Long(default_value=None, allow_none=True) # TODO
    format = tl.Unicode(default_value="geotiff")
    crs = tl.Unicode(default_value="EPSG:4326")

    _repr_keys = ["source", "layer"]

    _requested_coordinates = tl.Instance(Coordinates, allow_none=True)
    _evaluated_coordinates = tl.Instance(Coordinates)

    @cached_property
    def client(self):
        return owslib_wcs.WebCoverageService(self.source, version=self.version)

    def get_coordinates(self):
        metadata = self.client.contents[self.layer]

        # TODO select correct boundingbox by crs

        # coordinates
        w, s, e, n = metadata.boundingBoxWGS84
        low = metadata.grid.lowlimits
        high = metadata.grid.highlimits
        xsize = int(high[0]) - int(low[0])
        ysize = int(high[1]) - int(low[1])

        coords = []
        coords.append(UniformCoordinates1d(s, n, size=ysize, name="lat"))
        coords.append(UniformCoordinates1d(w, e, size=xsize, name="lon"))

        if metadata.timepositions or metadata.timelimits:
            # TODO
            raise NotImplemented("TODO")

        return Coordinates(coords, crs=self.crs)

    def _eval(self, coordinates, output=None, _selector=None):
        def selector(rsc, rsci, coordinates):
            # for a uniform grid, use the requested coordinates (the WCS server will interpolate)
            if (
                "lat" in coordinates.dims
                and "lon" in coordinates.dims
                and coordinates["lat"].is_uniform
                and coordinates["lon"].is_uniform
            ):
                return coordinates, tuple(slice(None) for dim in coordinates)

            # otherwise, use the selector or pass through the requested coordinates
            elif _selector:
                return _selector(rsc, rsci, coordinates)
            else:
                return rsc, rsci

        return super()._eval(coordinates, output=None, _selector=selector)

    def _get_data(self, coordinates, coordinates_index):
        """{get_data}

        """

        coordinates = coordinates.transpose("lat", "lon")

        w = coordinates["lon"].start - coordinates["lon"].step / 2.0
        e = coordinates["lon"].stop + coordinates["lon"].step / 2.0
        s = coordinates["lat"].start - coordinates["lat"].step / 2.0
        n = coordinates["lat"].stop + coordinates["lat"].step / 2.0
        width = coordinates["lon"].size
        height = coordinates["lat"].size

        kwargs = {}
        if isinstance(self.interpolation, str):
            kwargs["interpolation"] = self.interpolation

        response = self.client.getCoverage(
            identifier=self.layer,
            bbox=(w, n, e, s),
            width=width,
            height=height,
            crs=self.crs,
            format=self.format,
            version=self.version,
            **kwargs
        )
        content = response.read()

        # check for errors
        xml = bs4.BeautifulSoup(content, "lxml")
        error = xml.find("serviceexception")
        if error:
            raise WCSError(error.text)

        # get data using rasterio
        with rasterio.MemoryFile() as mf:
            mf.write(content)
            dataset = mf.open(driver="GTiff")

        data = dataset.read(1).astype(float)
        return self.create_output_array(coordinates, data=data)

    @staticmethod
    def get_layers(source):
        client = owslib_wcs.WebCoverageService(source)
        return list(client.contents)


class WCS(InterpolationMixin, WCSBase):
    pass
