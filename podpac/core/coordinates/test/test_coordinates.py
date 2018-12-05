
import sys
from copy import deepcopy
import json

import pytest
import numpy as np
import xarray as xr
import pandas as pd
from numpy.testing import assert_equal
# from six import string_types

from podpac.core.coordinates.coordinates1d import Coordinates1d
from podpac.core.coordinates.array_coordinates1d import ArrayCoordinates1d
from podpac.core.coordinates.stacked_coordinates import StackedCoordinates
from podpac.core.coordinates.cfunctions import crange, clinspace
from podpac.core.coordinates.coordinates import Coordinates
from podpac.core.coordinates.coordinates import concat

class TestCoordinateCreation(object):
    def test_empty(self):
        c = Coordinates([])
        assert c.dims == tuple()
        assert c.udims == tuple()
        assert c.shape == tuple()
        assert c.ndim == 0
        assert c.size == 0

    def test_single_dim(self):
        # single value
        date = '2018-01-01'

        c = Coordinates([date], dims=['time'])
        assert c.dims == ('time',)
        assert c.udims == ('time',)
        assert c.shape == (1,)
        assert c.ndim == 1
        assert c.size == 1

        # array
        dates = ['2018-01-01', '2018-01-02']

        c = Coordinates([dates], dims=['time'])
        assert c.udims == ('time',)
        assert c.dims == ('time',)
        assert c.shape == (2,)
        assert c.ndim == 1
        assert c.size == 2

        c = Coordinates([np.array(dates).astype(np.datetime64)], dims=['time'])
        assert c.dims == ('time',)
        assert c.udims == ('time',)
        assert c.shape == (2,)
        assert c.ndim == 1

        c = Coordinates([xr.DataArray(dates).astype(np.datetime64)], dims=['time'])
        assert c.dims == ('time',)
        assert c.udims == ('time',)
        assert c.shape == (2,)
        assert c.ndim == 1
        assert c.size == 2
        
        # use DataArray name, but dims overrides the DataArray name
        c = Coordinates([xr.DataArray(dates, name='time').astype(np.datetime64)])
        assert c.dims == ('time',)
        assert c.udims == ('time',)
        assert c.shape == (2,)
        assert c.ndim == 1
        assert c.size == 2

        c = Coordinates([xr.DataArray(dates, name='a').astype(np.datetime64)], dims=['time'])
        assert c.dims == ('time',)
        assert c.udims == ('time',)
        assert c.shape == (2,)
        assert c.ndim == 1
        assert c.size == 2

    def test_unstacked(self):
        # single value
        c = Coordinates([0, 10], dims=['lat', 'lon'])
        assert c.dims == ('lat', 'lon')
        assert c.udims == ('lat', 'lon',)
        assert c.shape == (1, 1)
        assert c.ndim == 2
        assert c.size == 1

        # arrays
        lat = [0, 1, 2]
        lon = [10, 20, 30, 40]

        c = Coordinates([lat, lon], dims=['lat', 'lon'])
        assert c.dims == ('lat', 'lon')
        assert c.udims == ('lat', 'lon',)
        assert c.shape == (3, 4)
        assert c.ndim == 2
        assert c.size == 12

        # use DataArray names
        c = Coordinates([xr.DataArray(lat, name='lat'), xr.DataArray(lon, name='lon')])
        assert c.dims == ('lat', 'lon')
        assert c.udims == ('lat', 'lon',)
        assert c.shape == (3, 4)
        assert c.ndim == 2
        assert c.size == 12

        # dims overrides the DataArray names
        c = Coordinates([xr.DataArray(lat, name='a'), xr.DataArray(lon, name='b')], dims=['lat', 'lon'])
        assert c.dims == ('lat', 'lon')
        assert c.udims == ('lat', 'lon',)
        assert c.shape == (3, 4)
        assert c.ndim == 2
        assert c.size == 12

    def test_stacked(self):
        # single value
        c = Coordinates([[0, 10]], dims=['lat_lon'])
        assert c.dims == ('lat_lon',)
        assert c.udims == ('lat', 'lon',)
        assert c.shape == (1,)
        assert c.ndim == 1
        assert c.size == 1

        # arrays
        lat = [0, 1, 2]
        lon = [10, 20, 30]
        c = Coordinates([[lat, lon]], dims=['lat_lon'])
        assert c.dims == ('lat_lon',)
        assert c.udims == ('lat', 'lon',)
        assert c.shape == (3,)
        assert c.ndim == 1
        assert c.size == 3

        # TODO lat_lon MultiIndex

    def test_mixed(self):
        lat = [0, 1, 2]
        lon = [10, 20, 30]
        dates = ['2018-01-01', '2018-01-02']

        c = Coordinates([[lat, lon], dates], dims=['lat_lon', 'time'])
        assert c.dims == ('lat_lon', 'time')
        assert c.udims == ('lat', 'lon', 'time')
        assert c.shape == (3, 2)
        assert c.ndim == 2
        assert c.size == 6

    def test_invalid_dims(self):
        lat = [0, 1, 2]
        lon = [10, 20, 30]
        dates = ['2018-01-01', '2018-01-02']

        with pytest.raises(TypeError, match="Invalid dims type"):
            Coordinates([dates], dims='time')

        with pytest.raises(ValueError, match="coords and dims size mismatch"):
            Coordinates(dates, dims=['time'])

        with pytest.raises(ValueError, match="coords and dims size mismatch"):
            Coordinates([lat, lon, dates], dims=['lat_lon', 'time'])
        
        with pytest.raises(ValueError, match="coords and dims size mismatch"):
            Coordinates([[lat, lon], dates], dims=['lat', 'lon', 'dates'])

        with pytest.raises(ValueError, match="coords and dims size mismatch"):
            Coordinates([lat, lon], dims=['lat_lon'])
        
        with pytest.raises(ValueError, match="coords and dims size mismatch"):
            Coordinates([[lat, lon]], dims=['lat', 'lon'])
        
        with pytest.raises(ValueError, match="coords and dims size mismatch"):
            Coordinates([lat, lon], dims=['lat_lon'])
        
        with pytest.raises(ValueError, match="Invalid coordinate values"):
            Coordinates([[lat, lon]], dims=['lat'])

        with pytest.raises(TypeError, match="Cannot get dim for coordinates at position"):
            # this doesn't work because lat and lon are not named BaseCoordinates/xarray objects
            Coordinates([lat, lon])

        with pytest.raises(ValueError, match="Duplicate dimension name"):
            Coordinates([lat, lon], dims=['lat', 'lat'])

    def test_invalid_coords(self):
        lat = [0, 1, 2]
        lon = [10, 20, 30]
        dates = ['2018-01-01', '2018-01-02']

        with pytest.raises(TypeError, match="Invalid coords"):
            Coordinates({'lat': lat, 'lon': lon})

    def test_base_coordinates(self):
        lat = [0, 1, 2]
        lon = [10, 20, 30]
        dates = ['2018-01-01', '2018-01-02']

        c = Coordinates([
            StackedCoordinates([
                ArrayCoordinates1d(lat, name='lat'),
                ArrayCoordinates1d(lon, name='lon')]),
            ArrayCoordinates1d(dates, name='time')])

        assert c.dims == ('lat_lon', 'time')
        assert c.shape == (3, 2)

        # TODO default and overridden properties

    def test_grid(self):
        # array
        lat = [0, 1, 2]
        lon = [10, 20, 30, 40]
        dates = ['2018-01-01', '2018-01-02']
            
        c = Coordinates.grid(lat=lat, lon=lon, time=dates, dims=['time', 'lat', 'lon'])
        assert c.dims == ('time', 'lat', 'lon')
        assert c.udims == ('time', 'lat', 'lon')
        assert c.shape == (2, 3, 4)
        assert c.ndim == 3
        assert c.size == 24

        # size
        lat = (0, 1, 3)
        lon = (10, 40, 4)
        dates = ('2018-01-01', '2018-01-05', 5)

        c = Coordinates.grid(lat=lat, lon=lon, time=dates, dims=['time', 'lat', 'lon'])
        assert c.dims == ('time', 'lat', 'lon')
        assert c.udims == ('time', 'lat', 'lon')
        assert c.shape == (5, 3, 4)
        assert c.ndim == 3
        assert c.size == 60

        # step
        lat = (0, 1, 0.5)
        lon = (10, 40, 10.0)
        dates = ('2018-01-01', '2018-01-05', '1,D')
        
        c = Coordinates.grid(lat=lat, lon=lon, time=dates, dims=['time', 'lat', 'lon'])
        assert c.dims == ('time', 'lat', 'lon')
        assert c.udims == ('time', 'lat', 'lon')
        assert c.shape == (5, 3, 4)
        assert c.ndim == 3
        assert c.size == 60

    def test_points(self):
        lat = [0, 1, 2]
        lon = [10, 20, 30]
        dates = ['2018-01-01', '2018-01-02', '2018-01-03']

        c = Coordinates.points(lat=lat, lon=lon, time=dates, dims=['time', 'lat', 'lon'])
        assert c.dims == ('time_lat_lon',)
        assert c.udims == ('time', 'lat', 'lon')
        assert c.shape == (3,)
        assert c.ndim == 1
        assert c.size == 3

    def test_grid_points_order(self):
        lat = [0, 1, 2]
        lon = [10, 20, 30, 40]
        dates = ['2018-01-01', '2018-01-02']

        with pytest.raises(ValueError):
            Coordinates.grid(lat=lat, lon=lon, time=dates, dims=['lat', 'lon'])

        with pytest.raises(ValueError):
            Coordinates.grid(lat=lat, lon=lon, dims=['lat', 'lon', 'time'])

        if sys.version < '3.6':
            with pytest.raises(TypeError):
                Coordinates.grid(lat=lat, lon=lon, time=dates)
        else:
            Coordinates.grid(lat=lat, lon=lon, time=dates)

    def test_from_xarray(self):
        lat = [0, 1, 2]
        lon = [10, 20, 30]
        dates = ['2018-01-01', '2018-01-02']

        c = Coordinates([
            StackedCoordinates([
                ArrayCoordinates1d(lat, name='lat'),
                ArrayCoordinates1d(lon, name='lon')]),
            ArrayCoordinates1d(dates, name='time')])

        # from xarray
        c2 = Coordinates.from_xarray(c.coords)
        assert c2.dims == c.dims
        assert c2.shape == c.shape
        assert isinstance(c2['lat_lon'], StackedCoordinates)
        assert isinstance(c2['time'], Coordinates1d)
        np.testing.assert_equal(c2.coords['lat'].data, np.array(lat, dtype=float))
        np.testing.assert_equal(c2.coords['lon'].data, np.array(lon, dtype=float))
        np.testing.assert_equal(c2.coords['time'].data, np.array(dates).astype(np.datetime64))

        # invalid
        with pytest.raises(TypeError, match="Coordinates.from_xarray expects xarray DataArrayCoordinates"):
            Coordinates.from_xarray([0, 10])

