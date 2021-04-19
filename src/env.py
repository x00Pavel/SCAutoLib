import logging
from os.path import (exists, realpath, isdir,
                     isfile, dirname, abspath)
import click
import yaml
import subprocess as subp
from shutil import copytree

log = logging.getLogger("env")

# TODO add docs about parameters
path = dirname(abspath(__file__))
SETUP_CA = f"{path}/env/setup_ca.sh"
SETUP_VSC = f"{path}/env/setup_virt_card.sh"
CLEANUP_CA = f"{path}/env/cleanup_ca.sh"


@click.group()
def cli():
    pass


@click.command()
@click.option("--work-dir", "-p", type=click.Path(), help="Path to working directory")
@click.option("--conf", "-c", type=click.Path(), help="Path to YAML file with configurations")
def setup_ca(work_dir, conf):
    """
    Call bash sript for settingup the local CA.
    """
    assert exists(work_dir), f"Path {work_dir} is not exist"
    assert isdir(work_dir), f"{work_dir} is not a directory"
    assert exists(realpath(conf)), f"File {conf} is not exist"
    assert isfile(realpath(conf)), f"{conf} is not a file"

    log.debug("Start setup of local CA")

    with open(conf, "r") as file:
        data = yaml.load(file, Loader=yaml.FullLoader)
    conf_dir = f"{work_dir}/conf"
    copytree(realpath(data["configs"]["dir"]), conf_dir)
    user = data["variables"]["user"]
    print(work_dir)
    out = subp.run(["bash", SETUP_CA, "--dir", work_dir,
                    "--username", user["name"],
                    "--userpasswd", user["passwd"],
                    "--pin", user["pin"],
                    "--conf-dir", conf_dir])
    assert out.returncode == 0, "Something break in setup playbook :("
    log.debug("Setup of local CA is completed")


@click.command()
@click.option("--conf-dir", "-C", type=click.Path(), help="Direc")
@click.option("--work-dir", "-w", type=click.Path())
def setup_virt_card(conf_dir, work_dir):
    assert exists(conf_dir), f"Path {conf_dir} is not exist"
    assert isdir(conf_dir), f"{conf_dir} Not a directory"
    assert exists(work_dir), f"Path {work_dir} is not exist"
    assert isdir(work_dir), f"{work_dir} Not a directory"

    log.debug("Start setup of local CA")
    out = subp.run(["bash", SETUP_VSC, "-c", conf_dir, "-w", work_dir])

    assert out.returncode == 0, "Something break in setup playbook :("
    log.debug("Setup of local CA is completed")


@click.command()
def cleanup_ca():
    log.debug("Start cleanup of local CA")
    out = subp.run(
        ["bash", CLEANUP_CA])

    assert out.returncode == 0, "Something break in setup script :("
    log.debug("Cleanup of local CA is completed")


cli.add_command(setup_ca)
cli.add_command(setup_virt_card)
cli.add_command(cleanup_ca)

if __name__ == "__main__":
    cli()
