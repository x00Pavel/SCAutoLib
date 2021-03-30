import shutil
import subprocess as subp
from os import path

from SCAutolib import log

FILE_PATH = path.dirname(path.abspath(__file__))
SERVICES = {"sssd": "/etc/sssd/sssd.conf", "krb": "/etc/krb5.conf"}
DEFAULTS = {"sssd": f"{FILE_PATH}/env/conf/sssd.conf"}


def _edit_config(config, string, section):
    with open(config, "r") as file:
        content = file.read()
    content = content.replace(f"#<{section}>", f"{string}\n#<{section}>")
    with open(config, "w+") as file:
        file.write(content)
    # TODO how to check if there was some errors?
    log.debug(f"File {config} is updated")


def edit_config(service, string, section):
    def wrapper(test):
        def inner_wrapper(*args):
            _edit_config(SERVICES[service], string, section)
            restart_service(service)
            test(args)
            restore_config(service)
            restart_service(service)
        return inner_wrapper
    return wrapper


def restart_service(service):
    try:
        subp.run(["systemctl", "restart", f"{service}"], check=True, capture_output=True, text=True, encoding="utf8")
        log.debug(f"Service {service} is restarted")
    except subp.CalledProcessError as e:
        log.error(f"Command {e.cmd} is ended with non-zero return code ({e.returncode})")
        log.error(f"stdout:\n{e.stdout}")
        log.error(f"stderr:\n{e.stderr}")
    except Exception as e:
        log.error(f"Unexpected exception is raised: {e}")
        raise e


def restore_config(service=None):
    try:
        shutil.copyfile(DEFAULTS[service], SERVICES[service])
        log.debug(f"File {SERVICES[service]} is restored")
    except shutil.SameFileError:
        log.debug(f"Source file {DEFAULTS[service]} and destination file {SERVICES[service]} are the same")
    except Exception as e:
        log.error(f"Unexpected exception is raised: {e}")
        log.error(f"File {SERVICES[service]} is not restored")
        raise e
