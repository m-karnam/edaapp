#!/usr/bin/env python3
import binascii
import hashlib

from common.constants import PLATFORM_SRL, PLATFORM_SROS, PLATFORM_IOSXR, TAG_OS, PLATFORM_NXOS, PLATFORM_EOS, PLATFORM_JUNOS, PLATFORM_CUMULUS, TAG_PLATFORM

# Given a long subinterface name, return a interface name and subinterface index
# Ex:
#   input => "ethernet-1/1.0", output => "ethernet-1/1", "0"


# SR Linux speeds:
#   1G, 10G, 25G, 40G, 50G, 100G, 200G, 400G
#
# SROS speeds:
#   1000, 10000, 25000, 40000, 50000, 100000, 200000, 400000
# EOS speeds
# SPEED_10MB, SPEED_1GB, SPEED_2500MB
def get_normalized_speed(speed: str, os: str) -> int:
    if os == PLATFORM_SRL or os == PLATFORM_NXOS or os == PLATFORM_CUMULUS:
        if 'G' in speed:
            return int(speed.replace('G', '000000000'))
        else:
            return int(speed)
    elif os == PLATFORM_EOS:
        parts = speed.split('_')
        if len(parts) >= 2 and parts[0] == "SPEED":
            value_str = parts[1][:-2]
            unit = parts[1][-2:].upper()
            value = float(value_str)
            if unit == "KB":
                return int(value * 1000)
            elif unit == "MB":
                return int(value * 1000000)
            else:
                return int(value * 1000000000)
        else:
            return 0
    elif os == PLATFORM_SROS:
        return int(speed) * 1000000
        # if isinstance(speed, (int, float)):
        #     speed_str = str(speed) + '000000'
        #     return int(speed_str)
        # else:
        #     return speed
    elif os == PLATFORM_JUNOS:
        # Junos ethernet state identities: speed-100gb, speed-10gb, speed-1gb, speed-2500mb, …
        # OpenConfig port-speed identities: SPEED_100GB, SPEED_400GB, …
        # Junos config identities (set via intent): 100g, 10g, 1g, 25g, 400g, …
        s = speed.split(':')[-1] if speed else ''
        if s.startswith('speed-'):
            s = s[len('speed-'):]
        elif s.startswith('SPEED_'):
            s = s[len('SPEED_'):].lower()
        if s.endswith('gb'):
            return int(float(s[:-2]) * 1000000000)
        if s.endswith('mb'):
            return int(float(s[:-2]) * 1000000)
        if s.endswith('g'):
            return int(float(s[:-1]) * 1000000000)
        if s.endswith('m'):
            return int(float(s[:-1]) * 1000000)
        return 0


def get_human_readable_speed(normalized_speed: int) -> str:
    if normalized_speed == 0:
        return 'N/A'
    if normalized_speed >= 1000000000:
        return f'{normalized_speed // 1000000000}G'
    elif normalized_speed >= 1000000:
        return f'{normalized_speed // 1000000}M'
    elif normalized_speed >= 1000:
        return f'{normalized_speed // 1000}K'
    else:
        return f'{normalized_speed}'


# returns device lag name from lagid
def get_lag_name(lagid, node_os):
    if node_os == PLATFORM_SROS:
        return f'lag-{lagid}'
    elif node_os == PLATFORM_EOS:
        return f'Port-Channel{lagid}'
    elif node_os == PLATFORM_NXOS:
        return f'po{lagid}'
    elif node_os == PLATFORM_CUMULUS:
        return f'lag{lagid}'
    return f'lag{lagid}'  # SRL


def get_node_interface_info(norm_intf_name, node_cr, isLoopback=False):
    node_os = node_cr['spec'].get(TAG_OS)
    if node_os == PLATFORM_SROS:
        return to_sros_interface(norm_intf_name, node_cr, isLoopback=isLoopback)
    elif node_os == PLATFORM_IOSXR:
        return to_iosxr_interface(norm_intf_name, node_cr, isLoopback=isLoopback)
    elif node_os == PLATFORM_NXOS:
        return to_nxos_interface(norm_intf_name, node_cr, isLoopback=isLoopback)
    elif node_os == PLATFORM_EOS:
        return to_eos_interface(norm_intf_name, node_cr, isLoopback=isLoopback)
    elif node_os == PLATFORM_JUNOS:
        return to_junos_interface(norm_intf_name, node_cr, isLoopback=isLoopback)
    elif node_os == PLATFORM_CUMULUS:
        return to_cumulus_interface(norm_intf_name, node_cr, isLoopback=isLoopback)
    return to_srl_interface(norm_intf_name, node_cr, isLoopback=isLoopback)


