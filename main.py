import asyncio
import logging
from ws_client import WSClient
from manager import reset_all_privacy_flags, check_rules_periodically, listen_rule_deletions
from firewall_controller import FirewallController
from asyncio import Queue

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s]: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

log = logging.getLogger("Main")


async def cleanup_on_shutdown():
    """
    Clear all firewall rules upon shutdown.
    """
    log.info("Shutting down, cleaning up cameras firewall rules...")
    await asyncio.to_thread(FirewallController.cleanup_all)

    # Remove the chain as well
    await asyncio.to_thread(FirewallController._run_command, 
                            ["iptables", "-D", "OUTPUT", "-j", "PRIVACY_CAM"])
    await asyncio.to_thread(FirewallController._run_command,
                            ["iptables", "-D", "FORWARD", "-j", "PRIVACY_CAM"])
    await asyncio.to_thread(FirewallController._run_command, 
                            ["iptables", "-X", "PRIVACY_CAM"])

    log.info("Cleanup completed")


async def main():
    message_queue = Queue()
    ws_client = WSClient(message_queue)

    # Initialize the firewall chain at startup
    await asyncio.to_thread(FirewallController.ensure_chain)
    log.info("Initialized cameras firewall chain")

    # Log of currently blocked IPs
    blocked = await asyncio.to_thread(FirewallController.list_blocked_ips)
    if blocked:
        log.warning(f"Found {len(blocked)} IPs already blocked: {blocked}")

    await reset_all_privacy_flags()

    tasks = [
        asyncio.create_task(ws_client.run()),
        asyncio.create_task(check_rules_periodically()),
        asyncio.create_task(listen_rule_deletions(ws_client))
    ]

    try:
        await asyncio.gather(*tasks)
    except asyncio.CancelledError:
        log.debug("Main: Tasks cancelled, shutting down")
    except KeyboardInterrupt:
        log.debug("Main: KeyboardInterrupt received, cancelling tasks...")
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
    finally:
        await cleanup_on_shutdown()
        log.debug("Main: Shutdown complete")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("Interrupted by user")
