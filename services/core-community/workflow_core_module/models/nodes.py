"""
Workflow Node Type Definitions
================================

Comprehensive dataclass definitions for all workflow node types.
Each node represents a distinct operation or control flow element in a workflow.

Node Categories:
- Trigger: Entry points (commands, events, webhooks, schedules)
- Condition: Control flow logic (if/else, switch, filters)
- Action: Execution nodes (modules, webhooks, chat, delays)
- Data: Variable operations (transform, get, set)
- Loop: Iteration control (foreach, while, break)
- Flow: Flow control (merge, parallel, end)
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, List, Optional
from datetime import datetime


class NodeType(str, Enum):
    """All available node types in workflow system"""
    # Trigger nodes
    TRIGGER_COMMAND = "trigger_command"
    TRIGGER_EVENT = "trigger_event"
    TRIGGER_WEBHOOK = "trigger_webhook"
    TRIGGER_SCHEDULE = "trigger_schedule"

    # Condition nodes
    CONDITION_IF = "condition_if"
    CONDITION_SWITCH = "condition_switch"
    CONDITION_FILTER = "condition_filter"

    # Action nodes
    ACTION_MODULE = "action_module"
    ACTION_WEBHOOK = "action_webhook"
    ACTION_CHAT_MESSAGE = "action_chat_message"
    ACTION_BROWSER_SOURCE = "action_browser_source"
    ACTION_DELAY = "action_delay"

    # Data nodes
    DATA_TRANSFORM = "data_transform"
    DATA_VARIABLE_SET = "data_variable_set"
    DATA_VARIABLE_GET = "data_variable_get"

    # Loop nodes
    LOOP_FOREACH = "loop_foreach"
    LOOP_WHILE = "loop_while"
    LOOP_BREAK = "loop_break"

    # Flow nodes
    FLOW_MERGE = "flow_merge"
    FLOW_PARALLEL = "flow_parallel"
    FLOW_END = "flow_end"


class OperatorType(str, Enum):
    """Comparison and logical operators for conditions"""
    # Comparison
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    GREATER_EQUAL = "greater_equal"
    LESS_EQUAL = "less_equal"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    MATCHES_REGEX = "matches_regex"
    IN_LIST = "in_list"
    NOT_IN_LIST = "not_in_list"
    # Logical
    AND = "and"
    OR = "or"
    NOT = "not"


class HttpMethod(str, Enum):
    """HTTP methods for webhook actions"""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"


class VariableScope(str, Enum):
    """Scope of variable availability"""
    LOCAL = "local"          # Node-only scope
    WORKFLOW = "workflow"    # All nodes in workflow
    GLOBAL = "global"        # Available across workflows


class PortType(str, Enum):
    """Port types for node connections"""
    INPUT = "input"
    OUTPUT = "output"


class DataType(str, Enum):
    """Data types for ports and variables"""
    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    OBJECT = "object"
    ARRAY = "array"
    DATE = "date"
    ANY = "any"


@dataclass(slots=True, frozen=True)
class PortDefinition:
    """
    Definition of an input or output port on a node.

    Ports define where connections can be made between nodes.
    Multiple connections can come into an input port.
    Multiple connections can originate from an output port.
    """
    name: str
    port_type: PortType
    data_type: DataType
    label: Optional[str] = None
    description: Optional[str] = None
    required: bool = False
    default_value: Optional[Any] = None
    multiple: bool = False  # Can accept/send multiple connections


@dataclass(slots=True)
class BaseNodeConfig:
    """
    Base configuration for all node types.

    Contains common fields shared across all node types.
    All specific node configs inherit from this class.

    Attributes:
        node_id: Unique identifier within workflow
        node_type: Type of node (from NodeType enum)
        label: Human-readable label for the node
        description: Optional description of node purpose
        position: X, Y position in visual workflow editor
        enabled: Whether node executes
        input_ports: List of input port definitions
        output_ports: List of output port definitions
        metadata: Additional custom metadata
        created_at: Timestamp of creation
        updated_at: Timestamp of last update
    """
    node_id: str
    node_type: NodeType
    label: str
    position: Dict[str, float]  # {"x": 100, "y": 200}
    enabled: bool = True
    description: Optional[str] = None
    input_ports: List[PortDefinition] = field(default_factory=list)
    output_ports: List[PortDefinition] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "node_id": self.node_id,
            "node_type": self.node_type.value,
            "label": self.label,
            "position": self.position,
            "enabled": self.enabled,
            "description": self.description,
            "input_ports": [
                {
                    "name": p.name,
                    "port_type": p.port_type.value,
                    "data_type": p.data_type.value,
                    "label": p.label,
                    "description": p.description,
                    "required": p.required,
                    "default_value": p.default_value,
                    "multiple": p.multiple,
                }
                for p in self.input_ports
            ],
            "output_ports": [
                {
                    "name": p.name,
                    "port_type": p.port_type.value,
                    "data_type": p.data_type.value,
                    "label": p.label,
                    "description": p.description,
                    "required": p.required,
                    "default_value": p.default_value,
                    "multiple": p.multiple,
                }
                for p in self.output_ports
            ],
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BaseNodeConfig":
        """Create from dictionary (for JSON deserialization)"""
        # Parse ports
        input_ports = [
            PortDefinition(
                name=p["name"],
                port_type=PortType(p["port_type"]),
                data_type=DataType(p["data_type"]),
                label=p.get("label"),
                description=p.get("description"),
                required=p.get("required", False),
                default_value=p.get("default_value"),
                multiple=p.get("multiple", False),
            )
            for p in data.get("input_ports", [])
        ]
        output_ports = [
            PortDefinition(
                name=p["name"],
                port_type=PortType(p["port_type"]),
                data_type=DataType(p["data_type"]),
                label=p.get("label"),
                description=p.get("description"),
                required=p.get("required", False),
                default_value=p.get("default_value"),
                multiple=p.get("multiple", False),
            )
            for p in data.get("output_ports", [])
        ]

        # Note: node_type has init=False, so we don't pass it
        return cls(
            node_id=data["node_id"],
            label=data["label"],
            position=data["position"],
            enabled=data.get("enabled", True),
            description=data.get("description"),
            input_ports=input_ports,
            output_ports=output_ports,
            metadata=data.get("metadata", {}),
            created_at=datetime.fromisoformat(data.get("created_at", datetime.utcnow().isoformat())),
            updated_at=datetime.fromisoformat(data.get("updated_at", datetime.utcnow().isoformat())),
        )


# ============================================================================
# TRIGGER NODE TYPES
# ============================================================================

@dataclass(slots=True)
class TriggerCommandConfig(BaseNodeConfig):
    """
    Command trigger - Executes when a specific command is issued.

    Attributes:
        command_pattern: Command pattern (e.g., "!help", "!stats [user]")
        platforms: List of platforms to listen on (twitch, discord, slack)
        require_mod: Require moderator+ permission
        require_bot_owner: Require bot owner
        require_permission: Custom permission string required
        cooldown_seconds: Global cooldown before command can run again
        user_cooldown_seconds: Per-user cooldown
        message_min_length: Minimum message length to trigger
        case_sensitive: Whether command is case sensitive
    """
    node_type: NodeType = field(default=NodeType.TRIGGER_COMMAND, init=False)
    command_pattern: str = ""
    platforms: List[str] = field(default_factory=list)
    require_mod: bool = False
    require_bot_owner: bool = False
    require_permission: Optional[str] = None
    cooldown_seconds: int = 0
    user_cooldown_seconds: int = 0
    message_min_length: int = 0
    case_sensitive: bool = False


@dataclass(slots=True)
class TriggerEventConfig(BaseNodeConfig):
    """
    Event trigger - Executes on specific platform events.

    Attributes:
        event_type: Type of event (follow, subscribe, raid, etc.)
        platforms: Platforms to listen on
        event_filters: Additional filters for event matching
    """
    node_type: NodeType = field(default=NodeType.TRIGGER_EVENT, init=False)
    event_type: str = ""  # follow, subscribe, raid, host, etc.
    platforms: List[str] = field(default_factory=list)
    event_filters: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class TriggerWebhookConfig(BaseNodeConfig):
    """
    Webhook trigger - Executes when webhook receives POST request.

    Attributes:
        webhook_path: Path for webhook endpoint (/webhook/my-workflow)
        require_auth: Whether webhook requires API key
        require_signature: Verify webhook signature
        allowed_ips: Whitelist of allowed IP addresses
    """
    node_type: NodeType = field(default=NodeType.TRIGGER_WEBHOOK, init=False)
    webhook_path: str = ""
    require_auth: bool = True
    require_signature: bool = False
    allowed_ips: List[str] = field(default_factory=list)


@dataclass(slots=True)
class TriggerScheduleConfig(BaseNodeConfig):
    """
    Schedule trigger - Executes on a cron schedule.

    Attributes:
        cron_expression: Cron format (e.g., "0 */6 * * *" for every 6 hours)
        timezone: Timezone for cron evaluation
        max_executions: Max times to run (None = infinite)
    """
    node_type: NodeType = field(default=NodeType.TRIGGER_SCHEDULE, init=False)
    cron_expression: str = ""
    timezone: str = "UTC"
    max_executions: Optional[int] = None


# ============================================================================
# CONDITION NODE TYPES
# ============================================================================

@dataclass(slots=True, frozen=True)
class ConditionRule:
    """Single condition rule: variable operator value"""
    variable: str
    operator: OperatorType
    value: Any


@dataclass(slots=True)
class ConditionIfConfig(BaseNodeConfig):
    """
    If condition - Branches on true/false evaluation.

    Attributes:
        condition: List of rules to evaluate (AND logic between rules)
        output_true_port: Name of true output port
        output_false_port: Name of false output port
    """
    node_type: NodeType = field(default=NodeType.CONDITION_IF, init=False)
    condition: List[ConditionRule] = field(default_factory=list)
    output_true_port: str = "true"
    output_false_port: str = "false"


@dataclass(slots=True)
class ConditionSwitchConfig(BaseNodeConfig):
    """
    Switch condition - Routes to one of multiple outputs based on value matching.

    Attributes:
        variable: Variable to switch on
        cases: Dict of case_value -> output_port_name
        default_port: Output port for no match case
    """
    node_type: NodeType = field(default=NodeType.CONDITION_SWITCH, init=False)
    variable: str = ""
    cases: Dict[str, str] = field(default_factory=dict)  # value -> port
    default_port: str = "default"


@dataclass(slots=True)
class ConditionFilterConfig(BaseNodeConfig):
    """
    Filter condition - Filters array items based on condition.

    Attributes:
        input_array: Variable containing array to filter
        condition: Filter condition
        output_variable: Where to store filtered array
    """
    node_type: NodeType = field(default=NodeType.CONDITION_FILTER, init=False)
    input_array: str = ""
    condition: List[ConditionRule] = field(default_factory=list)
    output_variable: str = "filtered_items"


# ============================================================================
# ACTION NODE TYPES
# ============================================================================

@dataclass(slots=True)
class ActionModuleConfig(BaseNodeConfig):
    """
    Module action - Calls a Waddles action module.

    Attributes:
        module_name: Name of action module (ai_interaction, shoutout, etc.)
        module_version: Module version to use
        input_mapping: Maps workflow variables to module inputs
        output_mapping: Maps module outputs to workflow variables
        timeout_seconds: Module execution timeout
    """
    node_type: NodeType = field(default=NodeType.ACTION_MODULE, init=False)
    module_name: str = ""
    module_version: str = "latest"
    input_mapping: Dict[str, str] = field(default_factory=dict)  # workflow_var -> module_input
    output_mapping: Dict[str, str] = field(default_factory=dict)  # module_output -> workflow_var
    timeout_seconds: int = 30


@dataclass(slots=True)
class ActionWebhookConfig(BaseNodeConfig):
    """
    Webhook action - Makes HTTP request to external service.

    Attributes:
        url: Target URL
        method: HTTP method
        headers: Additional headers
        body_template: Template for request body (supports variables)
        output_variable: Where to store response
        retry_count: Number of retries on failure
        timeout_seconds: Request timeout
    """
    node_type: NodeType = field(default=NodeType.ACTION_WEBHOOK, init=False)
    url: str = ""
    method: HttpMethod = HttpMethod.POST
    headers: Dict[str, str] = field(default_factory=dict)
    body_template: Optional[str] = None
    output_variable: Optional[str] = None
    retry_count: int = 0
    timeout_seconds: int = 10


@dataclass(slots=True)
class ActionChatMessageConfig(BaseNodeConfig):
    """
    Chat message action - Send message to chat platform.

    Attributes:
        message_template: Template for message (supports variables)
        destination: Where to send (current_channel, user_pm, specified_channel)
        channel_id: Target channel ID (if destination is specified_channel)
        user_id: Target user ID (if destination is user_pm)
        platform: Platform to send on
        reply_to_message: Whether to reply to source message
    """
    node_type: NodeType = field(default=NodeType.ACTION_CHAT_MESSAGE, init=False)
    message_template: str = ""
    destination: str = "current_channel"
    channel_id: Optional[str] = None
    user_id: Optional[str] = None
    platform: Optional[str] = None
    reply_to_message: bool = False


@dataclass(slots=True)
class ActionBrowserSourceConfig(BaseNodeConfig):
    """
    Browser source action - Update OBS browser source.

    Attributes:
        source_type: Type of source (ticker, media, general)
        action: Action to perform (display, update, clear)
        content_template: Template for content (supports variables)
        duration: Display duration in seconds
        priority: Display priority (higher = more urgent)
    """
    node_type: NodeType = field(default=NodeType.ACTION_BROWSER_SOURCE, init=False)
    source_type: str = "general"  # ticker, media, general
    action: str = "display"  # display, update, clear
    content_template: Optional[str] = None
    duration: int = 10
    priority: int = 0


@dataclass(slots=True)
class ActionDelayConfig(BaseNodeConfig):
    """
    Delay action - Pause workflow execution.

    Attributes:
        delay_ms: Delay in milliseconds
        delay_variable: Variable containing delay duration (if dynamic)
    """
    node_type: NodeType = field(default=NodeType.ACTION_DELAY, init=False)
    delay_ms: int = 0
    delay_variable: Optional[str] = None


# ============================================================================
# DATA NODE TYPES
# ============================================================================

@dataclass(slots=True)
class DataTransformConfig(BaseNodeConfig):
    """
    Data transform - Transform input data using expressions.

    Attributes:
        transformations: Dict of output_var -> expression
        expression_language: Language for expressions (js, python, jq)
    """
    node_type: NodeType = field(default=NodeType.DATA_TRANSFORM, init=False)
    transformations: Dict[str, str] = field(default_factory=dict)
    expression_language: str = "jq"


@dataclass(slots=True)
class DataVariableSetConfig(BaseNodeConfig):
    """
    Variable set - Set workflow variables.

    Attributes:
        variables: Dict of variable_name -> value
        scope: Scope of variables (local, workflow, global)
    """
    node_type: NodeType = field(default=NodeType.DATA_VARIABLE_SET, init=False)
    variables: Dict[str, Any] = field(default_factory=dict)
    scope: VariableScope = VariableScope.WORKFLOW


@dataclass(slots=True)
class DataVariableGetConfig(BaseNodeConfig):
    """
    Variable get - Get variable from context.

    Attributes:
        variable_name: Name of variable to retrieve
        output_variable: Where to store retrieved value
        default_value: Default if variable not found
    """
    node_type: NodeType = field(default=NodeType.DATA_VARIABLE_GET, init=False)
    variable_name: str = ""
    output_variable: str = ""
    default_value: Optional[Any] = None


# ============================================================================
# LOOP NODE TYPES
# ============================================================================

@dataclass(slots=True)
class LoopForeachConfig(BaseNodeConfig):
    """
    Foreach loop - Iterate over array items.

    Attributes:
        array_variable: Variable containing array to iterate
        item_variable: Name of variable for current item
        index_variable: Name of variable for current index
        max_iterations: Safety limit on iterations
    """
    node_type: NodeType = field(default=NodeType.LOOP_FOREACH, init=False)
    array_variable: str = ""
    item_variable: str = "item"
    index_variable: str = "index"
    max_iterations: int = 10000


@dataclass(slots=True)
class LoopWhileConfig(BaseNodeConfig):
    """
    While loop - Iterate while condition is true.

    Attributes:
        condition: Loop continue condition
        max_iterations: Safety limit on iterations
    """
    node_type: NodeType = field(default=NodeType.LOOP_WHILE, init=False)
    condition: List[ConditionRule] = field(default_factory=list)
    max_iterations: int = 10000


@dataclass(slots=True)
class LoopBreakConfig(BaseNodeConfig):
    """
    Break statement - Exit current loop.

    Attributes:
        break_condition: Optional condition to evaluate before breaking
    """
    node_type: NodeType = field(default=NodeType.LOOP_BREAK, init=False)
    break_condition: Optional[List[ConditionRule]] = None


# ============================================================================
# FLOW NODE TYPES
# ============================================================================

@dataclass(slots=True)
class FlowMergeConfig(BaseNodeConfig):
    """
    Merge node - Consolidate multiple paths into one.

    Attributes:
        input_ports_required: Number of inputs that must complete before continuing
    """
    node_type: NodeType = field(default=NodeType.FLOW_MERGE, init=False)
    input_ports_required: int = -1  # -1 = all


@dataclass(slots=True)
class FlowParallelConfig(BaseNodeConfig):
    """
    Parallel node - Execute multiple paths simultaneously.

    Attributes:
        execution_type: parallel, any_first (fastest), all_fastest
        merge_results: Whether to merge results into single output
        timeout_seconds: Max time to wait for slowest branch
    """
    node_type: NodeType = field(default=NodeType.FLOW_PARALLEL, init=False)
    execution_type: str = "parallel"
    merge_results: bool = True
    timeout_seconds: int = 300


@dataclass(slots=True)
class FlowEndConfig(BaseNodeConfig):
    """
    End node - Marks end of workflow execution path.

    Attributes:
        final_output_port: Output port name for final results
    """
    node_type: NodeType = field(default=NodeType.FLOW_END, init=False)
    final_output_port: str = "end"


# Type union for all node config types
WorkflowNode = (
    TriggerCommandConfig | TriggerEventConfig | TriggerWebhookConfig | TriggerScheduleConfig |
    ConditionIfConfig | ConditionSwitchConfig | ConditionFilterConfig |
    ActionModuleConfig | ActionWebhookConfig | ActionChatMessageConfig | ActionBrowserSourceConfig | ActionDelayConfig |
    DataTransformConfig | DataVariableSetConfig | DataVariableGetConfig |
    LoopForeachConfig | LoopWhileConfig | LoopBreakConfig |
    FlowMergeConfig | FlowParallelConfig | FlowEndConfig
)


def _get_base_node_fields(data: Dict[str, Any]) -> Dict[str, Any]:
    """Extract base node fields from dictionary"""
    # Parse ports
    input_ports = [
        PortDefinition(
            name=p["name"],
            port_type=PortType(p["port_type"]),
            data_type=DataType(p["data_type"]),
            label=p.get("label"),
            description=p.get("description"),
            required=p.get("required", False),
            default_value=p.get("default_value"),
            multiple=p.get("multiple", False),
        )
        for p in data.get("input_ports", [])
    ]
    output_ports = [
        PortDefinition(
            name=p["name"],
            port_type=PortType(p["port_type"]),
            data_type=DataType(p["data_type"]),
            label=p.get("label"),
            description=p.get("description"),
            required=p.get("required", False),
            default_value=p.get("default_value"),
            multiple=p.get("multiple", False),
        )
        for p in data.get("output_ports", [])
    ]

    return {
        "node_id": data["node_id"],
        "label": data["label"],
        "position": data["position"],
        "enabled": data.get("enabled", True),
        "description": data.get("description"),
        "input_ports": input_ports,
        "output_ports": output_ports,
        "metadata": data.get("metadata", {}),
        "created_at": datetime.fromisoformat(data.get("created_at", datetime.utcnow().isoformat())),
        "updated_at": datetime.fromisoformat(data.get("updated_at", datetime.utcnow().isoformat())),
    }


def node_from_dict(data: Dict[str, Any]) -> WorkflowNode:
    """
    Create appropriate node type from dictionary.

    Args:
        data: Dictionary with node_type and node configuration

    Returns:
        Appropriate node config instance
    """
    node_type = NodeType(data.get("node_type"))
    base_fields = _get_base_node_fields(data)

    # Trigger nodes
    if node_type == NodeType.TRIGGER_COMMAND:
        return TriggerCommandConfig(
            **base_fields,
            command_pattern=data.get("command_pattern", ""),
            platforms=data.get("platforms", []),
            require_mod=data.get("require_mod", False),
            require_bot_owner=data.get("require_bot_owner", False),
            require_permission=data.get("require_permission"),
            cooldown_seconds=data.get("cooldown_seconds", 0),
            user_cooldown_seconds=data.get("user_cooldown_seconds", 0),
            message_min_length=data.get("message_min_length", 0),
            case_sensitive=data.get("case_sensitive", False),
        )
    elif node_type == NodeType.TRIGGER_EVENT:
        return TriggerEventConfig(
            **base_fields,
            event_type=data.get("event_type", ""),
            platforms=data.get("platforms", []),
            event_filters=data.get("event_filters", {}),
        )
    elif node_type == NodeType.TRIGGER_WEBHOOK:
        return TriggerWebhookConfig(
            **base_fields,
            webhook_path=data.get("webhook_path", ""),
            require_auth=data.get("require_auth", True),
            require_signature=data.get("require_signature", False),
            allowed_ips=data.get("allowed_ips", []),
        )
    elif node_type == NodeType.TRIGGER_SCHEDULE:
        return TriggerScheduleConfig(
            **base_fields,
            cron_expression=data.get("cron_expression", ""),
            timezone=data.get("timezone", "UTC"),
            max_executions=data.get("max_executions"),
        )

    # Condition nodes
    elif node_type == NodeType.CONDITION_IF:
        conditions = [
            ConditionRule(
                variable=c["variable"],
                operator=OperatorType(c["operator"]),
                value=c["value"]
            )
            for c in data.get("condition", [])
        ]
        return ConditionIfConfig(
            **base_fields,
            condition=conditions,
            output_true_port=data.get("output_true_port", "true"),
            output_false_port=data.get("output_false_port", "false"),
        )
    elif node_type == NodeType.CONDITION_SWITCH:
        return ConditionSwitchConfig(
            **base_fields,
            variable=data.get("variable", ""),
            cases=data.get("cases", {}),
            default_port=data.get("default_port", "default"),
        )
    elif node_type == NodeType.CONDITION_FILTER:
        conditions = [
            ConditionRule(
                variable=c["variable"],
                operator=OperatorType(c["operator"]),
                value=c["value"]
            )
            for c in data.get("condition", [])
        ]
        return ConditionFilterConfig(
            **base_fields,
            input_array=data.get("input_array", ""),
            condition=conditions,
            output_variable=data.get("output_variable", "filtered_items"),
        )

    # Action nodes
    elif node_type == NodeType.ACTION_MODULE:
        return ActionModuleConfig(
            **base_fields,
            module_name=data.get("module_name", ""),
            module_version=data.get("module_version", "latest"),
            input_mapping=data.get("input_mapping", {}),
            output_mapping=data.get("output_mapping", {}),
            timeout_seconds=data.get("timeout_seconds", 30),
        )
    elif node_type == NodeType.ACTION_WEBHOOK:
        return ActionWebhookConfig(
            **base_fields,
            url=data.get("url", ""),
            method=HttpMethod(data.get("method", "POST")),
            headers=data.get("headers", {}),
            body_template=data.get("body_template"),
            output_variable=data.get("output_variable"),
            retry_count=data.get("retry_count", 0),
            timeout_seconds=data.get("timeout_seconds", 10),
        )
    elif node_type == NodeType.ACTION_CHAT_MESSAGE:
        return ActionChatMessageConfig(
            **base_fields,
            message_template=data.get("message_template", ""),
            destination=data.get("destination", "current_channel"),
            channel_id=data.get("channel_id"),
            user_id=data.get("user_id"),
            platform=data.get("platform"),
            reply_to_message=data.get("reply_to_message", False),
        )
    elif node_type == NodeType.ACTION_BROWSER_SOURCE:
        return ActionBrowserSourceConfig(
            **base_fields,
            source_type=data.get("source_type", "general"),
            action=data.get("action", "display"),
            content_template=data.get("content_template"),
            duration=data.get("duration", 10),
            priority=data.get("priority", 0),
        )
    elif node_type == NodeType.ACTION_DELAY:
        return ActionDelayConfig(
            **base_fields,
            delay_ms=data.get("delay_ms", 0),
            delay_variable=data.get("delay_variable"),
        )

    # Data nodes
    elif node_type == NodeType.DATA_TRANSFORM:
        return DataTransformConfig(
            **base_fields,
            transformations=data.get("transformations", {}),
            expression_language=data.get("expression_language", "jq"),
        )
    elif node_type == NodeType.DATA_VARIABLE_SET:
        return DataVariableSetConfig(
            **base_fields,
            variables=data.get("variables", {}),
            scope=VariableScope(data.get("scope", "workflow")),
        )
    elif node_type == NodeType.DATA_VARIABLE_GET:
        return DataVariableGetConfig(
            **base_fields,
            variable_name=data.get("variable_name", ""),
            output_variable=data.get("output_variable", ""),
            default_value=data.get("default_value"),
        )

    # Loop nodes
    elif node_type == NodeType.LOOP_FOREACH:
        return LoopForeachConfig(
            **base_fields,
            array_variable=data.get("array_variable", ""),
            item_variable=data.get("item_variable", "item"),
            index_variable=data.get("index_variable", "index"),
            max_iterations=data.get("max_iterations", 10000),
        )
    elif node_type == NodeType.LOOP_WHILE:
        conditions = [
            ConditionRule(
                variable=c["variable"],
                operator=OperatorType(c["operator"]),
                value=c["value"]
            )
            for c in data.get("condition", [])
        ]
        return LoopWhileConfig(
            **base_fields,
            condition=conditions,
            max_iterations=data.get("max_iterations", 10000),
        )
    elif node_type == NodeType.LOOP_BREAK:
        break_condition = None
        if data.get("break_condition"):
            break_condition = [
                ConditionRule(
                    variable=c["variable"],
                    operator=OperatorType(c["operator"]),
                    value=c["value"]
                )
                for c in data.get("break_condition", [])
            ]
        return LoopBreakConfig(
            **base_fields,
            break_condition=break_condition,
        )

    # Flow nodes
    elif node_type == NodeType.FLOW_MERGE:
        return FlowMergeConfig(
            **base_fields,
            input_ports_required=data.get("input_ports_required", -1),
        )
    elif node_type == NodeType.FLOW_PARALLEL:
        return FlowParallelConfig(
            **base_fields,
            execution_type=data.get("execution_type", "parallel"),
            merge_results=data.get("merge_results", True),
            timeout_seconds=data.get("timeout_seconds", 300),
        )
    elif node_type == NodeType.FLOW_END:
        return FlowEndConfig(
            **base_fields,
            final_output_port=data.get("final_output_port", "end"),
        )

    else:
        raise ValueError(f"Unknown node type: {node_type}")
