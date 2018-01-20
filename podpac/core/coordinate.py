from __future__ import division, unicode_literals, print_function, absolute_import

import numbers
import copy
import sys
import itertools

from six import string_types

import xarray as xr
import numpy as np
import traitlets as tl
from collections import OrderedDict


from podpac.core.units import Units
from podpac.core.utils import cached_property, clear_cache

class CoordinateException(Exception):
    pass

def get_timedelta(s):
    a, b = s.split(',')
    return np.timedelta64(int(a), b)

class Coord(tl.HasTraits):
    """ Base class """
    
    units = Units(allow_none=True, default_value=None)
    
    ctype = tl.Enum(['segment', 'point', 'fence', 'post'], default_value='segment',
                   help="Default is 'segment'."
                   "Indication of what coordinates type. "
                   "This is either a single point ('point' or 'post'), or it"
                   " is the whole segment between this coordinate and the next"
                   " ('segment', 'fence'). ")
    
    segment_position = tl.Float(default_value=0.5,
                                help="Default is 0.5. Where along a segment is"
                                "the coordinate specified. 0 <= segment <= ."
                                " For example, if segment=0, the coordinate is"
                                " specified at the left-most point of the line"
                                " segement connecting the current coordinate"
                                " and the next coordinate. If segment=0.5, "
                                " then the coordinate is specified at the "
                                " center of this line segement.")
    
    extents = tl.List(allow_none=True, default_value=None, 
                      help="When specifying non-uniform coordinates, set the "
                      "bounding box (extents) of the grid in case ctype is "
                      " 'segment' or 'fence'")
    coord_ref_sys = tl.Unicode()
    
    @tl.validate('segment_position')
    def _segment_position_validate(self, proposal):
        if not 0 <= proposal['value'] <= 1:
            raise CoordinateException("Coordinate dimension '" + self.dim + \
            "' must be in the segment position of [0, 1]")
        
        return proposal["value"]
        
    def __repr__(self):
        return '%s: Bounds[%s, %s], N[%d], ctype["%s"]' % (
            self.__class__.__name__,
            self.bounds[0], self.bounds[1],
            self.size,
            self.ctype)
    
    def __add__(self, other):
        """ Should be able to add two coords together in some situations
        Although I'm really not sure about this function... may be a mistake
        """
        # In most cases you should simply be able to stack together the 
        # coordinates into a non-uniform GridCoordinate
        if not isinstance(other, Coord):
            raise CoordinateException("Can only add objects of type Coord to "
                                      "other objects of type Coord.")
        # TODO: This function should really be using Group Coords to cover
        # the most general cases (like dependent coords)
        cs = [self.coordinates, other.coordinates]
        if self.is_max_to_min != other.is_max_to_min:
            cs[1] = cs[1][::-1]
        if self.is_max_to_min:
            if cs[0].min() > cs[1].max():
                pass #order is ok
            elif cs[0].max() < cs[1].min():
                cs = cs[::-1]
            else:  # overlapping!
                print ("Warning, added coordinates overlap")
        else:
            if cs[0].min() > cs[1].max():
                cs = cs[::-1]
            elif cs[0].max() < cs[1].min():
                pass #order is ok
            else:  # overlapping!
                print ("Warning, added coordinates overlap")
        return GridCoord(coords=np.concatenate(cs), **self.kwargs)

    def __init__(self, coords=None, **kwargs):
        """
        bounds is for fence-specification with non-uniform coordinates
        """
        super(Coord, self).__init__(coords=coords, **kwargs)

    @property
    def area_bounds(self):
        raise NotImplementedError

    @tl.observe('extents', 'ctype', 'segment_position')
    def _clear_bounds_cache(self, change):
        clear_cache(self, change, ['bounds'])
        
    @tl.observe('coords')
    def _clear_cache(self, change):
        clear_cache(self, change, ['coords', 'bounds', 'delta'])
        
    @property
    def kwargs(self):
        kwargs = {'units': self.units,
                  'ctype': self.ctype,
                  'segment_position': self.segment_position,
                  'extents': self.extents
        }
        return kwargs
    
    coords = tl.Any()
    @tl.validate("coords")
    def _coords_validate(self, proposal):
         raise NotImplementedError()

    _cached_bounds = tl.Instance(np.ndarray, allow_none=True)    
    @property
    def bounds(self):
        raise NotImplementedError()
        
    _cached_delta = tl.Union((tl.Float(), tl.Instance(np.timedelta64)),
                             allow_none=True)
    @property
    def delta(self):
        raise NotImplementedError()
 
    _cached_coords = tl.Any(default_value=None, allow_none=True)
    @property
    def coordinates(self):
        raise NotImplementedError()

    @property
    def size(self):
        raise NotImplementedError()

    def intersect_check(self, other_coord, ind):
        if self.units != other_coord.units:
            raise NotImplementedError("Still need to implement handling of different units")
        
        if np.all(self.bounds == other_coord.bounds):
            if ind:
                return [0, self.size]
            else:
                return self
        
        ibounds = [
            np.maximum(self.bounds[0], other_coord.bounds[0]),
            np.minimum(self.bounds[1], other_coord.bounds[1])]

        if np.any(ibounds[0] > ibounds[1]):
            if ind:
                return [0, 0]
            else:
                return self.__class__(coords=(self.bounds[0], self.bounds[1], 0)) 

    def intersect(self, other_coord, coord_ref_sys=None, pad=1, ind=False):
        """
        Returns an Coord object if ind==False
        Returns a list of start, stop coordinates if ind==True
        """
        check = self.intersect_check(other_coord, ind)
        if check:
            return check
        
        return self.intersect_bounds(other_coord.bounds, pad=pad, ind=ind)

    def intersect_bounds(self, bounds, pad=1, ind=False):
        """
        Returns an Coord object if ind==False
        Returns a list of start, stop coordinates if ind==True
        """
        raise NotImplementedError()

    @property
    def is_max_to_min(self):
        raise NotImplementedError()


