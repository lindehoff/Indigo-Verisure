#!/usr/bin/env python2.5

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

# for the latest version and documentation:
# https://github.com/jheddings/indigo-ghpu

import os
import tempfile
import subprocess
import shutil
import json
import httplib
import plistlib
import indigo

from urllib2 import urlopen
from StringIO import StringIO
from zipfile import ZipFile

################################################################################
class GitHubPluginUpdater(object):

    #---------------------------------------------------------------------------
    def __init__(self, owner, repo, plugin=None):
        self.owner = owner
        self.repo = repo
        self.plugin = plugin

    #---------------------------------------------------------------------------
    # install the latest version of the plugin represented by this updater
    def install(self):
        self._log('Installing plugin from %s/%s...' % (self.owner, self.repo))
        latestRelease = self.getLatestRelease()

        if (latestRelease == None):
            self._error('No release available')
            return False

        try:
            self._installRelease(latestRelease)
        except Exception as e:
            self._error(str(e))
            return False

        return True

    #---------------------------------------------------------------------------
    # updates the contained plugin if needed
    def update(self, currentVersion=None):
        update = self._prepareForUpdate(currentVersion)
        if (update == None): return False

        try:
            self._installRelease(update)
        except Exception as e:
            self._error(str(e))
            return False

        return True

    #---------------------------------------------------------------------------
    # returns the URL for an update if there is one
    def checkForUpdate(self, currentVersion=None):
        update = self._prepareForUpdate(currentVersion)

        return (update != None)

    #---------------------------------------------------------------------------
    # returns the update package, if there is one
    def getUpdate(self, currentVersion):
        self._debug('Current version is: %s' % currentVersion)

        update = self.getLatestRelease()

        if (update == None):
            self._debug('No release available')
            return None

        # assume the tag is the release version
        latestVersion = update['tag_name'].lstrip('v')
        self._debug('Latest release is: %s' % latestVersion)

        if (ver(currentVersion) >= ver(latestVersion)):
            return None

        return update

    #---------------------------------------------------------------------------
    # returns the latest release information from a given user / repo
    # https://developer.github.com/v3/repos/releases/
    def getLatestRelease(self):
        self._debug('Getting latest release from %s/%s...' % (self.owner, self.repo))
        return self._GET('/repos/' + self.owner + '/' + self.repo + '/releases/latest')

    #---------------------------------------------------------------------------
    # returns a tuple for the current rate limit: (limit, remaining, resetTime)
    # https://developer.github.com/v3/rate_limit/
    # NOTE this does not count against the current limit
    def getRateLimit(self):
        limiter = self._GET('/rate_limit')

        remain = int(limiter['rate']['remaining'])
        limit = int(limiter['rate']['limit'])
        resetAt = int(limiter['rate']['reset'])

        return (limit, remain, resetAt)

    #---------------------------------------------------------------------------
    # form a GET request to api.github.com and return the parsed JSON response
    def _GET(self, requestPath):
        self._debug('GET %s' % requestPath)

        headers = {
            'User-Agent': 'Indigo-Plugin-Updater',
            'Accept': 'application/vnd.github.v3+json'
        }

        data = None

        try:
            conn = httplib.HTTPSConnection('api.github.com')
            conn.request('GET', requestPath, None, headers)

            resp = conn.getresponse()
            self._debug('HTTP %d %s' % (resp.status, resp.reason))

            if (resp.status == 200):
                data = json.loads(resp.read())
            elif (400 <= resp.status < 500):
                error = json.loads(resp.read())
                self._error('Client Error: %s' % error['message'])
            else:
                self._error('Unhandled Error: %s' % resp.reason)

        except Exception as e:
            self._error('Unhandled Exception: %s' % str(e))
            return None

        return data

    #---------------------------------------------------------------------------
    # prepare for an update
    def _prepareForUpdate(self, currentVersion=None):
        self._log('Checking for updates...')

        # sort out the currentVersion based on user params
        if ((currentVersion == None) and (self.plugin == None)):
            self._error('Must provide either currentVersion or plugin reference')
            return None
        elif (currentVersion == None):
            currentVersion = str(self.plugin.pluginVersion)
            self._debug('Plugin version detected: %s' % currentVersion)
        else:
            self._debug('Plugin version provided: %s' % currentVersion)

        update = self.getUpdate(currentVersion)

        if (update == None):
            self._log('No updates are available')
            return None

        self._error('A new version is available: %s' % update['html_url'])

        return update

    #---------------------------------------------------------------------------
    # verifies the plugin info in the zipfile and returns the confirmed name-version
    def _verifyPluginInfo(self, zipfile):
        topdir = zipfile.namelist()[0]

        # read and confirm the plugin info contained in the zipfile
        plistFile = os.path.join(topdir, 'Contents', 'Info.plist')
        self._debug('Searching for plugin info: %s' % plistFile)

        plistData = zipfile.read(plistFile)
        if (plistData == None):
            raise Exception('Unable to read new plugin info')

        plist = plistlib.readPlistFromString(plistData)

        pluginId = plist.get('CFBundleIdentifier', None)
        pluginName = plist.get('CFBundleDisplayName', None)
        pluginVersion = plist.get('PluginVersion', None)

        self._debug('Detected plugin in zipfile: %s' % pluginId)

        if (pluginId == None):
            raise Exception('Unable to detect pluginId in download')
        elif (pluginName == None):
            raise Exception('Unable to detect pluginName in download')
        elif (pluginVersion == None):
            raise Exception('Unable to detect pluginVersion in download')
        elif (self.plugin and (self.plugin.pluginId != pluginId)):
            raise Exception('ID mismatch in download')

        self._debug('Found plugin: %s-%s' % (pluginName, pluginVersion))

        return pluginName + '-' + pluginVersion

    #---------------------------------------------------------------------------
    # install a given release
    def _installRelease(self, release):
        tmpdir = tempfile.gettempdir()
        self._debug('Workspace: %s' % tmpdir)

        zipfile = self._getZipFileFromRelease(release)
        newPluginName = self._verifyPluginInfo(zipfile)

        # the top level directory should be the first entry in the zipfile
        # it is typically a combination of the owner, repo & release tag
        repotag = zipfile.namelist()[0]

        # this is where the files will end up after extraction
        destDir = os.path.join(tmpdir, repotag)
        self._debug('Destination directory: %s' % destDir)
        if (os.path.exists(destDir)): shutil.rmtree(destDir)

        # this is where the plugin will reside prior to installation
        newPluginDir = os.path.join(tmpdir, newPluginName + '.indigoPlugin')
        self._debug('Plugin directory: %s' % newPluginDir)
        if (os.path.exists(newPluginDir)): shutil.rmtree(newPluginDir)

        # at this point, we should have been able to confirm the top-level directory
        # based on reading the pluginId, we know the plugin in the zipfile matches our
        # internal plugin reference (if we have one), temp directories are available
        # and we know the package location for installing the plugin

        zipfile.extractall(tmpdir)

        # now, make sure we got what we expected
        if (not os.path.exists(destDir)):
            raise Exception('Failed to extract plugin')

        # for 'open' to work properly, we need to use the .indigoPlugin package extension
        os.rename(destDir, newPluginDir)

        self._debug('Installing %s' % newPluginName)
        subprocess.call(['open', newPluginDir])

        # all clear...  the new plugin has been installed

    #---------------------------------------------------------------------------
    # return the valid zipfile from the release, or raise an exception
    def _getZipFileFromRelease(self, release):
        # download and verify zipfile from the release package
        zipball = release.get('zipball_url', None)
        if (zipball == None):
            raise Exception('Invalid release package: no zipball')

        self._debug('Downloading zip file: %s' % zipball)

        zipdata = urlopen(zipball).read()
        zipfile = ZipFile(StringIO(zipdata))

        self._debug('Verifying zip file (%d bytes)...' % len(zipdata))
        if (zipfile.testzip() != None):
            raise Exception('Download corrupted')

        return zipfile

    #---------------------------------------------------------------------------
    # convenience method for log messages
    def _log(self, msg):
        indigo.server.log(msg)

    #---------------------------------------------------------------------------
    # convenience method for debug messages
    def _debug(self, msg):
        if self.plugin:
            self.plugin.debugLog(msg)

    #---------------------------------------------------------------------------
    # convenience method for error messages
    def _error(self, msg):
        if self.plugin:
            self.plugin.errorLog(msg)

################################################################################
# maps the standard version string as a tuple for comparrison
def ver(vstr): return tuple(map(int, (vstr.split('.'))))
