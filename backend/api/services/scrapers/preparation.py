"""Common classification payload; no platform identity or official answers."""
class PreparationError(ValueError):
    pass


INPUT_FIELDS = frozenset(("description", "input_format", "output_format", "time_limit", "memory_limit", "notes", "testcases", "constraints", "images"))


def prepare_input(statement: dict, *, strict: bool = False) -> dict:
    prepared = {key: statement[key] for key in sorted(INPUT_FIELDS) if key in statement}
    for key in (("description", "input_format", "output_format", "time_limit", "memory_limit") if strict else ("description", "input_format", "output_format")):
        if not isinstance(prepared.get(key), str) or not prepared[key].strip():
            raise PreparationError(f"Incomplete statement: {key}")
    if "notes" in prepared and not isinstance(prepared["notes"], str):
        raise PreparationError("Invalid statement: notes must be text")
    if "constraints" in prepared and not isinstance(prepared["constraints"], str):
        raise PreparationError("Invalid constraints")
    if "images" in prepared:
        images = prepared["images"]
        if not isinstance(images, list) or any(not isinstance(i, dict) or
                not isinstance(i.get("url"), str) or not isinstance(i.get("alt"), str) or
                type(i.get("position")) is not int for i in images):
            raise PreparationError("Invalid images")
        prepared["images"] = [{k: i[k] for k in ("url", "alt", "position")} for i in images]
    if not strict and "testcases" not in prepared:
        return prepared
    samples = prepared.get("testcases")
    if not isinstance(samples, list) or (strict and not samples):
        raise PreparationError("Missing samples")
    prepared["testcases"] = []
    for sample in samples:
        if not isinstance(sample, dict) or any(not isinstance(sample.get(k), str) or (strict and not sample[k].strip()) for k in ("input", "output")):
            raise PreparationError("Invalid sample")
        prepared["testcases"].append({k: sample[k] for k in ("input", "output")})
    return prepared
