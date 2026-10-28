#!/usr/bin/env python3
"""Unit tests for EDA interfaces"""

from utils import interface
from common.constants import PLATFORM_SRL, PLATFORM_EOS, PLATFORM_NXOS, PLATFORM_SROS, PLATFORM_CUMULUS

INPUT_INTERFACE_NAME = "dut1-ethernet-1/1"
INPUT_SUBINTERFACE_NAME = "subif0"
INPUT_LAG_NAME = "lag-lagexample"


def test_get_human_readable_speed():
    """Sanity test for function get_human_readable_speed"""
    assert interface.get_human_readable_speed(0) == "N/A"
    assert interface.get_human_readable_speed(100000000000) == "100G"
    assert interface.get_human_readable_speed(10000000000) == "10G"
    assert interface.get_human_readable_speed(1000000000) == "1G"
    assert interface.get_human_readable_speed(1000000) == "1M"
    assert interface.get_human_readable_speed(1000) == "1K"
    assert interface.get_human_readable_speed(100) == "100"


def test_get_normalized_speed():
    """Sanity test for function get_normalized_speed"""
    assert interface.get_normalized_speed("1G", "srl") == 1000000000
    assert interface.get_normalized_speed("10G", "srl") == 10000000000
    assert interface.get_normalized_speed("100G", "srl") == 100000000000
    assert interface.get_normalized_speed("1000", "sros") == 1000000000
    assert interface.get_normalized_speed("10000", "sros") == 10000000000
    assert interface.get_normalized_speed("100000", "sros") == 100000000000
    assert interface.get_normalized_speed("1G", "nxos") == 1000000000
    assert interface.get_normalized_speed("SPEED_10MB", "eos") == 10000000
    assert interface.get_normalized_speed("SPEED_1GB", "eos") == 1000000000


def test__normalize_implicit_mda_a():
    """_normalize_implicit_mda_a strips explicit 'a' MDA-1 slot (SRL only)."""
    # Short (implicit) forms are returned unchanged.
    assert interface._normalize_implicit_mda_a('ethernet-1-1') == 'ethernet-1-1'
    assert interface._normalize_implicit_mda_a('ethernet-2-10') == 'ethernet-2-10'
    assert interface._normalize_implicit_mda_a('ethernet-1-1-1') == 'ethernet-1-1-1'
    assert interface._normalize_implicit_mda_a('ethernet-1-2-1') == 'ethernet-1-2-1'
    # Explicit 'a' is stripped.
    assert interface._normalize_implicit_mda_a('ethernet-1-a-1') == 'ethernet-1-1'
    assert interface._normalize_implicit_mda_a('ethernet-2-a-10') == 'ethernet-2-10'
    assert interface._normalize_implicit_mda_a('ethernet-1-a-1-1') == 'ethernet-1-1-1'
    assert interface._normalize_implicit_mda_a('ethernet-1-a-2-1') == 'ethernet-1-2-1'
    # Other MDA letters are left untouched (future multi-MDA).
    assert interface._normalize_implicit_mda_a('ethernet-1-b-1') == 'ethernet-1-b-1'
    assert interface._normalize_implicit_mda_a('ethernet-2-b-1-1') == 'ethernet-2-b-1-1'
    # SROS xiom form — 'a' is at parts[3], not parts[2]; must not be stripped.
    assert interface._normalize_implicit_mda_a('ethernet-1-1-a-1') == 'ethernet-1-1-a-1'
    # Non-ethernet names pass through.
    assert interface._normalize_implicit_mda_a('lag-10') == 'lag-10'
    assert interface._normalize_implicit_mda_a('system0') == 'system0'


