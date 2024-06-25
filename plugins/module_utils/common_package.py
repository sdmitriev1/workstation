"""Module containing common entities for different custom package installation modules"""

import os
import json
import zipfile
import platform
import shutil
import tempfile
import tarfile
import subprocess

from urllib.request import urlopen
from urllib.error import URLError
from urllib.request import urlretrieve


class CommonPackage:
    """Class representing common entities for different custom package installation modules"""
    def __init__(self, name, bin_dir, version_flag):
        self.name = name
        self.full_path = os.path.join(bin_dir, name)
        self.version_flag = version_flag
        self.failed = False
        self.changed = False
        self.message = None
        self.latest_version_data = None

    def run(self, desired_state):
        """Wrapper to launch one of the basic actions: present, latest or absent"""
        action = getattr(self, desired_state)
        action()
        return self._get_status()

    def present(self):
        """Method to make sure that the package is installed"""
        if not self.is_package_installed():
            if self._install_latest_package() is None:
                self.failed = True
            self.changed = True

    def latest(self):
        """Method to make sure that the latest version of package is installed"""
        if (not self.is_package_installed() or
                (self.is_package_installed() and not self.is_package_latest())):
            if self._install_latest_package() is None:
                self.failed = True
            self.changed = True

    def absent(self):
        """Method to make sure that the package is not installed"""
        if self.is_package_installed():
            if not self._uninstall_package():
                self.failed = True
            self.changed = True

    def is_package_installed(self):
        """Method to determine whether the required binary is presented"""
        return os.path.isfile(self.full_path)

    def is_package_latest(self):
        """Method to determine whether the required binary is the latest available version"""
        if self.get_latest_version() is None or self._get_current_version_data() is None:
            return None
        return self.get_latest_version() in str(self._get_current_version_data())

    def get_latest_version(self):
        """Method to get the latest available version of the package"""
        raise NotImplementedError

    def get_latest_version_data(self):
        """Method to get the JSON with the latest version data"""
        raise NotImplementedError

    def _get_status(self):
        return self.failed, self.changed, self.message

    def _get_current_version_data(self):
        output = subprocess.run(
            [self.full_path] + self.version_flag.split(),
            capture_output=True,
            check=False,
        )
        if output.returncode != 0:
            self.message = output.stderr
            self.failed = True
            return None
        return output.stdout

    def _uninstall_package(self):
        try:
            os.remove(self.full_path)
        except OSError as e:
            self.message = e.strerror
            self.failed = True
            return False
        return True

    def _get_latest_version(self, version_key):
        if self.get_latest_version_data() is None:
            return None
        return self.get_latest_version_data()[version_key]

    def _get_latest_version_data(self, url):
        if self.latest_version_data is None:
            try:
                with urlopen(url) as conn:
                    response = conn.read()
            except URLError as e:
                self.message = e.reason
                self.failed = True
                return None
            try:
                data = json.loads(response)
            except json.JSONDecodeError as e:
                self.message = e.msg
                self.failed = True
                return None
            self.latest_version_data = data
        return self.latest_version_data

    def _get_download_url(self):
        if self.get_latest_version_data() is None:
            return None
        system = platform.system().lower()
        arch = 'arm64' if platform.machine().lower() == 'aarch64' else platform.machine().lower()

        url = self._download_url_filter(system, arch)
        if url is None:
            self.failed = True
            self.message = "There are no installation candidates, aborting..."

        return url

    def _install_latest_package(self):
        url = self._get_download_url()
        if url is None:
            return None
        filename = url.split('/')[-1]

        with tempfile.TemporaryDirectory() as tmpdir:
            temp_path = os.path.join(tmpdir, filename)
            try:
                urlretrieve(url, temp_path)
            except URLError as e:
                self.message = e.reason
                self.failed = True
                return None

            _filename = filename.split('.')
            if len(_filename) > 1 and _filename[-1] == 'zip':
                with zipfile.ZipFile(temp_path) as z:
                    z.extractall(tmpdir)
            elif len(_filename) > 1 and _filename[-2] == 'tar':
                with tarfile.open(temp_path) as tar:
                    tar.extractall(tmpdir)

            if len(_filename) > 1:
                temp_path = os.path.join(tmpdir, self.name)

            shutil.copyfile(temp_path, self.full_path)
        os.chmod(self.full_path, 0o755)
        return self.full_path

    def _download_url_filter(self, system, arch):
        raise NotImplementedError
