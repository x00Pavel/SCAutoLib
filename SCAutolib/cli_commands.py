"""
Implementation of CLI commands for SCAutolib.
"""

import click
from SCAutolib.controller import Controller


@click.group()
def cli():
    pass


@click.command()
@click.option("--ca-type", "-t", required=False, default='all',
              show_default=True,
              help="Type of the CA to be configured. If not set, all CA's "
                   "from the config file would be configured")
@click.option("--conf-file", "-c", required=False, default="./conf.json",
              type=click.Path(exists=True, resolve_path=True),
              show_default=True)
def setup_ca(conf_file, ca_type):
    cnt = Controller(conf_file, {"ip_addr": "10.10.10.10"})
    cnt.setup_ipa_client()


@click.command()
@click.option("--conf", "-c", required=True)
@click.option("--force", "-f", required=False, default=False, is_flag=True)
@click.option("--gdm", "-g", required=False, default=False, is_flag=True)
@click.option("--install-missing", "-i", required=False, default=False,
              is_flag=True)
def prepare(conf, force, gdm, install_missing):
    cnt = Controller(conf)
    cnt.prepare(force, gdm, install_missing)


@click.command()
@click.option("--conf", "-c", required=True)
@click.option("--force", "-f", required=False, default=False, is_flag=True)
@click.option("--name", "-n", required=True, default=None)
def setup_user(name, conf, force):
    cnt = Controller(conf)
    user_dict = cnt.get_user_dict(name)
    cnt.init_ca(user_dict["local"])
    user = cnt.setup_user(user_dict, force)
    cnt.enroll_card(user, force)


cli.add_command(setup_ca)
cli.add_command(prepare)
cli.add_command(setup_user)