def test_to_srl_interface():
    """Sanity test for function to_srl_interface """
    itf_tuple = interface.to_srl_interface('ethernet-1-1', None)
    assert itf_tuple[0] == 'ethernet-1/1'
    assert itf_tuple[1] == '.interface{.name=="ethernet-1/1"}'
    itf_tuple = interface.to_srl_interface('ethernet-2-10', None)
    assert itf_tuple[0] == 'ethernet-2/10'
    assert itf_tuple[1] == '.interface{.name=="ethernet-2/10"}'
    itf_tuple = interface.to_srl_interface('ethernet-1-1-1', None)
    assert itf_tuple[0] == 'ethernet-1/1/1'
    assert itf_tuple[1] == '.interface{.name=="ethernet-1/1/1"}'
    itf_tuple = interface.to_srl_interface('ethernet-2-2-1', None)
    assert itf_tuple[0] == 'ethernet-2/2/1'
    assert itf_tuple[1] == '.interface{.name=="ethernet-2/2/1"}'
    itf_tuple = interface.to_srl_interface('system0', None)
    assert itf_tuple[0] == 'system0'
    assert itf_tuple[1] == '.interface{.name=="system0"}'
    itf_tuple = interface.to_srl_interface('lag10', None)
    assert itf_tuple[0] == 'lag10'
    assert itf_tuple[1] == '.interface{.name=="lag10"}'
    # Explicit 'a' MDA slot is equivalent to the implicit short form.
    itf_tuple = interface.to_srl_interface('ethernet-1-a-1', None)
    assert itf_tuple[0] == 'ethernet-1/1'
    assert itf_tuple[1] == '.interface{.name=="ethernet-1/1"}'
    itf_tuple = interface.to_srl_interface('ethernet-1-a-1-1', None)
    assert itf_tuple[0] == 'ethernet-1/1/1'
    assert itf_tuple[1] == '.interface{.name=="ethernet-1/1/1"}'
    itf_tuple = interface.to_srl_interface('ethernet-1-a-2-1', None)
    assert itf_tuple[0] == 'ethernet-1/2/1'
    assert itf_tuple[1] == '.interface{.name=="ethernet-1/2/1"}'


def test_to_eos_interface():
    """Sanity test for function to_eos_interface"""
    itf_tuple = interface.to_eos_interface('ethernet-1-1', None)
    assert itf_tuple[0] == 'Ethernet1/1'
    assert itf_tuple[1] == '.interfaces.interface{.name=="Ethernet1/1"}'
    itf_tuple = interface.to_eos_interface('ethernet-2-10', None)
    assert itf_tuple[0] == 'Ethernet2/10'
    assert itf_tuple[1] == '.interfaces.interface{.name=="Ethernet2/10"}'
    itf_tuple = interface.to_eos_interface('lag-5', None)
    assert itf_tuple[0] == 'Port-Channel5'
    itf_tuple = interface.to_eos_interface('ethernet-1', None)
    assert itf_tuple[0] == 'Ethernet1'
    assert itf_tuple[1] == '.interfaces.interface{.name=="Ethernet1"}'
    itf_tuple = interface.to_eos_interface('ethernet-3', None)
    assert itf_tuple[0] == 'Ethernet3'
    itf_tuple = interface.to_eos_interface('ethernet-1/1', None)
    assert itf_tuple[0] == 'Ethernet1/1'
    itf_tuple = interface.to_eos_interface('ethernet-3-1', None)
    assert itf_tuple[0] == 'Ethernet3/1'
    itf_tuple = interface.to_eos_interface('ethernet-3-5', None)
    assert itf_tuple[0] == 'Ethernet3/5'
    itf_tuple = interface.to_eos_interface('ethernet-1-3-1', None)
    assert itf_tuple[0] == 'Ethernet1/3/1'
    itf_tuple = interface.to_eos_interface('ethernet-1-3-5', None)
    assert itf_tuple[0] == 'Ethernet1/3/5'
    assert interface.from_eos_interface('Ethernet1', None) == 'ethernet-1'
    assert interface.from_eos_interface('Ethernet1/1', None) == 'ethernet-1-1'
    assert interface.from_eos_interface('Ethernet1/3/1', None) == 'ethernet-1-3-1'
    assert interface.from_eos_interface('Ethernet1/3/5', None) == 'ethernet-1-3-5'

    # Platform does not change the name: no slot 0 is inserted or dropped.
    for platform in ('veos-4.36.1f', 'DCS-7050CX3-32S', 'CCS-720XP-48ZC2', 'DCS-7808-CH', 'EOS'):
        node_cr = {'spec': {'platform': platform}}
        assert interface.from_eos_interface('Ethernet1', node_cr) == 'ethernet-1'
        assert interface.from_eos_interface('Ethernet1/1', node_cr) == 'ethernet-1-1'
        assert interface.from_eos_interface('Ethernet3/1/1', node_cr) == 'ethernet-3-1-1'
        assert interface.to_eos_interface('ethernet-1', node_cr)[0] == 'Ethernet1'
        assert interface.to_eos_interface('ethernet-1-1', node_cr)[0] == 'Ethernet1/1'
        assert interface.to_eos_interface('ethernet-3-1-1', node_cr)[0] == 'Ethernet3/1/1'


