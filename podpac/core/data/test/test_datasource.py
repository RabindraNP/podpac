"""
Test podpac.core.data.datasource module
"""

import pytest

import numpy as np
import xarray as xr
import traitlets as tl
from xarray.core.coordinates import DataArrayCoordinates

from podpac.core.units import UnitsDataArray
from podpac.core.node import COMMON_NODE_DOC, NodeException
from podpac.core.style import Style
from podpac.core.coordinates import Coordinates, clinspace, crange
from podpac.core.data.datasource import DataSource, COMMON_DATA_DOC, DATA_DOC
from podpac.core.data.types import rasterio
from podpac.core.data import datasource

class MockArrayDataSource(DataSource):
    def get_data(self, coordinates, coordinates_index):
        return self.create_output_array(coordinates, data=self.source[coordinates_index])

class MockDataSource(DataSource):
    data = np.zeros((101, 101))
    data[0, 0] = 10
    data[0, 1] = 1
    data[1, 0] = 5
    data[1, 1] = None

    def get_native_coordinates(self):
        return Coordinates([clinspace(-25, 25, 101), clinspace(-25, 25, 101)], dims=['lat', 'lon'])

    def get_data(self, coordinates, coordinates_index):
        return self.create_output_array(coordinates, data=self.data[coordinates_index])

class MockNonuniformDataSource(DataSource):
    """ Mock Data Source for testing that is non-uniform """

    # mock 3 x 3 grid of random values
    source = np.random.rand(3, 3)
    native_coordinates = Coordinates([[-10, -2, -1], [4, 32, 1]], dims=['lat', 'lon'])

    def get_native_coordinates(self):
        """ """
        return self.native_coordinates

    def get_data(self, coordinates, coordinates_index):
        """ """
        s = coordinates_index
        d = self.create_output_array(coordinates, data=self.source[s])
        return d

class TestDataDocs(object):
    def test_common_data_doc(self):
        # all DATA_DOC keys should be in the COMMON_DATA_DOC
        for key in DATA_DOC:
            assert key in COMMON_DATA_DOC
            assert COMMON_DATA_DOC[key] == DATA_DOC[key]

        # DATA_DOC should overwrite COMMON_NODE_DOC keys
        for key in COMMON_NODE_DOC:
            assert key in COMMON_DATA_DOC

            if key in DATA_DOC:
                assert COMMON_DATA_DOC[key] != COMMON_NODE_DOC[key]
            else:
                assert COMMON_DATA_DOC[key] == COMMON_NODE_DOC[key]