def eda_interface_aliases(eda_name: str) -> frozenset:
    """Return all EDA-normalized names equivalent to eda_name.

    Currently handles the SROS MDA-slot-1 implicit/explicit 'a' convention:
    SROS designates the first MDA slot as 'a' (ordinal 1).  For non-xiom
    ports on MDA 1, the letter 'a' may be written explicitly or omitted:

      ethernet-{lc}-{port}               (short, MDA 1 implicit)
      ethernet-{lc}-a-{port}             (long, MDA 1 explicit)
      ethernet-{lc}-{connector}-{port}   (short breakout, MDA 1 implicit)
      ethernet-{lc}-a-{connector}-{port} (long breakout, MDA 1 explicit)

    Both forms in each pair resolve to the same SROS port string.  Xiom
    ports (digit then letter at parts[3]), ports on MDA slots other than
    'a', and all non-ethernet names are returned as a singleton frozenset.

    Safe to call on any EDA-normalized interface name regardless of platform;
    non-SROS patterns simply return a singleton.
    """
    parts = eda_name.split('-')
    if parts[0] != 'ethernet' or len(parts) < 3:
        return frozenset([eda_name])
    lc = parts[1]
    rest = parts[2:]  # segments after ethernet-{lc}
    # Short form: no MDA letter — rest[0] is a digit.
    # Valid non-xiom short forms have length 1 (port) or 2 (connector + port).
    if rest[0].isdigit():
        if len(rest) == 1 or (len(rest) == 2 and rest[1].isdigit()):
            alias = f'ethernet-{lc}-a-{"-".join(rest)}'
            return frozenset([eda_name, alias])
    # Long form: explicit 'a' followed by a digit — rest[0]=='a', rest[1] digit.
    # Valid explicit-MDA-1 forms have length 2 (a + port) or 3 (a + connector + port).
    if rest[0] == 'a' and len(rest) >= 2 and rest[1].isdigit():
        if len(rest) == 2 or (len(rest) == 3 and rest[2].isdigit()):
            alias = f'ethernet-{lc}-{"-".join(rest[1:])}'
            return frozenset([eda_name, alias])
    return frozenset([eda_name])


def eda_interfaces_equivalent(a: str, b: str) -> bool:
    """True iff two normalized interface names name the same port.

    MDA-1 alias spellings (``ethernet-1-1`` / ``ethernet-1-a-1`` and the
    corresponding breakout pair) are equivalent. Non-ethernet names are
    equivalent only to themselves. String-only; callers must not pass None.
    """
    return b in eda_interface_aliases(a)


# Inverse of get_node_interface_info: convert a platform-specific node interface
# name (e.g. "ethernet-1/1", "1/x1/2/c1/1", "Port-Channel10") back into the
# normalized form (e.g. "ethernet-1-1", "ethernet-1-1-b-1-1", "lag-10").
# System (system0/system/lo0/Loopback0) and loopback (loN/LoopbackN) inputs are
# returned unchanged so callers can detect and skip them.
def get_normalized_interface_name(node_intf_name: str, node_cr) -> str:
    node_os = node_cr['spec'].get(TAG_OS)
    if node_os == PLATFORM_SROS:
        return from_sros_interface(node_intf_name, node_cr)
    elif node_os == PLATFORM_IOSXR:
        return from_iosxr_interface(node_intf_name, node_cr)
    elif node_os == PLATFORM_NXOS:
        return from_nxos_interface(node_intf_name, node_cr)
    elif node_os == PLATFORM_EOS:
        return from_eos_interface(node_intf_name, node_cr)
    elif node_os == PLATFORM_JUNOS:
        return from_junos_interface(node_intf_name, node_cr)
    elif node_os == PLATFORM_CUMULUS:
        return from_cumulus_interface(node_intf_name, node_cr)
    return from_srl_interface(node_intf_name, node_cr)


def _normalize_implicit_mda_a(norm_intf_name: str) -> str:
    """Strip the explicit MDA-1 slot letter 'a' from an EDA-normalized ethernet name.

    SRL only: the first MDA slot is implicit, so ethernet-{lc}-a-{port} is
    identical to ethernet-{lc}-{port} and ethernet-{lc}-a-{connector}-{port}
    to ethernet-{lc}-{connector}-{port}.

    SROS handles the 'a' MDA letter natively in to_sros_interface and must NOT
    use this helper. Other platforms have no MDA and must not use it either.
    """
    parts = norm_intf_name.split('-')
    if (len(parts) >= 4 and parts[0] == 'ethernet'
            and parts[2] == 'a' and parts[3].isdigit()):
        return f'ethernet-{parts[1]}-{"-".join(parts[3:])}'
    return norm_intf_name


