import logging
import datetime

import traitlets as tl
import numpy as np

import podpac

_logger = logging.getLogger(__name__)

SOILSCAPE_FILESERVER_BASE = "https://thredds.daac.ornl.gov/thredds/fileServer/ornldaac/1339"
CRS = "+proj=longlat +datum=WGS84 +vunits=cm"

NODES = {
    "BLMLand1STonzi_CA": [900, 901, 902, 903, 904, 905, 906, 907, 908, 909, 910, 911, 912, 913, 914, 915, 916],
    "BLMLand2STonzi_CA": [
        1000,
        1017,
        1018,
        1019,
        1020,
        1021,
        1022,
        1023,
        1024,
        1025,
        1026,
        1027,
        1028,
        1029,
        1030,
        1031,
    ],
    "BLMLand3NTonzi_CA": [1200, 1201, 1202, 1204, 1205, 1206],
    "Canton_OK": [
        101,
        102,
        103,
        104,
        105,
        106,
        107,
        108,
        109,
        110,
        111,
        112,
        113,
        114,
        115,
        116,
        117,
        118,
        119,
        120,
        121,
    ],
    "Kendall_AZ": [1400, 1401, 1402, 1403, 1404, 1405, 1406, 1407, 1408, 1409],
    "LuckyHills_AZ": [1500, 1501, 1502, 1503, 1504, 1505, 1506, 1507],
    "MatthaeiGardens_MI": [
        200,
        202,
        203,
        204,
        206,
        207,
        208,
        209,
        210,
        211,
        212,
        214,
        215,
        216,
        217,
        218,
        219,
        220,
        221,
        222,
        223,
        224,
        225,
        226,
        227,
        228,
        230,
    ],
    "NewHoganLakeN_CA": [701, 702, 703, 704, 705, 706, 707, 708, 709, 710, 711, 712, 713, 715],
    "NewHoganLakeS_CA": [501, 502, 503, 504, 505, 506, 507, 508, 509, 510, 511, 512, 513, 514, 515, 516, 517, 518],
    "TerradOro_CA": [
        1300,
        1301,
        1302,
        1303,
        1304,
        1305,
        1306,
        1307,
        1308,
        1309,
        1310,
        1311,
        1312,
        1313,
        1314,
        1315,
        1316,
        1317,
        1318,
        1319,
        1320,
        1321,
        1322,
        1323,
        801,
        802,
        803,
        804,
        805,
        806,
        807,
        808,
        809,
        810,
        811,
        812,
        813,
        814,
        815,
        816,
        817,
        818,
        819,
        820,
        821,
        822,
        823,
        824,
        825,
        827,
        828,
    ],
    "TonziRanch_CA": [401, 402, 403, 404, 405, 406, 408, 409, 410, 411, 412, 413, 414, 415, 416, 417, 418, 419, 420],
    "Vaira_CA": [
        600,
        642,
        644,
        645,
        646,
        649,
        651,
        653,
        656,
        659,
        661,
        662,
        664,
        665,
        666,
        667,
        668,
        669,
        670,
        671,
        675,
        676,
        679,
        680,
    ],
}

NODE2SITE = {node: site for site in NODES for node in NODES[site]}

