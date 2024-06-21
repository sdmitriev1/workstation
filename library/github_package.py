import os
import json
import shutil
import tarfile
import tempfile
import platform
import subprocess

from urllib.request import urlretrieve
from urllib.request import urlopen
from urllib.error import URLError
from ansible.module_utils.basic import AnsibleModule

GITHUB_LATEST_RELEASE_API = 'https://api.github.com/repos/'


class GithubPackage:
    def __init__(self, name, bin_dir, repo, version_flag):
        self.name = name
        self.dir = bin_dir
        self.full_path = os.path.join(self.dir, self.name)
        self.repo = repo
        self.version_flag = version_flag
        self.failed = False
        self.changed = False
        self.message = None
        self.latest_version_data = None
        self.current_version_data = None
        self.url = None

    def run(self, desired_state):
        action = getattr(self, '_' + desired_state)
        action()
        return self._get_status()

    def _get_status(self):
        return self.failed, self.changed, self.message

    def _is_package_installed(self):
        return os.path.isfile(self.full_path)

    def _install_latest_package(self):
        if self._get_download_url() is None:
            return None
        url = self._get_download_url()
        filename = url.split('/')[-1]

        with tempfile.TemporaryDirectory() as tmpdir:
            temp_path = os.path.join(tmpdir, filename)
            try:
                path = urlretrieve(url, temp_path)
            except URLError as e:
                self.message = e.reason
                self.failed = True
                return None

            if len(filename.split('.')) > 1:
                with tarfile.open(temp_path) as tar:
                    tar.extractall(path=tmpdir)
                temp_path = os.path.join(tmpdir, self.name)

            shutil.copyfile(temp_path, self.full_path)
        os.chmod(self.full_path, 0o755)
        return path

    def _is_package_latest(self):
        if self._get_latest_version() is None or self._get_current_version_data() is None:
            return None
        return self._get_latest_version() in str(self._get_current_version_data())

    def _get_latest_version_data(self):
        if self.latest_version_data is None:
            url = ''.join((GITHUB_LATEST_RELEASE_API, self.repo, '/releases/latest'))
            try:
                response = urlopen(url).read()
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
        if self._get_latest_version_data() is None:
            return None
        assets = self._get_latest_version_data()['assets']
        system = platform.system().lower()
        arch = 'arm64' if platform.machine().lower() == 'aarch64' else platform.machine().lower()
        urls = []
        for asset in assets:
            a = asset['name'].split('.')
            if len(a) > 0 and all([x in a[0] for x in (self.name, system, arch)]):
                if len(a) == 1 or any([x in a[-1] for x in ('gz',)]):
                    urls.append(asset['browser_download_url'])

        if len(urls) == 0:
            self.failed = True
            self.message = f"There are no installation candidates, aborting..."
            return None
        return sorted(urls)[0]

    def _get_latest_version(self):
        if self._get_latest_version_data() is None:
            return None
        return self._get_latest_version_data()['name']

    def _get_current_version_data(self):
        if self.current_version_data is None:
            output = subprocess.run([self.full_path] + self.version_flag.split(), capture_output=True)
            if output.returncode != 0:
                self.message = output.stderr
                self.failed = True
                return None
            self.current_version_data = output.stdout
        return self.current_version_data

    def _uninstall_package(self):
        try:
            os.remove(self.full_path)
        except OSError as e:
            self.message = e.strerror
            self.failed = True
            return None
        return True

    def _present(self):
        if not self._is_package_installed():
            if self._install_latest_package() is None:
                self._failed = True
            self.changed = True

    def _latest(self):
        if (not self._is_package_installed() or
                (self._is_package_installed() and not self._is_package_latest())):
            if self._install_latest_package() is None:
                self._failed = True
            self.changed = True

    def _absent(self):
        if self._is_package_installed():
            if self._uninstall_package() is None:
                self.failed = True
            self.changed = True


def main():
    module = AnsibleModule(
        argument_spec=dict(
            name=dict(
                required=True,
                type='str',
            ),
            path=dict(
                default='/usr/local/bin',
                required=False,
                type='path',
            ),
            repo=dict(
                required=True,
                type='str',
            ),
            state=dict(
                default='present',
                choices=[
                    'present',
                    'latest',
                    'absent',
                ],
            ),
            version_flag=dict(
                default='--version',
                required=False,
                type='str',
            ),
        ),
        supports_check_mode=True,
    )

    package_name = module.params.get('name')
    package_dir = module.params.get('path')
    package_repo = module.params.get('repo')
    package_desired_state = module.params.get('state')
    package_version_flag = module.params.get('version_flag')

    package = GithubPackage(
        name=package_name,
        bin_dir=package_dir,
        repo=package_repo,
        version_flag=package_version_flag,
    )

    failed, changed, message = package.run(package_desired_state)

    if failed:
        module.fail_json(msg=message)

    module.exit_json(
        changed=changed,
        msg=message,
    )


if __name__ == '__main__':
    main()