class TestCoordinatesDefinition(object):
    coords = Coordinates(
        [[[0, 1, 2], [10, 20, 30]], ['2018-01-01', '2018-01-02'], crange(0, 10, 0.5)],
        dims=['lat_lon', 'time', 'alt'])

    def test_definition(self):
        d = self.coords.definition
        c = Coordinates.from_definition(d)

        assert isinstance(c, Coordinates)
        assert c.dims == self.coords.dims
        assert_equal(c['lat'].coordinates, self.coords['lat'].coordinates)
        assert_equal(c['lon'].coordinates, self.coords['lon'].coordinates)
        assert_equal(c['time'].coordinates, self.coords['time'].coordinates)
        assert_equal(c['alt'].coordinates, self.coords['alt'].coordinates)

        with pytest.raises(TypeError, match="Could not parse coordinates definition of type"):
            Coordinates.from_definition({'lat': [0, 1, 2]})

        with pytest.raises(ValueError, match="Could not parse coordinates definition item"):
            Coordinates.from_definition([{"data": [0, 1, 2]}])

    def test_json(self):
        s = self.coords.json
        json.loads(s)
        c = Coordinates.from_json(s)

        assert isinstance(c, Coordinates)
        assert c.dims == self.coords.dims
        assert_equal(c['lat'].coordinates, self.coords['lat'].coordinates)
        assert_equal(c['lon'].coordinates, self.coords['lon'].coordinates)
        assert_equal(c['time'].coordinates, self.coords['time'].coordinates)
        assert_equal(c['alt'].coordinates, self.coords['alt'].coordinates)