NODE_LOCATIONS = {
    101: (36.00210189819336, -98.6310806274414),
    102: (36.00204849243164, -98.63016510009766),
    103: (36.00210189819336, -98.62930297851562),
    104: (36.00208282470703, -98.62843322753906),
    105: (36.00148391723633, -98.6310806274414),
    106: (36.00153350830078, -98.63020324707031),
    107: (36.00153350830078, -98.62933349609375),
    108: (36.00148391723633, -98.62846374511719),
    109: (36.00094985961914, -98.63113403320312),
    110: (36.00091552734375, -98.63023376464844),
    111: (36.00090026855469, -98.62934875488281),
    112: (36.00094985961914, -98.62848663330078),
    113: (36.0009651184082, -98.62813568115234),
    114: (36.00080108642578, -98.63224792480469),
    115: (36.00051498413086, -98.63228607177734),
    116: (36.0003662109375, -98.631103515625),
    117: (36.00038146972656, -98.63026428222656),
    118: (36.000450134277344, -98.62934875488281),
    119: (36.00043487548828, -98.62848663330078),
    120: (36.00041580200195, -98.62813568115234),
    121: (36.0002326965332, -98.63236999511719),
    900: (38.39332962036133, -120.9057388305664),
    901: (38.39311218261719, -120.90608978271484),
    902: (38.39351272583008, -120.90546417236328),
    903: (38.3934326171875, -120.90485382080078),
    904: (38.39322280883789, -120.90523529052734),
    905: (38.3930549621582, -120.90473937988281),
    906: (38.39268493652344, -120.90612030029297),
    907: (38.392616271972656, -120.90575408935547),
    908: (38.39276885986328, -120.90546417236328),
    909: (38.392539978027344, -120.90435791015625),
    910: (38.39240646362305, -120.90538024902344),
    911: (38.39205551147461, -120.90554809570312),
    912: (38.39206314086914, -120.90470123291016),
    913: (38.39163589477539, -120.9051513671875),
    914: (38.391475677490234, -120.90571594238281),
    915: (38.39125442504883, -120.90613555908203),
    916: (38.390968322753906, -120.90583038330078),
    1000: (38.38666534423828, -120.90629577636719),
    1017: (38.38922119140625, -120.90509796142578),
    1018: (38.38896179199219, -120.90476989746094),
    1019: (38.38833236694336, -120.90593719482422),
    1020: (38.388309478759766, -120.90525817871094),
    1021: (38.38798904418945, -120.90575408935547),
    1022: (38.38800048828125, -120.90465545654297),
    1023: (38.38770294189453, -120.90603637695312),
    1024: (38.38750457763672, -120.905517578125),
    1025: (38.38759231567383, -120.90480041503906),
    1026: (38.38713836669922, -120.9060287475586),
    1027: (38.38721466064453, -120.90483856201172),
    1028: (38.38737487792969, -120.90460205078125),
    1029: (38.387081146240234, -120.90457153320312),
    1030: (38.38673400878906, -120.90526580810547),
    1031: (38.38658142089844, -120.90449523925781),
    1200: (38.47132110595703, -120.99401092529297),
    1201: (38.47126770019531, -120.99333190917969),
    1202: (38.471134185791016, -120.99433135986328),
    1204: (38.47080612182617, -120.99436950683594),
    1205: (38.47153854370117, -120.99373626708984),
    1206: (38.47169876098633, -120.99419403076172),
    1400: (31.736480712890625, -109.94183349609375),
    1401: (31.737104415893555, -109.94342041015625),
    1402: (31.736867904663086, -109.94287109375),
    1403: (31.736665725708008, -109.94261169433594),
    1404: (31.735862731933594, -109.94123840332031),
    1405: (31.735509872436523, -109.94096374511719),
    1406: (31.736804962158203, -109.94418334960938),
    1407: (31.736730575561523, -109.94657897949219),
    1408: (31.737119674682617, -109.94674682617188),
    1409: (31.737913131713867, -109.9466323852539),
    1500: (31.743972778320312, -110.05152130126953),
    1501: (31.742450714111328, -110.05266571044922),
    1502: (31.742727279663086, -110.05255889892578),
    1503: (31.743019104003906, -110.05261993408203),
    1504: (31.742687225341797, -110.05278015136719),
    1505: (31.744464874267578, -110.05230712890625),
    1506: (31.744050979614258, -110.05297088623047),
    1507: (31.742982864379883, -110.05318450927734),
    200: (42.29828643798828, -83.66435241699219),
    202: (42.2977409362793, -83.66523742675781),
    203: (42.29869842529297, -83.66448974609375),
    204: (42.297706604003906, -83.66458892822266),
    206: (42.298709869384766, -83.66460418701172),
    207: (42.29875183105469, -83.66545867919922),
    208: (42.29795837402344, -83.66423797607422),
    209: (42.29881286621094, -83.66336822509766),
    210: (42.29900360107422, -83.66426086425781),
    211: (42.29833984375, -83.66524505615234),
    212: (42.299034118652344, -83.66350555419922),
    214: (42.29782485961914, -83.66586303710938),
    215: (42.298744201660156, -83.66431427001953),
    216: (42.29877853393555, -83.66446685791016),
    217: (42.29825210571289, -83.66380310058594),
    218: (42.298919677734375, -83.6642837524414),
    219: (42.29914855957031, -83.66537475585938),
    220: (42.29893112182617, -83.66461944580078),
    221: (42.29887390136719, -83.66364288330078),
    222: (42.297340393066406, -83.6669921875),
    223: (42.299259185791016, -83.66424560546875),
    224: (42.29872512817383, -83.66317749023438),
    225: (42.29872512817383, -83.66317749023438),
    226: (42.29866027832031, -83.66433715820312),
    227: (42.29909896850586, -83.66386413574219),
    228: (42.29883575439453, -83.66429138183594),
    230: (42.29800033569336, -83.66378021240234),
    701: (38.17225646972656, -120.80365753173828),
    702: (38.17338943481445, -120.80694580078125),
    703: (38.17353057861328, -120.806396484375),
    704: (38.17322540283203, -120.80656433105469),
    705: (38.172794342041016, -120.80677795410156),
    706: (38.17293167114258, -120.80503845214844),
    707: (38.17230987548828, -120.80622100830078),
    708: (38.171714782714844, -120.8061752319336),
    709: (38.172157287597656, -120.80663299560547),
    710: (38.171875, -120.80497741699219),
    711: (38.17270278930664, -120.80281066894531),
    712: (38.172607421875, -120.80424499511719),
    713: (38.17242431640625, -120.80474853515625),
    715: (38.17243576049805, -120.80218505859375),
    501: (38.149559020996094, -120.78845977783203),
    502: (38.14886474609375, -120.78742218017578),
    503: (38.14878463745117, -120.78624725341797),
    504: (38.14914321899414, -120.7858657836914),
    505: (38.14955520629883, -120.78559112548828),
    506: (38.15018081665039, -120.78546905517578),
    507: (38.148681640625, -120.78858184814453),
    508: (38.14809799194336, -120.78727722167969),
    509: (38.14791488647461, -120.78558349609375),
    510: (38.148048400878906, -120.78516387939453),
    511: (38.148773193359375, -120.78800201416016),
    512: (38.1482048034668, -120.78649139404297),
    513: (38.14846420288086, -120.78553771972656),
    514: (38.14806365966797, -120.78932189941406),
    515: (38.1475944519043, -120.78753662109375),
    516: (38.145992279052734, -120.78764343261719),
    517: (38.147003173828125, -120.78844451904297),
    518: (38.14594650268555, -120.78685760498047),
    1300: (38.506004333496094, -120.79766082763672),
    1301: (38.506587982177734, -120.79779052734375),
    1302: (38.50718688964844, -120.79734802246094),
    1303: (38.50724792480469, -120.79829406738281),
    1304: (38.50733184814453, -120.7967529296875),
    1305: (38.506893157958984, -120.79652404785156),
    1306: (38.50655746459961, -120.79510498046875),
    1307: (38.507179260253906, -120.79487609863281),
    1308: (38.506568908691406, -120.79683685302734),
    1309: (38.5062255859375, -120.79696655273438),
    1310: (38.506229400634766, -120.79557037353516),
    1311: (38.50590896606445, -120.79559326171875),
    1312: (38.50571060180664, -120.79660034179688),
    1313: (38.505611419677734, -120.79607391357422),
    1314: (38.50545120239258, -120.79638671875),
    1315: (38.50564956665039, -120.79755401611328),
    1316: (38.50514221191406, -120.7978744506836),
    1317: (38.505279541015625, -120.79678344726562),
    1318: (38.50477981567383, -120.7974853515625),
    1319: (38.505733489990234, -120.79812622070312),
    1320: (38.506534576416016, -120.7989730834961),
    1321: (38.505680084228516, -120.7990951538086),
    1322: (38.50444030761719, -120.79913330078125),
    1323: (38.50520324707031, -120.7984848022461),
    801: (38.506587982177734, -120.79779052734375),
    802: (38.50718688964844, -120.79734802246094),
    803: (38.50724792480469, -120.79829406738281),
    804: (38.50733184814453, -120.7967529296875),
    805: (38.506893157958984, -120.79652404785156),
    806: (38.50655746459961, -120.79510498046875),
    807: (38.507179260253906, -120.79487609863281),
    808: (38.506568908691406, -120.79683685302734),
    809: (38.5062255859375, -120.79696655273438),
    810: (38.506229400634766, -120.79557037353516),
    811: (38.50590896606445, -120.79559326171875),
    812: (38.50571060180664, -120.79660034179688),
    813: (38.505611419677734, -120.79607391357422),
    814: (38.50545120239258, -120.79638671875),
    815: (38.50564956665039, -120.79755401611328),
    816: (38.50514221191406, -120.7978744506836),
    817: (38.505279541015625, -120.79678344726562),
    818: (38.50477981567383, -120.7974853515625),
    819: (38.505733489990234, -120.79812622070312),
    820: (38.506534576416016, -120.7989730834961),
    821: (38.505680084228516, -120.7990951538086),
    822: (38.50444030761719, -120.79913330078125),
    823: (38.50520324707031, -120.7984848022461),
    824: (38.50476837158203, -120.79838562011719),
    825: (38.50437927246094, -120.79798126220703),
    827: (38.50798797607422, -120.79448699951172),
    828: (38.5061149597168, -120.79402923583984),
    401: (38.431915283203125, -120.96541595458984),
    402: (38.431888580322266, -120.96483612060547),
    403: (38.4322509765625, -120.96546936035156),
    404: (38.43227767944336, -120.96485900878906),
    405: (38.43230438232422, -120.96441650390625),
    406: (38.43255615234375, -120.96488952636719),
    408: (38.432777404785156, -120.9669189453125),
    409: (38.433223724365234, -120.96697235107422),
    410: (38.43375015258789, -120.9669418334961),
    411: (38.43077850341797, -120.96622467041016),
    412: (38.43091583251953, -120.96663665771484),
    413: (38.43063735961914, -120.96785736083984),
    414: (38.43002700805664, -120.96749877929688),
    415: (38.43063735961914, -120.9666976928711),
    416: (38.43058395385742, -120.96700286865234),
    417: (38.43080520629883, -120.96736145019531),
    418: (38.43077850341797, -120.96808624267578),
    419: (38.43033218383789, -120.96736145019531),
    420: (38.43030548095703, -120.96785736083984),
    600: (38.41737365722656, -120.9493179321289),
    642: (38.41261291503906, -120.95011138916016),
    644: (38.41255569458008, -120.95069122314453),
    645: (38.41291809082031, -120.94975280761719),
    646: (38.41238784790039, -120.95085906982422),
    649: (38.41522216796875, -120.95005798339844),
    651: (38.41477966308594, -120.95024871826172),
    653: (38.41236114501953, -120.94789123535156),
    656: (38.41458511352539, -120.95175170898438),
    659: (38.414249420166016, -120.94966888427734),
    661: (38.41211700439453, -120.9535140991211),
    662: (38.41253662109375, -120.95446014404297),
    664: (38.41349411010742, -120.94889068603516),
    665: (38.414520263671875, -120.94795989990234),
    666: (38.416015625, -120.94960021972656),
    667: (38.414939880371094, -120.94808197021484),
    668: (38.41300582885742, -120.95339965820312),
    669: (38.41335678100586, -120.95158386230469),
    670: (38.41355514526367, -120.95103454589844),
    671: (38.416221618652344, -120.95032501220703),
    675: (38.414466857910156, -120.9533920288086),
    676: (38.41484832763672, -120.95587158203125),
    679: (38.4171142578125, -120.9493179321289),
    680: (38.41756057739258, -120.94951629638672),
}