# Normalized interface name to SRL interface names:
# ethernet-1-1 => ethernet-1/1 for single mda and ethernet-1/a/1 for multi mda (future)
# ethernet-2-1 => ethernet-2/1 for single mda ethernet-2/a/1 for multi mda (future)
# ethernet-2-b-1 =>  ethernet-2/b/1 for multi mda (future)
# ethernet-1-1-1 (breakout) => ethernet-1/1/1 for single mda, ethernet-1/a/1/1 for multi mda (future)
# ethernet-2-b-1-1 (breakout) = > ethernet-2/b/1/1 for multi mda (future)
def to_srl_interface(norm_intf_name: str, node_cr, isLoopback=False):
    norm_intf_name = _normalize_implicit_mda_a(norm_intf_name)
    parts = norm_intf_name.split('-', 1)
    srl_name = parts[0]
    spec = (node_cr or {}).get('spec') or {}
    platform_type = spec.get(TAG_PLATFORM)
    if platform_type and platform_type.lower() == "vsrl":
        srl_name = f'lif-e{parts[1]}'
        return srl_name, f'.interface{{.name=="{srl_name}"}}', f'.interface{{.name=="{srl_name}"}}'

    if len(parts) > 1:
        if 'lag' in norm_intf_name:
            srl_name = f'lag{parts[1]}'
        else:
            # current SRL linecards does not support multiple MDAs,
            srl_name = f"{parts[0]}-{parts[1].replace('-', '/')}"
        # add logic based on SRL platform when linecard will support multiple MDAs(future)
    if isLoopback is True:
        if parts[0] == 'loopback' and parts[1].isdigit():
            srl_name = f'lo{parts[1]}'

    return srl_name, f'.interface{{.name=="{srl_name}"}}', f'.interface{{.name=="{srl_name}"}}'


# Inverse of to_srl_interface. Recognizes:
#   ethernet-X/Y[/...]     -> ethernet-X-Y[-...]
#   lif-eX-Y[-...] (vsrl)  -> ethernet-X-Y[-...]
#   lagN (SRL device form) -> lag-N  (EDA normalized form)
# Anything else (system0, loN, unrecognized shapes) is returned unchanged.
def from_srl_interface(node_intf_name: str, node_cr) -> str:
    spec = (node_cr or {}).get('spec') or {}
    platform_type = spec.get(TAG_PLATFORM)
    if platform_type and platform_type.lower() == "vsrl" and node_intf_name.startswith('lif-e'):
        return f'ethernet-{node_intf_name[len("lif-e"):]}'
    if node_intf_name.startswith('ethernet-') and '/' in node_intf_name:
        return node_intf_name.replace('/', '-')
    if node_intf_name.startswith('lag') and node_intf_name[3:].isdigit():
        return f'lag-{node_intf_name[3:]}'
    return node_intf_name


def _eos_name_from_eda(norm_intf_name: str) -> str | None:
    """ethernet-1 → Ethernet1, ethernet-1-1 → Ethernet1/1, ethernet-1-1-1 → Ethernet1/1/1."""
    parts = norm_intf_name.split('-')
    if len(parts) < 2 or parts[0] != 'ethernet' or not all(part.isdigit() for part in parts[1:]):
        return None
    return 'Ethernet' + '/'.join(parts[1:])


def to_eos_interface(norm_intf_name: str, node_cr, isLoopback=False):
    eos_name = _eos_name_from_eda(norm_intf_name)
    if eos_name is None:
        parts = norm_intf_name.split('-')
        eos_name = parts[0]
        if len(parts) > 1:
            if 'lag' in norm_intf_name:
                eos_name = f'Port-Channel{parts[1]}'
            elif len(parts) == 2 and parts[0] == 'ethernet' and '/' in parts[1]:
                eos_name = f'Ethernet{parts[1]}'
    if isLoopback is True:
        parts = norm_intf_name.split('-')
        if parts[0] == 'loopback' and parts[1].isdigit():
            eos_name = f'Loopback{parts[1]}'

    return eos_name, f'.interfaces.interface{{.name=="{eos_name}"}}', f'.interfaces.interface{{.name=="{eos_name}"}}'


