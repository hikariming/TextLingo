use openkoto_desktop_lib::types::FavoriteVocabulary;

#[test]
fn old_favorite_vocabulary_json_deserializes_with_defaults() {
    let old_json = r#"{
      "id":"old-1",
      "word":"apple",
      "meaning":"苹果",
      "usage":"n.",
      "example":null,
      "reading":null,
      "source_article_id":null,
      "source_article_title":null,
      "created_at":"2026-02-16T00:00:00Z"
    }"#;

    let vocab: FavoriteVocabulary = serde_json::from_str(old_json).unwrap();
    assert_eq!(vocab.word, "apple");
    assert!(vocab.pack_ids.is_empty());
    assert_eq!(vocab.srs_state, "new");
    assert!(vocab.ease_factor >= 2.5);
    assert_eq!(vocab.repetitions, 0);
    assert_eq!(vocab.interval_days, 0);
    assert!(!vocab.due_date.is_empty());
    assert_eq!(vocab.review_count, 0);
}