class TestDataSource(object):
    def test_init(self):
        node = DataSource()

    def test_nomethods_must_be_implemented(self):
        node = DataSource()
        
        with pytest.raises(NotImplementedError):
            node.get_native_coordinates()

        with pytest.raises(NotImplementedError):
            node.get_data(None, None)

    def test_set_native_coordinates(self):
        nc = Coordinates([clinspace(0, 50, 101), clinspace(0, 50, 101)], dims=['lat', 'lon'])
        node = DataSource(source='test', native_coordinates=nc)
        assert node.native_coordinates is not None
        
        with pytest.raises(tl.TraitError):
            DataSource(source='test', native_coordinates='not a coordinate')
        
        with pytest.raises(NotImplementedError):
            DataSource(source='test').native_coordinates

    def test_get_native_coordinates(self):
        # get_native_coordinates should set the native_coordinates by default
        node = MockDataSource()
        assert node.native_coordinates is not None
        np.testing.assert_equal(node.native_coordinates['lat'].coordinates, np.linspace(-25, 25, 101))
        np.testing.assert_equal(node.native_coordinates['lon'].coordinates, np.linspace(-25, 25, 101))

        # but don't call get_native_coordinates if the native_coordinates are set explicitly
        nc = Coordinates([clinspace(0, 50, 101), clinspace(0, 50, 101)], dims=['lat', 'lon'])
        node = MockDataSource(native_coordinates=nc)
        assert node.native_coordinates is not None
        np.testing.assert_equal(node.native_coordinates['lat'].coordinates, nc['lat'].coordinates)
        np.testing.assert_equal(node.native_coordinates['lat'].coordinates, nc['lat'].coordinates)

    def test_invalid_interpolation(self):
        with pytest.raises(tl.TraitError):
            MockDataSource(interpolation='myowninterp')

    def test_invalid_nan_vals(self):
        with pytest.raises(tl.TraitError):
            MockDataSource(nan_vals={})

        with pytest.raises(tl.TraitError):
            MockDataSource(nan_vals=10)

    def test_base_definition(self):
        """Test definition property method"""

        # TODO: add interpolation definition testing
        
        node = DataSource(source='test')
        d = node.base_definition

        assert d
        assert 'node' in d
        assert d['source'] == node.source

        class MyDataSource(DataSource):
            source = tl.Unicode().tag(attr=True)

        node = MyDataSource(source='test')
        with pytest.raises(NodeException, match="The 'source' property cannot be tagged as an 'attr'"):
            node.base_definition

    def test_evaluate_at_native_coordinates(self):
        """evaluate node at native coordinates"""

        node = MockDataSource()
        output = node.eval(node.native_coordinates)

        assert isinstance(output, UnitsDataArray)
        assert output.shape == (101, 101)
        assert output[0, 0] == 10
        assert output.lat.shape == (101,)
        assert output.lon.shape == (101,)

        # assert coordinates
        assert isinstance(output.coords, DataArrayCoordinates)
        assert output.coords.dims == ('lat', 'lon')

        # assert attributes
        assert isinstance(output.attrs['layer_style'], Style)

    def test_evaluate_with_output(self):
        node = MockDataSource()

        # initialize a large output array
        fullcoords = Coordinates([crange(20, 30, 1), crange(20, 30, 1)], dims=['lat', 'lon'])
        output = UnitsDataArray(np.ones(fullcoords.shape), coords=fullcoords.coords, dims=fullcoords.dims)
        
        # evaluate a subset of the full coordinates
        coords = Coordinates([fullcoords['lat'][3:8], fullcoords['lon'][3:8]])
        
        # after evaluation, the output should be
        # - the same where it was not evaluated
        # - NaN where it was evaluated but doesn't intersect with the data source
        # - 0 where it was evaluated and does intersect with the data source (because this datasource is all 0)
        expected = output.copy()
        expected[3:8, 3:8] = np.nan
        expected[3:6, 3:6] = 0

        # evaluate the subset coords, passing in the cooresponding slice of the initialized output array
        node.eval(coords, output=output[3:8, 3:8])
        np.testing.assert_equal(output.data, expected.data)

    def test_evaluate_with_output_no_intersect(self):
        # there is a shortcut if there is no intersect, so we test that here
        node = MockDataSource()
        coords = Coordinates([clinspace(30, 40, 10), clinspace(30, 40, 10)], dims=['lat', 'lon'])
        output = UnitsDataArray(np.ones(coords.shape), coords=coords.coords, dims=coords.dims)
        node.eval(coords, output=output)
        np.testing.assert_equal(output.data, np.full(output.shape, np.nan))

    def test_evaluate_with_output_transpose(self):
        # initialize coords with dims=[lon, lat]
        lat = clinspace(10, 20, 11)
        lon = clinspace(10, 15, 6)
        coords = Coordinates([lon, lat], dims=['lon', 'lat'])
        output = UnitsDataArray(np.ones(coords.shape), coords=coords.coords, dims=coords.dims)
        
        # evaluate with dims=[lat, lon], passing in the output
        node = MockDataSource()
        node.eval(coords.transpose('lat', 'lon'), output=output)
        
        # dims should stay in the order of the output, rather than the order of the requested coordinates
        assert output.dims == ('lon', 'lat')

    def test_evaluate_extra_dims(self):
        # drop extra dimension
        node = MockArrayDataSource(
            source=np.empty((3, 2)),
            native_coordinates=Coordinates([[0, 1, 2], [10, 11]], dims=['lat', 'lon']),
            interpolation='nearest_preview')

        output = node.eval(Coordinates([1, 11, '2018-01-01'], dims=['lat', 'lon', 'time']))
        assert output.dims == ('lat', 'lon') # time dropped

        # drop extra stacked dimension if none of its dimensions are needed 
        node = MockArrayDataSource(
            source=np.empty((2)),
            native_coordinates=Coordinates([['2018-01-01', '2018-01-02']], dims=['time']),
            interpolation='nearest_preview')
        
        output = node.eval(Coordinates([[1, 11], '2018-01-01'], dims=['lat_lon', 'time']))
        assert output.dims == ('time',) # lat_lon dropped

        # don't drop extra stacked dimension if any of its dimensions are needed
        # TODO interpolation is not yet implemented
        #node = MockArrayDataSource(
            #source=np.empty(3),
            #native_coordinates=Coordinates([[0, 1, 2]], dims=['lat']))
        #output = node.eval(Coordinates([[1, 11]], dims=['lat_lon']))
        #assert output.dims == ('lat_lon') # lon portion not dropped

    def test_evaluate_missing_dims(self):
        # missing unstacked dimension
        node = MockArrayDataSource(
            source=np.empty((3, 2)),
            native_coordinates=Coordinates([[0, 1, 2], [10, 11]], dims=['lat', 'lon']))

        with pytest.raises(ValueError, match="Cannot evaluate these coordinates.*"):
            node.eval(Coordinates([1], dims=['lat']))
        with pytest.raises(ValueError, match="Cannot evaluate these coordinates.*"):
            node.eval(Coordinates([11], dims=['lon']))
        with pytest.raises(ValueError, match="Cannot evaluate these coordinates.*"):
            node.eval(Coordinates(['2018-01-01'], dims=['time']))

        # missing any part of stacked dimension
        node = MockArrayDataSource(
            source=np.empty(3),
            native_coordinates=Coordinates([[[0, 1, 2], [10, 11, 12]]], dims=['lat_lon']))
        
        with pytest.raises(ValueError, match="Cannot evaluate these coordinates.*"):
            node.eval(Coordinates([1], dims=['time']))

        with pytest.raises(ValueError, match="Cannot evaluate these coordinates.*"):
            node.eval(Coordinates([1], dims=['lat']))

    def test_evaluate_no_overlap(self):
        """evaluate node with coordinates that do not overlap"""

        node = MockDataSource()
        coords = Coordinates([clinspace(-55, -45, 20), clinspace(-55, -45, 20)], dims=['lat', 'lon'])
        output = node.eval(coords)

        assert np.all(np.isnan(output))
    
    def test_nan_vals(self):
        """ evaluate note with nan_vals """

        node = MockDataSource(nan_vals=[10, None])
        output = node.eval(node.native_coordinates)

        assert output.values[np.isnan(output)].shape == (2,)

    def test_get_data_np_array(self):
        class MockDataSourceReturnsArray(MockDataSource):
            def get_data(self, coordinates, coordinates_index):
                return self.data[coordinates_index]

        node = MockDataSourceReturnsArray()
        output = node.eval(node.native_coordinates)

        assert isinstance(output, UnitsDataArray)
        assert node.native_coordinates['lat'].coordinates[4] == output.coords['lat'].values[4]

    def test_get_data_DataArray(self):
        class MockDataSourceReturnsDataArray(MockDataSource):
            def get_data(self, coordinates, coordinates_index):
                return xr.DataArray(self.data[coordinates_index])

        node = MockDataSourceReturnsDataArray()
        output = node.eval(node.native_coordinates)

        assert isinstance(output, UnitsDataArray)
        assert node.native_coordinates['lat'].coordinates[4] == output.coords['lat'].values[4]

