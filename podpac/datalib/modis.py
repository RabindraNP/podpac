"""
MODIS on AWS OpenData
"""

import logging

import traitlets as tl
import rasterio

from podpac.data import Rasterio
from podpac.core import cache
from podpac.node import DiskCacheMixin, S3Mixin

BUCKET = "modis-pds"
PRODUCTS = ["MCD43A4.006", "MOD09GA.006", "MYD09GA.006", "MOD09GQ.006", "MYD09GQ.006"]


class MODISSource(Rasterio, DiskCacheMixin, S3Mixin):
    """
    Individual MODIS data tile using AWS OpenData, with caching.

    Attributes
    ----------
    product : str
        MODIS product ('MCD43A4.006', 'MOD09GA.006', 'MYD09GA.006', 'MOD09GQ.006', or 'MYD09GQ.006')
    horizontal_grid : str
        horizontal grid in the MODIS Sinusoidal Tiling System, e.g. '21'
    vertical_grid : str
        vertical grid in the MODIS Sinusoidal Tiling System, e.g. '07'
    date : str
        year and three-digit day of year, e.g. '2011460'
    data : str
        individual object (varies by product)
    """

    product = tl.Enum(values=PRODUCTS, help="MODIS product ID")
    horizontal_grid = tl.Unicode(help="horizontal grid in the MODIS Sinusoidal Tiling System, e.g. '21'")
    vertical_grid = tl.Unicode(help="vertical grid in the MODIS Sinusoidal Tiling System, e.g. '07'")
    date = tl.Unicode(help="year and three-digit day of year, e.g. '2011460'")
    data = tl.Unicode(help="individual object (varies by product)")

    def init(self):
        self._logger = logging.getLogger(__name__)

        if not self.s3.exists(self.source):
            raise ValueError("No S3 object found at '%s'" % self.source)

    @property
    def _key(self):
        return "%s/%s/%s/%s/%s" % (self.product, self.horizontal_grid, self.vertical_grid, self.date, self.data)

    @property
    def source(self):
        return "s3://%s/%s" % (BUCKET, self._key)

    @tl.default("dataset")
    def open_dataset(self):
        """Opens the data source"""

        cache_key = "fileobj"
        if self.cache_ctrl and self.has_cache(key=cache_key):
            self._logger.info("Getting cached s3 file '%s'" % self.source)
            data = self.get_cache(key=cache_key)
            data = bytes.fromhex(data)

        else:
            self._logger.info("Downloading S3 file '%s'" % self.source)
            with self.s3.open(self.source, "rb") as f:
                data = f.read()
                self.cache_ctrl and self.put_cache(data.hex(), key=cache_key)

        with rasterio.MemoryFile() as mf:
            mf.write(data)
            dataset = mf.open()

        return dataset


class MODIS(object):
    """ Future MODIS node. """

    product = tl.Enum(values=PRODUCTS, help="MODIS product ID")

    s3 = tl.Instance(s3fs.S3FileSystem)

    @tl.default("s3")
    def _default_fs(self):
        # TODO use AWS credentials when available
        return s3fs.S3FileSystem(anon=True)

    @staticmethod
    def available(product=None, horizontal_grid=None, vertical_grid=None, date=None, data=None):
        prefix = [BUCKET]
        for value in [product, horizontal_grid, vertical_grid, date, data]:
            if value is None:
                break
            prefix.append(value)
        else:
            return None

        prefix = "/".join(prefix)
        objs = self.s3.ls(prefix)
        return [obj.replace(prefix + "/", "") for obj in objs if "_scenes.txt" not in obj]


if __name__ == "__main__":

    source = MODISSource(
        product=PRODUCTS[0],
        horizontal_grid="01",
        vertical_grid="11",
        date="2020009",
        data="MCD43A4.A2020009.h01v11.006.2020018035627_B01.TIF",
    )

    print(source.source)
    # print(source.native_coordinates)
    # print(source.eval(source.native_coordinates[:10, :10]))