def test_to_nxos_interface():
    """Sanity test for function to_nxos_interface"""
    itf_tuple = interface.to_nxos_interface('ethernet-1-1', None)
    assert itf_tuple[0] == 'eth1/1'
    assert itf_tuple[1] == '.System.intf-items.phys-items.PhysIf-list{.id=="eth1/1"}'
    itf_tuple = interface.to_nxos_interface('ethernet-2-10', None)
    assert itf_tuple[0] == 'eth2/10'
    assert itf_tuple[1] == '.System.intf-items.phys-items.PhysIf-list{.id=="eth2/10"}'
    itf_tuple = interface.to_nxos_interface('lag-5', None)
    assert itf_tuple[0] == 'po5'


def test_to_iosxr_interface():
    """Sanity test for function to_iosxr_interface """
    itf_tuple = interface.to_iosxr_interface('ethernet-1-1', None)
    assert itf_tuple[0] == 'GigabitEthernet0/0/0/0'
    assert itf_tuple[1] == '.interfaces.interface{.name=="GigabitEthernet0/0/0/0"}'
    itf_tuple = interface.to_iosxr_interface('ethernet-2-10', None)
    assert itf_tuple[0] == 'GigabitEthernet0/1/0/9'
    assert itf_tuple[1] == '.interfaces.interface{.name=="GigabitEthernet0/1/0/9"}'
    itf_tuple = interface.to_iosxr_interface('system0', None)
    assert itf_tuple[0] == 'Loopback0'
    assert itf_tuple[1] == '.interfaces.interface{.name=="Loopback0"}'


def test_to_sros_interface():
    """Sanity test for function to_sros_interface """
    itf_tuple = interface.to_sros_interface('ethernet-1-1', None)
    assert itf_tuple[0] == '1/1/1'
    assert itf_tuple[1] == '.configure.port{.port-id=="1/1/1"}'

    itf_tuple = interface.to_sros_interface('ethernet-2-10', None)
    assert itf_tuple[0] == '2/1/10'
    assert itf_tuple[1] == '.configure.port{.port-id=="2/1/10"}'

    itf_tuple = interface.to_sros_interface('ethernet-2-b-10', None)
    assert itf_tuple[0] == '2/2/10'
    assert itf_tuple[1] == '.configure.port{.port-id=="2/2/10"}'

    itf_tuple = interface.to_sros_interface('ethernet-1-1-1', None)
    assert itf_tuple[0] == '1/1/c1/1'
    assert itf_tuple[1] == '.configure.port{.port-id=="1/1/c1/1"}'

    itf_tuple = interface.to_sros_interface('ethernet-1-4-1', None)
    assert itf_tuple[0] == '1/1/c4/1'
    assert itf_tuple[1] == '.configure.port{.port-id=="1/1/c4/1"}'

    itf_tuple = interface.to_sros_interface('ethernet-2-2-1', None)
    assert itf_tuple[0] == '2/1/c2/1'
    assert itf_tuple[1] == '.configure.port{.port-id=="2/1/c2/1"}'

    itf_tuple = interface.to_sros_interface('ethernet-2-b-1-1', None)
    assert itf_tuple[0] == '2/2/c1/1'
    assert itf_tuple[1] == '.configure.port{.port-id=="2/2/c1/1"}'

    itf_tuple = interface.to_sros_interface('lag-10', None)
    assert itf_tuple[0] == 'lag-10'
    assert itf_tuple[1] == '.configure.lag{.lag-name=="lag-10"}'

    itf_tuple = interface.to_sros_interface('system0', None)
    assert itf_tuple[0] == 'system'
    assert itf_tuple[1] == '.configure.router{.router-name=="Base"}.interface{.interface-name=="system"}'

    itf_tuple = interface.to_sros_interface('ethernet-1-1-a-1', None)
    assert itf_tuple[0] == '1/x1/1/1'

    itf_tuple = interface.to_sros_interface('ethernet-2-2-b-10', None)
    assert itf_tuple[0] == '2/x2/2/10'

    itf_tuple = interface.to_sros_interface('ethernet-1-1-b-2-8', None)
    assert itf_tuple[0] == '1/x1/2/c2/8'

    itf_tuple = interface.to_sros_interface('ethernet-2-2-a-3-8', None)
    assert itf_tuple[0] == '2/x2/1/c3/8'