# Inverse of to_eos_interface, the same for every platform:
#   EthernetN / EthernetX/Y / EthernetX/Y/Z -> ethernet-N / ethernet-X-Y / ethernet-X-Y-Z
# Port-ChannelN -> lag-N. Anything else is returned unchanged.
def from_eos_interface(node_intf_name: str, node_cr) -> str:
    if node_intf_name.startswith('Ethernet'):
        rest = node_intf_name[len('Ethernet'):]
        if '/' in rest:
            return f'ethernet-{rest.replace("/", "-")}'
        if rest.isdigit():
            return f'ethernet-{rest}'
    if node_intf_name.startswith('Port-Channel'):
        n = node_intf_name[len('Port-Channel'):]
        if n.isdigit():
            return f'lag-{n}'
    return node_intf_name


# Normalized interface name to SROS interface names:
# ethernet-1-1 => 1/1/1
# ethernet-2-1 => 2/1/1
# ethernet-2-b-1 => 2/2/1
# ethernet-1-1-1 (breakout) => 1/1/c1/1 based on platform or card type
# ethernet-2-b-1-1 (breakout) = > 2/2/c1/1 based on platform or card type
# ethernet-1-1-a-1 => 1/x1/1/1
# ethernet-1-1-b-1-1 => 1/x1/2/c1/1 breakout
def to_sros_interface(norm_intf_name: str, node_cr, isLoopback=False):
    parts = norm_intf_name.split('-')
    sros_name = norm_intf_name
    config_path = ''
    state_path = ''
    is_xiom_mda = False
    mda_id = '1'
    linecard_id = '1'
    xiom_id = None
    port_id = ''

    if 'lag' in norm_intf_name:
        config_path = f'.configure.lag{{.lag-name=="{sros_name}"}}'
        state_path = f'.state.lag{{.lag-name=="{sros_name}"}}'
    elif parts[0] == 'system0':
        sros_name = 'system'
        config_path = f'.configure.router{{.router-name=="Base"}}.interface{{.interface-name=="{sros_name}"}}'
        state_path = f'.state.router{{.router-name=="Base"}}.interface{{.interface-name=="{sros_name}"}}'
    elif isLoopback is True:
        if parts[0] == 'loopback' and parts[1].isdigit():
            sros_name = f'lo{parts[1]}'
    elif parts[0] == 'esat':
        # satellite port
        sat_parts = norm_intf_name.split('-', 2)  # ['esat', '1', '1-c65-u1']
        sros_name = to_sros_satellite_port_name(sat_id=sat_parts[1], port_id=sat_parts[2])
        config_path = f'.configure.port{{.port-id=="{sros_name}"}}'
        state_path = f'.state.port{{.port-id=="{sros_name}"}}'
    else:
        if len(parts) > 4 and parts[3].isalpha():
            # ethernet-1-1-a-1 => 1/x1/1/1
            # ethernet-1-1-b-1-1 => 1/x1/2/c1/1 breakout
            is_xiom_mda = True
            mda_id = ord(parts[3].upper()) - 64
            linecard_id = parts[1]
            xiom_id = f'x{parts[2]}'
            if len(parts) == 5:
                port_id = parts[4]
            else:
                port_id = f'c{parts[4]}/{parts[5]}'
        elif len(parts) > 2:
            linecard_id = parts[1]
            # ethernet-2-b-1 => 2/2/1
            # ethernet-2-b-1-1 => 2/2/c1/1 breakout
            if parts[2].isalpha():
                mda_id = ord(parts[2].upper()) - 64
                if len(parts) == 4:
                    port_id = parts[3]
                elif len(parts) == 5:
                    port_id = f'c{parts[3]}/{parts[4]}'
            else:
                # ethernet-1-1-1  => 1/1/c1/1 breakout
                # ethernet-1-1 => 1/1/1
                # mda_id = 1 # already initialised.
                if len(parts) == 3:
                    port_id = parts[2]
                elif len(parts) == 4:
                    port_id = f'c{parts[2]}/{parts[3]}'
        # construct sros name.
        if len(port_id) != 0:
            if is_xiom_mda is True:
                sros_name = f'{linecard_id}/{xiom_id}/{mda_id}/{port_id}'
            else:
                sros_name = f'{linecard_id}/{mda_id}/{port_id}'

        config_path = f'.configure.port{{.port-id=="{sros_name}"}}'
        state_path = f'.state.port{{.port-id=="{sros_name}"}}'

    return sros_name, config_path, state_path


