from datetime import datetime
from zoneinfo import ZoneInfo

PRIVACY_RULE_TOPIC = "privacy_rule"

TZ = ZoneInfo("Europe/Rome")

class PrivacyRule:
    def __init__(self, uuid, target_topic, target_uuid, value):
        self.uuid = uuid
        self.target_topic = target_topic
        self.target_uuid = target_uuid
        self.value = value

    def _now(self):
        return datetime.now(TZ)

    def is_expired(self) -> bool:
        exp_date = datetime.strptime(
            self.value["expiration_date"], "%Y/%m/%d"
        ).date()
        return self._now().date() > exp_date

    def is_active(self) -> bool:
        now = self._now()

        # Check expiration date (<= valid)
        exp_date = datetime.strptime(
            self.value["expiration_date"], "%Y/%m/%d"
        ).date()
        if now.date() > exp_date:
            return False

        # Check day of week
        current_day = now.strftime("%A")  # Monday, Tuesday, ...
        if current_day not in self.value["days"]:
            return False

        # Check time window (bounds included)
        start = datetime.strptime(self.value["time_start"], "%H:%M").time()
        end = datetime.strptime(self.value["time_end"], "%H:%M").time()
        current_time = now.time()

        return start <= current_time <= end

