use openkoto_desktop_lib::commands::build_due_vocabulary_queue;
use openkoto_desktop_lib::types::FavoriteVocabulary;

fn make_vocab(
    id: &str,
    state: &str,
    due_date: &str,
    last_reviewed_at: Option<&str>,
    pack_ids: Vec<&str>,
) -> FavoriteVocabulary {
    FavoriteVocabulary {
        id: id.to_string(),
        word: format!("word-{}", id),
        meaning: "meaning".to_string(),
        usage: "usage".to_string(),
        explanation: None,
        example: None,
        reading: None,
        source_article_id: None,
        source_article_title: None,
        pack_ids: pack_ids.into_iter().map(|s| s.to_string()).collect(),
        srs_state: state.to_string(),
        ease_factor: 2.5,
        repetitions: 0,
        interval_days: 0,
        due_date: due_date.to_string(),
        last_reviewed_at: last_reviewed_at.map(|s| s.to_string()),
        review_count: 0,
        created_at: "2026-02-16T00:00:00Z".to_string(),
    }
}

#[test]
fn queue_prioritizes_new_learning_before_review() {
    let all = vec![
        make_vocab(
            "a",
            "review",
            "2026-02-16",
            Some("2026-02-15T10:00:00Z"),
            vec!["p1"],
        ),
        make_vocab("b", "new", "2026-02-16", None, vec!["p1"]),
    ];

    let queue = build_due_vocabulary_queue(all, "p1", "2026-02-16", 20, 100).unwrap();
    assert_eq!(queue.len(), 2);
    assert_eq!(queue[0].id, "b");
    assert_eq!(queue[1].id, "a");
}

#[test]
fn queue_applies_daily_limits() {
    let all = vec![
        make_vocab("n1", "new", "2026-02-16", None, vec!["p1"]),
        make_vocab("n2", "learning", "2026-02-16", None, vec!["p1"]),
        make_vocab(
            "r1",
            "review",
            "2026-02-16",
            Some("2026-02-14T10:00:00Z"),
            vec!["p1"],
        ),
        make_vocab(
            "r2",
            "review",
            "2026-02-16",
            Some("2026-02-15T10:00:00Z"),
            vec!["p1"],
        ),
    ];

    let queue = build_due_vocabulary_queue(all, "p1", "2026-02-16", 1, 1).unwrap();
    assert_eq!(queue.len(), 2);
    assert_eq!(queue[0].id, "n1");
    assert_eq!(queue[1].id, "r1");
}

#[test]
fn queue_filters_pack_and_due_date() {
    let all = vec![
        make_vocab("a", "new", "2026-02-17", None, vec!["p1"]),
        make_vocab("b", "new", "2026-02-16", None, vec!["p2"]),
        make_vocab("c", "new", "2026-02-16", None, vec!["p1"]),
    ];

    let queue = build_due_vocabulary_queue(all, "p1", "2026-02-16", 20, 100).unwrap();
    assert_eq!(queue.len(), 1);
    assert_eq!(queue[0].id, "c");
}