def get_node_location(node):
    """
    Get SoilSCAPE node location by id.

    Arguments
    ---------
    node : int
        node id

    Returns
    -------
    location : tuple
        (lat, lon) coordinates
    """

    if node not in NODE_LOCATIONS:
        _logger.info("Looking up location for '%s' node %d" % (NODE2SITE[node], node))
        source = SoilSCAPENode(site=NODE2SITE[node], node=node)
        NODE_LOCATIONS[node] = (source.lat, source.lon)
    return NODE_LOCATIONS[node]


def get_site_coordinates(site, time=None, depth=None):
    """
    Get location coordinates for the given SoilSCAPE site.

    Arguments
    ---------
    site : str
        SoilSCAPE site, e.g. 'Canton_OK'
    time : array, datetime64, str
        datetime(s). Default is the current time.
    depth : float, array
        depth(s). Default: [4, 13, 30] (all available depths)

    Returns
    -------
    coords : Coordinates
        Coordinates with (lat_lon) for all nodes at the site and the given time and depth
    """

    if site not in NODES:
        raise ValueError("site '%s' not found" % site)

    if time is None:
        time = np.datetime64(datetime.datetime.now())  # now

    if depth is None:
        depth = [4, 13, 30]  # all

    lats = []
    lons = []
    for node in NODES[site]:
        try:
            lat, lon = get_node_location(node)
        except:
            _logger.exception("Could not get coordinates for '%s' node '%s'" % (NODE2SITE[node], node))
            continue
        lats.append(lat)
        lons.append(lon)

    return podpac.Coordinates([[lats, lons], time, depth], dims=["lat_lon", "time", "alt"], crs=CRS)


