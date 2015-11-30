"""
Vacationmode device
"""

from .overview import Overview

OVERVIEW_URL = '/overview/vacationmode'


class Vacationmode(object):
    """ Vacationmode device
        Args:
            session (verisure.session): Current session
    """

    def __init__(self, session):
        self._session = session

    def get(self):
        """ Get device overview """
        status = self._session.get(OVERVIEW_URL)
        return [Overview('vacationmode', status)]
