"""
Connection Security Manager

Validates and secures database connection configurations to prevent security risks.
"""

import re
import ipaddress
import logging
from typing import Dict, Tuple, List, Set
from urllib.parse import urlparse


class ConnectionSecurityManager:
    """
    Manages security validation for database connections
    
    Implements whitelist/blacklist for hosts, port validation, and security checks.
    """
    
    # Default allowed hosts (can be overridden via configuration)
    DEFAULT_ALLOWED_HOSTS = [
        "localhost",
        "127.0.0.1",
        "::1",
    ]
    
    # Blocked hosts and IP ranges (security critical)
    BLOCKED_HOSTS = [
        "0.0.0.0",
        "169.254.169.254",  # AWS EC2 metadata
        "metadata.google.internal",  # GCP metadata
        "169.254.169.123",  # Oracle Cloud metadata
        "100.100.100.200",  # Alibaba Cloud metadata
    ]
    
    # Blocked IP ranges (CIDR notation)
    BLOCKED_IP_RANGES = [
        "169.254.0.0/16",   # AWS metadata and link-local
        "127.0.0.0/8",      # Loopback (except 127.0.0.1)
        "10.0.0.0/8",       # Private networks (can be enabled if needed)
        "172.16.0.0/12",    # Private networks
        "192.168.0.0/16",   # Private networks
    ]
    
    # Dangerous hostnames patterns
    DANGEROUS_HOSTNAME_PATTERNS = [
        r".*metadata.*",
        r".*admin.*",
        r".*root.*",
        r".*internal.*",
        r".*private.*",
        r".*secret.*",
    ]
    
    def __init__(self, 
                 allowed_hosts: List[str] = None, 
                 blocked_hosts: List[str] = None,
                 allow_private_networks: bool = False):
        """
        Initialize connection security manager
        
        Args:
            allowed_hosts: List of explicitly allowed hosts
            blocked_hosts: Additional hosts to block
            allow_private_networks: Whether to allow private network ranges
        """
        self.logger = logging.getLogger(__name__)
        
        # Configure allowed hosts
        self.allowed_hosts = set(allowed_hosts or self.DEFAULT_ALLOWED_HOSTS)
        
        # Configure blocked hosts
        self.blocked_hosts = set(self.BLOCKED_HOSTS)
        if blocked_hosts:
            self.blocked_hosts.update(blocked_hosts)
        
        # Configure IP range blocking
        self.allow_private_networks = allow_private_networks
        if allow_private_networks:
            # Remove private network ranges from blocked list
            self.blocked_ip_ranges = [
                "169.254.0.0/16",   # Keep AWS metadata blocked
            ]
        else:
            self.blocked_ip_ranges = self.BLOCKED_IP_RANGES.copy()
        
        self.logger.info(f"Connection security initialized with {len(self.allowed_hosts)} allowed hosts")
    
    def validate_connection_config(self, config: Dict) -> Tuple[bool, str]:
        """
        Validate complete connection configuration for security
        
        Args:
            config: Database connection configuration
            
        Returns:
            Tuple of (is_valid, reason)
        """
        # Validate hostname
        hostname = config.get("hostname") or config.get("host")
        if not hostname:
            return False, "Hostname is required"
        
        is_host_allowed, host_message = self.is_host_allowed(hostname)
        if not is_host_allowed:
            return False, host_message
        
        # Validate port
        port = config.get("port", 0)
        is_port_valid, port_message = self.is_port_allowed(port)
        if not is_port_valid:
            return False, port_message
        
        # Check SSL/TLS requirements
        is_ssl_valid, ssl_message = self._check_ssl_requirements(config)
        if not is_ssl_valid:
            return False, ssl_message
        
        # Validate credentials
        is_creds_valid, creds_message = self._validate_credentials(config)
        if not is_creds_valid:
            return False, creds_message
        
        return True, "Connection configuration is secure"
    
    def is_host_allowed(self, hostname: str) -> Tuple[bool, str]:
        """
        Check if a hostname is allowed for connections
        
        Args:
            hostname: Hostname or IP address to check
            
        Returns:
            Tuple of (is_allowed, reason)
        """
        if not hostname:
            return False, "Empty hostname not allowed"
        
        hostname_lower = hostname.lower()
        
        # Check explicit blacklist first
        if hostname_lower in self.blocked_hosts:
            return False, f"Host '{hostname}' is explicitly blocked"
        
        # Check dangerous hostname patterns
        for pattern in self.DANGEROUS_HOSTNAME_PATTERNS:
            if re.match(pattern, hostname_lower):
                return False, f"Host '{hostname}' matches blocked pattern: {pattern}"
        
        # Check if it's an IP address
        try:
            ip = ipaddress.ip_address(hostname)
            return self._validate_ip_address(ip)
        except ValueError:
            # Not an IP address, treat as hostname
            pass
        
        # Check if hostname is in allowed list
        if self.allowed_hosts and hostname_lower not in self.allowed_hosts:
            # If we have an explicit allowed list and hostname is not in it
            if len(self.allowed_hosts) > len(self.DEFAULT_ALLOWED_HOSTS):
                return False, f"Host '{hostname}' is not in the allowed hosts list"
        
        # Additional DNS validation
        if not self._is_valid_hostname(hostname):
            return False, f"Invalid hostname format: {hostname}"
        
        return True, f"Host '{hostname}' is allowed"
    
    def _validate_ip_address(self, ip: ipaddress.IPv4Address or ipaddress.IPv6Address) -> Tuple[bool, str]:
        """
        Validate IP address against security rules
        
        Args:
            ip: IP address object
            
        Returns:
            Tuple of (is_valid, reason)
        """
        ip_str = str(ip)
        
        # Check against blocked IP ranges
        for blocked_range in self.blocked_ip_ranges:
            try:
                network = ipaddress.ip_network(blocked_range, strict=False)
                if ip in network:
                    return False, f"IP address {ip_str} is in blocked range {blocked_range}"
            except ValueError:
                continue
        
        # Check for special addresses
        if ip.is_loopback and ip_str not in ["127.0.0.1", "::1"]:
            return False, f"Loopback address {ip_str} not allowed (use 127.0.0.1)"
        
        if ip.is_multicast:
            return False, f"Multicast address {ip_str} not allowed"
        
        if ip.is_unspecified:
            return False, f"Unspecified address {ip_str} not allowed"
        
        if ip.is_reserved:
            return False, f"Reserved address {ip_str} not allowed"
        
        # Check private addresses if not explicitly allowed
        if not self.allow_private_networks and ip.is_private and ip_str not in ["127.0.0.1"]:
            return False, f"Private address {ip_str} not allowed (enable private networks if needed)"
        
        return True, f"IP address {ip_str} is valid"
    
    def is_port_allowed(self, port: int) -> Tuple[bool, str]:
        """
        Validate port number
        
        Args:
            port: Port number to validate
            
        Returns:
            Tuple of (is_valid, reason)
        """
        if not isinstance(port, int):
            try:
                port = int(port)
            except (ValueError, TypeError):
                return False, "Port must be a valid integer"
        
        if port < 1 or port > 65535:
            return False, f"Port {port} is outside valid range (1-65535)"
        
        # Check for potentially dangerous ports
        dangerous_ports = {
            22: "SSH",
            23: "Telnet", 
            25: "SMTP",
            53: "DNS",
            80: "HTTP",
            135: "RPC",
            139: "NetBIOS",
            443: "HTTPS",
            445: "SMB",
            993: "IMAPS",
            995: "POP3S"
        }
        
        if port in dangerous_ports and port not in [80, 443]:  # Allow HTTP/HTTPS
            service = dangerous_ports[port]
            self.logger.warning(f"Using potentially dangerous port {port} ({service})")
        
        return True, f"Port {port} is valid"
    
    def _check_ssl_requirements(self, config: Dict) -> Tuple[bool, str]:
        """
        Check SSL/TLS requirements
        
        Args:
            config: Connection configuration
            
        Returns:
            Tuple of (is_valid, reason)
        """
        hostname = config.get("hostname") or config.get("host", "")
        ssl_enabled = config.get("ssl", False) or config.get("use_ssl", False)
        
        # Require SSL for remote connections
        if hostname not in ["localhost", "127.0.0.1", "::1"]:
            if not ssl_enabled:
                return False, "SSL/TLS is required for remote database connections"
        
        # Validate SSL certificate configuration if SSL is enabled
        if ssl_enabled:
            ssl_cert = config.get("ssl_cert")
            ssl_key = config.get("ssl_key") 
            ssl_ca = config.get("ssl_ca")
            
            if ssl_cert and not ssl_key:
                return False, "SSL key is required when SSL certificate is provided"
            
            if ssl_key and not ssl_cert:
                return False, "SSL certificate is required when SSL key is provided"
        
        return True, "SSL configuration is valid"
    
    def _validate_credentials(self, config: Dict) -> Tuple[bool, str]:
        """
        Validate database credentials
        
        Args:
            config: Connection configuration
            
        Returns:
            Tuple of (is_valid, reason)
        """
        username = config.get("dbuser") or config.get("username", "")
        password = config.get("dbpassword") or config.get("password", "")
        
        if not username:
            return False, "Database username is required"
        
        if not password:
            return False, "Database password is required"
        
        # Check for weak usernames
        weak_usernames = {"root", "admin", "administrator", "sa", "postgres", "mysql"}
        if username.lower() in weak_usernames:
            self.logger.warning(f"Using potentially risky username: {username}")
        
        # Basic password strength check
        if len(password) < 8:
            return False, "Password must be at least 8 characters long"
        
        # Check for common weak passwords (basic check)
        weak_passwords = {"password", "123456", "admin", "root", "test", "guest"}
        if password.lower() in weak_passwords:
            return False, "Password is too weak - use a strong password"
        
        return True, "Credentials are acceptable"
    
    def _is_valid_hostname(self, hostname: str) -> bool:
        """
        Validate hostname format
        
        Args:
            hostname: Hostname to validate
            
        Returns:
            True if hostname format is valid
        """
        if len(hostname) > 255:
            return False
        
        # Check for valid hostname pattern
        hostname_pattern = re.compile(
            r"^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$"
        )
        
        return hostname_pattern.match(hostname) is not None
    
    def add_allowed_host(self, hostname: str):
        """
        Add a host to the allowed list
        
        Args:
            hostname: Hostname to allow
        """
        self.allowed_hosts.add(hostname.lower())
        self.logger.info(f"Added {hostname} to allowed hosts")
    
    def remove_allowed_host(self, hostname: str):
        """
        Remove a host from the allowed list
        
        Args:
            hostname: Hostname to remove
        """
        self.allowed_hosts.discard(hostname.lower())
        self.logger.info(f"Removed {hostname} from allowed hosts")
    
    def add_blocked_host(self, hostname: str):
        """
        Add a host to the blocked list
        
        Args:
            hostname: Hostname to block
        """
        self.blocked_hosts.add(hostname.lower())
        self.logger.info(f"Added {hostname} to blocked hosts")
    
    def get_security_summary(self) -> Dict[str, any]:
        """
        Get current security configuration summary
        
        Returns:
            Dictionary with security settings
        """
        return {
            "allowed_hosts_count": len(self.allowed_hosts),
            "blocked_hosts_count": len(self.blocked_hosts),
            "allow_private_networks": self.allow_private_networks,
            "blocked_ip_ranges": self.blocked_ip_ranges,
            "sample_allowed_hosts": list(self.allowed_hosts)[:5] if self.allowed_hosts else [],
            "sample_blocked_hosts": list(self.blocked_hosts)[:5]
        }