class TestCoordinatesProperties(object):
    def test_xarray_coords(self):
        lat = [0, 1, 2]
        lon = [10, 20, 30]
        dates = ['2018-01-01', '2018-01-02']

        c = Coordinates([
            StackedCoordinates([
                ArrayCoordinates1d(lat, name='lat'),
                ArrayCoordinates1d(lon, name='lon')]),
            ArrayCoordinates1d(dates, name='time')])
        
        assert isinstance(c.coords, xr.core.coordinates.DataArrayCoordinates)
        assert c.coords.dims == ('lat_lon', 'time')
        np.testing.assert_equal(c.coords['lat'].data, np.array(lat, dtype=float))
        np.testing.assert_equal(c.coords['lon'].data, np.array(lon, dtype=float))
        np.testing.assert_equal(c.coords['time'].data, np.array(dates).astype(np.datetime64))

    def test_properties(self):
        # TODO
        pass

    def test_gdal_crs(self):
        # TODO
        pass

    # TODO update or remove
    # def test_ctype(self):
    #     # default
    #     coord = Coordinate()
    #     coord.ctype == 'segment'
        
    #     # init
    #     coord = Coordinate(ctype='segment')
    #     coord.ctype == 'segment'

    #     coord = Coordinate(ctype='point')
    #     coord.ctype == 'point'

    #     with pytest.raises(tl.TraitError):
    #         Coordinate(ctype='abc')

    #     # propagation
    #     coord = Coordinate(lat=[0.2, 0.4])
    #     coord._coords['lat'].ctype == 'segment'

    #     coord = Coordinate(lat=[0.2, 0.4], ctype='segment')
    #     coord._coords['lat'].ctype == 'segment'

    #     coord = Coordinate(lat=[0.2, 0.4], ctype='point')
    #     coord._coords['lat'].ctype == 'point'

    # TODO update or remove
    # def test_segment_position(self):
    #     # default
    #     coord = Coordinate()
    #     coord.segment_position == 0.5
        
    #     # init
    #     coord = Coordinate(segment_position=0.3)
    #     coord.segment_position == 0.3

    #     with pytest.raises(tl.TraitError):
    #         Coordinate(segment_position='abc')

    #     # propagation
    #     coord = Coordinate(lat=[0.2, 0.4])
    #     coord._coords['lat'].segment_position == 0.5

    #     coord = Coordinate(lat=[0.2, 0.4], segment_position=0.3)
    #     coord._coords['lat'].segment_position == 0.3
        
    # TODO update or remove
    # def test_coord_ref_sys(self):
    #     # default
    #     coord = Coordinate()
    #     assert coord.coord_ref_sys == 'WGS84'
    #     assert coord.gdal_crs == 'EPSG:4326'

    #     # init
    #     coord = Coordinate(coord_ref_sys='SPHER_MERC')
    #     assert coord.coord_ref_sys == 'SPHER_MERC'
    #     assert coord.gdal_crs == 'EPSG:3857'

    #     # propagation
    #     coord = Coordinate(lat=[0.2, 0.4])
    #     coord._coords['lat'].coord_ref_sys == 'WGS84'

    #     coord = Coordinate(lat=[0.2, 0.4], coord_ref_sys='SPHER_MERC')
    #     coord._coords['lat'].coord_ref_sys == 'SPHER_MERC'

    def test_distance_units(self):
        pass