class SoilSCAPEFile(podpac.data.Dataset):
    """ SoilSCAPE datasource from file. """

    data_key = ["soil_moisture", "moisture_flag"]
    alt_key = "depth"

    @property
    def lat(self):
        return self.dataset.lat.item()

    @property
    def lon(self):
        return self.dataset.lon.item()

    @property
    def physicalid(self):
        # note: this should be the same as the node number
        return self.dataset.physicalid.item()

    def get_coordinates(self):
        coordinates = super(SoilSCAPEFile, self).get_coordinates()
        coordinates.set_trait("crs", CRS)
        return coordinates


class SoilSCAPENode(SoilSCAPEFile):
    """ SoilSCAPE 20min soil moisture for a particular node.

        Data is loaded from the THREDDS https fileserver.

        Attributes
        ----------
        site : str
            SoilSCAPE site, e.g. 'Canton_OK'.
        node : int
            SoilSCAPE node id.
    """

    site = tl.Enum(list(NODES)).tag(attr=True)
    node = tl.Int().tag(attr=True)
    cache_dataset = tl.Bool(True)

    _repr_keys = ["site", "node"]

    @tl.validate("node")
    def _validate_node(self, d):
        if d["value"] not in NODES[self.site]:
            raise ValueError("Site '%s' does not have a node n%d" % (self.site, d["value"]))

        return d["value"]

    @property
    def source(self):
        return "{base_url}/{filename}.nc".format(base_url=SOILSCAPE_FILESERVER_BASE, filename=self.filename)

    @property
    def filename(self):
        return "soil_moist_20min_{site}_n{node}".format(site=self.site, node=self.node)


