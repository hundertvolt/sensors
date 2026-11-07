from asy_isl29125_driver import ISL29125_Reader

from asy_webserver_service import _ModuleLike


def check(reader: ISL29125_Reader) -> _ModuleLike:
    return reader