class SingleCoord(Coord):
    """ A single coordinate. """

    coords = tl.Any()
    @tl.validate("coords")
    def _coords_validate(self, proposal):
        val = proposal['value']
        if np.array(val).size != 1:
            raise CoordinateException("SingleCoord cannot have multiple values")

        # extract single value
        val = np.array(val).flatten()[0]

        # convert
        if isinstance(val, string_types):
            val = np.datetime64(val)

        # check type
        if not isinstance(val, (numbers.Number, np.datetime64)):
            raise CoordinateException("Coords type not recognized")
        
        return val

    def __repr__(self):
        return '%s: Value[%s], ctype["%s"]' % (
            self.__class__.__name__, self.coords, self.ctype)

    def __add__(self, other):
        if not isinstance(other, (SingleCoord, UniformGridCoord, GridCoord)):
            raise CoordinateException("Cannot add %s to %s." % (
                    str(self.__class__), str(other.__class__)))
        return super(self.__class__, self).__add__(other)

    @cached_property
    def bounds(self):
        bounds = np.array(
                [self.coords - self.delta, self.coords + self.delta])
        return bounds

    @property
    def area_bounds(self):
        return copy.deepcopy(self.bounds)

    @cached_property
    def delta(self):
        # Arbitrary
        if isinstance(self.coords, np.datetime64):
            dtype = self.coords - self.coords  # Creates timedelta64 object
            delta = np.array(1, dtype=dtype.dtype)
        else:
            delta = np.sqrt(np.finfo(np.float32).eps)
        return delta
            
    @cached_property
    def coordinates(self):
        return np.atleast_1d(self.coords)

    @property
    def size(self):
        return 1 

    def intersect_bounds(self, bounds, pad=1, ind=False):
        """
        Returns an Coord object if ind==False
        Returns a list of start, stop coordinates if ind==True
        """
        if ind:
            return [0, 1]
        else:
            return self

    @property
    def is_max_to_min(self):
        return False