def to_sros_satellite_port_name(sat_id, port_id: str):
    # sat_id 1, port-id 1-1 => esat-1/1/1
    # sat_id 1, port-id 1-c65-u1 => esat-1/1/c65/u1
    # sat_id 1, port-id 1-1-u1 => esat-1/1/1/u1
    return f'esat-{sat_id}/{port_id.replace('-', '/')}'


# Inverse of to_sros_interface. Recognizes:
#   lag-N                   -> lag-N
#   esat-S/REST             -> esat-S-{REST with '/' replaced by '-'}
#   LC/MDA/PORT             -> ethernet-LC-PORT          (MDA == 1)
#                              ethernet-LC-{letter(MDA)}-PORT
#   LC/MDA/cBR/PORT         -> ethernet-LC-BR-PORT       (MDA == 1)
#                              ethernet-LC-{letter(MDA)}-BR-PORT
#   LC/xX/MDA/PORT          -> ethernet-LC-X-{letter(MDA)}-PORT
#   LC/xX/MDA/cBR/PORT      -> ethernet-LC-X-{letter(MDA)}-BR-PORT
# Anything else (system, loN, unrecognized shapes) is returned unchanged.
def from_sros_interface(node_intf_name: str, node_cr) -> str:
    if node_intf_name.startswith('lag-'):
        return node_intf_name
    if node_intf_name.startswith('esat-'):
        head, sep, rest = node_intf_name.partition('/')
        if sep:
            return f"{head}-{rest.replace('/', '-')}"
        return node_intf_name
    if '/' not in node_intf_name:
        return node_intf_name

    parts = node_intf_name.split('/')
    if not parts[0].isdigit():
        return node_intf_name
    lc = parts[0]

    if len(parts) >= 4 and parts[1].startswith('x') and parts[1][1:].isdigit():
        xiom = parts[1][1:]
        if not parts[2].isdigit():
            return node_intf_name
        mda_letter = chr(ord('a') + int(parts[2]) - 1)
        if len(parts) == 4:
            return f'ethernet-{lc}-{xiom}-{mda_letter}-{parts[3]}'
        if len(parts) == 5 and parts[3].startswith('c') and parts[3][1:].isdigit():
            return f'ethernet-{lc}-{xiom}-{mda_letter}-{parts[3][1:]}-{parts[4]}'
        return node_intf_name

    if not parts[1].isdigit():
        return node_intf_name
    mda = int(parts[1])
    if len(parts) == 3:
        port = parts[2]
        if mda == 1:
            return f'ethernet-{lc}-{port}'
        return f'ethernet-{lc}-{chr(ord("a") + mda - 1)}-{port}'
    if len(parts) == 4 and parts[2].startswith('c') and parts[2][1:].isdigit():
        br = parts[2][1:]
        port = parts[3]
        if mda == 1:
            return f'ethernet-{lc}-{br}-{port}'
        return f'ethernet-{lc}-{chr(ord("a") + mda - 1)}-{br}-{port}'
    return node_intf_name


# Note: Cisco IOS-XR is 0 based
# Note: Need to add function to look at port speed to determine name correctly
# Normalized interface name to IOS-XR interface names:
# ethernet-1-1 => GigabitEthernet0/0/0/0
# ethernet-1-2 => GigabitEthernet0/0/0/1
# ethernet-2-1 => GigabitEthernet0/1/0/0
# ethernet-2-b-1 =>  GigabitEthernet0/1/1/0 for multi mda


def to_iosxr_interface(norm_intf_name: str, node_cr, isLoopback=False):  # pragma: no cover
    parts = norm_intf_name.split('-')
    if parts[0] != 'system0':
        # Subtract 1 from the slot and port number as IOS-XR is 0-based
        slot = int(parts[1]) - 1
        port = int(parts[2]) - 1 if len(parts) > 2 else 0
    iosxr_name = None
    if len(parts) == 3:
        # Format: ethernet-X-Y
        # Maps to: GigabitEthernet0/X/0/Y
        iosxr_name = f"GigabitEthernet0/{slot}/0/{port}"
    elif len(parts) == 4 and parts[2].isalpha():
        # Format: ethernet-X-b-Y (multi MDA)
        # Maps to: GigabitEthernet0/X/1/Y
        iosxr_name = f"GigabitEthernet0/{slot}/1/{port}"
    elif parts[0] == 'system0':
        iosxr_name = 'Loopback0'
    if iosxr_name:
        config_path = f'.interfaces.interface{{.name=="{iosxr_name}"}}'
        return iosxr_name, config_path, config_path
    return None, None, None


