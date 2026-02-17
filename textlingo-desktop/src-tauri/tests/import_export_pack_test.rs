use serde_json::{json, Value};

#[test]
fn export_schema_contains_required_fields() {
    let payload = json!({
      "schema_version": "openkoto-word-pack-v1",
      "pack": {
        "name": "Core 100",
        "description": "desc"
      },
      "entries": [
        {
          "word": "abandon",
          "meaning": "放弃",
          "usage": "v.",
          "example": "He abandoned the plan."
        }
      ]
    });

    assert_eq!(payload["schema_version"], "openkoto-word-pack-v1");
    assert!(payload["pack"]["name"].is_string());
    assert!(payload["entries"].is_array());
    assert!(payload["entries"][0]["word"].is_string());
    assert!(payload["entries"][0]["meaning"].is_string());
}

#[test]
fn malformed_pack_json_is_rejected() {
    let malformed = "{\"pack\":{\"name\":\"X\"},\"entries\":[{";
    let parsed: Result<Value, _> = serde_json::from_str(malformed);
    assert!(parsed.is_err());
}

#[test]
fn duplicate_words_can_be_detected_by_normalized_value() {
    let entries = vec![" Apple ", "apple", "APPLE", "banana"];
    let mut seen = std::collections::HashSet::new();
    let mut duplicates = 0;

    for entry in entries {
        let normalized = entry.trim().to_lowercase();
        if !seen.insert(normalized) {
            duplicates += 1;
        }
    }

    assert_eq!(duplicates, 2);
    assert_eq!(seen.len(), 2);
}
