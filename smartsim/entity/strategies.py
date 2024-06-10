# BSD 2-Clause License
#
# Copyright (c) 2021-2024, Hewlett Packard Enterprise
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice, this
#    list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

# Generation Strategies

from __future__ import annotations
from .param_data_class import ParamSet

import functools
import itertools
import random
import typing as t

from smartsim.error import errors

TPermutationStrategy = t.Callable[
    [t.Mapping[str, t.Sequence[str]], int], list[dict[str, str]]
]

_REGISTERED_STRATEGIES: t.Final[dict[str, TPermutationStrategy]] = {}


def _register(name: str) -> t.Callable[
    [TPermutationStrategy],
    TPermutationStrategy,
]:
    def _impl(fn: TPermutationStrategy) -> TPermutationStrategy:
        if name in _REGISTERED_STRATEGIES:
            msg = f"A strategy with the name '{name}' has already been registered"
            raise ValueError(msg)
        _REGISTERED_STRATEGIES[name] = fn
        return fn

    return _impl


def resolve(strategy: str | TPermutationStrategy) -> TPermutationStrategy:
    if callable(strategy):
        return _make_safe_custom_strategy(strategy)
    try:
        return _REGISTERED_STRATEGIES[strategy]
    except KeyError:
        raise ValueError(
            f"Failed to find an ensembling strategy by the name of '{strategy}'."
            f"All known strategies are:\n{', '.join(_REGISTERED_STRATEGIES)}"
        ) from None


def _make_safe_custom_strategy(fn: TPermutationStrategy) -> TPermutationStrategy:
    @functools.wraps(fn)
    def _impl(
        params: t.Mapping[str, t.Sequence[str]], n_permutations: int
    ) -> list[dict[str, str]]:
        try:
            permutations = fn(params, n_permutations)
        except Exception as e:
            raise errors.UserStrategyError(str(fn)) from e
        if not isinstance(permutations, list) or not all(
            isinstance(permutation, dict) for permutation in permutations
        ):
            raise errors.UserStrategyError(str(fn))
        return permutations

    return _impl


# create permutations of all parameters
# single application if parameters only have one value
@_register("all_perm")
def create_all_permutations(
    params: t.Mapping[str, t.Sequence[str]],
    exe_args: t.Mapping[str, t.Sequence[t.Sequence[str]]],
    _n_permutations: int = 0,
) -> list[dict[str, str]]:
    # Generate all possible permutations of parameter values
    params_permutations = itertools.product(*params.values())
    # Create dictionaries for each parameter permutation
    param_zip = [dict(zip(params, permutation)) for permutation in params_permutations][:_n_permutations]
    # Generate all possible permutations of executable arguments
    exe_arg_permutations = itertools.product(*exe_args.values())
    # Create dictionaries for each executable argument permutation
    exe_arg_zip = [dict(zip(exe_args, permutation)) for permutation in exe_arg_permutations][:_n_permutations]
    # Combine parameter and executable argument dictionaries
    combinations = itertools.product(param_zip,exe_arg_zip)
    matts_bad_idea = (ParamSet(file_params, exe_args) for file_params, exe_args in combinations)
    matt_bad_idea_part_2 = itertools.islice(matts_bad_idea, _n_permutations)
    return list(matt_bad_idea_part_2)


@_register("step")
def step_values(
    params: t.Mapping[str, t.Sequence[str]],
    exe_args: t.Mapping[str, t.Sequence[t.Sequence[str]]],
    _n_permutations: int = 0,
) -> list[dict[str, str]]:
    param_zip = zip(*params.values())
    param_zip = [dict(zip(params, step)) for step in param_zip][:_n_permutations]

    exe_arg_zip = zip(*exe_args.values())
    # Generate all possible permutations of executable arguments
    exe_arg_zip = [dict(zip(exe_args, step)) for step in exe_arg_zip][:_n_permutations]
    matts_bad_idea = (ParamSet(file_params, exe_args) for (file_params, exe_args) in itertools.zip_longest(param_zip,exe_arg_zip,fillvalue=-1))
    matt_bad_idea_part_2 = itertools.islice(matts_bad_idea, _n_permutations)
    return list(matt_bad_idea_part_2)
    


@_register("random")
def random_permutations(
    params: t.Mapping[str, t.Sequence[str]], n_permutations: int = 0
) -> list[dict[str, str]]:
    # Generate all possible permutations of parameter values
    params_permutations = itertools.product(*params.values())
    # Create dictionaries for each parameter permutation
    param_zip = [dict(zip(params, permutation)) for permutation in params_permutations][:_n_permutations]
    # Generate all possible permutations of executable arguments
    exe_arg_permutations = itertools.product(*exe_args.values())
    # Create dictionaries for each executable argument permutation
    exe_arg_zip = [dict(zip(exe_args, permutation)) for permutation in exe_arg_permutations][:_n_permutations]
    # Combine parameter and executable argument dictionaries
    combinations = itertools.product(param_zip,exe_arg_zip)

    # sample from available permutations if n_permutations is specified
    if 0 < n_permutations < len(combinations):
        permutations = random.sample(permutations, n_permutations)

    return permutations