class GridCoord(Coord):
    """ A list of arbitrary coordinates. """

    coords = tl.Any()
    @tl.validate("coords")
    def _coords_validate(self, proposal):
        if not isinstance(proposal['value'], (tuple, list, np.ndarray)):
            raise CoordinateException("Coords type not recognized: '%s'" % (
                type(proposal['value'])))

        # squeeze and check dimensions
        val = np.array(proposal['value']).squeeze()
        if val.ndim != 1:
            raise CoordinateException("Non-uniform coordinates can only "
                                      "have 1 dimension, not %d" % val.ndim)
        
        # convert strings to datetime
        if isinstance(val[0], string_types):
            val = np.array(val, dtype=np.datetime64)

        # check dtype
        if (not np.issubdtype(val.dtype, np.number) and
            not np.issubdtype(val.dtype, np.datetime64)):
            raise CoordinateException("GridCoord coordinates must all be the "
                                      "same type")

        return val

    def __add__(self, other):
        if not isinstance(other, (SingleCoord, UniformGridCoord, GridCoord)):
            raise CoordinateException("Cannot add %s to %s." % (
                    str(self.__class__), str(other.__class__)))
        return super(self.__class__, self).__add__(other)


    @cached_property
    def bounds(self):
        if isinstance(self.coords[0], np.datetime64):
            return np.array([np.min(self.coords), np.max(self.coords)])
        else:
            return np.array([np.nanmin(self.coords), np.nanmax(self.coords)])

    @property
    def area_bounds(self):
        if self.ctype in ['fence', 'segment'] and self.extents:
            extents = self.extents
        else:
            extents = copy.deepcopy(self.bounds)
        return extents
        
    _cached_delta = tl.Instance(np.ndarray, allow_none=True) 
    @cached_property
    def delta(self):
        #print("Warning: delta is not representative for non-uniform coords")
        return np.atleast_1d(np.array(
            (self.coords[-1] - self.coords[0]) / float(self.coords.size) \
            * (1 - 2 * self.is_max_to_min)).squeeze())
 
    @cached_property
    def coordinates(self):
        return self.coords
        
    @property
    def size(self):
        return self.coords.size

    def intersect_bounds(self, bounds, pad=1, ind=False):
        """
        Returns an Coord object if ind==False
        Returns a list of start, stop coordinates if ind==True
        """

        gt = self.coordinates >= bounds[0] - self.delta
        lt = self.coordinates <= bounds[1] + self.delta
        inds = np.where(gt & lt)[0]
        if inds.size == 0:
            if ind:
                return [0, 0]
            else:
                return self.__class__(coords=(self.bounds[0], self.bounds[1], 0))                 
        min_max_i = [min(inds), max(inds)]
        #if self.is_max_to_min:
            #min_max_i = min_max_i[::-1]
        lefti = np.maximum(0, min_max_i[0] - pad)
        righti = np.minimum(min_max_i[1] + pad + 1, self.size)
        if ind:
            return [int(lefti), int(righti)]
        else:
            coords = self.coordinates[lefti:righti]
            return self.__class__(coords=coords, **self.kwargs)

    @property
    def is_max_to_min(self):
        if isinstance(self.coords[0], np.datetime64):
            return self.coords[0] > self.coords[-1]
        else:
            non_nan_coords = self.coords[np.isfinite(self.coords)]
            return non_nan_coords[0] > non_nan_coords[-1]

