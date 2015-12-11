"""
Ethernet device
"""

from .overview import Overview

OVERVIEW_URL = '/overview/ethernetstatus'


class Ethernet(object):
    """ Ethernet device

    Args:
        session (verisure.session): Current session
    """

    def __init__(self, session):
        self._session = session

    def get(self):
        """ Get device overview """
        status = self._session.get(OVERVIEW_URL)
        return [Overview('ethernet', val) for val in status]
