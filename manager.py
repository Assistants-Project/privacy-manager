import asyncio
import logging
from dht_client import fetch_all_topics, fetch_topics, fetch_topic, update_topic, delete_topic
from privacy_rule import PrivacyRule, PRIVACY_RULE_TOPIC
from firewall_controller import FirewallController

log = logging.getLogger("Manager")


async def reset_all_privacy_flags():
    """
    On startup, reset all privacy flags and unblock all devices.
    IMPORTANT: This prevents devices from remaining locked after a crash.
    """
    log.info("Resetting device privacy flags...")

    topics = await fetch_all_topics()
    log.debug(f"Fetched {len(topics)} topics for initial privacy reset")

    for topic in topics:
        value = topic.get("value", {})

        if value.get("privacy", False):
            value["privacy"] = False

            # Unblock cameras
            if topic["topic_name"] == "domo_camera":
                ip = value.get("ip_address")
                if ip:
                    success = await asyncio.to_thread(FirewallController.unblock_ip, ip)
                    if success:
                        log.debug(f"Unblocked camera {value.get('name', 'unknown')} at {ip}")
                    else:
                        log.error(f"Failed to unblock camera at {ip}")

            await update_topic(
                topic["topic_name"],
                topic["topic_uuid"],
                value
            )
            log.debug(f"Reset privacy for {topic['topic_name']}:{topic['topic_uuid']}")

    log.info("Restore completed")


async def check_rules_periodically():
    """
    Periodically check the privacy rules and apply blocks/unblocks to the devices.
    """
    while True:
        try:
            rules_data = await fetch_topics(PRIVACY_RULE_TOPIC)

            for rule_json in rules_data:
                rule = PrivacyRule(
                    rule_json["topic_uuid"],
                    rule_json["value"]["target_topic"],
                    rule_json["value"]["target_uuid"],
                    rule_json["value"]
                )

                target_topic = await fetch_topic(
                    rule.target_topic,
                    rule.target_uuid
                )

                if not target_topic:
                    log.warning(f"Target topic not found: {rule.target_topic}:{rule.target_uuid}")
                    continue

                is_camera = target_topic["topic_name"] == "domo_camera"
                ip_address = target_topic["value"].get("ip_address") if is_camera else None
                name = target_topic["value"].get("name", "a device")

                # Expired rule
                if rule.is_expired():
                    if target_topic["value"].get("privacy", False):
                        target_topic["value"]["privacy"] = False

                        # Unblock the camera
                        if is_camera and ip_address:
                            success = await asyncio.to_thread(FirewallController.unblock_ip, ip_address)
                            if success:
                                log.debug(f"Unblocked camera {ip_address} due to expired rule")
                            else:
                                log.error(f"Failed to unblock camera {ip_address}")

                        await update_topic(
                            rule.target_topic,
                            rule.target_uuid,
                            target_topic["value"]
                        )
                        log.info(f"Privacy rule expired for {name}, device unblocked")

                    await delete_topic(PRIVACY_RULE_TOPIC, rule.uuid)
                    log.debug(f"Deleted expired privacy rule {rule.uuid}")
                    continue

                # Active rule
                if rule.is_active():
                    if not target_topic["value"].get("privacy", False):
                        target_topic["value"]["privacy"] = True
                        target_topic["value"]["privacy_until"] = rule.value["time_end"]

                        # Block the camera
                        if is_camera and ip_address:
                            success = await asyncio.to_thread(FirewallController.block_ip, ip_address)
                            if success:
                                camera_name = target_topic["value"].get("name", "unknown")
                                log.debug(f"✓ Blocked camera '{camera_name}' at {ip_address}")
                            else:
                                log.error(f"✗ Failed to block camera at {ip_address}")

                        await update_topic(
                            rule.target_topic,
                            rule.target_uuid,
                            target_topic["value"]
                        )
                        log.info(f"Privacy rule activated: {name} is now blocked")

                # Inactive rule
                else:
                    if target_topic["value"].get("privacy", False):
                        target_topic["value"]["privacy"] = False

                        # Unblock the camera
                        if is_camera and ip_address:
                            success = await asyncio.to_thread(FirewallController.unblock_ip, ip_address)
                            if success:
                                log.debug(f"Unblocked camera {ip_address} due to inactive rule")
                            else:
                                log.error(f"Failed to unblock camera {ip_address}")

                        await update_topic(
                            rule.target_topic,
                            rule.target_uuid,
                            target_topic["value"]
                        )
                        log.info(f"Privacy period ended: {name} is now available again")

        except Exception as e:
            log.error(f"Error in check_rules_periodically: {e}", exc_info=True)

        await asyncio.sleep(60)


async def listen_rule_deletions(ws_client):
    """
    Listen for WebSocket notifications for rule deletions.
    When a rule is deleted, unblock the device.
    """
    while True:
        try:
            message = await ws_client._message_queue.get()

            if "Persistent" in message:
                log.debug(f"Received WS message: {message}")
                msg = message["Persistent"]

                if msg["topic_name"] == PRIVACY_RULE_TOPIC and msg.get("deleted", False):
                    target_topic_name = msg["value"]["target_topic"]
                    target_uuid = msg["value"]["target_uuid"]

                    target_topic = await fetch_topic(target_topic_name, target_uuid)

                    if target_topic and target_topic["value"].get("privacy", False):
                        target_topic["value"]["privacy"] = False
                        name = target_topic.get("name", "a device")

                        # Unblock the camera
                        if target_topic_name == "domo_camera":
                            ip = target_topic["value"].get("ip_address")
                            if ip:
                                success = await asyncio.to_thread(FirewallController.unblock_ip, ip)
                                if success:
                                    camera_name = target_topic["value"].get("name", "unknown")
                                    log.debug(f"Unblocked camera '{camera_name}' at {ip} due to rule deletion")
                                else:
                                    log.error(f"Failed to unblock camera at {ip}")

                        await update_topic(target_topic_name, target_uuid, target_topic["value"])
                        log.info(f"Privacy rule removed by user: {name} unblocked")

        except Exception as e:
            log.error(f"Error in listen_rule_deletions: {e}", exc_info=True)
            await asyncio.sleep(1)  # Evita loop frenetici in caso di errori continui
