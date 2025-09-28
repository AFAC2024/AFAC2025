from abc import abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field

from src.agent.base import BaseAgent
from src.logger import logger


class BaseEnvironment(BaseModel):
    """Base environment class for all environments"""

    name: str = Field(default="base_environment")
    description: str = Field(default="Base environment class")
    agents: Dict[str, BaseAgent] = Field(default_factory=dict)
    max_steps: int = Field(default=3, description="Maximum steps for each agent")

    class Config:
        arbitrary_types_allowed = True

    @classmethod
    async def create(cls, **kwargs) -> "BaseEnvironment":
        """Factory method to create and initialize an environment"""
        instance = cls(**kwargs)
        await instance.initialize()
        return instance

    async def initialize(self) -> None:
        """Initialize the environment. Override in subclasses."""
        logger.info(f"Initializing {self.name} environment (max_steps={self.max_steps})")

    def register_agent(self, agent: BaseAgent) -> None:
        """Register an agent with the environment"""
        self.agents[agent.name] = agent
        logger.debug(f"Agent {agent.name} registered in {self.name}")

    # Alias for register_agent for better API flexibility
    def add_agent(self, agent: BaseAgent) -> None:
        """Alias for register_agent"""
        self.register_agent(agent)

    def get_agent(self, agent_name: str) -> Optional[BaseAgent]:
        """Get an agent by name"""
        return self.agents.get(agent_name)

    @abstractmethod
    async def run(self, **kwargs) -> Dict[str, Any]:
        """Run the environment. Override in subclasses."""
        raise NotImplementedError("Subclasses must implement run method")

    async def cleanup(self) -> None:
        """Clean up resources when done"""
        logger.info(f"Cleaning up {self.name} environment")


class EnvironmentType(str, Enum):
    """Enum of available environment types"""

    RESEARCH = "research"
    BATTLE = "battle"


class EnvironmentFactory:
    """Factory for creating different types of environments with support for multiple agents"""

    @staticmethod
    async def create_environment(
        environment_type: EnvironmentType,
        agents: Union[BaseAgent, List[BaseAgent], Dict[str, BaseAgent]] = None,
        **kwargs,
    ) -> BaseEnvironment:
        """Create and initialize an environment of the specified type

        Args:
            environment_type: The type of environment to create
            agents: One or more agents to add to the environment
            **kwargs: Additional arguments to pass to the environment constructor

        Returns:
            An initialized environment instance
        """
        from src.environment.battle import BattleEnvironment
        from src.environment.research import ResearchEnvironment

        environments = {
            EnvironmentType.RESEARCH: ResearchEnvironment,
            EnvironmentType.BATTLE: BattleEnvironment,
        }

        environment_class = environments.get(environment_type)
        if not environment_class:
            raise ValueError(f"Unknown environment type: {environment_type}")

        # Create the environment
        environment = await environment_class.create(**kwargs)

        # Add agents if provided
        if agents:
            if isinstance(agents, BaseAgent):
                environment.add_agent(agents)
            elif isinstance(agents, list):
                for agent in agents:
                    environment.add_agent(agent)
            elif isinstance(agents, dict):
                for agent in agents.values():
                    environment.add_agent(agent)

        return environment
