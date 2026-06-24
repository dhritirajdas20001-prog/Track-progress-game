import os
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from datetime import datetime, timedelta
from sqlalchemy import create_engine, Column, Integer, String, Boolean, ForeignKey, DateTime, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel, Field

# SQLite Database setup
DATABASE_URL = "sqlite:///./game.db"

engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- SQLALCHEMY MODELS ---

VALID_STATS = ("strength", "stamina", "intelligence", "agility", "vitality", "dexterity", "faith", "luck")
VALID_SCALING_GRADES = ("S", "A", "B", "C")
VALID_SLOT_TYPES = ("Weapon", "Armor", "Artifact", "Accessory")
EQUIPMENT_SLOTS = {
    "Weapon": "equipped_weapon_id",
    "Armor": "equipped_armor_id",
    "Artifact": "equipped_artifact_id",
    "Accessory": "equipped_accessory_id",
}


class ItemModel(Base):
    __tablename__ = "items"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    slot_type = Column(String, nullable=False)
    governing_stat = Column(String, nullable=False)
    stat_requirement = Column(Integer, default=1, nullable=False)
    scaling_grade = Column(String, nullable=False)
    passive_effect = Column(String, nullable=True)


class PlayerModel(Base):
    __tablename__ = "players"

    id = Column(Integer, primary_key=True, index=True)
    level = Column(Integer, default=1, nullable=False)
    current_xp = Column(Integer, default=0, nullable=False)
    gold = Column(Integer, default=0, nullable=False)
    equipped_weapon_id = Column(Integer, ForeignKey("items.id"), nullable=True)
    equipped_armor_id = Column(Integer, ForeignKey("items.id"), nullable=True)
    equipped_artifact_id = Column(Integer, ForeignKey("items.id"), nullable=True)
    equipped_accessory_id = Column(Integer, ForeignKey("items.id"), nullable=True)

    strength_level = Column(Integer, default=1, nullable=False)
    strength_xp = Column(Integer, default=0, nullable=False)
    stamina_level = Column(Integer, default=1, nullable=False)
    stamina_xp = Column(Integer, default=0, nullable=False)
    intelligence_level = Column(Integer, default=1, nullable=False)
    intelligence_xp = Column(Integer, default=0, nullable=False)
    agility_level = Column(Integer, default=1, nullable=False)
    agility_xp = Column(Integer, default=0, nullable=False)
    vitality_level = Column(Integer, default=1, nullable=False)
    vitality_xp = Column(Integer, default=0, nullable=False)
    dexterity_level = Column(Integer, default=1, nullable=False)
    dexterity_xp = Column(Integer, default=0, nullable=False)
    faith_level = Column(Integer, default=1, nullable=False)
    faith_xp = Column(Integer, default=0, nullable=False)
    luck_level = Column(Integer, default=1, nullable=False)
    luck_xp = Column(Integer, default=0, nullable=False)


class TaskModel(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True, nullable=False)
    task_type = Column(String, nullable=False)  # "daily" or "quest"
    xp_reward = Column(Integer, default=10, nullable=False)
    gold_reward = Column(Integer, default=5, nullable=False)
    stat_reward_type = Column(String, nullable=True)
    stat_xp_reward = Column(Integer, default=10, nullable=False)
    is_completed = Column(Boolean, default=False, nullable=False)


class RewardModel(Base):
    __tablename__ = "rewards"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    gold_cost = Column(Integer, nullable=False)


class ActivityLogModel(Base):
    __tablename__ = "activity_log"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    task_name = Column(String, nullable=False)
    general_xp_gained = Column(Integer, default=0, nullable=False)
    gold_gained = Column(Integer, default=0, nullable=False)
    stat_type = Column(String, nullable=True)
    stat_xp_gained = Column(Integer, default=0, nullable=False)


# Create tables
Base.metadata.create_all(bind=engine)

# --- PYDANTIC SCHEMAS ---

class StatSchema(BaseModel):
    level: int = 1
    xp: int = 0
    xp_current_level: int = 0
    xp_next_level: int = 100


class ItemSchema(BaseModel):
    id: int
    name: str
    slot_type: str
    governing_stat: str
    stat_requirement: int
    scaling_grade: str
    passive_effect: Optional[str] = None

    class Config:
        from_attributes = True


class LoadoutSchema(BaseModel):
    weapon: Optional[ItemSchema] = None
    armor: Optional[ItemSchema] = None
    artifact: Optional[ItemSchema] = None
    accessory: Optional[ItemSchema] = None


class PlayerSchema(BaseModel):
    id: int
    level: int
    current_xp: int
    gold: int
    xp_current_level: int = 0
    xp_next_level: int = 100
    stats: dict[str, StatSchema] = {}
    loadout: LoadoutSchema = LoadoutSchema()

    class Config:
        from_attributes = True


