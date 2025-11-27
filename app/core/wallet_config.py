"""
Wallet Configuration for Multi-Network Support
Defines supported networks and their corresponding currencies
"""

from typing import Dict, List, Optional
from pydantic import BaseModel


class NetworkConfig(BaseModel):
    """Configuration for a blockchain network"""
    network_name: str  # DFNS network identifier
    display_name: str  # Human-readable name
    native_currency: str  # Native currency symbol
    testnet_name: str  # Testnet equivalent
    min_confirmations: int  # Minimum confirmations for deposits


class CurrencyConfig(BaseModel):
    """Configuration for a currency/token"""
    symbol: str
    name: str
    networks: List[str]  # Networks where this currency is available
    contract_addresses: Dict[str, str]  # Network -> contract address mapping
    decimals: int


# Network configurations
NETWORKS = {
    # Bitcoin
    "Bitcoin": NetworkConfig(
        network_name="Bitcoin",
        display_name="Bitcoin",
        native_currency="BTC",
        testnet_name="BitcoinTestnet3",
        min_confirmations=6
    ),

    # Ethereum Mainnet
    "Ethereum": NetworkConfig(
        network_name="Ethereum",
        display_name="Ethereum",
        native_currency="ETH",
        testnet_name="EthereumSepolia",
        min_confirmations=16
    ),

    # Solana
    "Solana": NetworkConfig(
        network_name="Solana",
        display_name="Solana",
        native_currency="SOL",
        testnet_name="SolanaDevnet",
        min_confirmations=200
    ),

    # Layer 2s
    "ArbitrumOne": NetworkConfig(
        network_name="ArbitrumOne",
        display_name="Arbitrum",
        native_currency="ETH",
        testnet_name="ArbitrumSepolia",
        min_confirmations=64
    ),

    "Optimism": NetworkConfig(
        network_name="Optimism",
        display_name="Optimism",
        native_currency="ETH",
        testnet_name="OptimismSepolia",
        min_confirmations=64
    ),

    "Base": NetworkConfig(
        network_name="Base",
        display_name="Base",
        native_currency="ETH",
        testnet_name="BaseSepolia",
        min_confirmations=64
    ),
}


# Currency/Token configurations
CURRENCIES = {
    "BTC": CurrencyConfig(
        symbol="BTC",
        name="Bitcoin",
        networks=["Bitcoin"],
        contract_addresses={},  # Native currency, no contract
        decimals=8
    ),

    "ETH": CurrencyConfig(
        symbol="ETH",
        name="Ethereum",
        networks=["Ethereum", "ArbitrumOne", "Optimism", "Base"],
        contract_addresses={},  # Native currency on all networks
        decimals=18
    ),

    "SOL": CurrencyConfig(
        symbol="SOL",
        name="Solana",
        networks=["Solana"],
        contract_addresses={},  # Native currency
        decimals=9
    ),

    "USDT": CurrencyConfig(
        symbol="USDT",
        name="Tether USD",
        networks=["Ethereum", "ArbitrumOne", "Optimism", "Base", "Solana"],
        contract_addresses={
            "Ethereum": "0xdAC17F958D2ee523a2206206994597C13D831ec7",
            "ArbitrumOne": "0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9",
            "Optimism": "0x94b008aA00579c1307B0EF2c499aD98a8ce58e58",
            "Base": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",  # Base USDT contract
            "Solana": "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",  # USDT SPL token
        },
        decimals=6
    ),

    "USDC": CurrencyConfig(
        symbol="USDC",
        name="USD Coin",
        networks=["Ethereum", "ArbitrumOne", "Optimism", "Base", "Solana"],
        contract_addresses={
            "Ethereum": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
            "ArbitrumOne": "0xaf88d065e77c8cC2239327C5EDb3A432268e5831",
            "Optimism": "0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85",
            "Base": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
            "Solana": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC SPL token
        },
        decimals=6
    ),
}


# Default wallet creation configuration
# Defines which wallets to create by default for new users
DEFAULT_WALLETS = [
    # Bitcoin
    {"currency": "BTC", "network": "Bitcoin"},

    # Ethereum Mainnet
    {"currency": "ETH", "network": "Ethereum"},
    {"currency": "USDT", "network": "Ethereum"},
    {"currency": "USDC", "network": "Ethereum"},

    # Solana
    {"currency": "SOL", "network": "Solana"},
    {"currency": "USDT", "network": "Solana"},
    {"currency": "USDC", "network": "Solana"},

    # Layer 2s (Arbitrum, Optimism, Base) mainly USDT
    {"currency": "USDT", "network": "ArbitrumOne"},
    {"currency": "USDT", "network": "Optimism"},
    {"currency": "USDT", "network": "Base"},
]


# Testnet wallet creation configuration (for development/testing)
TESTNET_WALLETS = [
    {"currency": "USDT", "network": "EthereumSepolia"},
    {"currency": "USDC", "network": "EthereumSepolia"},
]


def get_network_for_currency(currency: str, preferred_network: Optional[str] = None) -> str:
    """
    Get the appropriate network for a currency

    Args:
        currency: Currency symbol (e.g., "USDT", "BTC")
        preferred_network: Preferred network if available

    Returns:
        Network name
    """
    if currency not in CURRENCIES:
        raise ValueError(f"Unsupported currency: {currency}")

    available_networks = CURRENCIES[currency].networks

    if preferred_network and preferred_network in available_networks:
        return preferred_network

    # Return first available network
    return available_networks[0]


def get_contract_address(currency: str, network: str) -> str:
    """
    Get contract address for a token on a specific network

    Args:
        currency: Currency symbol
        network: Network name

    Returns:
        Contract address or empty string for native currencies
    """
    if currency not in CURRENCIES:
        raise ValueError(f"Unsupported currency: {currency}")

    return CURRENCIES[currency].contract_addresses.get(network, "")


def is_testnet_mode() -> bool:
    """Check if running in testnet mode based on environment"""
    import os
    return os.getenv("DFNS_BASE_URL", "").endswith("sandbox") or \
           os.getenv("ENVIRONMENT", "development") in ["development", "staging"]


def get_wallets_to_create() -> List[Dict[str, str]]:
    """
    Get list of wallets to create based on environment

    Returns:
        List of {currency, network} dictionaries
    """
    if is_testnet_mode():
        return TESTNET_WALLETS
    return DEFAULT_WALLETS
