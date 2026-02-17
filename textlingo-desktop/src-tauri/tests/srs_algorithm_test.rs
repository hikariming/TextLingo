use chrono::NaiveDate;
use openkoto_desktop_lib::commands::calculate_sm2_update;

#[test]
fn unknown_resets_card_to_learning() {
    let review_date = NaiveDate::from_ymd_opt(2026, 2, 16).unwrap();
    let next = calculate_sm2_update(5, 21, 2.6, "unknown", review_date).unwrap();

    assert_eq!(next.srs_state, "learning");
    assert_eq!(next.repetitions, 0);
    assert_eq!(next.interval_days, 1);
    assert_eq!(next.due_date, "2026-02-17");
}

#[test]
fn uncertain_promotes_first_review_step() {
    let review_date = NaiveDate::from_ymd_opt(2026, 2, 16).unwrap();
    let next = calculate_sm2_update(0, 0, 2.5, "uncertain", review_date).unwrap();

    assert_eq!(next.srs_state, "review");
    assert_eq!(next.repetitions, 1);
    assert_eq!(next.interval_days, 1);
    assert_eq!(next.due_date, "2026-02-17");
}

#[test]
fn known_second_step_sets_six_day_interval() {
    let review_date = NaiveDate::from_ymd_opt(2026, 2, 16).unwrap();
    let next = calculate_sm2_update(1, 1, 2.5, "known", review_date).unwrap();

    assert_eq!(next.srs_state, "review");
    assert_eq!(next.repetitions, 2);
    assert_eq!(next.interval_days, 6);
    assert_eq!(next.due_date, "2026-02-22");
}

#[test]
fn ease_factor_has_floor() {
    let review_date = NaiveDate::from_ymd_opt(2026, 2, 16).unwrap();
    let next = calculate_sm2_update(4, 20, 1.31, "unknown", review_date).unwrap();
    assert!(next.ease_factor >= 1.3);
}

#[test]
fn leap_year_date_rollover_is_valid() {
    let review_date = NaiveDate::from_ymd_opt(2024, 2, 28).unwrap();
    let next = calculate_sm2_update(1, 1, 2.5, "known", review_date).unwrap();
    assert_eq!(next.due_date, "2024-03-05");
}