class TaskCreateSchema(BaseModel):
    title: str = Field(..., min_length=1)
    task_type: str = Field(..., pattern="^(daily|quest)$")
    xp_reward: int = Field(default=10, ge=0)
    gold_reward: int = Field(default=5, ge=0)
    stat_reward_type: Optional[str] = None
    stat_xp_reward: int = Field(default=10, ge=0)


class TaskUpdateSchema(BaseModel):
    title: Optional[str] = Field(None, min_length=1)
    task_type: Optional[str] = Field(None, pattern="^(daily|quest)$")
    xp_reward: Optional[int] = Field(None, ge=0)
    gold_reward: Optional[int] = Field(None, ge=0)
    stat_reward_type: Optional[str] = None
    stat_xp_reward: Optional[int] = Field(None, ge=0)
    is_completed: Optional[bool] = None


class TaskSchema(BaseModel):
    id: int
    title: str
    task_type: str
    xp_reward: int
    gold_reward: int
    stat_reward_type: Optional[str] = None
    stat_xp_reward: int = 10
    is_completed: bool

    class Config:
        from_attributes = True


class LevelUpEvent(BaseModel):
    name: str
    old_level: int
    new_level: int


class TaskCompleteResponse(BaseModel):
    player: PlayerSchema
    level_ups: list[LevelUpEvent] = []
    weapon_multiplier: float = 1.0


class RewardCreateSchema(BaseModel):
    name: str = Field(..., min_length=1)
    gold_cost: int = Field(..., gt=0)


class RewardSchema(BaseModel):
    id: int
    name: str
    gold_cost: int

    class Config:
        from_attributes = True


# --- FASTAPI APP ---

