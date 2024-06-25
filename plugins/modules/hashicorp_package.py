"""Ansible module to install, remove or update packages from HashiCorp"""

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.common_package import CommonPackage

HASHICORP_LATEST_RELEASE_API = 'https://api.releases.hashicorp.com/v1/releases/'


class HashiCorpPackage(CommonPackage):
    """Class representing unique entities required for HashCorp package operations"""
    def get_latest_version_data(self):
        """Method to get the latest release data from the repository"""
        url = ''.join((HASHICORP_LATEST_RELEASE_API, self.name, '/latest'))
        return self._get_latest_version_data(url)

    def get_latest_version(self):
        """Method to get the latest version from the latest release data"""
        return self._get_latest_version(version_key='version')

    def _download_url_filter(self, system, arch):
        url = None
        for build in self.get_latest_version_data()['builds']:
            if build['os'] == system and build['arch'] == arch:
                url = build['url']
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
            'state': {
                'default': 'present',
                'choices': [
                    'present',
                    'latest',
                    'absent',
                ],
            },
            'version_flag': {
                'default': '-version',
                'required': False,
                'type': 'str',
            },
        },
        supports_check_mode=False,
    )

    package_name = module.params.get('name')
    package_dir = module.params.get('path')
    package_desired_state = module.params.get('state')
    package_version_flag = module.params.get('version_flag')

    package = HashiCorpPackage(
        name=package_name,
        bin_dir=package_dir,
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
