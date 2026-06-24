import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from main import app, Base, get_db, xp_required_for_level, ItemModel, PlayerModel

# --- IN-MEMORY TEST DATABASE ---

test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSession = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def reset_db():
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    yield


client = TestClient(app)


# --- HELPERS ---

def create_task(title="Test Task", xp=100, gold=50, stat=None, stat_xp=20):
    payload = {
        "title": title,
        "task_type": "daily",
        "xp_reward": xp,
        "gold_reward": gold,
        "stat_reward_type": stat,
        "stat_xp_reward": stat_xp,
    }
    res = client.post("/api/tasks", json=payload)
    assert res.status_code == 201
    return res.json()["id"]


def complete(task_id):
    res = client.post(f"/api/tasks/{task_id}/complete")
    assert res.status_code == 200
    return res.json()


def seed_weapon(name, stat, requirement, grade):
    db = TestSession()
    w = ItemModel(name=name, slot_type="Weapon", governing_stat=stat, stat_requirement=requirement, scaling_grade=grade)
    db.add(w)
    db.commit()
    db.refresh(w)
    wid = w.id
    db.close()
    return wid


def set_player_stat(stat, level, xp=0):
    db = TestSession()
    player = db.query(PlayerModel).filter(PlayerModel.id == 1).first()
    if not player:
        player = PlayerModel(id=1)
        db.add(player)
        db.commit()
        db.refresh(player)
    setattr(player, f"{stat}_level", level)
    setattr(player, f"{stat}_xp", xp)
    db.commit()
    db.close()


def equip_weapon_direct(weapon_id):
    db = TestSession()
    player = db.query(PlayerModel).filter(PlayerModel.id == 1).first()
    if not player:
        player = PlayerModel(id=1)
        db.add(player)
        db.commit()
        db.refresh(player)
    player.equipped_weapon_id = weapon_id
    db.commit()
    db.close()


# --- TEST: XP & STAT XP ACCURACY ---

class TestTaskCompletion:
    def test_general_xp_and_gold_added_exactly(self):
        tid = create_task(xp=42, gold=17)
        data = complete(tid)
        p = data["player"]
        assert p["current_xp"] == 42
        assert p["gold"] == 17

    def test_stat_xp_added_exactly(self):
        tid = create_task(xp=10, gold=5, stat="strength", stat_xp=25)
        data = complete(tid)
        p = data["player"]
        assert p["stats"]["strength"]["xp"] == 25

    def test_stat_xp_unaffected_by_weapon_multiplier(self):
        wid = seed_weapon("Pen", "intelligence", 1, "S")
        set_player_stat("intelligence", 10)
        equip_weapon_direct(wid)
        tid = create_task(xp=100, gold=50, stat="strength", stat_xp=30)
        data = complete(tid)
        assert data["weapon_multiplier"] > 1.0
        assert data["player"]["stats"]["strength"]["xp"] == 30

    def test_completing_already_done_returns_400(self):
        tid = create_task()
        complete(tid)
        res = client.post(f"/api/tasks/{tid}/complete")
        assert res.status_code == 400


# --- TEST: LEVEL-UP MATH ---

class TestLevelUp:
    def test_no_level_up_below_threshold(self):
        threshold = xp_required_for_level(2)
        tid = create_task(xp=threshold - 1, gold=0)
        data = complete(tid)
        assert data["player"]["level"] == 1
        assert data["level_ups"] == []

    def test_level_up_at_exact_threshold(self):
        threshold = xp_required_for_level(2)
        tid = create_task(xp=threshold, gold=0)
        data = complete(tid)
        assert data["player"]["level"] == 2
        assert len(data["level_ups"]) == 1
        assert data["level_ups"][0]["name"] == "character"
        assert data["level_ups"][0]["old_level"] == 1
        assert data["level_ups"][0]["new_level"] == 2

    def test_multi_level_up(self):
        threshold_lvl5 = xp_required_for_level(5)
        tid = create_task(xp=threshold_lvl5, gold=0)
        data = complete(tid)
        assert data["player"]["level"] >= 5

    def test_stat_level_up(self):
        threshold = xp_required_for_level(2)
        tid = create_task(xp=0, gold=0, stat="dexterity", stat_xp=threshold)
        data = complete(tid)
        assert data["player"]["stats"]["dexterity"]["level"] == 2
        stat_ups = [lu for lu in data["level_ups"] if lu["name"] == "dexterity"]
        assert len(stat_ups) == 1


# --- TEST: WEAPON SCALING PENALTY ---

class TestWeaponScaling:
    def test_penalty_when_under_requirement(self):
        wid = seed_weapon("Arcane Rod", "intelligence", 30, "A")
        set_player_stat("intelligence", 10)
        equip_weapon_direct(wid)
        tid = create_task(xp=100, gold=50)
        data = complete(tid)
        assert data["weapon_multiplier"] == 0.5
        assert data["player"]["current_xp"] == 50
        assert data["player"]["gold"] == 25

    def test_no_penalty_when_meeting_requirement(self):
        wid = seed_weapon("Short Sword", "strength", 1, "C")
        set_player_stat("strength", 1)
        equip_weapon_direct(wid)
        tid = create_task(xp=100, gold=50)
        data = complete(tid)
        assert data["weapon_multiplier"] == 1.0
        assert data["player"]["current_xp"] == 100
        assert data["player"]["gold"] == 50

    def test_bonus_when_exceeding_requirement(self):
        wid = seed_weapon("Great Axe", "strength", 5, "A")
        set_player_stat("strength", 15)
        equip_weapon_direct(wid)
        tid = create_task(xp=100, gold=100)
        data = complete(tid)
        expected_mult = 1.0 + (15 - 5) * 0.02  # 1.20
        assert data["weapon_multiplier"] == pytest.approx(expected_mult)
        assert data["player"]["current_xp"] == round(100 * expected_mult)
        assert data["player"]["gold"] == round(100 * expected_mult)

    def test_no_weapon_means_1x(self):
        tid = create_task(xp=100, gold=50)
        data = complete(tid)
        assert data["weapon_multiplier"] == 1.0
        assert data["player"]["current_xp"] == 100