class TestCoordinatesDict(object):
    coords = Coordinates([[[0, 1, 2], [10, 20, 30]], ['2018-01-01', '2018-01-02']], dims=['lat_lon', 'time'])

    def test_keys(self):
        assert [dim for dim in self.coords.keys()] == ['lat_lon', 'time']

    def test_values(self):
        assert [c for c in self.coords.values()] == [self.coords['lat_lon'], self.coords['time']]

    def test_items(self):
        assert [dim for dim, c in self.coords.items()] == ['lat_lon', 'time']
        assert [c for dim, c in self.coords.items()] == [self.coords['lat_lon'], self.coords['time']]

    def test_iter(self):
        assert [dim for dim in self.coords] == ['lat_lon', 'time']

    def test_getitem(self):
        lat = ArrayCoordinates1d([0, 1, 2], name='lat')
        lon = ArrayCoordinates1d([10, 20, 30], name='lon')
        time = ArrayCoordinates1d(['2018-01-01', '2018-01-02'], name='time')
        lat_lon = StackedCoordinates([lat, lon])
        coords = Coordinates([lat_lon, time])

        assert coords['lat_lon'] == lat_lon
        assert coords['time'] == time
        assert coords['lat'] == lat
        assert coords['lon'] == lon

        with pytest.raises(KeyError, match="Dimension 'alt' not found in Coordinates"):
            coords['alt']

    def test_get(self):
        assert self.coords.get('lat_lon') is self.coords['lat_lon']
        assert self.coords.get('lat') is self.coords['lat']
        assert self.coords.get('alt') == None
        assert self.coords.get('alt', 'DEFAULT') == 'DEFAULT'

    def test_setitem(self):
        self.coords['time'] = ArrayCoordinates1d([1, 2, 3])
        self.coords['time'] = ArrayCoordinates1d([1, 2, 3], name='time')
        self.coords['time'] = [1, 2, 3]

        self.coords['lat_lon'] == clinspace((0, 1), (10, 20), 5)

        with pytest.raises(KeyError, match="Cannot set dimension"):
            self.coords['alt'] = ArrayCoordinates1d([1, 2, 3], name='alt')

        with pytest.raises(KeyError, match="Cannot set dimension"):
            self.coords['alt'] = ArrayCoordinates1d([1, 2, 3], name='lat')
        
        with pytest.raises(ValueError, match="Dimension name mismatch"):
            self.coords['time'] = ArrayCoordinates1d([1, 2, 3], name='alt')

    def test_delitem(self):
        # unstacked
        coords = deepcopy(self.coords)
        del coords['time']
        assert coords.dims == ('lat_lon',)

        # stacked
        coords = deepcopy(self.coords)
        del coords['lat_lon']
        assert coords.dims == ('time',)

        # missing 
        coords = deepcopy(self.coords)
        with pytest.raises(KeyError, match="Cannot delete dimension 'alt' in Coordinates"):
            del coords['alt']

        # part of stacked dimension
        coords = deepcopy(self.coords)
        with pytest.raises(KeyError, match="Cannot delete dimension 'lat' in Coordinates"):
            del coords['lat']

    def test_update(self):
        # add a new dimension
        coords = deepcopy(self.coords)
        c = Coordinates([[100, 200, 300]], dims=['alt'])
        coords.update(c)
        assert coords.dims == ('lat_lon', 'time', 'alt')
        assert coords['lat_lon'] == self.coords['lat_lon']
        assert coords['time'] == self.coords['time']
        assert coords['alt'] == c['alt']

        # overwrite a dimension
        coords = deepcopy(self.coords)
        c = Coordinates([[100, 200, 300]], dims=['time'])
        coords.update(c)
        assert coords.dims == ('lat_lon', 'time')
        assert coords['lat_lon'] == self.coords['lat_lon']
        assert coords['time'] == c['time']

        # overwrite a stacked dimension
        coords = deepcopy(self.coords)
        c = Coordinates([clinspace((0, 1), (10, 20), 5)], dims=['lat_lon'])
        coords.update(c)
        assert coords.dims == ('lat_lon', 'time')
        assert coords['lat_lon'] == c['lat_lon']
        assert coords['time'] == self.coords['time']

        # mixed
        coords = deepcopy(self.coords)
        c = Coordinates([clinspace((0, 1), (10, 20), 5), [100, 200, 300]], dims=['lat_lon', 'alt'])
        coords.update(c)
        assert coords.dims == ('lat_lon', 'time', 'alt')
        assert coords['lat_lon'] == c['lat_lon']
        assert coords['time'] == self.coords['time']
        assert coords['alt'] == c['alt']

        # invalid
        coords = deepcopy(self.coords)
        with pytest.raises(TypeError, match="Cannot update Coordinates with object of type"):
            coords.update({'time': [1, 2, 3]})

        # duplicate dimension
        coords = deepcopy(self.coords)
        c = Coordinates([[0, 0.1, 0.2]], dims=['lat'])
        with pytest.raises(ValueError, match="Duplicate dimension name 'lat'"):
            coords.update(c)

    def test_len(self):
        assert len(self.coords) == 2