class TestInterpolateData(object):
    """test interpolation functions"""

    def test_one_data_point(self):
        """ test when there is only one data point """
        # TODO: as this is currently written, this would never make it to the interpolater
        pass
        
    def test_nearest_preview(self):
        """ test interpolation == 'nearest_preview' """
        source = np.random.rand(5)
        coords_src = Coordinates([clinspace(0, 10, 5,)], dims=['lat'])
        coords_dst = Coordinates([[1, 1.2, 1.5, 5, 9]], dims=['lat'])

        node = MockArrayDataSource(source=source, native_coordinates=coords_src, interpolation='nearest_preview')
        output = node.eval(coords_dst)

        assert isinstance(output, UnitsDataArray)
        assert np.all(output.lat.values == coords_dst.coords['lat'])


    def test_interpolate_time(self):
        """ for now time uses nearest neighbor """

        source = np.random.rand(5)
        coords_src = Coordinates([clinspace(0, 10, 5,)], dims=['time'])
        coords_dst = Coordinates([clinspace(1, 11, 5,)], dims=['time'])

        node = MockArrayDataSource(source=source, native_coordinates=coords_src)
        output = node.eval(coords_dst)

        assert isinstance(output, UnitsDataArray)
        assert np.all(output.time.values == coords_dst.coords['time'])

    def test_interpolate_lat_time(self):
        """interpolate with n dims and time"""
        pass

    def test_interpolate_alt(self):
        """ for now alt uses nearest neighbor """

        source = np.random.rand(5)
        coords_src = Coordinates([clinspace(0, 10, 5)], dims=['alt'])
        coords_dst = Coordinates([clinspace(1, 11, 5)], dims=['alt'])

        node = MockArrayDataSource(source=source, native_coordinates=coords_src)
        output = node.eval(coords_dst)

        assert isinstance(output, UnitsDataArray)
        assert np.all(output.alt.values == coords_dst.coords['alt'])


    def test_interpolate_nearest(self):
        """ regular nearest interpolation """

        source = np.random.rand(5, 5)
        coords_src = Coordinates([clinspace(0, 10, 5), clinspace(0, 10, 5)], dims=['lat', 'lon'])
        coords_dst = Coordinates([clinspace(2, 12, 5), clinspace(2, 12, 5)], dims=['lat', 'lon'])

        node = MockArrayDataSource(source=source, native_coordinates=coords_src)
        node.interpolation = 'nearest'
        output = node.eval(coords_dst)

        assert isinstance(output, UnitsDataArray)
        assert np.all(output.lat.values == coords_dst.coords['lat'])
        assert output.values[0, 0] == source[1, 1]

