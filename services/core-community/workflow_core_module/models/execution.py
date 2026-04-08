"""
Workflow Execution State Models
================================

Dataclasses for tracking workflow execution state, node execution, and results.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, List, Optional
from datetime import datetime


class ExecutionStatus(str, Enum):
    """Overall execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class NodeExecutionStatus(str, Enum):
    """Individual node execution status"""
    PENDING = "pending"
    READY = "ready"         # All inputs available, ready to execute
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"
    PAUSED = "paused"


@dataclass(slots=True)
class ExecutionContext:
    """
    Execution context for a workflow execution.

    Contains all state and variables available during workflow execution.

    Attributes:
        execution_id: Unique identifier for this execution
        workflow_id: ID of workflow being executed
        workflow_version: Version of workflow
        session_id: Session identifier (from trigger)
        entity_id: Community/entity ID
        user_id: User ID (from trigger)
        username: Username (from trigger)
        platform: Platform (from trigger)
        variables: Current variable state
        metadata: Additional metadata from trigger
        start_time: When execution started
        current_node_id: Currently executing node (for debugging)
        execution_path: List of executed node IDs
    """
    execution_id: str
    workflow_id: str
    workflow_version: str
    session_id: str
    entity_id: str
    user_id: str
    variables: Dict[str, Any] = field(default_factory=dict)
    username: Optional[str] = None
    platform: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    start_time: datetime = field(default_factory=datetime.utcnow)
    current_node_id: Optional[str] = None
    execution_path: List[str] = field(default_factory=list)
    cancelled: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "execution_id": self.execution_id,
            "workflow_id": self.workflow_id,
            "workflow_version": self.workflow_version,
            "session_id": self.session_id,
            "entity_id": self.entity_id,
            "user_id": self.user_id,
            "username": self.username,
            "platform": self.platform,
            "variables": self.variables,
            "metadata": self.metadata,
            "start_time": self.start_time.isoformat(),
            "current_node_id": self.current_node_id,
            "execution_path": self.execution_path,
            "cancelled": self.cancelled,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExecutionContext":
        """Create from dictionary"""
        return cls(
            execution_id=data["execution_id"],
            workflow_id=data["workflow_id"],
            workflow_version=data["workflow_version"],
            session_id=data["session_id"],
            entity_id=data["entity_id"],
            user_id=data["user_id"],
            username=data.get("username"),
            platform=data.get("platform"),
            variables=data.get("variables", {}),
            metadata=data.get("metadata", {}),
            start_time=datetime.fromisoformat(data.get("start_time", datetime.utcnow().isoformat())),
            current_node_id=data.get("current_node_id"),
            execution_path=data.get("execution_path", []),
            cancelled=data.get("cancelled", False),
        )

    def get_variable(self, name: str, default: Any = None) -> Any:
        """Get variable value"""
        return self.variables.get(name, default)

    def set_variable(self, name: str, value: Any) -> None:
        """Set variable value"""
        self.variables[name] = value

    def set_variables(self, variables: Dict[str, Any]) -> None:
        """Set multiple variables"""
        self.variables.update(variables)

    def add_to_path(self, node_id: str) -> None:
        """Record node execution in path"""
        self.execution_path.append(node_id)

    def get_elapsed_seconds(self) -> float:
        """Get elapsed time since execution start"""
        return (datetime.utcnow() - self.start_time).total_seconds()


@dataclass(slots=True)
class PortData:
    """
    Data flowing through a connection port.

    Attributes:
        port_name: Name of the port
        data: The actual data value
        timestamp: When data was produced
    """
    port_name: str
    data: Any
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "port_name": self.port_name,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PortData":
        """Create from dictionary"""
        return cls(
            port_name=data["port_name"],
            data=data["data"],
            timestamp=datetime.fromisoformat(data.get("timestamp", datetime.utcnow().isoformat())),
        )


