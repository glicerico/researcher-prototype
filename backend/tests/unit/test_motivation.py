from motivation import MotivationSystem, DriveConfig


def test_tick_increases_boredom():
    cfg = DriveConfig(boredom_rate=0.1, curiosity_decay=0, tiredness_decay=0, satisfaction_decay=0, threshold=1)
    m = MotivationSystem(cfg)
    m.last_tick -= 10
    m.tick()
    assert m.boredom > 0.9


def test_user_activity_changes_drives():
    m = MotivationSystem(DriveConfig())
    m.curiosity = 0.0
    m.boredom = 0.5
    m.on_user_activity()
    assert m.curiosity > 0
    assert m.boredom < 0.5


def test_should_research_threshold():
    cfg = DriveConfig(boredom_rate=0, curiosity_decay=0, tiredness_decay=0, satisfaction_decay=0, threshold=0.5)
    m = MotivationSystem(cfg)
    m.boredom = 0.3
    m.curiosity = 0.3
    assert m.should_research()
