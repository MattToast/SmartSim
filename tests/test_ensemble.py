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

import itertools
import typing as t

import pytest

from smartsim.settings import LaunchSettings
from smartsim.entity._new_ensemble import Ensemble
from smartsim.entity.param_data_class import ParamSet
from smartsim.error import errors

pytestmark = pytest.mark.group_a

_2x2_PARAMS = {"SPAM": ["a", "b"], "EGGS": ["c", "d"]}
_2x2_EXE_ARG = {"EXE": [["a"], ["b", "c"]], "ARGS": [["d"], ["e", "f"]]}

def user_created_function(
    file_params: t.Mapping[str, t.Sequence[str]],
    exe_arg_params: t.Mapping[str, t.Sequence[t.Sequence[str]]],
    _n_permutations: int = 0,
) -> list[ParamSet]:
    # Create dictionaries for each parameter permutation
    param_zip = [dict(zip(file_params, permutation)) for permutation in file_params][
        :_n_permutations
    ]
    # Create dictionaries for each executable argument permutation
    exe_arg_zip = [
        dict(zip(exe_arg_params, permutation)) for permutation in exe_arg_params
    ][:_n_permutations]
    # Combine parameter and executable argument dictionaries
    combinations = itertools.product(param_zip, exe_arg_zip)
    # Combine the parameter sets from 'param_zip' and 'exe_arg_zip' using itertools.zip_longest
    param_set = (ParamSet(file_param, exe_arg) for file_param, exe_arg in combinations)
    return list(param_set)


def test_ensemble_without_any_members_raises_when_cast_to_jobs(wlmutils):
    test_launcher = wlmutils.get_test_launcher()
    with pytest.raises(ValueError):
        Ensemble(
            "test_ensemble",
            "echo",
            ("hello", "world"),
            file_parameters=_2x2_PARAMS,
            exe_arg_parameters=_2x2_EXE_ARG,
            permutation_strategy="random",
            max_permutations=1,
            replicas=0,
        ).as_jobs(LaunchSettings(test_launcher))


def test_strategy_error_raised_if_a_strategy_that_dne_is_requested():
    with pytest.raises(ValueError):
        Ensemble(
            "test_ensemble",
            "echo",
            ("hello",),
            permutation_strategy="THIS-STRATEGY-DNE",
        )._create_applications()


@pytest.mark.parametrize(
    "params",
    (
        pytest.param({"SPAM": ["eggs"]}, id="Non-Empty Params"),
        pytest.param({}, id="Empty Params"),
        pytest.param(None, id="Nullish Params"),
    ),
)
def test_replicated_applications_have_eq_deep_copies_of_parameters(params):
    apps = list(
        Ensemble(
            "test_ensemble", "echo", ("hello",), replicas=4, file_parameters=params
        )._create_applications()
    )
    assert len(apps) >= 2  # Sanitiy check to make sure the test is valid
    assert all(app_1.params == app_2.params for app_1 in apps for app_2 in apps)
    assert all(
        app_1.params is not app_2.params
        for app_1 in apps
        for app_2 in apps
        if app_1 is not app_2
    )


# fmt: off
@pytest.mark.parametrize(
    "                  params,      exe_arg_params,   strategy,  max_perms, replicas, expected_num_jobs",  # Test Name          
    (pytest.param(_2x2_PARAMS,        _2x2_EXE_ARG, "all_perm",         30,        1,                16 , id="get_all_permutations"),
     pytest.param(_2x2_PARAMS,                None, "all_perm",         30,        1,                4  , id="set_exe_arg_params_to_none"),
     pytest.param(       None,        _2x2_EXE_ARG, "all_perm",         30,        1,                4  , id="set_file_params_to_none"),
     pytest.param(       None,                None, "all_perm",         30,        1,                1  , id="set_both_params_to_none"),
     pytest.param(_2x2_PARAMS,        _2x2_EXE_ARG, "all_perm",          8,        1,                8  , id="limit_max_permutations"),
     pytest.param(_2x2_PARAMS,        _2x2_EXE_ARG, "all_perm",         30,        2,                32 , id="replicate_all_permutations"),
     pytest.param(_2x2_PARAMS,                  {}, "all_perm",         30,        1,                 4 , id="set_exe_arg_params_to_empty_dict"),
     pytest.param({},                 _2x2_EXE_ARG, "all_perm",         30,        1,                 4 , id="set_file_params_to_empty_dict"),
     pytest.param({},                           {}, "all_perm",         30,        1,                 1 , id="set_both_params_to_empty_dict"),
))
# fmt: on
def test_all_perm_strategy(
    # Parameterized
    params,
    exe_arg_params,
    strategy,
    max_perms,
    replicas,
    expected_num_jobs,
    # Other fixtures
    wlmutils
):
    test_launcher = wlmutils.get_test_launcher()
    jobs = Ensemble(
        "test_ensemble",
        "echo",
        ("hello", "world"),
        file_parameters=params,
        exe_arg_parameters=exe_arg_params,
        permutation_strategy=strategy,
        max_permutations=max_perms,
        replicas=replicas,
    ).as_jobs(LaunchSettings(test_launcher))
    assert len(jobs) == expected_num_jobs


