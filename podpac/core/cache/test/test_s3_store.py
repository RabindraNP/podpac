import pytest
import numpy as np
import os
import time

from numpy.testing import assert_equal

from podpac.core.cache.cache import CacheException
from podpac.core.cache.cache import CacheCtrl
from podpac.core.cache.cache import CacheStore
from podpac.core.cache.cache import S3CacheStore
from podpac.core.cache.cache import CacheException
from podpac.core.cache.cache import CacheListing

from podpac.core.data.types import Array
from podpac.core.coordinates.coordinates import Coordinates

root_disk_cache_dir = 'tmp_cache'

def make_cache_ctrl():
    store = S3CacheStore(root_cache_dir_path=root_disk_cache_dir, s3_bucket='podpac-internal-test')
    ctrl = CacheCtrl(cache_stores=[store])
    return ctrl



def make_array_data_source(coords_func=None, data_func=None):
    if data_func is None:
        data_func = np.zeros
    if coords_func is None:
        coords_func = make_lat_lon_time_grid_coords
    coords = coords_func()
    return Array(source=data_func(coords.shape), native_coordinates=coords)

def make_lat_lon_time_grid_coords():
    lat = [0, 1, 2]
    lon = [10, 20, 30, 40]
    dates = ['2018-01-01', '2018-01-02']
    coords = Coordinates([lat,lon,dates],['lat','lon','time'])
    return coords

coord_funcs = [make_lat_lon_time_grid_coords]
array_data_funcs = [np.zeros, np.ones]
node_funcs = [lambda: make_array_data_source(coords_func=c, data_func=d) for d in array_data_funcs for c in coord_funcs if c() is not None]
data_funcs = [lambda: np.zeros((2,3,4)), lambda: np.ones((2,3,4))]
coord_funcs = coord_funcs + [lambda: None]

@pytest.mark.skipif(pytest.config.getoption('--ci'), reason="not a ci test")
def test_put_and_get():
    cache = make_cache_ctrl()
    for coord_f in coord_funcs:
        for node_f in node_funcs:
            for data_f in data_funcs:
                c1,c2 = coord_f(),coord_f()
                n1,n2 = node_f(), node_f()
                din = data_f()
                k = "key"
                cache.put(node=n1, data=din, key=k, coordinates=c1, mode='all', update=False)
                dout = cache.get(node=n1, key=k, coordinates=c1, mode='all')
                assert (din == dout).all()
                dout = cache.get(node=n2, key=k, coordinates=c2, mode='all')
                assert (din == dout).all()
                cache.rem(node='*', key='*', coordinates='*', mode='all')

@pytest.mark.skipif(pytest.config.getoption('--ci'), reason="not a ci test")
def test_put_and_update():
    cache = make_cache_ctrl()
    for coord_f in coord_funcs:
        for node_f in node_funcs:
            for data_f in data_funcs:
                c1,c2 = coord_f(),coord_f()
                n1,n2 = node_f(), node_f()
                din = data_f()
                dupdate = data_f() + np.pi
                assert not (dupdate == din).all()
                k = "key"
                cache.put(node=n1, data=din, key=k, coordinates=c1, mode='all', update=False)
                with pytest.raises(CacheException):
                    cache.put(node=n2, data=dupdate, key=k, coordinates=c2, mode='all', update=False)
                dout = cache.get(node=n1, key=k, coordinates=c1, mode='all')
                assert (din == dout).all()
                cache.put(node=n2, data=dupdate, key=k, coordinates=c2, mode='all', update=True)
                dout = cache.get(node=n2, key=k, coordinates=c2, mode='all')
                assert (dupdate == dout).all()
                cache.rem(node='*', key='*', coordinates='*', mode='all')

