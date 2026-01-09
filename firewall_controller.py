import subprocess
import logging

log = logging.getLogger("FirewallController")
CHAIN = "PRIVACY_CAM"

def host_iptables_cmd(*args) -> list[str]:
    return ["iptables"] + list(args)

class FirewallController:
    """
    Manages IP blocking via iptables on the host gateway.
    Uses a custom chain to isolate privacy rules for the cameras.
    """

    @staticmethod
    def _run_check(cmd) -> bool:
        try:
            result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)
            return result.returncode == 0
        except subprocess.TimeoutExpired:
            log.error(f"Timeout executing command: {' '.join(cmd)}")
            return False
        except Exception as e:
            log.error(f"Error checking iptables rule: {e}")
            return False

    @staticmethod
    def _run_command(cmd) -> bool:
        try:
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5, text=True)
            if result.returncode != 0:
                log.error(f"iptables command failed: {' '.join(cmd)}")
                log.error(f"stdout: {result.stdout}")
                log.error(f"stderr: {result.stderr}")
                return False
            return True
        except subprocess.TimeoutExpired:
            log.error(f"Timeout executing: {' '.join(cmd)}")
            return False
        except Exception as e:
            log.error(f"Exception running iptables: {e}")
            return False

    @classmethod
    def ensure_chain(cls) -> bool:
        if not cls._run_check(host_iptables_cmd("-L", CHAIN, "-n")):
            log.debug(f"Creating chain {CHAIN}")
            if not cls._run_command(host_iptables_cmd("-N", CHAIN)):
                log.error(f"Failed to create chain {CHAIN}")
                return False
            log.debug(f"Chain {CHAIN} created successfully")

        if not cls._run_check(host_iptables_cmd("-C", "FORWARD", "-j", CHAIN)):
            log.debug(f"Attaching {CHAIN} to FORWARD chain")
            if not cls._run_command(host_iptables_cmd("-I", "FORWARD", "1", "-j", CHAIN)):
                log.error(f"Failed to attach {CHAIN} to FORWARD")
                return False
            log.debug(f"Chain {CHAIN} attached to FORWARD successfully")

        if not cls._run_check(host_iptables_cmd("-C", "OUTPUT", "-j", CHAIN)):
            log.debug(f"Attaching {CHAIN} to OUTPUT chain")
            if not cls._run_command(host_iptables_cmd("-I", "OUTPUT", "1", "-j", CHAIN)):
                log.error(f"Failed to attach {CHAIN} to OUTPUT")
                return False
            log.debug(f"Chain {CHAIN} attached to OUTPUT successfully")

        return True

    @classmethod
    def block_ip(cls, ip: str) -> bool:
        if not ip:
            log.warning("block_ip called with empty IP")
            return False

        if not cls.ensure_chain():
            return False

        if cls._run_check(host_iptables_cmd("-C", CHAIN, "-d", ip, "-j", "DROP")):
            log.debug(f"IP {ip} already blocked")
            return True

        if cls._run_command(host_iptables_cmd("-A", CHAIN, "-d", ip, "-j", "DROP")):
            log.debug(f"✓ Blocked IP {ip}")
            return True
        else:
            log.error(f"✗ Failed to block IP {ip}")
            return False

    @classmethod
    def unblock_ip(cls, ip: str) -> bool:
        if not ip:
            log.warning("unblock_ip called with empty IP")
            return False

        if not cls.ensure_chain():
            return False

        removed_any = False
        max_attempts = 10
        attempts = 0

        while cls._run_check(host_iptables_cmd("-C", CHAIN, "-d", ip, "-j", "DROP")):
            if attempts >= max_attempts:
                log.error(f"Max attempts reached removing rule for {ip}")
                break
            if cls._run_command(host_iptables_cmd("-D", CHAIN, "-d", ip, "-j", "DROP")):
                removed_any = True
                attempts += 1
            else:
                log.error(f"Failed to remove rule for {ip} on attempt {attempts}")
                break

        if removed_any:
            log.debug(f"✓ Unblocked IP {ip} ({attempts} rule(s) removed)")
        else:
            log.debug(f"IP {ip} was not blocked")

        return True

    @classmethod
    def cleanup_all(cls) -> bool:
        if not cls._run_check(host_iptables_cmd("-L", CHAIN, "-n")):
            log.debug(f"Chain {CHAIN} does not exist, nothing to clean")
            return True

        log.debug(f"Cleaning up all rules in {CHAIN}")
        if cls._run_command(host_iptables_cmd("-F", CHAIN)):
            log.debug(f"✓ All rules flushed from {CHAIN}")
            return True
        else:
            log.error(f"✗ Failed to flush {CHAIN}")
            return False

    @classmethod
    def list_blocked_ips(cls) -> list[str]:
        if not cls._run_check(host_iptables_cmd("-L", CHAIN, "-n")):
            return []

        try:
            result = subprocess.run(
                host_iptables_cmd("-L", CHAIN, "-n", "--line-numbers"),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=5,
                text=True
            )

            if result.returncode != 0:
                return []

            blocked_ips = []
            for line in result.stdout.split("\n"):
                if "DROP" in line and "0.0.0.0/0" in line:
                    parts = line.split()
                    if len(parts) >= 5:
                        ip = parts[4]
                        if ip != "0.0.0.0/0":
                            blocked_ips.append(ip)
            return blocked_ips

        except Exception as e:
            log.error(f"Error listing blocked IPs: {e}")
            return []

    @classmethod
    def is_ip_blocked(cls, ip: str) -> bool:
        return cls._run_check(host_iptables_cmd("-C", CHAIN, "-d", ip, "-j", "DROP"))