# Inverse of to_iosxr_interface. Recognizes:
#   GigabitEthernet0/A/0/C  -> ethernet-{A+1}-{C+1}
#   GigabitEthernet0/A/B/C  -> ethernet-{A+1}-{letter(B+1)}-{C+1}  (B != 0)
# Anything else (Loopback0, unrecognized shapes) is returned unchanged.
def from_iosxr_interface(node_intf_name: str, node_cr) -> str:  # pragma: no cover
    prefix = 'GigabitEthernet0/'
    if not node_intf_name.startswith(prefix):
        return node_intf_name
    parts = node_intf_name[len(prefix):].split('/')
    if len(parts) != 3:
        return node_intf_name
    try:
        slot, mda, port = int(parts[0]), int(parts[1]), int(parts[2])
    except ValueError:
        return node_intf_name
    if mda == 0:
        return f'ethernet-{slot + 1}-{port + 1}'
    return f'ethernet-{slot + 1}-{chr(ord("a") + mda)}-{port + 1}'


def to_nxos_interface(norm_intf_name: str, node_cr, isLoopback=False):  # pragma: no cover
    parts = norm_intf_name.split('-')
    nxos_name = parts[0]
    if len(parts) > 1:
        if len(parts) == 3:
            nxos_name = f"eth{parts[1]}/{parts[2]}"
            _path = f'.System.intf-items.phys-items.PhysIf-list{{.id=="{nxos_name}"}}'
            return nxos_name, _path, _path
        elif 'lag' in norm_intf_name:
            nxos_name = f'po{parts[1]}'
            _path = f'.System.intf-items.aggr-items.AggrIf-list{{.id=="{nxos_name}"}}'
            return nxos_name, _path, _path
    elif parts[0] == 'system0':
        nxos_name = 'lo0'
        isLoopback = True

    if isLoopback is True:
        if parts[1].isdigit():
            nxos_name = f'lo{parts[1]}'
        _path = f'.System.intf-items.lb-items.LbRtdIf-list{{.id=="{nxos_name}"}}'
        return nxos_name, _path, _path

    return None, None, None


# Junos physical-interface speed prefix mapping.
#
# EDA normalized prefix  Junos prefix  Speed
# ---------------------  ------------  -----
# ethernet               et            25G / 40G / 50G / 100G / 400G
# gethernet              ge            1G
# xethernet              xe            10G
_JUNOS_PREFIX_FROM_EDA: dict[str, str] = {
    'ethernet': 'et',
    'gethernet': 'ge',
    'xethernet': 'xe',
}
_EDA_PREFIX_FROM_JUNOS: dict[str, str] = {v: k for k, v in _JUNOS_PREFIX_FROM_EDA.items()}


# Normalized interface name to Junos interface names.
#
# Junos port names have the form  {type}-{FPC}/{PIC}/{Port}  where:
#   FPC  = Flexible PIC Concentrator slot (0 for fixed chassis)
#   PIC  = Physical Interface Card slot   (0 for onboard; 0-based)
#   Port = Physical port number           (0-based)
#
# EDA normalized form uses numeric PIC (0-based):
#   ethernet-0-0-0  ->  et-0/0/0
#   ethernet-0-1-0  ->  et-0/1/0
#   gethernet-0-0-0 ->  ge-0/0/0
#   xethernet-0-0-0 ->  xe-0/0/0
#   lag-1           ->  ae1
#   loopback-0      ->  lo0
def to_junos_interface(norm_intf_name: str, node_cr, isLoopback=False):
    parts = norm_intf_name.split('-')

    if parts[0] == 'lag' and len(parts) == 2 and parts[1].isdigit():
        junos_name = f'ae{parts[1]}'
        _path = f'.configuration.interfaces.interface{{.name=="{junos_name}"}}'
        return junos_name, _path, _path

    if isLoopback or parts[0] in ('loopback', 'system0'):
        if parts[0] == 'system0':
            junos_name = 'lo0'
        elif parts[0] == 'loopback' and len(parts) > 1 and parts[1].isdigit():
            junos_name = f'lo{parts[1]}'
        else:
            junos_name = norm_intf_name
        _path = f'.configuration.interfaces.interface{{.name=="{junos_name}"}}'
        return junos_name, _path, _path

    eda_prefix = parts[0]
    junos_prefix = _JUNOS_PREFIX_FROM_EDA.get(eda_prefix)
    if junos_prefix is None or len(parts) < 4:
        return norm_intf_name, None, None

    fpc, pic, port = parts[1], parts[2], parts[3]
    if not pic.isdigit():
        return norm_intf_name, None, None

    junos_name = f'{junos_prefix}-{fpc}/{pic}/{port}'
    _path = f'.configuration.interfaces.interface{{.name=="{junos_name}"}}'
    return junos_name, _path, _path


