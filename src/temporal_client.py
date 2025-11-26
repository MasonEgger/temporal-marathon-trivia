# ABOUTME: Temporal client connection utilities with environment configuration.
# Helper functions for creating Temporal clients (local and cloud deployments).

import os

from temporalio.client import Client
from temporalio.contrib.pydantic import pydantic_data_converter
from temporalio.service import TLSConfig


async def create_temporal_client() -> Client:
    """Create Temporal client with automatic environment configuration.

    Supports both local Temporal dev server and Temporal Cloud deployments.
    Configuration is determined by environment variables:

    Local Development:
        - TEMPORAL_ADDRESS: localhost:7233 (default)
        - TEMPORAL_NAMESPACE: default (default)
        - No TLS required

    Temporal Cloud:
        - TEMPORAL_ADDRESS: <namespace>.tmprl.cloud:7233
        - TEMPORAL_NAMESPACE: <namespace>
        - TEMPORAL_TLS_CERT: Path to client certificate file
        - TEMPORAL_TLS_KEY: Path to client key file

    The client is configured with pydantic_data_converter to support
    serialization of pydantic models (EmailStr, BaseModel, etc.) in
    workflow parameters and return values.

    Returns:
        Client: Configured Temporal client instance

    Raises:
        ValueError: If TLS cert/key paths are invalid
        ConnectionError: If unable to connect to Temporal server

    Example:
        >>> client = await create_temporal_client()
        >>> # Local: connects to localhost:7233
        >>> # Cloud: connects with TLS to <namespace>.tmprl.cloud:7233
    """
    # Read environment variables with sensible defaults for local development
    address = os.getenv("TEMPORAL_ADDRESS", "localhost:7233")
    namespace = os.getenv("TEMPORAL_NAMESPACE", "default")
    tls_cert_path = os.getenv("TEMPORAL_TLS_CERT")
    tls_key_path = os.getenv("TEMPORAL_TLS_KEY")

    # Determine if we need TLS (Temporal Cloud) or plaintext (local)
    tls_config = None
    if tls_cert_path and tls_key_path:
        # Temporal Cloud deployment - load TLS certificates
        try:
            with open(tls_cert_path, "rb") as cert_file:
                client_cert = cert_file.read()
            with open(tls_key_path, "rb") as key_file:
                client_key = key_file.read()

            tls_config = TLSConfig(
                client_cert=client_cert,
                client_private_key=client_key,
            )
        except FileNotFoundError as e:
            raise ValueError(f"TLS certificate or key file not found: {e}") from e
        except Exception as e:
            raise ValueError(f"Error loading TLS certificates: {e}") from e

    # Create client with pydantic data converter
    # This enables serialization of pydantic models in workflow parameters
    try:
        if tls_config:
            # Temporal Cloud with TLS
            client = await Client.connect(
                target_host=address,
                namespace=namespace,
                tls=tls_config,
                data_converter=pydantic_data_converter,
            )
        else:
            # Local Temporal without TLS
            client = await Client.connect(
                target_host=address,
                namespace=namespace,
                data_converter=pydantic_data_converter,
            )
        return client
    except Exception as e:
        raise ConnectionError(f"Failed to connect to Temporal at {address}: {e}") from e