@dataclass(slots=True)
class NodeExecutionState:
    """
    Execution state for a single node within a workflow.

    Tracks all information about how a node executed: when it ran, what
    inputs it received, what it produced, any errors, etc.

    Attributes:
        node_id: ID of the node
        status: Current execution status
        input_data: Data received on input ports
        output_data: Data produced on output ports
        started_at: When node started executing
        completed_at: When node finished executing
        error: Error message if execution failed
        error_type: Type of error (validation, execution, timeout, etc.)
        retry_count: Number of retry attempts
        logs: Any logs produced during execution
        metadata: Additional metadata
    """
    node_id: str
    status: NodeExecutionStatus = NodeExecutionStatus.PENDING
    input_data: Dict[str, PortData] = field(default_factory=dict)
    output_data: Dict[str, PortData] = field(default_factory=dict)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    error_type: Optional[str] = None
    retry_count: int = 0
    logs: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "node_id": self.node_id,
            "status": self.status.value,
            "input_data": {
                port: port_data.to_dict()
                for port, port_data in self.input_data.items()
            },
            "output_data": {
                port: port_data.to_dict()
                for port, port_data in self.output_data.items()
            },
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error": self.error,
            "error_type": self.error_type,
            "retry_count": self.retry_count,
            "logs": self.logs,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NodeExecutionState":
        """Create from dictionary"""
        input_data = {
            port: PortData.from_dict(port_data)
            for port, port_data in data.get("input_data", {}).items()
        }

        output_data = {
            port: PortData.from_dict(port_data)
            for port, port_data in data.get("output_data", {}).items()
        }

        return cls(
            node_id=data["node_id"],
            status=NodeExecutionStatus(data.get("status", "pending")),
            input_data=input_data,
            output_data=output_data,
            started_at=datetime.fromisoformat(data["started_at"]) if data.get("started_at") else None,
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
            error=data.get("error"),
            error_type=data.get("error_type"),
            retry_count=data.get("retry_count", 0),
            logs=data.get("logs", []),
            metadata=data.get("metadata", {}),
        )

    def get_execution_time_seconds(self) -> Optional[float]:
        """Get how long node took to execute"""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    def add_log(self, message: str) -> None:
        """Add a log message"""
        timestamp = datetime.utcnow().isoformat()
        self.logs.append(f"[{timestamp}] {message}")

    def set_output(self, port_name: str, data: Any) -> None:
        """Set output data on a port"""
        self.output_data[port_name] = PortData(port_name=port_name, data=data)

    def get_output(self, port_name: str, default: Any = None) -> Any:
        """Get output data from a port"""
        port_data = self.output_data.get(port_name)
        return port_data.data if port_data else default

    def mark_started(self) -> None:
        """Mark node as started"""
        self.status = NodeExecutionStatus.RUNNING
        self.started_at = datetime.utcnow()

    def mark_completed(self) -> None:
        """Mark node as completed"""
        self.status = NodeExecutionStatus.COMPLETED
        self.completed_at = datetime.utcnow()

    def mark_failed(self, error: str, error_type: str = "execution") -> None:
        """Mark node as failed"""
        self.status = NodeExecutionStatus.FAILED
        self.completed_at = datetime.utcnow()
        self.error = error
        self.error_type = error_type

    def mark_skipped(self) -> None:
        """Mark node as skipped"""
        self.status = NodeExecutionStatus.SKIPPED
        self.completed_at = datetime.utcnow()


@dataclass(slots=True)
class ExecutionResult:
    """
    Result of a complete workflow execution.

    Contains final status, execution path, variable state, and any errors.

    Attributes:
        execution_id: ID of the execution
        workflow_id: ID of the workflow
        status: Final execution status
        execution_path: List of node IDs in execution order
        node_states: Dict of node_id -> execution state for all nodes
        final_variables: Final state of all variables
        final_output: Output from the end node
        error_message: Error message if execution failed
        error_node_id: ID of node where error occurred
        start_time: When execution started
        end_time: When execution ended
        execution_time_seconds: Total execution duration
        node_execution_times: Dict of node_id -> execution_seconds
    """
    execution_id: str
    workflow_id: str
    status: ExecutionStatus
    execution_path: List[str]
    node_states: Dict[str, NodeExecutionState] = field(default_factory=dict)
    final_variables: Dict[str, Any] = field(default_factory=dict)
    final_output: Optional[Any] = None
    error_message: Optional[str] = None
    error_node_id: Optional[str] = None
    start_time: datetime = field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    execution_time_seconds: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "execution_id": self.execution_id,
            "workflow_id": self.workflow_id,
            "status": self.status.value,
            "execution_path": self.execution_path,
            "node_states": {
                node_id: state.to_dict()
                for node_id, state in self.node_states.items()
            },
            "final_variables": self.final_variables,
            "final_output": self.final_output,
            "error_message": self.error_message,
            "error_node_id": self.error_node_id,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "execution_time_seconds": self.execution_time_seconds,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExecutionResult":
        """Create from dictionary"""
        node_states = {
            node_id: NodeExecutionState.from_dict(state_data)
            for node_id, state_data in data.get("node_states", {}).items()
        }

        return cls(
            execution_id=data["execution_id"],
            workflow_id=data["workflow_id"],
            status=ExecutionStatus(data["status"]),
            execution_path=data.get("execution_path", []),
            node_states=node_states,
            final_variables=data.get("final_variables", {}),
            final_output=data.get("final_output"),
            error_message=data.get("error_message"),
            error_node_id=data.get("error_node_id"),
            start_time=datetime.fromisoformat(data.get("start_time", datetime.utcnow().isoformat())),
            end_time=datetime.fromisoformat(data["end_time"]) if data.get("end_time") else None,
            execution_time_seconds=data.get("execution_time_seconds", 0.0),
        )

    @property
    def is_successful(self) -> bool:
        """Check if execution was successful"""
        return self.status == ExecutionStatus.COMPLETED

    @property
    def is_failed(self) -> bool:
        """Check if execution failed"""
        return self.status == ExecutionStatus.FAILED

    @property
    def is_running(self) -> bool:
        """Check if execution is still running"""
        return self.status == ExecutionStatus.RUNNING

    def get_node_state(self, node_id: str) -> Optional[NodeExecutionState]:
        """Get execution state of a specific node"""
        return self.node_states.get(node_id)

    def get_failed_nodes(self) -> List[str]:
        """Get list of node IDs that failed"""
        return [
            node_id
            for node_id, state in self.node_states.items()
            if state.status == NodeExecutionStatus.FAILED
        ]

    def get_execution_summary(self) -> Dict[str, Any]:
        """Get summary of execution"""
        failed_nodes = self.get_failed_nodes()

        return {
            "execution_id": self.execution_id,
            "workflow_id": self.workflow_id,
            "status": self.status.value,
            "success": self.is_successful,
            "total_nodes_executed": len(self.execution_path),
            "total_nodes": len(self.node_states),
            "failed_nodes": failed_nodes,
            "execution_time_seconds": self.execution_time_seconds,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "error": self.error_message,
        }


