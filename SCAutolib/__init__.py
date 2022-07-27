from os.path import (join)

import coloredlogs
import logging
import subprocess
from pathlib import Path

fmt = "%(name)s:%(module)s.%(funcName)s.%(lineno)d [%(levelname)s] %(message)s"
date_fmt = "%H:%M:%S"
coloredlogs.install(level="DEBUG", fmt=fmt, datefmt=date_fmt,
                    field_styles={'levelname': {'bold': True, 'color': 'blue'}})
logger = logging.getLogger(__name__)
# Disable logs from imported packages
logging.getLogger("paramiko").setLevel(logging.WARNING)
logging.getLogger("invoke").setLevel(logging.WARNING)
logging.getLogger("fabric").setLevel(logging.WARNING)

DIR_PATH = Path(__file__).parent
TEMPLATES_DIR = DIR_PATH.joinpath("templates")

LIB_DIR = Path("/etc/SCAutolib")
SETUP_IPA_SERVER = LIB_DIR.joinpath("ipa-install-server.sh")
LIB_BACKUP = LIB_DIR.joinpath("backup")
LIB_KEYS = join(LIB_DIR, "keys")
LIB_CERTS = join(LIB_DIR, "certs")
LIB_DUMP = LIB_DIR.joinpath("dump")
LIB_DUMP_USERS = LIB_DUMP.joinpath("users")
LIB_DUMP_CAS = LIB_DUMP.joinpath("cas")
LIB_DUMP_CARDS = LIB_DUMP.joinpath("cards")


def run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True,
        print_=True, **kwargs) -> subprocess.CompletedProcess:
    """
    Wrapper for subrpocess.run function. This function explicitly set several
    parameter of original function and also provides similar thing as
    subprocess.check_output do. But with having this wrapper, functionality
    of this two functions is generalized and can be changed by setting
    corresponding parameters. If there are any specific parameter of
    subprocess.run function needed to be passed to this wrapper, you can do
    it by adding same parameters names in key=value format.

    :param cmd: Command to be executed
    :type cmd: list or str
    :param stdout: Redirection of stdout. Default is subprocess.PIPE
    :type stdout: None or int or IO
    :param stderr: Redirection of stderr. Default is subprocess.PIPE
    :type stderr: None or int or IO
    :param check: Specifies it return code of the command would be checked for
        0 (if return code == 0). If True and return code is not 0, then
        subprocess.CalledProcessError exception would be risen. Default is
        False.
    :type check: bool
    :param print_: Specifies it stdout and stderr should be printed to the
        terminal. Log message with stdout would have debug type and stderr
        log message would have error type. Default is True.
    :type print_: bool
    :param kwargs: Other parameters to subprocess.run function

    :exception subprocess.CalledProcessError:

    :return: Completed process from subprocess.run
    :rtype: subprocess.CompletedProcess
    """
    if type(cmd) == str:
        cmd = cmd.split(" ")
    out = subprocess.run(cmd, stdout=stdout, stderr=stderr, encoding="utf-8",
                         **kwargs)
    if print_:
        if out.stdout != "":
            logger.debug(out.stdout)
        if out.stderr != "":
            logger.warning(out.stderr)

    if check and out.returncode != 0:
        raise subprocess.CalledProcessError(out.returncode, cmd)
    return out
