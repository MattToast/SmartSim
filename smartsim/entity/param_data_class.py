from dataclasses import dataclass, field


@dataclass
class ParamSet:
    """
    Represents a set of file parameters and execution arguments.
    """

    params: dict[str, str] = field(default_factory=dict)
    exe_args: dict[str, list[str]] = field(default_factory=dict)