app = FastAPI(
    title="Gamified Life API",
    description="A minimalist, high-performance API to gamify tasks and rewards.",
    version="1.0.0"
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Dependency to get db session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Helper function to get or create the default player (ID=1)
def get_or_create_default_player(db: Session) -> PlayerModel:
    player = db.query(PlayerModel).filter(PlayerModel.id == 1).first()
    if not player:
        player = PlayerModel(id=1, level=1, current_xp=0, gold=0)
        db.add(player)
        db.commit()
        db.refresh(player)
    return player


def xp_required_for_level(level: int) -> int:
    """Total cumulative XP needed to reach `level`. Formula: 100 * level^1.5"""
    if level <= 1:
        return 0
    return int(100 * (level ** 1.5))


SCALING_FACTORS = {"S": 0.03, "A": 0.02, "B": 0.015, "C": 0.01}


def compute_weapon_multiplier(player_stat_level: int, stat_requirement: int, scaling_grade: str) -> float:
    if player_stat_level < stat_requirement:
        return 0.5
    grade_factor = SCALING_FACTORS.get(scaling_grade, 0.01)
    return 1.0 + (player_stat_level - stat_requirement) * grade_factor


def check_level_up(current_xp: int, current_level: int) -> tuple[int, int, bool]:
    """Pure function. Returns (new_level, new_xp, leveled_up).
    XP is cumulative — never reset. Level advances when total XP
    crosses the next threshold."""
    new_level = current_level
    while current_xp >= xp_required_for_level(new_level + 1):
        new_level += 1
    return new_level, current_xp, new_level > current_level


# --- ENDPOINTS ---

# Player Stats
def player_to_schema(player: PlayerModel, db: Session) -> PlayerSchema:
    stats = {}
    for stat in VALID_STATS:
        lvl = getattr(player, f"{stat}_level")
        xp = getattr(player, f"{stat}_xp")
        stats[stat] = StatSchema(
            level=lvl,
            xp=xp,
            xp_current_level=xp_required_for_level(lvl),
            xp_next_level=xp_required_for_level(lvl + 1),
        )

    loadout_data = {}
    for slot_name, col_name in EQUIPMENT_SLOTS.items():
        item_id = getattr(player, col_name)
        if item_id:
            item = db.query(ItemModel).filter(ItemModel.id == item_id).first()
            loadout_data[slot_name.lower()] = item
    loadout = LoadoutSchema(**loadout_data)

    return PlayerSchema(
        id=player.id,
        level=player.level,
        current_xp=player.current_xp,
        gold=player.gold,
        xp_current_level=xp_required_for_level(player.level),
        xp_next_level=xp_required_for_level(player.level + 1),
        stats=stats,
        loadout=loadout,
    )


@app.get("/api/player", response_model=PlayerSchema)
def get_player(db: Session = Depends(get_db)):
    return player_to_schema(get_or_create_default_player(db), db)


# Task CRUD & Complete

@app.get("/api/tasks", response_model=List[TaskSchema])
def get_tasks(db: Session = Depends(get_db)):
    return db.query(TaskModel).all()


@app.post("/api/tasks", response_model=TaskSchema, status_code=status.HTTP_201_CREATED)
def create_task(task_data: TaskCreateSchema, db: Session = Depends(get_db)):
    if task_data.stat_reward_type and task_data.stat_reward_type not in VALID_STATS:
        raise HTTPException(status_code=422, detail=f"stat_reward_type must be one of: {', '.join(VALID_STATS)}")
    db_task = TaskModel(
        title=task_data.title,
        task_type=task_data.task_type,
        xp_reward=task_data.xp_reward,
        gold_reward=task_data.gold_reward,
        stat_reward_type=task_data.stat_reward_type,
        stat_xp_reward=task_data.stat_xp_reward,
        is_completed=False,
    )
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task


@app.put("/api/tasks/{task_id}", response_model=TaskSchema)
def update_task(task_id: int, task_data: TaskUpdateSchema, db: Session = Depends(get_db)):
    db_task = db.query(TaskModel).filter(TaskModel.id == task_id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    for key, value in task_data.model_dump(exclude_unset=True).items():
        setattr(db_task, key, value)
        
    db.commit()
    db.refresh(db_task)
    return db_task


@app.delete("/api/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: int, db: Session = Depends(get_db)):
    db_task = db.query(TaskModel).filter(TaskModel.id == task_id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
    db.delete(db_task)
    db.commit()
    return None


@app.post("/api/tasks/{task_id}/complete", response_model=TaskCompleteResponse)
def complete_task(task_id: int, db: Session = Depends(get_db)):
    db_task = db.query(TaskModel).filter(TaskModel.id == task_id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")

    if db_task.is_completed:
        raise HTTPException(status_code=400, detail="Task is already completed")

    db_task.is_completed = True
    player = get_or_create_default_player(db)
    level_ups: list[LevelUpEvent] = []

    multiplier = 1.0
    if player.equipped_weapon_id:
        weapon = db.query(ItemModel).filter(ItemModel.id == player.equipped_weapon_id).first()
        if weapon:
            stat_level = getattr(player, f"{weapon.governing_stat}_level", 0)
            multiplier = compute_weapon_multiplier(stat_level, weapon.stat_requirement, weapon.scaling_grade)

    effective_xp = round(db_task.xp_reward * multiplier)
    effective_gold = round(db_task.gold_reward * multiplier)

    old_level = player.level
    player.current_xp += effective_xp
    player.gold += effective_gold
    player.level, player.current_xp, leveled = check_level_up(player.current_xp, player.level)
    if leveled:
        level_ups.append(LevelUpEvent(name="character", old_level=old_level, new_level=player.level))

    stat_type_logged = None
    stat_xp_logged = 0
    if db_task.stat_reward_type and db_task.stat_reward_type in VALID_STATS:
        stat = db_task.stat_reward_type
        stat_type_logged = stat
        stat_xp_logged = db_task.stat_xp_reward
        old_stat_level = getattr(player, f"{stat}_level")
        new_xp = getattr(player, f"{stat}_xp") + db_task.stat_xp_reward
        new_stat_level, new_xp, stat_leveled = check_level_up(new_xp, old_stat_level)
        setattr(player, f"{stat}_xp", new_xp)
        setattr(player, f"{stat}_level", new_stat_level)
        if stat_leveled:
            level_ups.append(LevelUpEvent(name=stat, old_level=old_stat_level, new_level=new_stat_level))

    db.add(ActivityLogModel(
        task_name=db_task.title,
        general_xp_gained=effective_xp,
        gold_gained=effective_gold,
        stat_type=stat_type_logged,
        stat_xp_gained=stat_xp_logged,
    ))

    db.commit()
    db.refresh(player)
    return TaskCompleteResponse(player=player_to_schema(player, db), level_ups=level_ups, weapon_multiplier=multiplier)


# Reward List, Create, Delete & Purchase

@app.get("/api/rewards", response_model=List[RewardSchema])
def get_rewards(db: Session = Depends(get_db)):
    return db.query(RewardModel).all()


@app.post("/api/rewards", response_model=RewardSchema, status_code=status.HTTP_201_CREATED)
def create_reward(reward_data: RewardCreateSchema, db: Session = Depends(get_db)):
    db_reward = RewardModel(
        name=reward_data.name,
        gold_cost=reward_data.gold_cost
    )
    db.add(db_reward)
    db.commit()
    db.refresh(db_reward)
    return db_reward


@app.delete("/api/rewards/{reward_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_reward(reward_id: int, db: Session = Depends(get_db)):
    db_reward = db.query(RewardModel).filter(RewardModel.id == reward_id).first()
    if not db_reward:
        raise HTTPException(status_code=404, detail="Reward not found")
    db.delete(db_reward)
    db.commit()
    return None


@app.post("/api/rewards/{reward_id}/purchase", response_model=PlayerSchema)
def purchase_reward(reward_id: int, db: Session = Depends(get_db)):
    db_reward = db.query(RewardModel).filter(RewardModel.id == reward_id).first()
    if not db_reward:
        raise HTTPException(status_code=404, detail="Reward not found")
        
    player = get_or_create_default_player(db)
    if player.gold < db_reward.gold_cost:
        raise HTTPException(status_code=400, detail="Insufficient gold to purchase this reward")
        
    player.gold -= db_reward.gold_cost
    db.commit()
    db.refresh(player)
    return player_to_schema(player, db)


# --- ANALYTICS ---

@app.get("/api/analytics/history")
def get_history(db: Session = Depends(get_db)):
    cutoff = datetime.utcnow() - timedelta(days=30)
    logs = (
        db.query(ActivityLogModel)
        .filter(ActivityLogModel.timestamp >= cutoff)
        .order_by(ActivityLogModel.timestamp)
        .all()
    )

    buckets: dict[str, dict] = {}
    for log in logs:
        day = log.timestamp.strftime("%Y-%m-%d")
        if day not in buckets:
            buckets[day] = {"date": day, "general_xp": 0, "gold": 0}
            for s in VALID_STATS:
                buckets[day][s] = 0
        buckets[day]["general_xp"] += log.general_xp_gained
        buckets[day]["gold"] += log.gold_gained
        if log.stat_type and log.stat_type in VALID_STATS:
            buckets[day][log.stat_type] += log.stat_xp_gained

    return sorted(buckets.values(), key=lambda d: d["date"])


# --- ITEM & LOADOUT ENDPOINTS ---

@app.get("/api/items", response_model=List[ItemSchema])
def get_items(db: Session = Depends(get_db)):
    return db.query(ItemModel).all()


@app.get("/api/items/{slot_type}", response_model=List[ItemSchema])
def get_items_by_slot(slot_type: str, db: Session = Depends(get_db)):
    if slot_type not in VALID_SLOT_TYPES:
        raise HTTPException(status_code=422, detail=f"slot_type must be one of: {', '.join(VALID_SLOT_TYPES)}")
    return db.query(ItemModel).filter(ItemModel.slot_type == slot_type).all()


@app.get("/api/loadout", response_model=LoadoutSchema)
def get_loadout(db: Session = Depends(get_db)):
    player = get_or_create_default_player(db)
    loadout_data = {}
    for slot_name, col_name in EQUIPMENT_SLOTS.items():
        item_id = getattr(player, col_name)
        if item_id:
            loadout_data[slot_name.lower()] = db.query(ItemModel).filter(ItemModel.id == item_id).first()
    return LoadoutSchema(**loadout_data)


@app.patch("/api/loadout/{slot_type}", response_model=PlayerSchema)
def equip_item(slot_type: str, item_id: int, db: Session = Depends(get_db)):
    if slot_type not in VALID_SLOT_TYPES:
        raise HTTPException(status_code=422, detail=f"slot_type must be one of: {', '.join(VALID_SLOT_TYPES)}")

    item = db.query(ItemModel).filter(ItemModel.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    if item.slot_type != slot_type:
        raise HTTPException(status_code=400, detail=f"Item '{item.name}' is a {item.slot_type}, not a {slot_type}")

    player = get_or_create_default_player(db)
    stat_level = getattr(player, f"{item.governing_stat}_level", 0)
    if stat_level < item.stat_requirement:
        raise HTTPException(
            status_code=400,
            detail=f"Requires {item.governing_stat} level {item.stat_requirement} (you have {stat_level})",
        )

    col_name = EQUIPMENT_SLOTS[slot_type]
    setattr(player, col_name, item.id)
    db.commit()
    db.refresh(player)
    return player_to_schema(player, db)


@app.delete("/api/loadout/{slot_type}", response_model=PlayerSchema)
def unequip_slot(slot_type: str, db: Session = Depends(get_db)):
    if slot_type not in VALID_SLOT_TYPES:
        raise HTTPException(status_code=422, detail=f"slot_type must be one of: {', '.join(VALID_SLOT_TYPES)}")

    player = get_or_create_default_player(db)
    col_name = EQUIPMENT_SLOTS[slot_type]
    setattr(player, col_name, None)
    db.commit()
    db.refresh(player)
    return player_to_schema(player, db)


# Mount static files at root
app.mount("/", StaticFiles(directory="static", html=True), name="static")