class UniformGridCoord(Coord):
    """
    A uniformly-spaced coordinates defined by a start, stop, and step/size.

    Attributes
    ----------
    start : float or np.datetime64
        start coordinate
    stop : float or np.datetime64
        stop coordinate
    size : int
        number of coordinate; can be specified or calculate from the step
    step : float, np.timedealta64, or None
        specified delta between coordinates; either size or step is required
    epsg : TODO, str, unicode, or possibly enum
        <not yet in use>
    
    Properties
    ----------
    coords : tuple
        (start, stop, size) or (start, stop, size, epsg)
    delta : float or np.timedelta64
        delta between coordinates; this is either the step or calculated from
        the start, stop, and size.
    """

    start = tl.Union((tl.Float(), tl.Instance(np.datetime64)))
    stop = tl.Union((tl.Float(), tl.Instance(np.datetime64)))
    num = tl.Integer(allow_none=True, default_value=None)
    step = tl.Union((tl.Float(), tl.Instance(np.timedelta64)),
                    allow_none=True, default_value=None)
    epsg = tl.Unicode(allow_none=True, default_value=None) # or enum?

    @tl.validate('num')
    def _validate_num(self, d):
        if self.step is not None:
            raise CoordinateException(
                "UniformGridCoord requires num or step, not both")
        return d['value']

    @tl.validate('step')
    def _validate_step(self, d):
        if self.num is not None:
            raise CoordinateException(
                "UniformGridCoord requires num or step, not both")
        return d['value']

    @tl.observe('start', 'stop', 'num', 'step')
    def _clear_cache(self, change):
        clear_cache(self, change, ['coords', 'bounds', 'delta'])

    def __init__(self, start=None, stop=None, num=None, epsg=None, step=None,
                 coords=None, **kwargs):
        """
        """

        if coords is not None:
            start, stop, size, epsg = self._parse_coords(coords)
        else:
            if isinstance(start, string_types):
                start = np.datetime64(start)
            if isinstance(stop, string_types):
                stop = np.datetime64(stop)
            if isinstance(step, string_types):
                step = get_timedelta(step)

        if num is None and step is None:
            raise CoordinateException("UniformGridCoord requires num or step")

        super(Coord, self).__init__(
            start=start, stop=stop, num=num, epsg=epsg, step=step, **kwargs)

    def __add__(self, other):
        if not isinstance(other, (SingleCoord, UniformGridCoord, GridCoord)):
            raise CoordinateException("Cannot add %s to %s." % (
                    str(self.__class__), str(other.__class__)))
        if isinstance(other, UniformGridCoord):
            pass # TODO: add some optimizations here
        return super(self.__class__, self).__add__(other)

    @property
    def coords(self):
        """
        Either (start, stop, size) or (start, stop, size, epsg)
        """
        coords = self.start, self.start + self.delta*self.size, self.size
        if self.epsg is not None:
            coords = coords + (self.epsg,)
        return coords

    def _parse_coords(self, coords):
        if not isinstance(coords, (tuple, list)) or len(coords) not in [3, 4]:
            raise CoordinateException(
                'Invalid UniformGridCoord coords argument; expected '
                '(start, stop, num) or (start, stop, num, epsg)')
        
        start, stop, num = coords[:3]
        if len(coords) == 4:
            epsg = coords[3]
        else:
            epsg = None

        if isinstance(start, np.ndarray) and start.size == 1:
            start = start.flatten()[0]
        
        if isinstance(stop, np.ndarray) and stop.size == 1:
            stop = stop.flatten()[0]
    
        return start, stop, num, epsg

    @cached_property
    def bounds(self):
        if self.is_max_to_min:
            return np.array([self.stop, self.start])
        else:
            return np.array([self.start, self.stop])

    @property
    def area_bounds(self):
        extents = copy.deepcopy(self.bounds)
        if self.ctype in ['fence', 'segment']:
            p = self.segment_position
            # for stacked coodinates
            extents += np.array([-p, 1 - p]) * self.delta
        return extents
    
    @cached_property
    def delta(self):
        if self.step is not None:
            delta = self.step
        else:
            delta = (self.stop - self.start + 1) / self.num
            if self.is_max_to_min:
                delta *= -1 # TODO is this correct

        return delta

    @property
    def size(self):
        if self.num is not None:
            size = self.num
        else:
            size = max(0, int(np.ceil((self.start - self.stop) / self.step)))

        return size
 
    @cached_property
    def coordinates(self):
        if isinstance(self.start, np.datetime64):
            # TODO datetime should include upper boundary?
            coords = np.arange(self.start, self.stop+self.delta, self.delta)
        elif self.step is not None:
            coords = np.arange(self.start, self.stop+self.delta, self.step)
        else:
            coords = np.linspace(self.start, self.stop, self.size)
        return coords

    def intersect_bounds(self, bounds, pad=1, ind=False):
        """
        Returns an Coord object if ind==False
        Returns a list of start, stop coordinates if ind==True
        """

        bounds[0] = max(self.bounds[0], bounds[0])
        bounds[1] = min(self.bounds[1], bounds[1])

        imin = np.floor((bounds[0] - self.bounds[0]) / self.delta)
        imax = np.ceil((self.bounds[1] - bounds[1]) / self.delta)

        if ind:
            if self.is_max_to_min:
                imin, imax = imax, imin
            imin = int(min(self.size, max(0, imin - pad)))
            imax = int(min(self.size, max(0, self.size - imax + pad)))
            return [imin, imax]

        cmin = max(self.bounds[0], self.bounds[0]+max(0,imin-pad)*self.delta)
        cmax = min(self.bounds[1], self.bounds[1]-max(0,imax-pad)*self.delta)
        if self.is_max_to_min:
            cmin, cmax = cmax, cmin

        new_crd = UniformGridCoord(
            start=cmin, stop=cmax, step=self.delta, **self.kwargs)
        
        return new_crd
        
    @property
    def is_max_to_min(self):
        return self.start > self.stop

class RotatedGridCoord(Coord):
    coords = tl.Any()
    @tl.validate("coords")
    def _coords_validate(self, proposal):
         raise NotImplementedError()

    @property
    def bounds(self):
        raise NotImplementedError()

    @property
    def delta(self):
        raise NotImplementedError()
 
    @property
    def coordinates(self):
        raise NotImplementedError()

    @property
    def size(self):
        raise NotImplementedError()

    def intersect_bounds(self, bounds, pad=1, ind=False):
        """
        Returns an Coord object if ind==False
        Returns a list of start, stop coordinates if ind==True
        """
        raise NotImplementedError()

    @property
    def is_max_to_min(self):
        raise NotImplementedError()


