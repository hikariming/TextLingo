use openkoto_desktop_lib::types::WordPack;

#[test]
fn word_pack_roundtrip_serialization() {
    let pack = WordPack {
        id: "pack-1".to_string(),
        name: "TOEFL 500".to_string(),
        description: Some("Core words".to_string()),
        cover_url: Some("https://example.com/cover.png".to_string()),
        author: Some("OpenKoto".to_string()),
        language_from: Some("en".to_string()),
        language_to: Some("zh-CN".to_string()),
        tags: vec!["toefl".to_string(), "exam".to_string()],
        version: Some("1.0.0".to_string()),
        created_at: "2026-02-16T00:00:00Z".to_string(),
        updated_at: "2026-02-16T00:00:00Z".to_string(),
        is_system: false,
    };

    let json = serde_json::to_string(&pack).unwrap();
    let restored: WordPack = serde_json::from_str(&json).unwrap();

    assert_eq!(restored.id, "pack-1");
    assert_eq!(restored.name, "TOEFL 500");
    assert_eq!(restored.tags.len(), 2);
    assert!(!restored.is_system);
}

#[test]
fn system_flag_defaults_to_false() {
    let json = r#"{
      "id":"pack-x",
      "name":"Pack X",
      "created_at":"2026-02-16T00:00:00Z",
      "updated_at":"2026-02-16T00:00:00Z"
    }"#;

    let pack: WordPack = serde_json::from_str(json).unwrap();
    assert!(!pack.is_system);
}