@dataclass(slots=True)
class ExecutionMetrics:
    """
    Performance metrics for a workflow execution.

    Attributes:
        execution_id: ID of the execution
        workflow_id: ID of the workflow
        total_duration_seconds: Total execution time
        node_count: Total number of nodes in workflow
        nodes_executed: Number of nodes actually executed
        nodes_skipped: Number of nodes skipped
        nodes_failed: Number of nodes that failed
        average_node_time_seconds: Average time per executed node
        slowest_node_id: ID of slowest node
        slowest_node_time_seconds: Time for slowest node
        variable_count: Total variables in final state
        memory_used_mb: Memory used during execution (if tracked)
        timestamp: When metrics were recorded
    """
    execution_id: str
    workflow_id: str
    total_duration_seconds: float
    node_count: int
    nodes_executed: int
    nodes_skipped: int
    nodes_failed: int
    average_node_time_seconds: float = 0.0
    slowest_node_id: Optional[str] = None
    slowest_node_time_seconds: float = 0.0
    variable_count: int = 0
    memory_used_mb: Optional[float] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "execution_id": self.execution_id,
            "workflow_id": self.workflow_id,
            "total_duration_seconds": self.total_duration_seconds,
            "node_count": self.node_count,
            "nodes_executed": self.nodes_executed,
            "nodes_skipped": self.nodes_skipped,
            "nodes_failed": self.nodes_failed,
            "average_node_time_seconds": self.average_node_time_seconds,
            "slowest_node_id": self.slowest_node_id,
            "slowest_node_time_seconds": self.slowest_node_time_seconds,
            "variable_count": self.variable_count,
            "memory_used_mb": self.memory_used_mb,
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExecutionMetrics":
        """Create from dictionary"""
        return cls(
            execution_id=data["execution_id"],
            workflow_id=data["workflow_id"],
            total_duration_seconds=data["total_duration_seconds"],
            node_count=data["node_count"],
            nodes_executed=data["nodes_executed"],
            nodes_skipped=data["nodes_skipped"],
            nodes_failed=data["nodes_failed"],
            average_node_time_seconds=data.get("average_node_time_seconds", 0.0),
            slowest_node_id=data.get("slowest_node_id"),
            slowest_node_time_seconds=data.get("slowest_node_time_seconds", 0.0),
            variable_count=data.get("variable_count", 0),
            memory_used_mb=data.get("memory_used_mb"),
            timestamp=datetime.fromisoformat(data.get("timestamp", datetime.utcnow().isoformat())),
        )

    @staticmethod
    def from_execution_result(result: ExecutionResult) -> "ExecutionMetrics":
        """Create metrics from execution result"""
        node_times = [
            state.get_execution_time_seconds()
            for state in result.node_states.values()
            if state.get_execution_time_seconds() is not None
        ]

        slowest_node_id = None
        slowest_node_time = 0.0
        if node_times:
            slowest_node_time = max(node_times)
            for node_id, state in result.node_states.items():
                if state.get_execution_time_seconds() == slowest_node_time:
                    slowest_node_id = node_id
                    break

        nodes_skipped = sum(
            1 for state in result.node_states.values()
            if state.status == NodeExecutionStatus.SKIPPED
        )
        nodes_failed = sum(
            1 for state in result.node_states.values()
            if state.status == NodeExecutionStatus.FAILED
        )

        return ExecutionMetrics(
            execution_id=result.execution_id,
            workflow_id=result.workflow_id,
            total_duration_seconds=result.execution_time_seconds,
            node_count=len(result.node_states),
            nodes_executed=len(result.execution_path),
            nodes_skipped=nodes_skipped,
            nodes_failed=nodes_failed,
            average_node_time_seconds=sum(node_times) / len(node_times) if node_times else 0.0,
            slowest_node_id=slowest_node_id,
            slowest_node_time_seconds=slowest_node_time,
            variable_count=len(result.final_variables),
        )