def test_to_cumulus_interface():
    """Sanity test for function to_cumulus_interface"""
    itf_tuple = interface.to_cumulus_interface('ethernet-1-1', None)
    assert itf_tuple[0] == 'swp1'
    assert itf_tuple[1] == '.interface{.interface-id=="swp1"}'
    itf_tuple = interface.to_cumulus_interface('ethernet-1-2', None)
    assert itf_tuple[0] == 'swp2'
    assert itf_tuple[1] == '.interface{.interface-id=="swp2"}'
    itf_tuple = interface.to_cumulus_interface('ethernet-1-10', None)
    assert itf_tuple[0] == 'swp10'
    itf_tuple = interface.to_cumulus_interface('lag-5', None)
    assert itf_tuple[0] == 'lag5'
    assert itf_tuple[1] == '.interface{.interface-id=="lag5"}'
    itf_tuple = interface.to_cumulus_interface('system0', None)
    assert itf_tuple[0] == 'lo'
    assert itf_tuple[1] == '.interface{.interface-id=="lo"}'
    itf_tuple = interface.to_cumulus_interface('loopback-1', None, isLoopback=True)
    assert itf_tuple[0] == 'lo1'
    assert itf_tuple[1] == '.interface{.interface-id=="lo1"}'
    # Breakout sub-ports: EDA channel index matches Cumulus 0-based sN suffix.
    itf_tuple = interface.to_cumulus_interface('ethernet-1-3-0', None)
    assert itf_tuple[0] == 'swp3s0'
    assert itf_tuple[1] == '.interface{.interface-id=="swp3s0"}'
    itf_tuple = interface.to_cumulus_interface('ethernet-1-3-1', None)
    assert itf_tuple[0] == 'swp3s1'
    assert itf_tuple[1] == '.interface{.interface-id=="swp3s1"}'
    itf_tuple = interface.to_cumulus_interface('ethernet-1-47-3', None)
    assert itf_tuple[0] == 'swp47s3'
    assert itf_tuple[1] == '.interface{.interface-id=="swp47s3"}'


def test_cumulus_interface_type_cfg():
    """Sanity test for function cumulus_interface_type_cfg (mirrors NVUE interface type derivation)"""
    assert interface.cumulus_interface_type_cfg('swp1') == {'type': 'swp'}
    assert interface.cumulus_interface_type_cfg('swp3s1') == {'type': 'swp'}
    assert interface.cumulus_interface_type_cfg('swp1.100') == {'type': 'sub', 'base-interface': 'swp1', 'vlan': 100}
    assert interface.cumulus_interface_type_cfg('eth0') == {'type': 'eth'}
    assert interface.cumulus_interface_type_cfg('bond1') == {'type': 'bond'}
    assert interface.cumulus_interface_type_cfg('lo') == {'type': 'loopback'}
    assert interface.cumulus_interface_type_cfg('vlan10') == {'type': 'svi', 'vlan': 10}
    assert interface.cumulus_interface_type_cfg('peerlink') == {'type': 'peerlink'}
    assert interface.cumulus_interface_type_cfg('tunnel1') == {'type': 'tunnel'}
    assert interface.cumulus_interface_type_cfg('lag5') == {}