class GroupCoord(Coord):
    coords = tl.Any()
    @tl.validate("coords")
    def _coords_validate(self, proposal):
         raise NotImplementedError()

    @property
    def bounds(self):
        raise NotImplementedError()

    @property
    def delta(self):
        raise NotImplementedError()
 
    @property
    def coordinates(self):
        raise NotImplementedError()

    @property
    def size(self):
        raise NotImplementedError()

    def intersect_bounds(self, bounds, pad=1, ind=False):
        """
        Returns an Coord object if ind==False
        Returns a list of start, stop coordinates if ind==True
        """
        raise NotImplementedError()

    @property
    def is_max_to_min(self):
        raise NotImplementedError()

def make_coord(coords, **kwargs): 
    """ Coord factory """

    if isinstance(coords, Coord):
        pass
    elif np.array(coords).size == 1:
        coords = SingleCoord(coords, **kwargs)
    else:
        coords = GridCoord(coords, **kwargs)
        
    return coords

class Coordinate(tl.HasTraits):
    """
    You can initialize a coordinate like this: 
    # Single number
    c = Coordinate(lat=1) 
    # Single number for stacked coordinate
    c = Coordinate(lat_lon=((1, 2))) 
    # uniformly spaced range (start, stop, number)
    c = Coordinate(lat=(49.1, 50.2, 100) 
    # uniform range for stacked coordinate
    c = Coordinate(lat_lon=((49.1, -120), (50.2, -122), 100) 
    # uniformly spaced steps (start, stop, step)
    c = Coordinate(lat=(49.1, 50.1, 0.1)) 
    # uniform steps for stacked coordinate
    c = Coordinate(lat_lon=((49.1, -120), (50.2, -122), (0.1, 0.2)) 
    # specified coordinates
    c = Coordinate(lat=np.array([50, 50.1, 50.4, 50.8, 50.9])) 
    # specified stacked coordinates
    c = Coordinate(lat_lon=(np.array([50, 50.1, 50.4, 50.8, 50.9]), 
                            np.array([-120, -125, -126, -127, -130]) 
    # Depended specified coordinates
    c = Coordinate(lat=xr.DataArray([[50.1, 50.2, 50.3], [50.2, 50.3, 50.4]],
                   dims=['lat', 'lon']), lon=... )) 
    # Dependent from 3 points
    c = Coordinate(lat=((50.1, 51.4, 51.2), 100),
                   lon=((120, 120.1, 121.1), 50)) 
    """

    @property
    def _valid_dims(self):
        return ('time', 'lat', 'lon', 'alt')
    
    # default val set in constructor
    ctype = tl.Enum(['segment', 'point', 'fence', 'post'])  
    segment_position = tl.Float()  # default val set in constructor
    coord_ref_sys = tl.CUnicode()
    _coords = tl.Instance(OrderedDict)
    dims_map = tl.Dict()

    def __init__(self, coords=None, coord_ref_sys="WGS84", order=None,
            segment_position=0.5, ctype='segment', **kwargs):
        """
        bounds is for fence-specification with non-uniform coordinates
        
        order is required for Python 2.x where the order of kwargs is not
        preserved.
        """
        if coords is None:
            if sys.version_info.major < 3:
                if order is None:
                    if len(kwargs) > 1:
                        raise CoordinateException(
                            "Need to specify the order of the coordinates "
                            "using 'order'.")
                    else:
                        order = kwargs.keys()
                
                coords = OrderedDict()
                for k in order:
                    coords[k] = kwargs[k]
            else:
                coords = OrderedDict(kwargs)
        elif not isinstance(coords, OrderedDict):
            raise CoordinateException("coords needs to be an "
                    "OrderedDict, not " + str(type(coords)))

        self.dims_map = self.get_dims_map(coords)
        _coords = self.unstack_dict(coords)
        for key, val in _coords.items():
            if not isinstance(_coords[key], Coord):
                _coords[key] = make_coord(coords=val, ctype=ctype,
                                     coord_ref_sys=coord_ref_sys, 
                                     segment_position=segment_position,
                                     )
        super(Coordinate, self).__init__(_coords=_coords,
                                         coord_ref_sys=coord_ref_sys,
                                         segment_position=segment_position,
                                         ctype=ctype)
    
    def __repr__(self):
        rep = str(self.__class__.__name__)
        for d in self._coords:
            d2 = self.dims_map[d]
            if d2 != d:
                d2 = d2 + '[%s]' % d
            rep += '\n\t{}: '.format(d2) + str(self._coords[d])
        return rep
    
    def __getitem__(self, item):
        return self._coords[item]
    
    @tl.validate('_coords')
    def _coords_validate(self, proposal):
        seen_dims = []
        stack_dims = {}
        for key in proposal['value']:
            self._validate_dim(key, seen_dims)
            val = proposal['value'][key]
            self._validate_val(val, key, proposal['value'].keys())
            if key not in self.dims_map.values():  # stacked dim
                if self.dims_map[key] not in stack_dims:
                    stack_dims[self.dims_map[key]] = val.size
                else:
                    if val.size != stack_dims[self.dims_map[key]]:
                        raise CoordinateException("Stacked dimensions need to"
                                                  " have the same size:"
                                                  " %d != %d for %s in %s" % (
                                                   val.size, 
                                                   stack_dims[self.dims_map[key]],
                                                   key, self.dims_map[key]))
        return proposal['value']
        
    def _validate_dim(self, dim, seen_dims):
        if dim not in self._valid_dims:
            raise CoordinateException(
                "The '%s' dimension is not a valid dimension %s" % (
                    dim, self._valid_dims))
        if dim in seen_dims:
            raise CoordinateException("The dimensions '" + dim + \
            "' cannot be repeated.")
        seen_dims.append(dim)
    
    def _validate_val(self, val, dim='', dims=[]):
        # Dependent array, needs to be an xarray.DataArray
        if isinstance(val, xr.DataArray):
            for key in val._coords: 
                if key not in dims:
                    raise CoordinateException("Dimensions of dependent" 
                    " coordinate DatArray needs to be in " + str(dims))
   
    def get_dims_map(self, coords=None):
        if coords is None:
            coords = self._coords
        stacked_coords = OrderedDict()
        for c in coords:
            if '_' in c:
                for cc in c.split('_'):
                    stacked_coords[cc] = c       
            else:
                stacked_coords[c] = c 
        return stacked_coords        
    
    def unstack_dict(self, coords=None, check_dim_repeat=False):
        if coords is None: 
            coords = self._coords
        dims_map = self.get_dims_map(coords)
       
        new_crds = OrderedDict()
        seen_dims = []
        for key, val in coords.items():
            if key not in self.dims_map:  # stacked
                keys = key.split('_')
                for i, k in enumerate(keys):
                    new_crds[k] = val[i]
                    if check_dim_repeat and k in seen_dims:
                        raise CoordinateException("Dimension %s " 
                                "cannot be repeated." % k)
                    seen_dims.append(k)
            else:
                new_crds[key] = val
                if check_dim_repeat and key in seen_dims:
                    raise CoordinateException("Dimension %s " 
                        "cannot be repeated." % key)
                seen_dims.append(key)

        return new_crds

    def stack_dict(self, coords=None, dims_map=None):
        if coords is None: 
            coords = self._coords
        if dims_map is None:
            dims_map = self.dims_map

        stacked_coords = OrderedDict()
        for key, val in dims_map.items():
            if val in stacked_coords:
                temp = stacked_coords[val]
                if not isinstance(temp, list):
                    temp = [temp]
                temp.append(coords[key])
                stacked_coords[val] = temp
            else:
                stacked_coords[val] = coords[key]
        return stacked_coords
   
    def stack(self, stack_dims, copy=True):
        stack_dim = '_'.join(stack_dims)
        dims_map = {k:v for k,v in self.dims_map.items()}
        for k in stack_dims:
            dims_map[k] = stack_dim
        stack_dict = self.stack_dict(self._coords.copy(), dims_map=dims_map)
        if copy:
            return self.__class__(coords=stack_dict, **self.kwargs)
        else:
            # Check for correct dimensions
            tmp = self.dims_map
            self.dims_map = dims_map
            try:
                self._coords_validate({'value': self._coords})
            except CoordinateException as e:
                self.dims_map = tmp
                raise(e)
                
            
            return self

    def unstack(self, copy=True):
        if copy:
            return self.__class__(coords=self._coords.copy())
        else:
            self.dims_map = {v:v for v in self.dims_map}
            return self

    def intersect(self, other, coord_ref_sys=None, pad=1):
        new_crds = OrderedDict()
        for i, d in enumerate(self._coords):
            if isinstance(pad, (list, tuple)):
                spad = pad[i]
            elif isinstance(pad, dict):
                spad = pad[d]
            else:
                spad = pad
            
            if  d not in other._coords:
                new_crds[d] = self._coords[d]
                continue
            else:
                new_crds[d] = self._coords[d].intersect(other._coords[d],
                                                        coord_ref_sys, pad=spad)
        stacked_coords = self.stack_dict(new_crds)
        return self.__class__(stacked_coords, **self.kwargs)

    def intersect_ind_slice(self, other, coord_ref_sys=None, pad=1):
        slc = []
        for j, d in enumerate(self._coords):
            if isinstance(pad, (list, tuple)):
                spad = pad[j]
            elif isinstance(pad, dict):
                spad = pad[d]
            else:
                spad = pad
                
            if d not in other._coords:
                slc.append(slice(None, None))
                continue
            else:    
                ind = self._coords[d].intersect(other._coords[d], 
                                                coord_ref_sys, ind=True, pad=spad)
                # if self._coords[d].regularity == 'dependent':  # untested
                #     i = self.coordinates.dims.index(d)
                #     ind = [inds[i] for inds in ind]
                if ind:
                    slc.append(slice(ind[0], ind[1]))
                else:
                    slc.append(slice(0, 0))
        return slc
    
    @property
    def kwargs(self):
        return {
                'coord_ref_sys': self.coord_ref_sys,
                'segment_position': self.segment_position,
                'ctype': self.ctype
                }
    
    def replace_coords(self, other, copy=True):
        if copy:
            coords = self._coords.copy()
            dims_map = self.dims_map.copy()
        else:
            coords = self._coords
            dims_map = self.dims_map
            
        for c in coords:
            if c in other._coords:
                coords[c] = other._coords[c]
                dims_map[c] = other.dims_map[c]
        
        if copy:
            stack_dict = self.stack_dict(coords, dims_map=dims_map)
            return self.__class__(coords=stack_dict)
        else:
            return self   
    
    def get_shape(self, other_coords=None):
        if other_coords is None:
            other_coords = self
        # Create shape for each dimension
        shape = []
        seen_dims = []
        for k in self._coords:
            if k in other_coords._coords:
                shape.append(other_coords._coords[k].size)
                # Remove stacked duplicates
                if other_coords.dims_map[k] in seen_dims:
                    shape.pop()
                else:
                    seen_dims.append(other_coords.dims_map[k])
            else:
                shape.append(self._coords[k].size)

        return shape
        
    @property
    def shape(self):
        return self.get_shape()
    
    @property
    def delta(self):
        return np.array([c.delta for c in self._coords.values()]).squeeze()
    
    @property
    def dims(self):
        dims = []
        for v in self.dims_map.values():
            if v not in dims:
                dims.append(v)
        return dims
    
    @property
    def coords(self):
        crds = OrderedDict()
        for k in self.dims:
            if k in self.dims_map:  # not stacked
                crds[k] = self._coords[k].coordinates
            else:
                coordinates = [self._coords[kk].coordinates 
                               for kk in k.split('_')]
                dtype = [(str(kk), coordinates[i].dtype) 
                         for i, kk in enumerate(k.split('_'))]
                n_coords = len(coordinates)
                s_coords = len(coordinates[0])
                crds[k] = np.array([[tuple([coordinates[j][i]
                                     for j in range(n_coords)])] 
                                   for i in range(s_coords)],
                    dtype=dtype).squeeze()
        return crds
    
    #@property
    #def gdal_transform(self):
        #if self['lon'].regularity == 'regular' \
               #and self['lat'].regularity == 'regular':
            #lon_bounds = self['lon'].area_bounds
            #lat_bounds = self['lat'].area_bounds
        
            #transform = [lon_bounds[0], self['lon'].delta, 0,
                         #lat_bounds[0], 0, -self['lat'].delta]
        #else:
            #raise NotImplementedError
        #return transform
    
    @property
    def gdal_crs(self):
        crs = {'WGS84': 'EPSG:4326',
               'SPHER_MERC': 'EPSG:3857'}
        return crs[self.coord_ref_sys.upper()]
    
    def __add__(self, other):
        if not isinstance(other, Coordinate):
            raise CoordinateException("Can only add Coordinate objects"
                   " together.")
        new_coords = copy.deepcopy(self._coords)
        for key in other._coords:
            if key in self._coords:
                if np.all(np.array(self._coords[key].coords) !=
                        np.array(other._coords[key].coords)):
                    new_coords[key] = self._coords[key] + other._coords[key]
            else:
                new_coords[key] = copy.deepcopy(other._coords[key])
        return self.__class__(coords=new_coords)

    def iterchunks(self, shape, return_slice=False):
        # TODO assumes the input shape dimension and order matches
        # TODO replace self[k].coords[slc] with self[k][slc] (and implement the slice)

        slices = [
            map(lambda i: slice(i, i+n), range(0, m, n))
            for m, n
            in zip(self.shape, shape)]

        for l in itertools.product(*slices):
            kwargs = {k:self.coords[k][slc] for k, slc in zip(self.dims, l)}
            kwargs['order'] = self.dims
            coords = Coordinate(**kwargs)
            if return_slice:
                yield l, coords
            else:
                yield coords

    @property
    def latlon_bounds_str(self):
        if 'lat' in self.dims and 'lon' in self.dims:
            return '%s_%s_x_%s_%s' % (
                self['lat'].bounds[0],
                self['lon'].bounds[0],
                self['lat'].bounds[1],
                self['lon'].bounds[1]
            )
        elif 'lat_lon' in self.dims:
            return 'TODO'
        else:
            return 'NA'

