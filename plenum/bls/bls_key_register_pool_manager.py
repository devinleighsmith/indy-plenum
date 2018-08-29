from logging import getLogger

from crypto.bls.bls_key_register import BlsKeyRegister
from plenum.common.constants import BLS_KEY, BLS_KEY_PROOF, ALIAS
from plenum.server.pool_manager import TxnPoolManager

logger = getLogger()


class BlsKeyRegisterPoolManager(BlsKeyRegister):
    def __init__(self, pool_manager: TxnPoolManager):
        self._pool_manager = pool_manager
        # since pool state isn't changed very often, we cache keys corresponded
        # to the pool_state to not get them from the state trie each time
        self._current_bls_keys = {}  # {node_name : BLS key}
        self._current_pool_state_root_hash = None

    def get_pool_root_hash_committed(self):
        return self._pool_manager.state.committedHeadHash

    def get_key_by_name(self, node_name, pool_state_root_hash=None):
        if not pool_state_root_hash:
            pool_state_root_hash = self.get_pool_root_hash_committed()

        if self._current_pool_state_root_hash != pool_state_root_hash:
            self._current_pool_state_root_hash = pool_state_root_hash
            self._load_keys_for_root(pool_state_root_hash)
        if not self._pool_manager.config.VALIDATE_SIGN_WITHOUT_BLS_KEY_PROOF and \
                self._current_bls_keys_proof.get(node_name, None) in [False, None]:
            logger.info("{} has no proof of possession for BLS public key.".format(node_name))
            return None
        return self._current_bls_keys.get(node_name)

    def _load_keys_for_root(self, pool_state_root_hash):
        self._current_bls_keys = {}
        self._current_bls_keys_proof = {}
        for data in self._pool_manager.reqHandler.get_all_node_data_for_root_hash(
                pool_state_root_hash):
            if BLS_KEY in data:
                self._current_bls_keys[data[ALIAS]] = data[BLS_KEY]
                self._current_bls_keys_proof[data[ALIAS]] = \
                    BLS_KEY_PROOF in data and data[BLS_KEY_PROOF] is not None
