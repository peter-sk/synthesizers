from typing import Any, Dict, List, Optional, Tuple, Type, Union

from ..adapters import NAME_TO_ADAPTER
from ..adapters.base import Adapter
from ..utils import ensure_format, MultiStateDict, StateDict
from ..utils import logging

logger = logging.get_logger(__name__)

class PipelineRegistry:
    def __init__(self, supported_tasks: Dict[str, Any], task_aliases: Dict[str, str]) -> None:
        self.supported_tasks = supported_tasks
        self.task_aliases = task_aliases

    def get_supported_tasks(self) -> List[str]:
        supported_task = list(self.supported_tasks.keys()) + list(self.task_aliases.keys())
        supported_task.sort()
        return supported_task

    def check_task(self, task: str) -> Tuple[str, Dict, Any]:
        if task in self.task_aliases:
            task = self.task_aliases[task]
        if task in self.supported_tasks:
            targeted_task = self.supported_tasks[task]
            return task, targeted_task, None

        if task.startswith("tabular-synthesis-dp"):
            tokens = task.split("_")
            if len(tokens) == 3 and tokens[0] == "tabular-synthesis-dp":
                targeted_task = self.supported_tasks["tabular-synthesis"]
                task = "tabular-synthesis"
                return task, targeted_task, (float(tokens[1]), float(tokens[2]))
            raise KeyError(f"Invalid tabular-synthesis-dp task {task}, use 'tabular-synthesis-dp_EPSILON_DELTA' format with EPSILON and DELTA being floats")

        raise KeyError(
            f"Unknown task {task}, available tasks are {self.get_supported_tasks() + ['tabular-synthesis-dp_EPSILON_DELTA']}"
        )

class Pipeline():
    def __init__(self,
            task: str,
            train_adapter: Optional[Union[Adapter, str]] = None,
            eval_adapter: Optional[Union[Adapter, str]] = None,
            output_format: Optional[Type] = None,
            train_args: Optional[dict] = None,
            gen_args: Optional[dict] = None,
            eval_args: Optional[dict] = None,
            split_args: Optional[dict] = None,
            save_args: Optional[dict] = None,
            **kwargs,
        ):
        self.task = task
        if isinstance(train_adapter, str):
            train_adapter = NAME_TO_ADAPTER[train_adapter]()
        self.train_adapter = train_adapter
        if isinstance(eval_adapter, str):
            eval_adapter = NAME_TO_ADAPTER[eval_adapter]()
        self.eval_adapter = eval_adapter
        self.output_format = output_format
        self.train_args = train_args
        self.gen_args = gen_args
        self.eval_args = eval_args
        self.split_args = split_args
        self.save_args = save_args
        self.kwargs = kwargs

    def __call__(
        self,
        state: Union[StateDict, MultiStateDict],
    ):
        state = StateDict.wrap(state)
        states = state.states if isinstance(state, MultiStateDict) else [state]
        states = [self._call_one(state) for state in states] #TODO: parallelize this
        new_states = []
        for state in states:
            if isinstance(state, MultiStateDict):
                new_states.extend(state.states)
            else:
                new_states.append(state)
        return new_states[0] if len(new_states) == 1 else MultiStateDict(new_states)

    def _call_one(self, state: StateDict):
        state = self._call(state)
        if self.save_args.get("name", None) is not None:
            state.Save(**self.save_args)
        return state

    def ensure_output_format(self, data, output_format=None, **kwargs):
        return ensure_format(data, (self.output_format if output_format is None else output_format,), **kwargs)
