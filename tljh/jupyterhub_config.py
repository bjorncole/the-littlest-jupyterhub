"""
JupyterHub config for the littlest jupyterhub.
"""

from glob import glob
import os
import pluggy

from systemdspawner import SystemdSpawner
from dockerspawner import DockerSpawner
from tljh import configurer, user, hooks
from tljh.config import INSTALL_PREFIX, USER_ENV_PREFIX, CONFIG_DIR
from tljh.normalize import generate_system_username
from tljh.yaml import yaml
from jupyterhub_traefik_proxy import TraefikTomlProxy

from traitlets import Dict, Unicode, List

class UserCreatingSpawner(SystemdSpawner):
    """
    SystemdSpawner with user creation on spawn.

    FIXME: Remove this somehow?
    """
    user_groups = Dict(key_trait=Unicode(), value_trait=List(Unicode()), config=True)

    def start(self):
        """
        Perform system user activities before starting server
        """
        # FIXME: Move this elsewhere? Into the Authenticator?
        system_username = generate_system_username('jupyter-' + self.user.name)

        # FIXME: This is a hack. Allow setting username directly instead
        self.username_template = system_username
        user.ensure_user(system_username)
        user.ensure_user_group(system_username, 'jupyterhub-users')
        if self.user.admin:
            user.ensure_user_group(system_username, 'jupyterhub-admins')
        else:
            user.remove_user_group(system_username, 'jupyterhub-admins')
        if self.user_groups:
            for group, users in self.user_groups.items():
                if self.user.name in users:
                    user.ensure_user_group(system_username, group)
        return super().start()

#c.JupyterHub.spawner_class = UserCreatingSpawner

c.JupyterHub.spawner_class = UserCreatingSpawner

c.JupyterHub.log_level = 'DEBUG'

c.UserCreatingSpawner.debug = True

# smaller notebook - use scipy-notebook when feeling more spunky
#c.DockerSpawner.image = 'jupyter/base-notebook'

#c.DockerSpawner.environment.update({'JUPYTERHUB_API_URL': 'http://172.17.0.1:80'})

#c.DockerSpawner.host_ip = '172.17.0.2'

# leave users running when the Hub restarts
c.JupyterHub.cleanup_servers = False

# Use a high port so users can try this on machines with a JupyterHub already present
c.JupyterHub.hub_port = 15001

#c.JupyterHub.hub_bind_url = 'http://172.17.0.1:80'

#c.JupyterHub.hub_connect_url = 'http://172.17.0.1:80'

#c.JupyterHub.hub_ip = '172.17.0.1'

c.TraefikTomlProxy.should_start = False

dynamic_conf_file_path = os.path.join(INSTALL_PREFIX, 'state', 'rules.toml')
c.TraefikTomlProxy.toml_dynamic_config_file = dynamic_conf_file_path
c.JupyterHub.proxy_class = TraefikTomlProxy

#c.SystemdSpawner.extra_paths = [os.path.join(USER_ENV_PREFIX, 'bin')]
#c.SystemdSpawner.default_shell = '/bin/bash'
# Drop the '-singleuser' suffix present in the default template
#c.SystemdSpawner.unit_name_template = 'jupyter-{USERNAME}'

tljh_config = configurer.load_config()
configurer.apply_config(tljh_config, c)

# Let TLJH hooks modify `c` if they want

# Set up plugin infrastructure
pm = pluggy.PluginManager('tljh')
pm.add_hookspecs(hooks)
pm.load_setuptools_entrypoints('tljh')
# Call our custom configuration plugin
pm.hook.tljh_custom_jupyterhub_config(c=c)

# Load arbitrary .py config files if they exist.
# This is our escape hatch
extra_configs = sorted(glob(os.path.join(CONFIG_DIR, 'jupyterhub_config.d', '*.py')))
for ec in extra_configs:
    load_subconfig(ec)
