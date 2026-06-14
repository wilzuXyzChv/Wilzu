import json
import os
from datetime import datetime, timedelta

class OTPFilter:
    def __init__(self, cache_file='otp_cache.json', expire_minutes=30):
        self.cache_file = cache_file
        self.expire_minutes = expire_minutes
        self.cache = self._load_cache()

    def _load_cache(self):
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {}

    def _save_cache(self):
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(self.cache, f, indent=2)
        except:
            pass

    def _cleanup_expired(self):
        now = datetime.now()
        expired = []
        for k, v in self.cache.items():
            try:
                if now - datetime.fromisoformat(v['timestamp']) > timedelta(minutes=self.expire_minutes):
                    expired.append(k)
            except:
                expired.append(k)
        for k in expired:
            del self.cache[k]

    def _generate_key(self, otp_data):
        return f"{otp_data.get('otp','')}_{otp_data.get('phone','')}_{otp_data.get('service','')}"

    def is_duplicate(self, otp_data):
        self._cleanup_expired()
        return self._generate_key(otp_data) in self.cache

    def add_otp(self, otp_data):
        key = self._generate_key(otp_data)
        self.cache[key] = {'timestamp': datetime.now().isoformat()}
        self._save_cache()

    def filter_new_otps(self, otp_list):
        new_otps = []
        for otp in otp_list:
            if not self.is_duplicate(otp):
                new_otps.append(otp)
                self.add_otp(otp)
        return new_otps

    def get_cache_stats(self):
        self._cleanup_expired()
        return {'total_cached': len(self.cache)}

otp_filter = OTPFilter()