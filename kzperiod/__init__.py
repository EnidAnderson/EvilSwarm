"""kzperiod: exact representation of Kontsevich-Zagier period data.

Every value is an exact integer or an exact integer pair; serialization is
canonical, injective and deterministic; iterated words are machine-width
bit patterns; rational matrices ride per-prime residue lanes with height
ledgers; proofs are integer move records.
"""

from .exact import Q, LibRefusal
from .godel import serialize, deserialize, serial_number, hash128
from .arena import Arena
from .words import (Word, compose, parse_blocks, is_room, compositions,
                    room_keys, census_rec, word_from_indices, shuffle_words,
                    stuffle2)
from .lanes import (QMat, LaneStack, lane_matmul, crt_lift, wang_reconstruct,
                    modulus_product, inv_mod)
from .moves import (MoveRecord, Proof, TranspositionTable, SPECIES_RELATION,
                    SPECIES_CERTIFICATE, SPECIES_CLAIM, weight4_proof,
                    verify_weight4)
