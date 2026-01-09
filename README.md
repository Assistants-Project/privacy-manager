# Privacy Manager

**Privacy Manager** is a software component that enforces user-defined privacy rules by temporarily blocking Smartotum devices during specific days and time ranges, until a predefined expiration date.

The manager operates as a **periodic background service**, ensuring consistency between privacy rules and device states stored in the Distributed Hash Table (DHT).

## Device example

Consider a smart light named **Kitchen Light**, represented in the DHT by the following topic:

```json
{
  "topic_name": "domo_light",
  "topic_uuid": "caba8a46-9486-4333-8d80-36cf6ddee387",
  "value": {
    "name": "Kitchen Light",
    "area_name": "bf673d0c-13ff-4e7c-9169-9a2cf2d28bb4",
    "status": true,
  }
}
```

## Privacy rule definition

A privacy rule can be defined to prevent interactions with the light through the Smartotum interface on **Mondays** and **Wednesdays**, between **21:00** and **22:00**, until **August 1st, 2026**.

The rule is stored in the DHT as follows:

```json
{
    "topic_name": "privacy_rule",
    "topic_uuid": "a79882ed-5aa0-451b-bd5b-c5147e801d0c",
    "value": {
      "target_topic": "domo_light",
      "target_uuid": "caba8a46-9486-4333-8d80-36cf6ddee387",
      "time_start": "21:00",
      "time_end": "22:00",
      "days": [
        "Monday",
        "Wednesday"
      ],
      "expiration_date": "2026/08/01"
    }
}
```

## Privacy Manager behavior

The Privacy Manager periodically scans the privacy rules stored in the DHT and:

- Detects newly added rules.
- Determines whether a rule is currently active based on day, time range, and expiration date.
- Applies device blocking when a rule becomes active.
- Removes blocking when a rule is no longer active.
- Automatically deletes expired rules.
- Detects manual rule removal by the user and unblocks any devices previously blocked by that rule.

## Rule enforcement

Device blocking is implemented by updating the device topic in the DHT and setting the `privacy` and `privacy_until` fields:

```json
{
  "topic_name": "domo_light",
  "topic_uuid": "caba8a46-9486-4333-8d80-36cf6ddee387",
  "value": {
    "name": "Kitchen Light",
    "area_name": "bf673d0c-13ff-4e7c-9169-9a2cf2d28bb4",
    "status": true,
    "privacy": true,
    "privacy_until": "22:00",
  }
}
```

These fields indicate that a temporary restriction is active and specify when the block will end.

## Camera-specific handling

For **cameras**, in addition to updating the DHT topic, the Privacy Manager enforces a network-level block.

Firewall rules are applied on the Smartotum gateway to completely prevent any direct access to the camera during the privacy period, including access attempts outside the Smartotum application.
