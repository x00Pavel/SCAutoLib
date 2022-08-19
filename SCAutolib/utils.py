"""
This module provides a set of additional helping functions that are used
across the library. These functions are made based on library demands and are
not attended to cover some general use-cases or specific corner cases.
"""
import json
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from enum import Enum
from pathlib import Path

from SCAutolib import run, logger, TEMPLATES_DIR, LIB_DUMP_USERS
from SCAutolib.exceptions import SCAutolibException
from SCAutolib.models.CA import LocalCA
from SCAutolib.models.card import Card
from SCAutolib.models.file import OpensslCnf
from SCAutolib.models.user import BaseUser


class OSVersion(Enum):
    """
    Enumeration for Linux versions. Used for more convenient checks.
    """
    Fedora = 1
    RHEL_9 = 2
    RHEL_8 = 3
    CentOS_8 = 4
    CentOS_9 = 5


def _check_selinux():
    """
    Checks if specific SELinux module for virtual smart card is installed.
    This is implemented be checking the hardcoded name for the module
    (virtcacard) to be present in the list of SELinux modules. If this name is
    not present in the list, then virtcacard.cil file would be created in conf
    or subdirectory in the CA directory specified by the configuration file.
    """
    result = run("semodule -l", print_=False)
    if "virtcacard" not in result.stdout:
        logger.debug(
            "SELinux module for virtual smart cards is not present in the "
            "system. Installing...")

        run(["semodule", "-i", f"{TEMPLATES_DIR}/virtcacard.cil"])

        run(["systemctl", "restart", "pcscd"])
        logger.debug("pcscd service is restarted")

    logger.debug(
        "SELinux module for virtual smart cards is installed")


def _gen_private_key(key_path: Path):
    """
    Generate RSA private key to specified location.

    :param key_path: path to output certificate
    """
    # CAC specification do not specify key size specifies key size
    # up to 2048 bits, so keys greater than 2048 bits is not supported
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    with key_path.open("wb") as f:
        f.write(key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()))


def _get_os_version():
    """
    Find Linux version. Available version: RHEL 8, RHEL 9, Fedora.
    :return: Enum with OS version
    """
    with open('/etc/redhat-release', "r") as f:
        cnt = f.read()

    if "Red Hat Enterprise Linux release 9" in cnt:
        return OSVersion.RHEL_9
    elif "Red Hat Enterprise Linux release 8" in cnt:
        return OSVersion.RHEL_8
    elif "Fedora" in cnt:
        return OSVersion.Fedora
    elif "CentOS Stream release 8" in cnt:
        return OSVersion.CentOS_8
    elif "CentOS Stream release 9" in cnt:
        return OSVersion.CentOS_9
    else:
        raise SCAutolibException("OS is not detected.")


def _install_packages(packages):
    """
    Install given packages and log package version

    :param packages: list of packages to be installed
    """
    run(f"dnf install -y {' '.join(packages)}")
    for pkg in packages:
        pkg = run(["rpm", "-q", pkg]).stdout
        logger.debug(f"Package {pkg} is installed")


def _check_packages(packages):
    """
    Find missing packages

    :param packages: list of required packages
    :type packages: list
    :return: list of missing packages
    """
    missing = []
    for pkg in packages:
        # Return code 1 means the package is not installed
        out = run(["rpm", "-q", pkg], return_code=[0, 1])
        if out.returncode == 1:
            logger.warning(f"Package {pkg} is required for the testing, "
                           f"but is not present in the system")
            missing.append(pkg)
        else:
            logger.debug(f"Package {out.stdout.strip()} is present")
    return missing


def dump_to_json(obj):
    """
    Store serialised object to the JSON file.
    """
    with obj.dump_file.open("w") as f:
        json.dump(obj.__dict__, f)
    logger.debug(f"Object {type(obj)} is stored to the {obj.dump_file} file")


def user_factory(username):
    """
    Load user with given username from JSON file. If user have the card file
    linked, then load it as well.

    :param username: username of the user
    :type username: str

    :return: user object
    :rtype: BaseUser
    """
    user_file = LIB_DUMP_USERS.joinpath(f"{username}.json")
    logger.debug(f"Loading user {username} from {user_file}")
    result = None
    user = None
    if user_file.exists():
        result = BaseUser.load(user_file)
    if type(result) == tuple:
        user, card_file = result
        logger.debug(f"Loading card from {card_file}")
        user.card = Card.load(card_file, user=user)
    else:
        user = result
    return user


def ca_factory(path, force=False):
    """
    Create a new LocalCA object.

    .. note: Creating new IPA server with CA is not supported.
    """
    path.mkdir(exist_ok=True, parents=True)
    cnf = OpensslCnf(path.joinpath("ca.cnf"), "CA", str(path))
    ca = LocalCA(root_dir=path, cnf=cnf)
    if force:
        logger.warning(f"Removing previous local CA in a directory {path}")
        ca.cleanup()
    ca.dump_file = path.joinpath("ca-dump.json")
    cnf.create()
    cnf.save()
    ca.setup()
    run(["systemctl", "restart", "sssd"], sleep=5)
