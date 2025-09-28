import asyncio
import random
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict

from src.agent.base import BaseAgent
from src.agent.toolcall import ToolCallAgent
from src.schema import AgentState
from src.environment.base import BaseEnvironment
from src.logger import logger
from src.prompt.battle import (
    EVENT_TYPES,
    VOTE_OPTIONS,
    get_agent_instructions,
    get_broadcast_message,
    get_report_context,
)
from src.tool.base import BaseTool, ToolResult
from src.tool.battle import Battle
from src.tool.terminate import Terminate
from src.tool.tool_collection import ToolCollection


class BattleState(BaseModel):
    """Battle state tracking"""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    active_agents: Dict[str, str] = Field(default_factory=dict)
    agent_order: List[str] = Field(default_factory=list)  # 发言顺序
    voted_agents: Dict[str, str] = Field(default_factory=dict)
    terminated_agents: Dict[str, bool] = Field(default_factory=dict)
    battle_history: List[Dict[str, Any]] = Field(default_factory=list)
    debate_history: List[Dict[str, Any]] = Field(default_factory=list)  # 辩论历史
    vote_results: Dict[str, int] = Field(
        default_factory=lambda: {option: 0 for option in VOTE_OPTIONS}
    )
    battle_highlights: List[Dict[str, Any]] = Field(default_factory=list)
    battle_over: bool = Field(default=False)
    current_round: int = Field(default=0)  # 当前轮次
    current_speaker_index: int = Field(default=0)  # 当前发言者索引

    def is_agent_active(self, agent_id: str) -> bool:
        """Check if agent is active and can participate"""
        return (
            agent_id in self.active_agents
            and agent_id not in self.voted_agents
            and agent_id not in self.terminated_agents
        )

    def add_event(self, event_type: str, agent_id: str, **kwargs) -> Dict[str, Any]:
        """Add event to history and return the event"""
        event = {
            "type": event_type,
            "agent_id": agent_id,
            "agent_name": self.active_agents.get(agent_id, "Unknown"),
            **kwargs,
        }
        self.battle_history.append(event)
        return event

    def mark_terminated(self, agent_id: str, reason: str = "Unknown reason") -> None:
        """Mark agent as terminated"""
        self.terminated_agents[agent_id] = True

    def record_vote(self, agent_id: str, vote: str) -> None:
        """Record agent vote"""
        self.voted_agents[agent_id] = vote
        self.vote_results[vote] += 1

        # Check if battle is over
        if len(self.voted_agents) + len(self.terminated_agents) == len(
            self.active_agents
        ):
            self.battle_over = True

    def add_highlight(self, agent_name: str, content: str) -> None:
        """Add highlight if content is significant"""
        if len(content) > 20:  # Simple heuristic
            self.battle_highlights.append({"agent": agent_name, "point": content})

    def all_agents_decided(self) -> bool:
        """Check if all agents have voted or terminated"""
        return all(
            agent_id in self.voted_agents or agent_id in self.terminated_agents
            for agent_id in self.active_agents
        )