class TestInterpolateRasterio(object):
    """test interpolation functions"""

    def test_interpolate_rasterio(self):
        """ regular interpolation using rasterio"""

        assert rasterio is not None

        rasterio_interps = ['nearest', 'bilinear', 'cubic', 'cubic_spline',
                            'lanczos', 'average', 'mode', 'max', 'min',
                            'med', 'q1', 'q3']
        source = np.random.rand(5, 5)
        coords_src = Coordinates([clinspace(0, 10, 5), clinspace(0, 10, 5)], dims=['lat', 'lon'])
        coords_dst = Coordinates([clinspace(2, 12, 5), clinspace(2, 12, 5)], dims=['lat', 'lon'])

        node = MockArrayDataSource(source=source, native_coordinates=coords_src)

        # make sure it raises trait error
        with pytest.raises(tl.TraitError):
            node.interpolation = 'myowninterp'
            output = node.eval(coords_dst)

        # make sure rasterio_interpolation method requires lat and lon
        # with pytest.raises(ValueError):
        #     coords_not_lon = Coordinates([clinspace(0, 10, 5)], dims=['lat'])
        #     node = MockArrayDataSource(source=source, native_coordinates=coords_not_lon)
        #     node.rasterio_interpolation(node, coords_src, coords_dst)

        # try all other interp methods
        for interp in rasterio_interps:
            node.interpolation = interp
            print(interp)
            output = node.eval(coords_dst)

            assert isinstance(output, UnitsDataArray)
            assert np.all(output.lat.values == coords_dst.coords['lat'])


    def test_interpolate_rasterio_descending(self):
        """should handle descending"""

        source = np.random.rand(5, 5)
        coords_src = Coordinates([clinspace(0, 10, 5), clinspace(0, 10, 5)], dims=['lat', 'lon'])
        coords_dst = Coordinates([clinspace(2, 12, 5), clinspace(2, 12, 5)], dims=['lat', 'lon'])
        
        node = MockArrayDataSource(source=source, native_coordinates=coords_src)
        output = node.eval(coords_dst)
        
        assert isinstance(output, UnitsDataArray)
        assert np.all(output.lat.values == coords_dst.coords['lat'])
        assert np.all(output.lon.values == coords_dst.coords['lon'])