def test_from_cumulus_interface():
    """Sanity test for function from_cumulus_interface"""
    assert interface.from_cumulus_interface('swp1', None) == 'ethernet-1-1'
    assert interface.from_cumulus_interface('swp2', None) == 'ethernet-1-2'
    assert interface.from_cumulus_interface('swp10', None) == 'ethernet-1-10'
    # Breakout sub-ports: Cumulus 0-based sN suffix is kept as-is in EDA form.
    assert interface.from_cumulus_interface('swp3s0', None) == 'ethernet-1-3-0'
    assert interface.from_cumulus_interface('swp3s1', None) == 'ethernet-1-3-1'
    assert interface.from_cumulus_interface('swp47s3', None) == 'ethernet-1-47-3'
    assert interface.from_cumulus_interface('lag5', None) == 'lag-5'
    assert interface.from_cumulus_interface('bond5', None) == 'lag-5'
    assert interface.from_cumulus_interface('lo', None) == 'system0'
    assert interface.from_cumulus_interface('lo1', None) == 'loopback-1'
    assert interface.from_cumulus_interface('lo2', None) == 'loopback-2'
    # Unrecognized names pass through unchanged.
    assert interface.from_cumulus_interface('mgmt0', None) == 'mgmt0'


def test_get_lag_name():
    """Sanity test for function get_lag_name """
    assert interface.get_lag_name(20, PLATFORM_SRL) == "lag20"
    assert interface.get_lag_name(20, PLATFORM_SROS) == "lag-20"
    assert interface.get_lag_name(20, PLATFORM_EOS) == "Port-Channel20"
    assert interface.get_lag_name(20, PLATFORM_NXOS) == "po20"
    assert interface.get_lag_name(20, PLATFORM_CUMULUS) == "lag20"


def test_eda_interface_aliases():
    """eda_interface_aliases returns both short and long MDA-1 forms for SROS.

    SROS MDA slot 1 ('a') is implicit: ethernet-{lc}-{port} and
    ethernet-{lc}-a-{port} denote the same physical port.  The same applies
    to breakout connectors: ethernet-{lc}-{br}-{port} ↔
    ethernet-{lc}-a-{br}-{port}.  Non-MDA-1 and xiom patterns must return
    a singleton (no alias).
    """
    # Non-breakout MDA-1: short form ↔ long form
    assert interface.eda_interface_aliases('ethernet-1-1') == frozenset({'ethernet-1-1', 'ethernet-1-a-1'})
    assert interface.eda_interface_aliases('ethernet-1-a-1') == frozenset({'ethernet-1-1', 'ethernet-1-a-1'})
    assert interface.eda_interface_aliases('ethernet-2-10') == frozenset({'ethernet-2-10', 'ethernet-2-a-10'})
    assert interface.eda_interface_aliases('ethernet-2-a-10') == frozenset({'ethernet-2-10', 'ethernet-2-a-10'})

    # Breakout MDA-1: short form ↔ long form (DTS-512658 case)
    assert interface.eda_interface_aliases('ethernet-1-1-1') == frozenset({'ethernet-1-1-1', 'ethernet-1-a-1-1'})
    assert interface.eda_interface_aliases('ethernet-1-a-1-1') == frozenset({'ethernet-1-1-1', 'ethernet-1-a-1-1'})
    assert interface.eda_interface_aliases('ethernet-2-2-1') == frozenset({'ethernet-2-2-1', 'ethernet-2-a-2-1'})
    assert interface.eda_interface_aliases('ethernet-2-a-2-1') == frozenset({'ethernet-2-2-1', 'ethernet-2-a-2-1'})

    # MDA letter other than 'a' — no alias
    assert interface.eda_interface_aliases('ethernet-1-b-1') == frozenset({'ethernet-1-b-1'})
    assert interface.eda_interface_aliases('ethernet-2-b-1-1') == frozenset({'ethernet-2-b-1-1'})

    # Xiom form (digit at parts[2], letter at parts[3]) — no alias
    assert interface.eda_interface_aliases('ethernet-1-1-a-1') == frozenset({'ethernet-1-1-a-1'})
    assert interface.eda_interface_aliases('ethernet-1-1-b-2-8') == frozenset({'ethernet-1-1-b-2-8'})

    # Non-ethernet names — singleton pass-through
    assert interface.eda_interface_aliases('lag-10') == frozenset({'lag-10'})
    assert interface.eda_interface_aliases('system') == frozenset({'system'})