@pytest.mark.skipif(pytest.config.getoption('--ci'), reason="not a ci test")
def test_put_and_remove():
    cache = make_cache_ctrl()
    for coord_f in coord_funcs:
        for node_f in node_funcs:
            for data_f in data_funcs:
                c1,c2 = coord_f(),coord_f()
                n1,n2 = node_f(), node_f()
                din = data_f()
                k = "key"
                cache.put(node=n1, data=din, key=k, coordinates=c1, mode='all', update=False)
                assert cache.has(node=n1, key=k, coordinates=c1, mode='all')
                cache.rem(node=n2, key=k, coordinates=c2, mode='all')
                assert not cache.has(node=n1, key=k, coordinates=c1, mode='all')
                with pytest.raises(CacheException):
                    cache.get(node=n1, key=k, coordinates=c1, mode='all')
                cache.rem(node='*', key='*', coordinates='*', mode='all')

@pytest.mark.skipif(pytest.config.getoption('--ci'), reason="not a ci test")
def test_put_two_and_remove_one():
    cache = make_cache_ctrl()
    for coord_f in coord_funcs:
        for node_f in node_funcs:
            for data_f in data_funcs:
                c1,c2 = coord_f(),coord_f()
                n1,n2 = node_f(), node_f()
                d1 = data_f()
                d2 = data_f() + np.pi
                k1 = "key"
                k2 = k1 + "2"
                cache.put(node=n1, data=d1, key=k1, coordinates=c1, mode='all', update=False)
                cache.put(node=n2, data=d2, key=k2, coordinates=c2, mode='all', update=False)
                assert cache.has(node=n1, key=k1, coordinates=c1, mode='all')
                assert cache.has(node=n2, key=k2, coordinates=c2, mode='all')
                cache.rem(node=n2, key=k1, coordinates=c2, mode='all')
                assert not cache.has(node=n1, key=k1, coordinates=c1, mode='all')
                assert cache.has(node=n1, key=k2, coordinates=c1, mode='all')
                with pytest.raises(CacheException):
                    cache.get(node=n1, key=k1, coordinates=c1, mode='all')
                cache.rem(node='*', key='*', coordinates='*', mode='all')

@pytest.mark.skipif(pytest.config.getoption('--ci'), reason="not a ci test")
def test_put_two_and_remove_all():
    cache = make_cache_ctrl()
    for coord_f in coord_funcs:
        for node_f in node_funcs:
            for data_f in data_funcs:
                c1,c2 = coord_f(),coord_f()
                n1,n2 = node_f(), node_f()
                d1 = data_f()
                d2 = data_f() + np.pi
                k1 = "key"
                k2 = k1 + "2"
                cache.put(node=n1, data=d1, key=k1, coordinates=c1, mode='all', update=False)
                cache.put(node=n1, data=d1, key=k2, coordinates=c1, mode='all', update=False)
                assert cache.has(node=n2, key=k1, coordinates=c2, mode='all')
                assert cache.has(node=n2, key=k2, coordinates=c2, mode='all')
                cache.rem(node=n2, key='*', coordinates='*', mode='all')
                assert not cache.has(node=n1, key=k1, coordinates=c1, mode='all')
                assert not cache.has(node=n1, key=k2, coordinates=c1, mode='all')
                with pytest.raises(CacheException):
                    cache.get(node=n1, key=k2, coordinates=c1, mode='all')
                with pytest.raises(CacheException):
                    cache.get(node=n1, key=k1, coordinates=c1, mode='all')
                cache.rem(node='*', key='*', coordinates='*', mode='all')

@pytest.mark.skipif(pytest.config.getoption('--ci'), reason="not a ci test")
def test_two_different_nodes_put_and_one_node_removes_all():
    cache = make_cache_ctrl()
    lat = np.random.rand(3)
    lon = np.random.rand(4)
    coords = Coordinates([lat,lon],['lat','lon'])
    persistent_node = Array(source=np.random.random_sample(coords.shape), native_coordinates=coords)
    persistent_node_din = np.random.rand(6,7,8)
    persistent_node_key = "key"
    cache.put(node=persistent_node, data=persistent_node_din, key=persistent_node_key, coordinates=None)
    for coord_f in coord_funcs:
        for node_f in node_funcs:
            for data_f in data_funcs:
                c1,c2 = coord_f(),coord_f()
                n1,n2 = node_f(), node_f()
                d1 = data_f()
                d2 = data_f() + np.pi
                k1 = "key"
                k2 = k1 + "2"
                cache.put(node=n1, data=d1, key=k1, coordinates=c1, mode='all', update=False)
                cache.put(node=n1, data=d1, key=k2, coordinates=c1, mode='all', update=False)
                assert cache.has(node=n2, key=k1, coordinates=c2, mode='all')
                assert cache.has(node=n2, key=k2, coordinates=c2, mode='all')
                cache.rem(node=n2, key='*', coordinates='*', mode='all')
                assert not cache.has(node=n1, key=k1, coordinates=c1, mode='all')
                assert not cache.has(node=n1, key=k2, coordinates=c1, mode='all')
                with pytest.raises(CacheException):
                   cache.get(node=n1, key=k2, coordinates=c1, mode='all')
                with pytest.raises(CacheException):
                   cache.get(node=n1, key=k1, coordinates=c1, mode='all')
                assert cache.has(node=persistent_node, key=persistent_node_key, coordinates=None)
    cache.rem(node='*', key='*', coordinates='*', mode='all')

