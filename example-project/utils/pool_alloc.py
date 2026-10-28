import eda_config as ecfg
import eda_common as eda
import utils.exceptions as e

# Allocation pool type strings (match protoengine eda_config.Pool; do not use ecfg.Pool.TYPE_* —
# micropython may not expose Pool class attributes during early import).
POOL_TYPE_INDEX = 'Index'
POOL_TYPE_IP = 'IP'
POOL_TYPE_IP_IN_SUBNET = 'IPInSubnet'
POOL_TYPE_SUBNET = 'Subnet'


def get_pool_item(key: str, pool_name: str, pool_scope: str, pool_type: str):
    pool_obj = ecfg.Pool(name=pool_name, scope=pool_scope, type=pool_type)
    try:
        pool_item = pool_obj.alloc(f'{key}')
    except eda.InfrastructureError as ierr:  # pragma: no cover
        raise e.InvalidInput(
            msg=pool_alloc_error_message(
                err_msg=str(ierr), pool_name=pool_name, pool_type=pool_type))  # pragma: no cover
    return pool_item


def pool_alloc_error_message(err_msg: str, pool_name: str, pool_type: str) -> str:
    # keep in sync with fabrics pool_alloc_error_message (apps/fabrics/intents/fabric/common.py)
    if err_msg.endswith(' is exhausted'):
        if pool_type == POOL_TYPE_IP:
            return f'IP allocation pool {pool_name} is exhausted'
        if pool_type == POOL_TYPE_SUBNET:
            return f'subnet allocation pool {pool_name} is exhausted'
        if pool_type == POOL_TYPE_IP_IN_SUBNET:
            return f'IP in subnet allocation pool {pool_name} is exhausted'
        if pool_type == POOL_TYPE_INDEX:
            return f'index allocation pool {pool_name} is exhausted'
        return f'allocation pool {pool_name} is exhausted'
    return err_msg