class TestCoordinatesMethods(object):
    def test_drop(self):
        pass

    def test_udrop(self):
        pass

    def test_unique(self):
        pass

    def test_unstack(self):
        pass

    def test_iterchunks(self):
        pass
        # coord = Coordinate(
        #     lat=(0, 1, 100),
        #     lon=(0, 1, 200),
        #     time=['2018-01-01', '2018-01-02'],
        #     order=['lat', 'lon', 'time'])
        
        # for chunk in coord.iterchunks(shape=(10, 10, 10)):
        #     assert chunk.shape == (10, 10, 2)

        # for chunk, slices in coord.iterchunks(shape=(10, 10, 10), return_slices=True):
        #     assert isinstance(slices, tuple)
        #     assert len(slices) == 3
        #     assert isinstance(slices[0], slice)
        #     assert isinstance(slices[1], slice)
        #     assert isinstance(slices[2], slice)
        #     assert chunk.shape == (10, 10, 2)

    def test_tranpose(self):
        pass
        # coord = Coordinate(
        #     lat=[0.2, 0.4],
        #     lon=[0.3, -0.1],
        #     time=['2018-01-01', '2018-01-02'],
        #     order=['lat', 'lon', 'time'])

        # transposed = coord.transpose('lon', 'lat', 'time', inplace=False)
        # assert coord.dims == ['lat', 'lon', 'time']
        # assert transposed.dims == ['lon', 'lat', 'time']

        # transposed = coord.transpose(inplace=False)
        # assert coord.dims == ['lat', 'lon', 'time']
        # assert transposed.dims == ['time', 'lon', 'lat']

        # transposed = coord.transpose('lon', 'lat', 'time')
        # assert coord.dims == ['lat', 'lon', 'time']
        # assert transposed.dims == ['lon', 'lat', 'time']

        # # TODO not working
        # # coord.transpose('lon', 'lat', 'time', inplace=True)
        # # assert coord.dims == ['lon', 'lat', 'time']

        # # TODO check not implemented yet
        # # with pytest.raises(ValueError):
        # #     coord.transpose('lon', 'lat')

        # # TODO check not implemented yet
        # # with pytest.raises(ValueError):
        # #     coord.transpose('lon', 'lat', inplace=True)