def test_all_perm_strategy_contents(wlmutils):
    test_launcher = wlmutils.get_test_launcher()
    jobs = Ensemble(
        "test_ensemble",
        "echo",
        ("hello", "world"),
        file_parameters=_2x2_PARAMS,
        exe_arg_parameters=_2x2_EXE_ARG,
        permutation_strategy="all_perm",
        max_permutations=16,
        replicas=1,
    ).as_jobs(LaunchSettings(test_launcher))
    assert len(jobs) == 16

def test_user_created_strategy(wlmutils):
    test_launcher = wlmutils.get_test_launcher()
    jobs = Ensemble(
        "test_ensemble",
        "echo",
        ("hello", "world"),
        file_parameters=_2x2_PARAMS,
        exe_arg_parameters=_2x2_EXE_ARG,
        permutation_strategy=user_created_function,
        max_permutations=16,
        replicas=1,
    ).as_jobs(LaunchSettings(test_launcher))
    assert len(jobs) == 4


# fmt: off
@pytest.mark.parametrize(
    "                  params,      exe_arg_params,   strategy,  max_perms, replicas, expected_num_jobs",  # Test Name          
    (pytest.param(_2x2_PARAMS,        _2x2_EXE_ARG,     "step",         30,        1,                 2 , id="get_all_permutations"),
     pytest.param(_2x2_PARAMS,                None,     "step",         30,        1,                 2 , id="set_exe_arg_params_to_none"),
     pytest.param(       None,        _2x2_EXE_ARG,     "step",         30,        1,                 2 , id="set_file_params_to_none"),
     pytest.param(       None,                None,     "step",         30,        1,                 1 , id="set_both_params_to_none"),
     pytest.param(_2x2_PARAMS,        _2x2_EXE_ARG,     "step",          2,        1,                 2 , id="limit_max_permutations"),
     pytest.param(_2x2_PARAMS,        _2x2_EXE_ARG,     "step",         30,        2,                 4 , id="replicate_all_permutations"),
     pytest.param(_2x2_PARAMS,                  {},     "step",         30,        1,                 2 , id="set_exe_arg_params_to_empty_dict"),
     pytest.param({},                 _2x2_EXE_ARG,     "step",         30,        1,                 2 , id="set_file_params_to_empty_dict"),
     pytest.param({},                           {},     "step",         30,        1,                 1 , id="set_both_params_to_empty_dict"),
))
# fmt: on
def test_step_strategy(
    # Parameterized
    params,
    exe_arg_params,
    strategy,
    max_perms,
    replicas,
    expected_num_jobs,
    # Other fixtures
    wlmutils,
):
    test_launcher = wlmutils.get_test_launcher()
    jobs = Ensemble(
        "test_ensemble",
        "echo",
        ("hello", "world"),
        file_parameters=params,
        exe_arg_parameters=exe_arg_params,
        permutation_strategy=strategy,
        max_permutations=max_perms,
        replicas=replicas,
    ).as_jobs(LaunchSettings(test_launcher))
    assert len(jobs) == expected_num_jobs


# fmt: off
@pytest.mark.parametrize(
    "                  params,      exe_arg_params,   strategy,  max_perms, replicas, expected_num_jobs",         
    (pytest.param(_2x2_PARAMS,        _2x2_EXE_ARG,   "random",         30,        1,                16 , id="get_all_permutations"),
     pytest.param(_2x2_PARAMS,                None,   "random",         30,        1,                 4 , id="set_exe_arg_params_to_none"),
     pytest.param(       None,        _2x2_EXE_ARG,   "random",         30,        1,                 4 , id="set_file_params_to_none"),
     pytest.param(       None,                None,   "random",         30,        1,                 1 , id="set_both_params_to_none"),
     pytest.param(_2x2_PARAMS,        _2x2_EXE_ARG,   "random",          2,        1,                 2 , id="limit_max_permutations"),
     pytest.param(_2x2_PARAMS,        _2x2_EXE_ARG,   "random",         30,        2,                32 , id="replicate_all_permutations"),
     pytest.param(_2x2_PARAMS,                  {},   "random",         30,        1,                 4 , id="set_exe_arg_params_to_empty_dict"),
     pytest.param({},                 _2x2_EXE_ARG,   "random",         30,        1,                 4 , id="set_file_params_to_empty_dict"),
     pytest.param({},                           {},   "random",         30,        1,                 1 , id="set_both_params_to_empty_dict"),
))
# fmt: on
def test_random_strategy(
    # Parameterized
    params,
    exe_arg_params,
    strategy,
    max_perms,
    replicas,
    expected_num_jobs,
    # Other fixtures
    wlmutils
):
    test_launcher = wlmutils.get_test_launcher()
    jobs = Ensemble(
        "test_ensemble",
        "echo",
        ("hello", "world"),
        file_parameters=params,
        exe_arg_parameters=exe_arg_params,
        permutation_strategy=strategy,
        max_permutations=max_perms,
        replicas=replicas,
    ).as_jobs(LaunchSettings(test_launcher))
    assert len(jobs) == expected_num_jobs
