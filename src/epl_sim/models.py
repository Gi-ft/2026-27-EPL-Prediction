from dataclasses import dataclass


@dataclass(frozen=True)
class TeamRating:
    name: str
    attack: float
    defense: float
    home_advantage: float = 0.0


@dataclass
class TableRow:
    team: str
    played: int = 0
    wins: int = 0
    draws: int = 0
    losses: int = 0
    goals_for: int = 0
    goals_against: int = 0

    @property
    def goal_difference(self) -> int:
        return self.goals_for - self.goals_against

    @property
    def points(self) -> int:
        return self.wins * 3 + self.draws


@dataclass
class SeasonResult:
    team: str
    simulations: int = 0
    titles: int = 0
    top_four: int = 0
    relegations: int = 0

    @property
    def title_probability(self) -> float:
        return self.titles / self.simulations if self.simulations else 0.0

    @property
    def top_four_probability(self) -> float:
        return self.top_four / self.simulations if self.simulations else 0.0

    @property
    def relegation_probability(self) -> float:
        return self.relegations / self.simulations if self.simulations else 0.0