class TestCoordinatesSpecial(object):
    def test_repr(self):
        pass

    def test_eq(self):
        c1 = Coordinates([[[0, 1, 2], [10, 20, 30]], ['2018-01-01', '2018-01-02']], dims=['lat_lon', 'time'])
        c2 = Coordinates([[[0, 1, 2], [10, 20, 30]], ['2018-01-01', '2018-01-02']], dims=['lat_lon', 'time'])
        c3 = Coordinates([[[0, 1, 2], [10, 20, 30]], ['2018-01-01', '2018-01-02']], dims=['lat_lon', 'time'], ctype='point')
        c4 = Coordinates([[[0, 2, 1], [10, 20, 30]], ['2018-01-01', '2018-01-02']], dims=['lat_lon', 'time'])
        c5 = Coordinates([[[0, 1, 2], [10, 20, 30]], ['2018-01-01', '2018-01-02']], dims=['lon_lat', 'time'])
        c6 = Coordinates([[[0, 1, 2], [10, 20, 30]], ['2018-01-01']], dims=['lat_lon', 'time'])
        c7 = Coordinates([[0, 1, 2], [10, 20, 30], ['2018-01-01', '2018-01-02']], dims=['lat', 'lon', 'time'])

        assert c1 == c1
        assert c1 == c2
        assert c1 == deepcopy(c1)

        assert c1 != c3
        assert c1 != c4
        assert c1 != c5
        assert c1 != c6
        assert c1 != c7
        assert c1 != None

    def test_hash(self):
        c1 = Coordinates([[[0, 1, 2], [10, 20, 30]], ['2018-01-01', '2018-01-02']], dims=['lat_lon', 'time'])
        c2 = Coordinates([[[0, 1, 2], [10, 20, 30]], ['2018-01-01', '2018-01-02']], dims=['lat_lon', 'time'], ctype='point')
        c3 = Coordinates([[[0, 2, 1], [10, 20, 30]], ['2018-01-01', '2018-01-02']], dims=['lat_lon', 'time'])
        c4 = Coordinates([[[0, 1, 2], [10, 20, 30]], ['2018-01-01', '2018-01-02']], dims=['lon_lat', 'time'])
        c5 = Coordinates([[[0, 1, 2], [10, 20, 30]], ['2018-01-01']], dims=['lat_lon', 'time'])
        c6 = Coordinates([[0, 1, 2], [10, 20, 30], ['2018-01-01', '2018-01-02']], dims=['lat', 'lon', 'time'])
        
        assert c1.hash == c1.hash
        assert c1.hash == deepcopy(c1).hash
        
        assert c1.hash != c2.hash
        assert c1.hash != c3.hash
        assert c1.hash != c4.hash
        assert c1.hash != c5.hash
        assert c1.hash != c6.hash