class SoilSCAPE20min(podpac.core.compositor.compositor.BaseCompositor):
    """ SoilSCAPE 20min soil moisture data for an entire site.

        Data is loaded from the THREDDS https fileserver.

        Attributes
        ----------
        site : str
            SoilSCAPE site, e.g. 'Canton_OK'.
        exclude : list
            data points with these quality flags will be excluded. Default excludes [1, 2, 3, 4].
            Flags::
             * 0 - (G) Good (Standard for all data)
             * 1 - (D) Dubious (Automatically flagged, spikes etc.,)
             * 2 - (I) Interpolated / Estimated
             * 3 - (B) Bad (Manually flagged)
             * 4 - (M) Missing
             * 5 - (C) Exceeds field size (Negative SM values, fixed at 0.1 percent)
    """

    site = tl.Enum(list(NODES), allow_none=True, default_value=None).tag(attr=True)
    exclude = tl.List([1, 2, 3, 4]).tag(attr=True)
    dataset_expires = tl.Any()

    @tl.validate("dataset_expires")
    def _validate_dataset_expires(self, d):
        podpac.core.cache.utils.expiration_timestamp(d["value"])
        return d["value"]

    @property
    def _repr_keys(self):
        keys = []
        if self.site is not None:
            keys.append("site")
        return keys

    @podpac.cached_property
    def nodes(self):
        if self.site is not None:
            return [(self.site, node) for node in NODES[self.site]]
        else:
            return [(site, node) for site in NODES for node in NODES[node]]

    @podpac.cached_property
    def sources(self):
        return [self._make_source(site, node) for site, node in self.nodes]

    def _make_source(self, site, node):
        return SoilSCAPENode(site=site, node=node, cache_ctrl=self.cache_ctrl, dataset_expires=self.dataset_expires)

    def select_sources(self, coordinates):
        return [source for source in self.sources if (source.lat, source.lon) in coordinates["lat_lon"]]

    def composite(self, coordinates, data_arrays, result=None):
        if result is None:
            result = self.create_output_array(coordinates)

        flag = self.create_output_array(coordinates)
        for source, data in zip(self.select_sources(coordinates), data_arrays):
            loc = {"alt": data.alt, "time": data.time, "lat_lon": (source.lat, source.lon)}
            result.loc[loc] = data.sel(output="soil_moisture", drop=True)
            flag.loc[loc] = data.sel(output="moisture_flag", drop=True)

        b = flag.isin(self.exclude)
        result.data[b.data] = np.nan
        return result

    def make_coordinates(self, time=None, depth=None):
        """
        Make coordinates with the site locations and the given time and depth.

        Arguments
        ---------
        time : array, datetime64, str
            datetime(s). Default is the current time.
        depth : float, array
            depth(s). Default: [4, 13, 30] (all available depths)

        Returns
        -------
        coords : Coordinates
            Coordinates with (lat_lon) for all nodes at the site and the given time and depth
        """

        return get_site_coordinates(self.site, time=time, depth=depth)

    @property
    def available_sites(self):
        return list(NODES.keys())


