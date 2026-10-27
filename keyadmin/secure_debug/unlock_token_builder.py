import struct

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature

from keyadmin.core.constants import (
    SDL_ECC_COORD_SIZE,
    SDL_CERT_MAGIC,
    SDL_CERT_AUTH_DEBUG,
    SDL_CERT_AUTH_MISC,
    SDL_CERT_KEY_INDEX,
    SDL_CERT_AUTH_TAMPER,
    SDL_DEBUG_ACCESS_CMD,
    SDL_DEBUG_UNLOCK_PARAM,
    SDL_CERT_BODY_STRUCT,
    SDL_CHALLENGE_RESP_STRUCT,
    SDL_ACCESS_CERT_SIZE,
    SDL_UNLOCK_TOKEN_SIZE,
)


class UnlockTokenBuilder:
    """
    Builds Silicon Labs Series 2 Secure Debug unlock tokens.

    access_certificate (156 B) = magic | auth_debug | auth_misc | key_index | auth_tamper
                                 | serial[16] | cert_pubkey[64] | sig_by_command_key[64]
    unlock_token       (220 B) = access_certificate | sig_by_cert_key(challenge_response)[64]
    challenge_response  (24 B) = DEBUG_ACCESS_CMD | unlock_param | challenge[16]
    """

    @staticmethod
    def raw_public_key(public_key: ec.EllipticCurvePublicKey) -> bytes:
        """Returns the 64-byte raw X||Y (big-endian) format used by the Secure Engine."""
        point = public_key.public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
        return point[1:]

    @staticmethod
    def raw_signature(private_key: ec.EllipticCurvePrivateKey, data: bytes) -> bytes:
        """ECDSA P-256 / SHA-256 signature in the Secure Engine raw r||s format."""
        r, s = decode_dss_signature(private_key.sign(data, ec.ECDSA(hashes.SHA256())))
        return r.to_bytes(SDL_ECC_COORD_SIZE, "big") + s.to_bytes(SDL_ECC_COORD_SIZE, "big")

    def build_access_certificate(self, serial: bytes, cert_public_key: ec.EllipticCurvePublicKey,
                                 command_private_key: ec.EllipticCurvePrivateKey) -> bytes:
        body = struct.pack(
            SDL_CERT_BODY_STRUCT,
            SDL_CERT_MAGIC, SDL_CERT_AUTH_DEBUG, SDL_CERT_AUTH_MISC, SDL_CERT_KEY_INDEX,
            SDL_CERT_AUTH_TAMPER, serial, self.raw_public_key(cert_public_key),
        )
        certificate = body + self.raw_signature(command_private_key, body)
        assert len(certificate) == SDL_ACCESS_CERT_SIZE
        return certificate

    def build_unlock_token(self, access_certificate: bytes, cert_private_key: ec.EllipticCurvePrivateKey,
                           challenge: bytes) -> bytes:
        challenge_response = struct.pack(SDL_CHALLENGE_RESP_STRUCT, SDL_DEBUG_ACCESS_CMD,
                                         SDL_DEBUG_UNLOCK_PARAM, challenge)
        token = access_certificate + self.raw_signature(cert_private_key, challenge_response)
        assert len(token) == SDL_UNLOCK_TOKEN_SIZE
        return token
