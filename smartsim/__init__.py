
# -*- coding: utf-8 -*-
__version__ = "0.1.0"

import sys
if sys.version_info < (3,7):
    sys.exit('Python 3.7 or greater must be used with SmartSim.')

# Main API module
from .experiment import Experiment

# MPO module
from .mpo import MPO

# Slurm helpers
from .launcher import slurm