def test_eda_interfaces_equivalent():
    """MDA-1 alias spellings name the same port; other names do not.

    Both directions of the short/long pair (including the breakout pair
    ethernet-1-10-2 / ethernet-1-a-10-2) must match. A different port
    (ethernet-1-a-1 vs ethernet-1-2) must not. Non-ethernet names (lag-10)
    are equivalent only to themselves.
    """
    assert interface.eda_interfaces_equivalent('ethernet-1-1', 'ethernet-1-a-1')
    assert interface.eda_interfaces_equivalent('ethernet-1-a-1', 'ethernet-1-1')
    assert interface.eda_interfaces_equivalent('ethernet-1-10-2', 'ethernet-1-a-10-2')
    assert interface.eda_interfaces_equivalent('ethernet-1-a-10-2', 'ethernet-1-10-2')
    assert not interface.eda_interfaces_equivalent('ethernet-1-a-1', 'ethernet-1-2')
    assert interface.eda_interfaces_equivalent('lag-10', 'lag-10')
    assert not interface.eda_interfaces_equivalent('lag-10', 'ethernet-1-1')


def test_esi_name_short_unchanged():
    """Names within the 32-byte limit are returned unchanged."""
    assert interface.esi_name('') == ''
    assert interface.esi_name('short') == 'short'
    assert interface.esi_name('a' * 32) == 'a' * 32
    assert interface.esi_name('lag-dc1-compute-eslag-1-local') == 'lag-dc1-compute-eslag-1-local'


def test_esi_name_long_fits_32():
    """Names exceeding 32 bytes are shortened to exactly 32 bytes."""
    long_name = 'lag-dc1-1-1-profile3-lag-1-eslag-1-local'  # 40 bytes
    result = interface.esi_name(long_name)
    assert len(result.encode()) == 32
    assert result == result[:23] + '-' + result[24:]


def test_esi_name_deterministic():
    """The same input always produces the same output."""
    long_name = 'lag-dc1-1-1-profile3-lag-1-eslag-1-local'
    assert interface.esi_name(long_name) == interface.esi_name(long_name)


def test_esi_name_no_collision():
    """Two distinct over-limit names produce distinct shortened names."""
    name_a = 'lag-dc1-1-1-profile3-lag-1-eslag-1-local'
    name_b = 'lag-dc1-1-1-profile3-lag-1-eslag-2-local'
    assert interface.esi_name(name_a) != interface.esi_name(name_b)


def test_esi_name_boundary():
    """32-byte name is unchanged; 33-byte name is shortened."""
    assert interface.esi_name('a' * 32) == 'a' * 32
    result = interface.esi_name('a' * 33)
    assert len(result.encode()) == 32


if __name__ == "__main__":
    test_get_human_readable_speed()
    test_get_normalized_speed()
    test__normalize_implicit_mda_a()
    test_to_srl_interface()
    test_to_eos_interface()
    test_to_nxos_interface()
    test_to_iosxr_interface()
    test_to_sros_interface()
    test_to_cumulus_interface()
    test_cumulus_interface_type_cfg()
    test_from_cumulus_interface()
    test_get_lag_name()
    test_eda_interface_aliases()
    test_eda_interfaces_equivalent()
    test_esi_name_short_unchanged()
    test_esi_name_long_fits_32()
    test_esi_name_deterministic()
    test_esi_name_no_collision()
    test_esi_name_boundary()