class TestInterpolateNoRasterio(object):
    """test interpolation functions"""


    def test_interpolate_irregular_arbitrary(self):
        """ irregular interpolation """

        # suppress module to force statement
        datasource.rasterio = None

        rasterio_interps = ['nearest', 'bilinear', 'cubic', 'cubic_spline',
                            'lanczos', 'average', 'mode', 'max', 'min',
                            'med', 'q1', 'q3']
        source = np.random.rand(5, 5)
        coords_src = Coordinates([clinspace(0, 10, 5), clinspace(0, 10, 5)], dims=['lat', 'lon'])
        coords_dst = Coordinates([clinspace(2, 12, 5), clinspace(2, 12, 5)], dims=['lat', 'lon'])

        node = MockArrayDataSource(source=source, native_coordinates=coords_src)

        for interp in rasterio_interps:
            node.interpolation = interp
            print(interp)
            output = node.eval(coords_dst)

            assert isinstance(output, UnitsDataArray)
            assert np.all(output.lat.values == coords_dst.coords['lat'])

    def test_interpolate_irregular_arbitrary_2dims(self):
        """ irregular interpolation """

        datasource.rasterio = None

        # try >2 dims
        source = np.random.rand(5, 5, 3)
        coords_src = Coordinates(
            [clinspace(0, 10, 5), clinspace(0, 10, 5), [2, 3, 5]], dims=['lat', 'lon', 'time'])
        coords_dst = Coordinates(
            [clinspace(2, 12, 5), clinspace(2, 12, 5), [2, 3, 5]], dims=['lat', 'lon', 'time'])
        
        node = MockArrayDataSource(source=source, native_coordinates=coords_src)
        node.interpolation = 'nearest'
        output = node.eval(coords_dst)
        
        assert isinstance(output, UnitsDataArray)
        assert np.all(output.lat.values == coords_dst.coords['lat'])
        assert np.all(output.lon.values == coords_dst.coords['lon'])
        assert np.all(output.time.values == coords_dst.coords['time'])

    def test_interpolate_irregular_arbitrary_descending(self):
        """should handle descending"""

        datasource.rasterio = None

        source = np.random.rand(5, 5)
        coords_src = Coordinates([clinspace(0, 10, 5), clinspace(0, 10, 5)], dims=['lat', 'lon'])
        coords_dst = Coordinates([clinspace(2, 12, 5), clinspace(2, 12, 5)], dims=['lat', 'lon'])
        
        node = MockArrayDataSource(source=source, native_coordinates=coords_src)
        node.interpolation = 'nearest'
        output = node.eval(coords_dst)
        
        assert isinstance(output, UnitsDataArray)
        assert np.all(output.lat.values == coords_dst.coords['lat'])
        assert np.all(output.lon.values == coords_dst.coords['lon'])

    def test_interpolate_irregular_arbitrary_swap(self):
        """should handle descending"""

        datasource.rasterio = None

        source = np.random.rand(5, 5)
        coords_src = Coordinates([clinspace(0, 10, 5), clinspace(0, 10, 5)], dims=['lat', 'lon'])
        coords_dst = Coordinates([clinspace(2, 12, 5), clinspace(2, 12, 5)], dims=['lat', 'lon'])
        
        node = MockArrayDataSource(source=source, native_coordinates=coords_src)
        node.interpolation = 'nearest'
        output = node.eval(coords_dst)
        
        assert isinstance(output, UnitsDataArray)
        assert np.all(output.lat.values == coords_dst.coords['lat'])
        assert np.all(output.lon.values == coords_dst.coords['lon'])

    def test_interpolate_irregular_lat_lon(self):
        """ irregular interpolation """

        datasource.rasterio = None

        source = np.random.rand(5, 5)
        coords_src = Coordinates([clinspace(0, 10, 5), clinspace(0, 10, 5)], dims=['lat', 'lon'])
        coords_dst = Coordinates([[[0, 2, 4, 6, 8, 10], [0, 2, 4, 5, 6, 10]]], dims=['lat_lon'])

        node = MockArrayDataSource(source=source, native_coordinates=coords_src)
        node.interpolation = 'nearest'
        output = node.eval(coords_dst)

        assert isinstance(output, UnitsDataArray)
        assert np.all(output.lat_lon.values == coords_dst.coords['lat_lon'])
        assert output.values[0] == source[0, 0]
        assert output.values[1] == source[1, 1]
        assert output.values[-1] == source[-1, -1]

    def test_interpolate_point(self):
        """ interpolate point data to nearest neighbor with various coords_dst"""

        datasource.rasterio = None

        source = np.random.rand(6)
        coords_src = Coordinates([[[0, 2, 4, 6, 8, 10], [0, 2, 4, 5, 6, 10]]], dims=['lat_lon'])
        coords_dst = Coordinates([[[1, 2, 3, 4, 5], [1, 2, 3, 4, 5]]], dims=['lat_lon'])
        node = MockArrayDataSource(source=source, native_coordinates=coords_src)

        output = node.eval(coords_dst)
        assert isinstance(output, UnitsDataArray)
        assert np.all(output.lat_lon.values == coords_dst.coords['lat_lon'])
        assert output.values[0] == source[0]
        assert output.values[-1] == source[3]


        coords_dst = Coordinates([[1, 2, 3, 4, 5], [1, 2, 3, 4, 5]], dims=['lat', 'lon'])
        output = node.eval(coords_dst)
        assert isinstance(output, UnitsDataArray)
        assert np.all(output.lat.values == coords_dst.coords['lat'])
        assert output.values[0, 0] == source[0]
        assert output.values[-1, -1] == source[3]

