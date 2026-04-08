"""
Workflow Definition Models
===========================

Dataclasses for complete workflow definitions, including metadata, nodes, and connections.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, List, Optional
from datetime import datetime
from .nodes import WorkflowNode, node_from_dict


class WorkflowStatus(str, Enum):
    """Workflow deployment status"""
    DRAFT = "draft"           # Not published
    ACTIVE = "active"         # Published and running
    PAUSED = "paused"         # Published but paused
    DISABLED = "disabled"     # Disabled
    ARCHIVED = "archived"     # Archived


class VersionStatus(str, Enum):
    """Status of a workflow version"""
    DRAFT = "draft"
    PUBLISHED = "published"
    RETIRED = "retired"


@dataclass(slots=True)
class WorkflowConnection:
    """
    Connection between two nodes.

    Defines how data/control flow moves from one node's output port
    to another node's input port.

    Attributes:
        connection_id: Unique identifier for this connection
        from_node_id: Source node ID
        from_port_name: Source node output port name
        to_node_id: Target node ID
        to_port_name: Target node input port name
        enabled: Whether connection is active
        conditional: Optional condition for activating connection
    """
    connection_id: str
    from_node_id: str
    from_port_name: str
    to_node_id: str
    to_port_name: str
    enabled: bool = True
    conditional: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "connection_id": self.connection_id,
            "from_node_id": self.from_node_id,
            "from_port_name": self.from_port_name,
            "to_node_id": self.to_node_id,
            "to_port_name": self.to_port_name,
            "enabled": self.enabled,
            "conditional": self.conditional,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkflowConnection":
        """Create from dictionary"""
        return cls(
            connection_id=data["connection_id"],
            from_node_id=data["from_node_id"],
            from_port_name=data["from_port_name"],
            to_node_id=data["to_node_id"],
            to_port_name=data["to_port_name"],
            enabled=data.get("enabled", True),
            conditional=data.get("conditional"),
        )


@dataclass(slots=True)
class WorkflowMetadata:
    """
    Workflow metadata and configuration.

    Contains workflow name, description, author, and execution settings.

    Attributes:
        workflow_id: Unique workflow identifier
        name: Human-readable workflow name
        description: Long description of workflow purpose
        author_id: User ID of workflow creator
        community_id: Community this workflow belongs to
        version: Semantic version (e.g., "1.2.3")
        tags: List of tags for categorization
        status: Current workflow status
        enabled: Whether workflow is enabled
        is_template: Whether this is a reusable template
        icon_url: URL to workflow icon
        documentation_url: URL to documentation
        # Execution settings
        max_execution_time_seconds: Global timeout for execution
        max_parallel_executions: Max concurrent executions
        timeout_on_error: Continue on node error
        retry_failed_nodes: Retry failed nodes
        max_retries: Max retries per node
        # Metadata
        created_at: Creation timestamp
        updated_at: Last update timestamp
        published_at: When workflow was published
        last_executed_at: Last execution timestamp
        execution_count: Total execution count
    """
    workflow_id: str
    name: str
    description: str
    author_id: str
    community_id: str
    version: str = "1.0.0"
    tags: List[str] = field(default_factory=list)
    status: WorkflowStatus = WorkflowStatus.DRAFT
    enabled: bool = True
    is_template: bool = False
    icon_url: Optional[str] = None
    documentation_url: Optional[str] = None

    # Execution settings
    max_execution_time_seconds: int = 300
    max_parallel_executions: int = 10
    timeout_on_error: bool = False
    retry_failed_nodes: bool = False
    max_retries: int = 0

    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    published_at: Optional[datetime] = None
    last_executed_at: Optional[datetime] = None
    execution_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "workflow_id": self.workflow_id,
            "name": self.name,
            "description": self.description,
            "author_id": self.author_id,
            "community_id": self.community_id,
            "version": self.version,
            "tags": self.tags,
            "status": self.status.value,
            "enabled": self.enabled,
            "is_template": self.is_template,
            "icon_url": self.icon_url,
            "documentation_url": self.documentation_url,
            "max_execution_time_seconds": self.max_execution_time_seconds,
            "max_parallel_executions": self.max_parallel_executions,
            "timeout_on_error": self.timeout_on_error,
            "retry_failed_nodes": self.retry_failed_nodes,
            "max_retries": self.max_retries,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "last_executed_at": self.last_executed_at.isoformat() if self.last_executed_at else None,
            "execution_count": self.execution_count,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkflowMetadata":
        """Create from dictionary"""
        return cls(
            workflow_id=data["workflow_id"],
            name=data["name"],
            description=data["description"],
            author_id=data["author_id"],
            community_id=data["community_id"],
            version=data.get("version", "1.0.0"),
            tags=data.get("tags", []),
            status=WorkflowStatus(data.get("status", "draft")),
            enabled=data.get("enabled", True),
            is_template=data.get("is_template", False),
            icon_url=data.get("icon_url"),
            documentation_url=data.get("documentation_url"),
            max_execution_time_seconds=data.get("max_execution_time_seconds", 300),
            max_parallel_executions=data.get("max_parallel_executions", 10),
            timeout_on_error=data.get("timeout_on_error", False),
            retry_failed_nodes=data.get("retry_failed_nodes", False),
            max_retries=data.get("max_retries", 0),
            created_at=datetime.fromisoformat(data.get("created_at", datetime.utcnow().isoformat())),
            updated_at=datetime.fromisoformat(data.get("updated_at", datetime.utcnow().isoformat())),
            published_at=datetime.fromisoformat(data["published_at"]) if data.get("published_at") else None,
            last_executed_at=datetime.fromisoformat(data["last_executed_at"]) if data.get("last_executed_at") else None,
            execution_count=data.get("execution_count", 0),
        )


@dataclass(slots=True)
class WorkflowDefinition:
    """
    Complete workflow definition.

    Contains all information needed to execute a workflow:
    - Metadata about the workflow
    - List of all nodes
    - Connections between nodes
    - Global variables and settings

    This is the primary data structure for workflow management.

    Attributes:
        metadata: Workflow metadata and configuration
        nodes: Dict of node_id -> node_config for all nodes
        connections: List of connections between nodes
        global_variables: Dict of variable_name -> initial_value
        trigger_nodes: List of node IDs that are trigger nodes
        validate: Whether to validate on creation
    """
    metadata: WorkflowMetadata
    nodes: Dict[str, WorkflowNode] = field(default_factory=dict)
    connections: List[WorkflowConnection] = field(default_factory=list)
    global_variables: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert complete workflow to dictionary for JSON serialization"""
        return {
            "metadata": self.metadata.to_dict(),
            "nodes": {
                node_id: node.to_dict()
                for node_id, node in self.nodes.items()
            },
            "connections": [
                conn.to_dict()
                for conn in self.connections
            ],
            "global_variables": self.global_variables,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkflowDefinition":
        """Create complete workflow from dictionary"""
        metadata = WorkflowMetadata.from_dict(data["metadata"])

        # Parse nodes
        nodes = {
            node_id: node_from_dict(node_data)
            for node_id, node_data in data.get("nodes", {}).items()
        }

        # Parse connections
        connections = [
            WorkflowConnection.from_dict(conn_data)
            for conn_data in data.get("connections", [])
        ]

        return cls(
            metadata=metadata,
            nodes=nodes,
            connections=connections,
            global_variables=data.get("global_variables", {}),
        )

    def get_trigger_nodes(self) -> List[str]:
        """Get all trigger node IDs"""
        from .nodes import (
            TriggerCommandConfig, TriggerEventConfig,
            TriggerWebhookConfig, TriggerScheduleConfig
        )

        trigger_types = (
            TriggerCommandConfig, TriggerEventConfig,
            TriggerWebhookConfig, TriggerScheduleConfig
        )

        return [
            node_id
            for node_id, node in self.nodes.items()
            if isinstance(node, trigger_types)
        ]

    def get_end_nodes(self) -> List[str]:
        """Get all end node IDs"""
        from .nodes import FlowEndConfig

        return [
            node_id
            for node_id, node in self.nodes.items()
            if isinstance(node, FlowEndConfig)
        ]

    def get_node(self, node_id: str) -> Optional[WorkflowNode]:
        """Get node by ID"""
        return self.nodes.get(node_id)

    def get_connections_from(self, node_id: str) -> List[WorkflowConnection]:
        """Get all connections originating from a node"""
        return [
            conn for conn in self.connections
            if conn.from_node_id == node_id and conn.enabled
        ]

    def get_connections_to(self, node_id: str) -> List[WorkflowConnection]:
        """Get all connections targeting a node"""
        return [
            conn for conn in self.connections
            if conn.to_node_id == node_id and conn.enabled
        ]

    def validate(self) -> tuple[bool, List[str]]:
        """
        Validate workflow structure.

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        # Check for empty workflow
        if not self.nodes:
            errors.append("Workflow must contain at least one node")
            return False, errors

        # Check for trigger nodes
        trigger_nodes = self.get_trigger_nodes()
        if not trigger_nodes:
            errors.append("Workflow must have at least one trigger node")

        # Check for end nodes
        end_nodes = self.get_end_nodes()
        if not end_nodes:
            errors.append("Workflow should have at least one end node")

        # Validate connections
        for conn in self.connections:
            # Check that nodes exist
            if conn.from_node_id not in self.nodes:
                errors.append(f"Connection references non-existent node: {conn.from_node_id}")
            if conn.to_node_id not in self.nodes:
                errors.append(f"Connection references non-existent node: {conn.to_node_id}")

            # Check that ports exist
            if conn.from_node_id in self.nodes:
                from_node = self.nodes[conn.from_node_id]
                port_names = [p.name for p in from_node.output_ports]
                if conn.from_port_name not in port_names:
                    errors.append(
                        f"Node {conn.from_node_id} has no output port: {conn.from_port_name}"
                    )

            if conn.to_node_id in self.nodes:
                to_node = self.nodes[conn.to_node_id]
                port_names = [p.name for p in to_node.input_ports]
                if conn.to_port_name not in port_names:
                    errors.append(
                        f"Node {conn.to_node_id} has no input port: {conn.to_port_name}"
                    )

        return len(errors) == 0, errors

    def add_node(self, node: WorkflowNode) -> None:
        """Add node to workflow"""
        self.nodes[node.node_id] = node

    def remove_node(self, node_id: str) -> None:
        """Remove node and all its connections"""
        if node_id in self.nodes:
            del self.nodes[node_id]

        # Remove all connections involving this node
        self.connections = [
            conn for conn in self.connections
            if conn.from_node_id != node_id and conn.to_node_id != node_id
        ]

    def add_connection(self, connection: WorkflowConnection) -> None:
        """Add connection between nodes"""
        self.connections.append(connection)

    def remove_connection(self, connection_id: str) -> None:
        """Remove connection by ID"""
        self.connections = [
            conn for conn in self.connections
            if conn.connection_id != connection_id
        ]

    def get_next_nodes(self, current_node_id: str) -> List[str]:
        """Get node IDs of nodes directly connected to output of current node"""
        return [
            conn.to_node_id
            for conn in self.get_connections_from(current_node_id)
        ]

    def get_previous_nodes(self, current_node_id: str) -> List[str]:
        """Get node IDs of nodes directly connected to input of current node"""
        return [
            conn.from_node_id
            for conn in self.get_connections_to(current_node_id)
        ]