class BattleEnvironment(BaseEnvironment):
    """Environment for agents to battle and vote on stock sentiment"""

    name: str = Field(default="battle_environment")
    description: str = Field(default="Environment for stock market battles")
    state: BattleState = Field(default_factory=BattleState)
    tools: Dict[str, BaseTool] = Field(default_factory=dict)
    max_steps: int = Field(default=3, description="Maximum steps for each agent")
    debate_rounds: int = Field(default=2, description="Number of debate rounds")
    tool_calls: int = Field(default=0, description="Total number of tool calls")
    llm_calls: int = Field(default=0, description="Total number of LLM calls")

    async def initialize(self) -> None:
        """Initialize the battle environment"""
        await super().initialize()
        self.state = BattleState()
        logger.info(f"Battle environment initialized (max_steps={self.max_steps})")

    def register_agent(self, agent: BaseAgent) -> None:
        """Register an agent with battle tools and instructions"""
        super().register_agent(agent)
        agent_id = agent.name
        self.state.active_agents[agent_id] = agent.name
        
        # Record agent speaking order
        if agent_id not in self.state.agent_order:
            self.state.agent_order.append(agent_id)

        # Set max_steps for the agent
        if hasattr(agent, "max_steps"):
            agent.max_steps = self.max_steps

        if isinstance(agent, ToolCallAgent) and hasattr(agent, "available_tools"):
            battle_tool = Battle(agent_id=agent_id)
            battle_tool.controller = self
            self.tools[agent_id] = battle_tool
            agent.available_tools = ToolCollection(battle_tool, Terminate())

            # Add battle instructions while preserving research context
            agent_description = getattr(agent, "description", "")
            agent_instructions = get_agent_instructions(agent.name, agent_description)
            agent.update_memory("system", f"[Battle Environment] {agent_instructions}")
            
            logger.info(f"Agent {agent_id} registered for battle with preserved research context")

    async def run(self, report: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Run the battle environment with the given research report."""
        try:
            # Reset counters
            self.tool_calls = 0
            self.llm_calls = 0
            
            # Send initial context to all agents
            await self._send_initial_context(report)
            
            # Run structured debate
            await self._run_structured_debate()
            
            # Run final voting
            await self._run_final_voting()

            # Return results
            return self._prepare_results()
            
        except Exception as e:
            logger.error(f"Battle environment execution failed: {str(e)}")
            return None

    async def handle_speak(self, agent_id: str, content: str) -> ToolResult:
        """Handle agent speech during debate."""
        self.tool_calls += 1
        if not self.state.is_agent_active(agent_id):
            return ToolResult(error=self._get_error_message(agent_id))

        event = self.state.add_event(EVENT_TYPES["speak"], agent_id, content=content)
        self.state.add_highlight(event["agent_name"], content)
        await self._broadcast_message(agent_id, content, EVENT_TYPES["speak"])

        return ToolResult(output=f"Message sent: {content}")

    async def handle_vote(self, agent_id: str, vote: str) -> ToolResult:
        """Handle agent voting."""
        self.tool_calls += 1
        if not self.state.is_agent_active(agent_id):
            return ToolResult(error=self._get_error_message(agent_id))

        if vote not in VOTE_OPTIONS:
            return ToolResult(
                error=f"Invalid vote option. Must be one of: {', '.join(VOTE_OPTIONS)}"
            )

        self.state.record_vote(agent_id, vote)
        self.state.add_event(EVENT_TYPES["vote"], agent_id, vote=vote)
        await self._broadcast_message(agent_id, f"voted {vote}", EVENT_TYPES["vote"])

        return ToolResult(output=f"Vote recorded: {vote}")

    async def cleanup(self) -> None:
        """Clean up battle resources"""
        for tool in self.tools.values():
            tool.controller = None
        await super().cleanup()

    # Private helper methods
    def _get_error_message(self, agent_id: str) -> str:
        """Get appropriate error message for agent"""
        if agent_id not in self.state.active_agents:
            return f"Agent {agent_id} is not registered"
        return f"Agent {agent_id} has already {agent_id in self.state.voted_agents and 'voted' or 'terminated'}"

    async def _run_agent_steps(self) -> None:
        """Run steps for all active agents."""
        for agent_id, agent in self.agents.items():
            if not self.state.is_agent_active(agent_id):
                continue
                
            try:
                result = await agent.step()
                self.llm_calls += 1
                if isinstance(result, str) and result == AgentState.FINISHED:
                    self.state.mark_terminated(agent_id, "Agent finished")
                elif isinstance(result, BaseAgent):
                    if result.state == AgentState.FINISHED:
                        self.state.mark_terminated(agent_id, "Agent finished")
            except Exception as e:
                logger.error(f"Error running agent {agent_id} step: {str(e)}")
                self.state.mark_terminated(agent_id, str(e))

    async def _send_initial_context(self, report: Dict[str, Any]) -> None:
        """Send comprehensive research results to all agents."""
        # 构建完整的研究分析上下文
        context_parts = ["# 📊 完整研究阶段分析结果\n"]
        
        # 添加各专家的详细分析
        expert_analyses = {
            "sentiment": "🧠 市场情绪分析师",
            "risk": "🛡️ 风险控制专家", 
            "hot_money": "💰 游资分析师",
            "technical": "📈 技术分析师",
            "chip_analysis": "🔍 筹码分析师",
            "big_deal": "💹 大单分析师"
        }
        
        for analysis_key, expert_name in expert_analyses.items():
            if analysis_key in report:
                analysis_content = report[analysis_key]
                if analysis_content and str(analysis_content).strip():
                    context_parts.append(f"## {expert_name}分析结果:")
                    context_parts.append(f"{analysis_content}")
                    context_parts.append("")  # 空行分隔
        
        # 添加基本信息（如果有）
        if "basic_info" in report:
            context_parts.append("## 📋 股票基本信息:")
            context_parts.append(f"{report['basic_info']}")
            context_parts.append("")
        
        # 添加任务说明
        context_parts.append("## 🎯 辩论任务:")
        context_parts.append("请基于以上所有专家的分析结果，进行深度讨论并最终投票决定该股票是看涨(bullish)还是看跌(bearish)。")
        context_parts.append("你需要引用具体的分析数据来支持你的观点，并与其他专家进行充分讨论。")
        
        full_context = "\n".join(context_parts)
        
        # 发送给所有agents
        for agent_id, agent in self.agents.items():
            if isinstance(agent, ToolCallAgent):
                agent.update_memory("user", full_context)
                self.llm_calls += 1
                logger.info(f"Sent comprehensive research context to {agent_id}")

    async def _run_structured_debate(self) -> None:
        """Run structured debate rounds with cumulative context passing."""
        for round_num in range(self.debate_rounds):
            self.state.current_round = round_num + 1
            logger.info(f"🗣️ Starting debate round {round_num + 1}/{self.debate_rounds}")
            
            # Run debate round with each agent speaking once
            for speaker_index, agent_id in enumerate(self.state.agent_order):
                if not self.state.is_agent_active(agent_id):
                    continue
                    
                self.state.current_speaker_index = speaker_index
                
                logger.info(f"📢 {agent_id} turn to speak (#{speaker_index + 1})")
                
                # 为当前发言者提供辩论指导
                await self._send_debate_instruction(agent_id, speaker_index, round_num)
                
                # 执行单个专家的发言轮次 (限制步数为1)
                await self._run_single_agent_debate_turn(agent_id)
    
    async def _send_debate_instruction(self, current_agent_id: str, speaker_index: int, round_num: int) -> None:
        """Send specific debate instruction to current speaker."""
        # 构建前面发言的总结
        previous_speeches = []
        for event in self.state.battle_history:
            if event.get("type") == "speak":
                speaker_name = event.get("agent_name", "Unknown")
                content = event.get("content", "")
                if content:
                    previous_speeches.append(f"**{speaker_name}**: {content[:200]}...")
        
        # 构建辩论指导
        context_parts = [
            f"# 🎯 第{round_num}轮辩论发言 (你是第{speaker_index + 1}位发言者)",
            "",
            "**你的任务非常明确：**",
            "1. 立即使用Battle.speak发表你的观点（看涨或看跌）",
            "2. 引用研究阶段的具体数据支持你的立场", 
            "3. 回应前面专家的观点（支持或反驳）",
            "4. 如果是最后一轮，请立即投票（Battle.vote）",
            "",
            "⚠️ **严禁行为**：不要再做深度分析，直接基于已有数据发言！",
            ""
        ]
        
        if previous_speeches:
            context_parts.extend([
                "## 📋 前面专家的观点：",
                ""
            ])
            context_parts.extend(previous_speeches)
            context_parts.extend([
                "",
                "## 🗣️ 现在轮到你发言，请立即表态并说出理由！"
            ])
        else:
            context_parts.extend([
                "## 🗣️ 你是第一位发言者，请率先表明立场！",
                "直接说出你的观点：看涨还是看跌，并给出核心理由。"
            ])
        
        debate_instruction = "\n".join(context_parts)
        
        # 发送给当前发言的agent
        if current_agent_id in self.agents:
            agent = self.agents[current_agent_id]
            if isinstance(agent, ToolCallAgent):
                agent.update_memory("user", debate_instruction)
                self.llm_calls += 1
                logger.info(f"✉️ Sent debate instruction to {current_agent_id} (Round {round_num}, Speaker #{speaker_index + 1})")

    async def _run_single_agent_debate_turn(self, agent_id: str) -> None:
        """Run a single agent's debate turn with limited steps."""
        if agent_id not in self.agents:
            return
        
        agent = self.agents[agent_id]
        original_max_steps = agent.max_steps
        
        try:
            # 限制步数为1，强制专家快速发言
            agent.max_steps = 1
            agent.current_step = 0
            agent.state = AgentState.IDLE
            
            # 执行单步
            logger.info(f"🎤 {agent_id} speaking...")
            result = await agent.run(f"现在是你的发言时间，请立即使用Battle.speak表达观点！")
            logger.info(f"✅ {agent_id} completed speaking turn")
            
        except Exception as e:
            logger.error(f"❌ Error in {agent_id} debate turn: {str(e)}")
        finally:
            # 恢复原始设置
            agent.max_steps = original_max_steps

    async def _run_final_voting(self) -> None:
        """Run final voting phase."""
        logger.info("🗳️ Starting final voting phase")
        
        # 为每个尚未投票的专家发送投票指令
        for agent_id in self.state.agent_order:
            if not self.state.is_agent_active(agent_id):
                continue
                
            if agent_id in self.state.voted_agents:
                logger.info(f"✅ {agent_id} already voted: {self.state.voted_agents[agent_id]}")
                continue
            
            logger.info(f"🗳️ Requesting vote from {agent_id}")
            await self._send_voting_instruction(agent_id)
            await self._run_single_agent_voting_turn(agent_id)

    async def _send_voting_instruction(self, agent_id: str) -> None:
        """Send voting instruction to agent."""
        voting_instruction = """
# 🗳️ 最终投票时间！

基于前面的辩论和你的专业分析，现在必须做出最终投票决定。

**请立即使用Battle.vote工具投票：**
- 看涨：Battle.vote("bullish")  
- 看跌：Battle.vote("bearish")

**然后使用Terminate结束参与。**

⚠️ 不要再分析，直接投票！
        """
        
        if agent_id in self.agents:
            agent = self.agents[agent_id]
            if isinstance(agent, ToolCallAgent):
                agent.update_memory("user", voting_instruction)
                self.llm_calls += 1
                logger.info(f"📮 Sent voting instruction to {agent_id}")

    async def _run_single_agent_voting_turn(self, agent_id: str) -> None:
        """Run a single agent's voting turn."""
        if agent_id not in self.agents:
            return
        
        agent = self.agents[agent_id]
        original_max_steps = agent.max_steps
        
        try:
            # 限制步数为1，强制快速投票
            agent.max_steps = 1
            agent.current_step = 0
            agent.state = AgentState.IDLE
            
            logger.info(f"🗳️ {agent_id} voting...")
            result = await agent.run("请立即投票！")
            logger.info(f"✅ {agent_id} completed voting")
            
        except Exception as e:
            logger.error(f"❌ Error in {agent_id} voting: {str(e)}")
        finally:
            agent.max_steps = original_max_steps

    def _prepare_results(self) -> Dict[str, Any]:
        """Prepare battle results."""
        return {
            "vote_results": self.state.vote_results,
            "battle_history": self.state.battle_history,
            "battle_highlights": self.state.battle_highlights,
            "tool_calls": self.tool_calls,
            "llm_calls": self.llm_calls,
        }

    async def _broadcast_message(self, sender_id: str, content: str, event_type: str) -> None:
        """Broadcast message to all active agents."""
        message = get_broadcast_message(
            sender_name=self.state.active_agents[sender_id],
            content=content,
            action_type=event_type,
        )
        
        for agent_id, agent in self.agents.items():
            if agent_id != sender_id and isinstance(agent, ToolCallAgent):
                agent.update_memory("user", message)
                self.llm_calls += 1
