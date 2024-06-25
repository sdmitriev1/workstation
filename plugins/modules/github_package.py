"""Ansible module to install, remove or update packages from GitHub"""

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.common_package import CommonPackage

GITHUB_LATEST_RELEASE_API = 'https://api.github.com/repos/'


class GithubPackage(CommonPackage):
    """Class representing unique entities required for GitHub package operations"""
    def __init__(self, name, bin_dir, repo, version_flag):
        super().__init__(name, bin_dir, version_flag)
        self.repo = repo

    def get_latest_version_data(self):
        """Method to get the latest release data from the repository"""
        url = ''.join((GITHUB_LATEST_RELEASE_API, self.repo, '/releases/latest'))
        return self._get_latest_version_data(url)

    def get_latest_version(self):
        """Method to get the latest version from the latest release data"""
        return self._get_latest_version(version_key='name')

    def _download_url_filter(self, system, arch):
        url = None
        for asset in self.get_latest_version_data()['assets']:
            a = asset['name'].split('.')
            if len(a) > 0 and all(x in a[0] for x in (self.name, system, arch)):
                if len(a) == 1 or any(x in a[-2] for x in ('tar',)):
                    url = asset['browser_download_url']
                    break
        return url


def main():
    """main function is an entry point for AnsibleModule"""
    module = AnsibleModule(
        argument_spec={
            'name': {
                'required': True,
                'type': 'str',
            },
            'path': {
                'default': '/usr/local/bin',
                'type': 'path',
            },
            'repo': {
                'required': True,
                'type': 'str',
            },
            'state': {
                'default': 'present',
                'choices': [
                    'present',
                    'latest',
                    'absent',
                ],
            },
            'version_flag': {
                'default': '--version',
                'required': False,
                'type': 'str',
            },
        },
        supports_check_mode=False,
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
