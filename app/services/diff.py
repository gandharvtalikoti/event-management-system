from app.models.version import EventVersion

def diff_versions(v1: EventVersion, v2: EventVersion) -> dict:
    """
    Return a mapping of fields that differ between two versions.
    Format: { field_name: {"from": old, "to": new}, ... }
    """
    diffs = {}
    fields = ["title", "description", "start_time", "end_time", "location"]
    for f in fields:
        old = getattr(v1, f)
        new = getattr(v2, f)
        if old != new:
            diffs[f] = {"from": old, "to": new}
    return diffs
