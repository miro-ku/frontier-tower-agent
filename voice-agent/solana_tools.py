"""
Solana Tools for the Frontier Tower Agent

Provides wallet management and SOL transfer capabilities.
The agent's keypair is loaded from environment, enabling it
to be an economic actor — managing building treasury, bounties,
and governance fund allocation.
"""

import json
import os
from typing import Any

LAMPORTS_PER_SOL = 1_000_000_000

# Lazy imports — solana packages are optional (only needed when wallet is configured)
_solana_available = False
try:
    from solders.keypair import Keypair
    from solders.pubkey import Pubkey
    from solders.system_program import TransferParams, transfer
    from solana.rpc.async_api import AsyncClient
    _solana_available = True
except ImportError:
    pass


def _check_available():
    if not _solana_available:
        raise RuntimeError("Solana packages not installed. Run: pip install solders solana")


def _load_keypair():
    """Load the agent's Solana keypair from environment."""
    key_path = os.environ.get("SOLANA_KEYPAIR_PATH", "")
    key_json = os.environ.get("SOLANA_PRIVATE_KEY", "")

    if key_json:
        secret = json.loads(key_json)
        return Keypair.from_bytes(bytes(secret))
    elif key_path and os.path.exists(key_path):
        with open(key_path) as f:
            secret = json.loads(f.read())
        return Keypair.from_bytes(bytes(secret))
    else:
        raise RuntimeError(
            "No Solana keypair configured. Set SOLANA_PRIVATE_KEY or SOLANA_KEYPAIR_PATH."
        )


def _get_rpc_url() -> str:
    return os.environ.get("SOLANA_RPC_URL", "https://api.devnet.solana.com")


async def check_balance() -> str:
    """Check the agent wallet's SOL balance."""
    _check_available()
    keypair = _load_keypair()
    client = AsyncClient(_get_rpc_url())

    try:
        resp = await client.get_balance(keypair.pubkey())
        lamports = resp.value
        sol = lamports / LAMPORTS_PER_SOL
        return f"Agent wallet balance: {sol:.4f} SOL ({keypair.pubkey()})"
    finally:
        await client.close()


async def transfer_sol(to_address: str, amount: float, memo: str = "") -> str:
    """Transfer SOL from the agent wallet to a recipient.

    Args:
        to_address: Recipient's Solana address
        amount: Amount in SOL
        memo: Optional transaction memo
    """
    _check_available()
    keypair = _load_keypair()
    client = AsyncClient(_get_rpc_url())

    try:
        recipient = Pubkey.from_string(to_address)
        lamports = int(amount * LAMPORTS_PER_SOL)

        # Get recent blockhash
        blockhash_resp = await client.get_latest_blockhash()
        blockhash = blockhash_resp.value.blockhash

        # Build and sign transaction
        txn = Transaction()
        txn.add(
            transfer(
                TransferParams(
                    from_pubkey=keypair.pubkey(),
                    to_pubkey=recipient,
                    lamports=lamports,
                )
            )
        )
        txn.recent_blockhash = blockhash
        txn.sign(keypair)

        # Send
        result = await client.send_transaction(txn, keypair)
        signature = str(result.value)

        return (
            f"Transferred {amount} SOL to {to_address}. "
            f"Transaction: {signature}"
        )
    finally:
        await client.close()


async def get_wallet_address() -> str:
    """Get the agent's Solana wallet public address."""
    _check_available()
    keypair = _load_keypair()
    return f"Agent wallet address: {keypair.pubkey()}"