def test_soilscape():
    # 20m local file
    node = SoilSCAPEFile(source="/home/jmilloy/Creare/Pipeline/SoilSCAPE_1339/data/soil_moist_20min_Canton_OK_n101.nc")
    coords_source = podpac.Coordinates([node.coordinates["alt"], node.coordinates["time"][:5]], crs=CRS)
    coords_interp_time = podpac.Coordinates(
        [node.coordinates["alt"], "2012-01-01T12:00:00"], dims=["alt", "time"], crs=CRS
    )
    coords_interp_alt = podpac.Coordinates([5, node.coordinates["time"][:5]], dims=["alt", "time"], crs=CRS)

    o1 = node.eval(coords_source)
    o2 = node.eval(coords_interp_time)
    o3 = node.eval(coords_interp_alt)

    # 20m url https url
    node = SoilSCAPEFile(
        source="https://thredds.daac.ornl.gov/thredds/fileServer/ornldaac/1339/soil_moist_20min_Canton_OK_n101.nc"
    )
    node.coordinates
    o1 = node.eval(coords_source)
    o2 = node.eval(coords_interp_time)
    o3 = node.eval(coords_interp_alt)

    # 20m site and node
    node = SoilSCAPENode(site="Canton_OK", node=101, cache_ctrl=["disk"])
    node.coordinates
    o1 = node.eval(coords_source)
    o2 = node.eval(coords_interp_time)
    o3 = node.eval(coords_interp_alt)

    # 20m site (composite), with filtering
    sm = SoilSCAPE20min(site="Canton_OK", cache_ctrl=["disk"])
    coords_source = sm.make_coordinates(time=sm.sources[0].coordinates["time"][:5])
    coords_interp_time = sm.make_coordinates(time="2016-01-01")
    coords_interp_alt = sm.make_coordinates(time=sm.sources[0].coordinates["time"][:5], depth=5)
    o1 = sm.eval(coords_source)
    o2 = sm.eval(coords_interp_time)
    o3 = sm.eval(coords_interp_alt)