# Inverse of to_junos_interface. Recognizes:
#   et-F/P/Port  -> ethernet-F-P-Port   (25G/40G/50G/100G/400G)
#   ge-F/P/Port  -> gethernet-F-P-Port  (1G)
#   xe-F/P/Port  -> xethernet-F-P-Port  (10G)
#   aeN          -> lag-N
# Anything else (lo0, loN, unrecognized shapes) is returned unchanged.
def from_junos_interface(node_intf_name: str, node_cr) -> str:
    if node_intf_name.startswith('ae') and node_intf_name[2:].isdigit():
        return f'lag-{node_intf_name[2:]}'

    dash_idx = node_intf_name.find('-')
    if dash_idx < 0 or '/' not in node_intf_name:
        return node_intf_name

    junos_prefix = node_intf_name[:dash_idx]
    eda_prefix = _EDA_PREFIX_FROM_JUNOS.get(junos_prefix)
    if eda_prefix is None:
        return node_intf_name

    slash_parts = node_intf_name[dash_idx + 1:].split('/')
    if len(slash_parts) != 3:
        return node_intf_name
    fpc, pic, port = slash_parts
    if not pic.isdigit():
        return node_intf_name
    return f'{eda_prefix}-{fpc}-{pic}-{port}'


# Normalized interface name to Cumulus interface names.
#
# Cumulus Linux uses a flat port namespace where physical ports are numbered
# sequentially as swpN regardless of linecard.  The EDA port index (last
# segment of the ethernet-{lc}-{port} name) maps 1:1 to swpN.
#
# Breakout sub-ports use the form swpNsM where M is 0-based (Cumulus). The EDA
# normalized sub-port index matches that suffix (topology allows channel index 0):
#
#   ethernet-1-1      ->  swp1
#   ethernet-1-2      ->  swp2
#   ethernet-1-3-0    ->  swp3s0
#   ethernet-1-3-1    ->  swp3s1
#   lag-N             ->  lagN
#   system0           ->  lo
#   loopback-N        ->  loN
def to_cumulus_interface(norm_intf_name: str, node_cr, isLoopback=False):
    parts = norm_intf_name.split('-')

    if parts[0] == 'lag' and len(parts) == 2 and parts[1].isdigit():
        cumulus_name = f'lag{parts[1]}'
        _path = f'.interface{{.interface-id=="{cumulus_name}"}}'
        return cumulus_name, _path, _path

    if parts[0] == 'system0':
        cumulus_name = 'lo'
        _path = f'.interface{{.interface-id=="{cumulus_name}"}}'
        return cumulus_name, _path, _path

    if isLoopback or parts[0] == 'loopback':
        if len(parts) > 1 and parts[1].isdigit():
            cumulus_name = f'lo{parts[1]}'
        else:
            cumulus_name = norm_intf_name
        _path = f'.interface{{.interface-id=="{cumulus_name}"}}'
        return cumulus_name, _path, _path

    if parts[0] == 'ethernet' and len(parts) == 4 and parts[2].isdigit() and parts[3].isdigit():
        # Breakout sub-port: ethernet-{lc}-{port}-{sub}. Channel index is kept as-is
        # (EDA 0-based matches Cumulus swpNsM).
        cumulus_name = f'swp{parts[2]}s{int(parts[3])}'
        _path = f'.interface{{.interface-id=="{cumulus_name}"}}'
        return cumulus_name, _path, _path

    if parts[0] == 'ethernet' and len(parts) >= 3 and parts[2].isdigit():
        cumulus_name = f'swp{parts[2]}'
        _path = f'.interface{{.interface-id=="{cumulus_name}"}}'
        return cumulus_name, _path, _path

    return norm_intf_name, None, None