@pytest.mark.xfail(reason="MockDataSource has no attribute get_data_subset")
class TestGetDataSubset(object):
    """Test Get Data Subset """
    
    # def test_no_intersect(self):
    #     """Test where the requested coordinates have no intersection with the native coordinates """
    #     node = MockDataSource()
    #     coords = Coordinates([clinspace(-30, -27, 5), clinspace(-30, -27, 5)], dims=['lat', 'lon'])
    #     data = node.get_data_subset(coords)
        
    #     assert isinstance(data, UnitsDataArray)     # should return a UnitsDataArray
    #     assert np.all(np.isnan(data.values))        # all values should be nan


    def test_subset(self):
        """Test the standard operation of get_subset """

        node = MockDataSource()
        coords = Coordinates([clinspace(-25, 0, 50), clinspace(-25, 0, 50)], dims=['lat', 'lon'])
        data, coords_subset = node.get_data_subset(coords)

        assert isinstance(data, UnitsDataArray)             # should return a UnitsDataArray
        assert isinstance(coords_subset, Coordinates)       # should return the coordinates subset

        assert not np.all(np.isnan(data.values))            # all values should not be nan
        assert data.shape == (52, 52)
        assert np.min(data.lat.values) == -25
        assert np.max(data.lat.values) == .5
        assert np.min(data.lon.values) == -25
        assert np.max(data.lon.values) == 0.5

    def test_interpolate_nearest_preview(self):
        """test nearest_preview interpolation method. this runs before get_data_subset"""

        # test with same dims as native coords
        node = MockDataSource(interpolation='nearest')
        coords = Coordinates([clinspace(-25, 0, 20), clinspace(-25, 0, 20)], dims=['lat', 'lon'])
        data, coords_subset = node.get_data_subset(coords)

        assert data.shape == (18, 18)
        assert coords_subset.shape == (18, 18)

        # test with different dims and uniform coordinates
        node = MockDataSource(interpolation='nearest')
        coords = Coordinates([clinspace(-25, 0, 20)], dims=['lat'])
        data, coords_subset = node.get_data_subset(coords)

        assert data.shape == (18, 101)
        assert coords_subset.shape == (18, 101)

        # test with different dims and non uniform coordinates
        node = MockNonuniformDataSource(interpolation='nearest')
        coords = Coordinates([[-25, -10, -2]], dims=['lat'])
        data, coords_subset = node.get_data_subset(coords)

        # TODO: in the future this should have default to pass back native_coordinates
        # assert node.get_native_coordinates()