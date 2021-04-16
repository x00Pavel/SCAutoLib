#!/usr/bin/bash

DIR="."
NAME="localuser1"
PIN='123456'
SOPIN='12345678'
export GNUTLS_PIN=$PIN
VIRT=$DIR
NSSDB=$VIRT/db
CONF=$VIRT/conf

function help() {
  echo -e "Script for settingup the local Certificate Authority and virtual smart card"
  echo -e "\t-h -- this message"
  echo -e "\t-dir directory where SCAutoLib directory is located"
}

while (("$#")); do
  case "$1" in
  -d | --dir)
    DIR=$2
    shift 2
    ;;
  --username)
    if [ -n "$2" ] && [ ${2:0:1} != "-" ]; then
      NAME=$2
      shift 2
    else
      echo "Error: Argument for $1 is missing" >&2
      exit 1
    fi
    ;;
  --userpasswd)
    if [ -n "$2" ] && [ "${2:0:1}" != "-" ]; then
      USER_PASSWD=$2
      shift 2
    else
      echo "Error: Argument for $1 is missing" >&2
      exit 1
    fi
    ;;
  --pin)
    if [ -n "$2" ] && [ "${2:0:1}" != "-" ]; then
      PIN=$2
      shift 2
    else
      echo "Error: Argument for $1 is missing" >&2
      exit 1
    fi
    ;;

  -h | --help)
    help
    shift
    ;;
  -* | --*=) # unsupported flags
    echo "Error: Unsupported flag $1" >&2
    exit 1
    ;;
  esac
done

dnf -y module enable idm:DL1
dnf -y copr enable jjelen/vsmartcard
dnf -y install vpcd softhsm python3-pip sssd-tools
yum groupinstall "Smart Card Support" -y

if [[ ! -f "$CONF/softhsm2.conf" ]]; then
  echo "File $CONF/softhsm2.conf does not exist"
  exit 1
elif [[ ! -f "$CONF/ca.cnf" ]]; then
  echo "File $CONF/ca.cnf does not exist"
  exit
elif [[ ! -f "$CONF/req_${NAME}.cnf" ]]; then
  echo "File $CONF/req_${NAME}.cnf does not exist"
  exit 1
elif [[ ! -f "$CONF/virtcacard.cil" ]]; then
  echo "File $CONF/virtcacard.cil does not exist"
  exit 1
elif [[ ! -f "$CONF/virt_cacard.service" ]]; then
  echo "File $CONF/virt_cacard.service does not exist"
  exit 1
elif [[ ! -f "$CONF/sssd.conf" ]]; then
  echo "File $CONF/sssd.conf does not exist"
  exit 1
fi

# Configurting softhm2
P11LIB='/usr/lib64/pkcs11/libsofthsm2.so'
sed -i "s,<TESTDIR>,$VIRT,g" $CONF/softhsm2.conf
pushd $VIRT || exit

mkdir tokens
export SOFTHSM2_CONF="$CONF/softhsm2.conf" # Should I save previous value of
softhsm2-util --init-token --slot 0 --label "SC test" --so-pin="$SOPIN" --pin="$PIN"

# Creating NSS database
mkdir $NSSDB
modutil -create -dbdir sql:$NSSDB -force
modutil -list -dbdir sql:$NSSDB | grep 'library name: p11-kit-proxy.so'
if [ "$?" = "1" ]; then
  modutil -force -add 'SoftHSM PKCS#11' -dbdir sql:$NSSDB -libfile $P11LIB
fi

# Setup local openssl CA
mkdir {certs,crl,newcerts}
touch serial index.txt crlnumber index.txt.attr
echo 01 >serial
openssl genrsa -out rootCA.key 2048

openssl req -batch -config $CONF/ca.cnf -x509 -new -nodes \
  -key rootCA.key -sha256 -days 10000 -set_serial 0 \
  -extensions v3_ca -out $VIRT/rootCA.crt
openssl ca -config $CONF/ca.cnf -gencrl -out crl/root.crl

# Setup user and certs on the card
useradd -m $NAME
echo -e "${USER_PASSWD}\n${USER_PASSWD}" | passwd "${NAME}"

openssl genrsa -out ${NAME}.key 2048
openssl req -new -nodes -key ${NAME}.key -reqexts req_exts -config $CONF/req_${NAME}.cnf -out ${NAME}.csr
openssl ca -config $CONF/ca.cnf -batch -notext -keyfile rootCA.key -in ${NAME}.csr -days 365 -extensions usr_cert -out ${NAME}.crt

pkcs11-tool --module libsofthsm2.so --slot-index 0 -w ${NAME}.key -y privkey --label ${NAME} -p $PIN --set-id 0 -d 0
pkcs11-tool --module libsofthsm2.so --slot-index 0 -w ${NAME}.crt -y cert --label ${NAME} -p $PIN --set-id 0 -d 0
######################################
# Setup SELinux module
######################################
semodule -i $CONF/virtcacard.cil
cp /usr/lib/systemd/system/pcscd.service /etc/systemd/system/
sed -i 's/ --auto-exit//' /etc/systemd/system/pcscd.service
systemctl daemon-reload
systemctl restart pcscd

exit 0