@pytest.mark.skipif(pytest.config.getoption('--ci'), reason="not a ci test")
def test_put_something_new_into_existing_file():
    cache = make_cache_ctrl()
    lat = np.random.rand(3)
    lon = np.random.rand(4)
    dummy_coords = Coordinates([lat,lon],['lat','lon'])
    dummy_node = Array(source=np.random.random_sample(dummy_coords.shape), native_coordinates=dummy_coords)
    dummy_node_din = np.random.rand(6,7,8)
    dummy_node_key = "key"
    disk_stores = [c for c in cache._cache_stores if type(c) is S3CacheStore]
    for coord_f in coord_funcs:
        for node_f in node_funcs:
            for data_f in data_funcs:
                c1,c2 = coord_f(),coord_f()
                n1,n2 = node_f(), node_f()
                din = data_f()
                k = "key"
                assert not cache.has(node=n1, key=k, coordinates=c1, mode='all')
                for store in disk_stores:
                    store.make_cache_dir(node=n1)
                    path = store.cache_path(node=n1, key=k, coordinates=c1)
                    listing = CacheListing(node=dummy_node, key=dummy_node_key, coordinates=dummy_coords, data=dummy_node_din)
                    store.save_new_container(listings=[listing], path=path)
                    #import pdb
                    #pdb.set_trace()
                time.sleep(1)
                assert not cache.has(node=n1, key=k, coordinates=c1, mode='all')
                cache.put(node=n1, data=din, key=k, coordinates=c1, mode='all', update=False)
                assert cache.has(node=n1, key=k, coordinates=c1, mode='all')
                dout = cache.get(node=n1, key=k, coordinates=c1, mode='all')
                assert (din == dout).all()
                dout = cache.get(node=n2, key=k, coordinates=c2, mode='all')
                assert (din == dout).all()
                #assert False

                cache.rem(node=n1, key=k, coordinates=c1, mode='all')

                #assert False
                assert not cache.has(node=n1, key=k, coordinates=c1, mode='all')
                for store in disk_stores:
                    path = store.cache_path(node=n1, key=k, coordinates=c1)
#                    assert os.path.exists(path)
                    c = store.load_container(path)
                    listing = CacheListing(node=dummy_node, key=dummy_node_key, coordinates=dummy_coords, data=dummy_node_din)
                    assert c.has(listing)
                cache.rem(node='*', key='*', coordinates='*', mode='all')

@pytest.mark.skipif(pytest.config.getoption('--ci'), reason="not a ci test")
def test_put_and_get_array_datasource_output():
    cache = make_cache_ctrl()
    lat = [0, 1, 2]
    lon = [10, 20, 30, 40]
    dates = ['2018-01-01', '2018-01-02']
    native_coordinates = Coordinates([lat,lon,dates],['lat','lon','time'])
    source = np.zeros(native_coordinates.shape)
    array_data_source = Array(source=source, native_coordinates=native_coordinates)
    output = array_data_source.eval(native_coordinates)
    cache.put(node=array_data_source, data=output, key='output', coordinates=native_coordinates, mode='all', update=False)
    cached_output = cache.get(node=array_data_source, key='output', coordinates=native_coordinates, mode='all')
    assert (cached_output == output).all()
    cache.rem(node='*', key='*', coordinates='*', mode='all') # clear the cache stores