# NVUE derives the interface type (and base-interface/vlan for subinterfaces)
# from the interface name when a PATCH omits them. EDA sets them explicitly
# so the device never has to fill them in and running config matches intent:
#
#   swp1.100  ->  type sub, base-interface swp1, vlan 100
#   swpN      ->  type swp          ethN      ->  type eth
#   bondN     ->  type bond         loN / lo  ->  type loopback
#   vlanN     ->  type svi, vlan N  peerlinkN ->  type peerlink
#   tunnelN   ->  type tunnel
def cumulus_interface_type_cfg(cumulus_name: str) -> dict:
    if '.' in cumulus_name:
        base, _, vlan = cumulus_name.rpartition('.')
        cfg = {'type': 'sub', 'base-interface': base}
        if vlan.isdigit():
            cfg['vlan'] = int(vlan)
        return cfg
    if cumulus_name.startswith('vlan'):
        cfg = {'type': 'svi'}
        if cumulus_name[4:].isdigit():
            cfg['vlan'] = int(cumulus_name[4:])
        return cfg
    for prefix, intf_type in (('swp', 'swp'), ('eth', 'eth'), ('bond', 'bond'), ('lo', 'loopback'),
                              ('peerlink', 'peerlink'), ('tunnel', 'tunnel')):
        if cumulus_name.startswith(prefix):
            return {'type': intf_type}
    return {}


# Inverse of to_cumulus_interface. Recognizes:
#   swpNsM  -> ethernet-1-N-M       (breakout sub-port, channel index kept as-is)
#   swpN    -> ethernet-1-N         (Cumulus flat port -> EDA normalized, linecard 1)
#   lagN    -> lag-N
#   bondN   -> lag-N   (legacy Cumulus bond naming)
#   lo      -> system0
#   loN     -> loopback-N   (N > 0)
# Anything else is returned unchanged.
def from_cumulus_interface(node_intf_name: str, node_cr) -> str:
    if node_intf_name.startswith('swp'):
        rest = node_intf_name[3:]
        if 's' in rest:
            port, sub = rest.split('s', 1)
            if port.isdigit() and sub.isdigit():
                return f'ethernet-1-{port}-{int(sub)}'
        elif rest.isdigit():
            return f'ethernet-1-{rest}'
    if node_intf_name.startswith('lag') and node_intf_name[3:].isdigit():
        return f'lag-{node_intf_name[3:]}'
    if node_intf_name.startswith('bond') and node_intf_name[4:].isdigit():
        return f'lag-{node_intf_name[4:]}'
    if node_intf_name == 'lo':
        return 'system0'
    if node_intf_name.startswith('lo') and node_intf_name[2:].isdigit():
        return f'loopback-{node_intf_name[2:]}'
    return node_intf_name


# Inverse of to_nxos_interface. Recognizes:
#   ethX/Y       -> ethernet-X-Y
#   EthernetX/Y  -> ethernet-X-Y   (some NXOS deployments use the long form)
#   poN          -> lag-N
# Anything else (lo0, loN, unrecognized shapes) is returned unchanged.
def from_nxos_interface(node_intf_name: str, node_cr) -> str:  # pragma: no cover
    rest = None
    if node_intf_name.startswith('Ethernet'):
        rest = node_intf_name[len('Ethernet'):]
    elif node_intf_name.startswith('eth'):
        rest = node_intf_name[len('eth'):]
    if rest is not None and '/' in rest:
        parts = rest.split('/')
        if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
            return f'ethernet-{parts[0]}-{parts[1]}'
    if node_intf_name.startswith('po') and node_intf_name[2:].isdigit():
        return f'lag-{node_intf_name[2:]}'
    return node_intf_name


# SR OS and SR Linux enforce a 32-byte maximum on ethernet-segment identifiers.
_MAX_ETH_SEGMENT_NAME = 32


def esi_name(name: str) -> str:
    """Return a ≤32-byte ethernet-segment name derived from a CR name or computed key.

    SR OS and SR Linux enforce a 32-byte maximum on ethernet-segment identifiers
    (/configure/service/system/bgp/evpn/ethernet-segment/ethernet-segment-name on SR OS;
    /system/network-instance/protocols/evpn/ethernet-segments/.../ethernet-segment/name on SR Linux).

    When name fits within the limit it is returned unchanged (backward compatible).
    When name exceeds the limit, returns:
        name[:23] + '-' + sha256(name)[:8]   →  exactly 32 bytes

    hashlib.sha256 is available in the MicroPython config engine runtime. The suffix is
    deterministic — the same input name always produces the same ethernet-segment name
    across intent re-runs, making reconcile idempotent.
    """
    if len(name.encode()) <= _MAX_ETH_SEGMENT_NAME:
        return name
    # hexdigest() is CPython-only; MicroPython requires binascii.hexlify(digest()[:4]).
    # digest()[:4] → 4 raw bytes → hexlify → 8 hex chars, same bits as hexdigest()[:8].
    raw = hashlib.sha256(name.encode()).digest()
    suffix = binascii.hexlify(raw[:4]).decode()  # 8 hex chars
    return name[:23] + '-' + suffix  # 23 + 1 + 8 = 32