# alias

if __name__ == '__main__': 
    
    U = UniformGridCoord
    
    coord = U(1, 10, 10) # or U(start=1, stop=10, num=10)
    coord_left = U(-2, 7, 10)
    coord_right = U(4, 13, 10)
    coord_cent = U(4, 7, 4)
    coord_cover = U(-2, 13, 15)
    
    c = coord.intersect(coord_left)
    c = coord.intersect(coord_right)
    c = coord.intersect(coord_cent)
    
    c = Coordinate(lat=coord, lon=coord, order=('lat', 'lon'))
    c_s = Coordinate(lat_lon=(coord, coord))
    c_cent = Coordinate(lat=coord_cent, lon=coord_cent, order=('lat', 'lon'))
    c_cent_s = Coordinate(lon_lat=(coord_cent, coord_cent))

    print(c.intersect(c_cent))
    print(c.intersect(c_cent_s))
    print(c_s.intersect(c_cent))
    print(c_s.intersect(c_cent_s))
    
    try:
        c = Coordinate(lat_lon=((0, 1, 10), (0, 1, 11)))
    except CoordinateException as e:
        print(e)
    
    c = Coordinate(lat_lon=((0, 1, 10), (0, 1, 10)), time=(0, 1, 2), order=('lat_lon', 'time'))
    c2 = Coordinate(lat_lon=((0.5, 1.5, 15), (0.1, 1.1, 15)))
    print (c.shape)
    print (c.unstack().shape)
    print (c.get_shape(c2))
    print (c.get_shape(c2.unstack()))
    print (c.unstack().get_shape(c2))
    print (c.unstack().get_shape(c2.unstack()))
    
    c = Coordinate(lat=U(0, 1, 10), lon=U(0, 1, 10), time=U(0, 1, 2), order=('lat', 'lon', 'time'))
    print(c.stack(['lat', 'lon']))
    try:
        c.stack(['lat','time'])
        raise Exception
    except CoordinateException as e:
        print(e)
        pass

    try:
        c.stack(['lat','time'], copy=False)
        raise Exception
    except CoordinateException as e:
        print(e)
        pass

    coord_left = U(-2, 7, 3)
    coord_right = U(8, 13, 3)
    coord_right2 = U(13, 8, 3)
    coord_cent = U(4, 11, 4)
    coord_pts = SingleCoord(15) # or make_coord(15)
    coord_irr = GridCoord(np.random.rand(5)) # or make_coord(np.random.rand(5))
    
    print ((coord_left + coord_right).coordinates)
    print ((coord_right + coord_left).coordinates)
    print ((coord_left + coord_right2).coordinates)
    print ((coord_right2 + coord_left).coordinates)
    print ((coord_left + coord_pts).coordinates)
    print (coord_irr + coord_pts + coord_cent)

    c = Coordinate(lat_lon=((0, 1, 10), (0, 1, 10)), time=U(0, 1, 2), order=('lat_lon', 'time'))
    c2 = Coordinate(lat_lon=((0.5, 1.5, 15), (0.1, 1.1, 15)))

    print (c.replace_coords(c2))
    print (c.replace_coords(c2.unstack()))
    print (c.unstack().replace_coords(c2))
    print (c.unstack().replace_coords(c2.unstack()))
    
    
    print('Done')