@pytest.mark.skipif(pytest.config.getoption('--ci'), reason="not a ci test")
def test_put_and_get_with_different_instances_of_same_key_objects_array_datasource_output():
    cache = make_cache_ctrl()
    lat = [0, 1, 2]
    lon = [10, 20, 30, 40]
    dates = ['2018-01-01', '2018-01-02']
    
    # create data source node and coordinates for put operation
    native_coordinates_put = Coordinates([lat,lon,dates],['lat','lon','time'])
    source_put = np.zeros(native_coordinates_put.shape)
    array_data_source_put = Array(source=source_put, native_coordinates=native_coordinates_put)
    output = array_data_source_put.eval(native_coordinates_put)
    
    cache.put(node=array_data_source_put, data=output, key='output', coordinates=native_coordinates_put, mode='all', update=False)
    
    # create equivalent (but new objects) data source node and coordinates for get operation
    native_coordinates_get = Coordinates([lat,lon,dates],['lat','lon','time'])
    source_get = np.zeros(native_coordinates_get.shape)
    array_data_source_get = Array(source=source_get, native_coordinates=native_coordinates_get)    
    
    cached_output = cache.get(node=array_data_source_get, key='output', coordinates=native_coordinates_get, mode='all')
    
    assert (cached_output == output).all()
    cache.rem(node='*', key='*', coordinates='*', mode='all') # clear the cache stores

@pytest.mark.skipif(pytest.config.getoption('--ci'), reason="not a ci test")
def test_put_and_update_array_datasource_numpy_array():
    cache = make_cache_ctrl()
    lat = [0, 1, 2]
    lon = [10, 20, 30, 40]
    dates = ['2018-01-01', '2018-01-02']
    native_coordinates = Coordinates([lat,lon,dates],['lat','lon','time'])
    source = np.zeros(native_coordinates.shape)
    array_data_source = Array(source=source, native_coordinates=native_coordinates)
    put_data = np.zeros(native_coordinates.shape)
    cache.put(node=array_data_source, data=put_data, key='key', coordinates=native_coordinates, mode='all', update=False)
    cached_data = cache.get(node=array_data_source, key='key', coordinates=native_coordinates, mode='all')
    assert (cached_data == put_data).all()
    update_data = np.ones(native_coordinates.shape)
    assert (update_data != put_data).any()
    with pytest.raises(CacheException):
        cache.put(node=array_data_source, data=update_data, key='key', coordinates=native_coordinates, mode='all', update=False)
    cache.put(node=array_data_source, data=update_data, key='key', coordinates=native_coordinates, mode='all', update=True)
    cached_data = cache.get(node=array_data_source, key='key', coordinates=native_coordinates, mode='all')
    assert (cached_data == update_data).all()
    cache.rem(node='*', key='*', coordinates='*', mode='all') # clear the cache stores

@pytest.mark.skipif(pytest.config.getoption('--ci'), reason="not a ci test")
def test_put_and_remove_array_datasource_numpy_array():
    cache = make_cache_ctrl()
    lat = [0, 1, 2]
    lon = [10, 20, 30, 40]
    dates = ['2018-01-01', '2018-01-02']
    native_coordinates = Coordinates([lat,lon,dates],['lat','lon','time'])
    source = np.zeros(native_coordinates.shape)
    array_data_source = Array(source=source, native_coordinates=native_coordinates)
    put_data = np.zeros(native_coordinates.shape)
    cache.put(node=array_data_source, data=put_data, key='key', coordinates=native_coordinates, mode='all', update=False)
    cached_data = cache.get(node=array_data_source, key='key', coordinates=native_coordinates, mode='all')
    assert (cached_data == put_data).all()
    cache.rem(node=array_data_source, key='key', coordinates=native_coordinates, mode='all')
    assert not cache.has(node=array_data_source, key='key', coordinates=native_coordinates, mode='all')
    with pytest.raises(CacheException):
        cache.get(node=array_data_source, key='key', coordinates=native_coordinates, mode='all')
    cache.rem(node='*', key='*', coordinates='*', mode='all') # clear the cache stores