def test_merge_dims():
    pass

def test_concat():
    pass

#     def test_add(self):
#         coord1 = Coordinate(
#             lat=[0.2, 0.4, 0.5],
#             lon=[0.3, -0.1, 0.5],
#             order=['lat', 'lon'])

#         coord2 = Coordinate(
#             lat=[0.2, 0.3],
#             lon=[0.3, 0.0],
#             time=['2018-01-01', '2018-01-02'],
#             order=['lat', 'lon', 'time'])

#         coord3 = Coordinate(
#             lat_lon=([0.2, 0.3], [0.3, 0.0]),
#             order=['lat_lon'])

#         coord = coord1 + coord2
#         assert coord.shape == (5, 5, 2)

#         # TODO not working?
#         # coord = coord1.add_unique(coord2)
#         # assert coord.shape == (4, 4, 2)

#         with pytest.raises(TypeError):
#             coord1 + [1, 2]

#         with pytest.raises(ValueError):
#             coord1 + coord3

def test_concat_stacked_datetimes():
    c1 = Coordinates([[0, 0.5, '2018-01-01']], dims=['lat_lon_time'])
    c2 = Coordinates([[1, 1.5, '2018-01-02']], dims=['lat_lon_time'])
    c = concat([c1, c2])
    np.testing.assert_array_equal(c['lat'].coordinates, np.array([0.0, 1.0]))
    np.testing.assert_array_equal(c['lon'].coordinates, np.array([0.5, 1.5]))
    np.testing.assert_array_equal(
        c['time'].coordinates,
        np.array(['2018-01-01', '2018-01-02']).astype(np.datetime64))

    c1 = Coordinates([[0, 0.5, '2018-01-01T01:01:01']], dims=['lat_lon_time'])
    c2 = Coordinates([[1, 1.5, '2018-01-01T01:01:02']], dims=['lat_lon_time'])
    c = concat([c1, c2])
    np.testing.assert_array_equal(c['lat'].coordinates, np.array([0.0, 1.0]))
    np.testing.assert_array_equal(c['lon'].coordinates, np.array([0.5, 1.5]))
    np.testing.assert_array_equal(
        c['time'].coordinates,
        np.array(['2018-01-01T01:01:01', '2018-01-01T01:01:02']).astype(np.datetime64))

def test_union():
    pass