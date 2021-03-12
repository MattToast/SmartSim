from smartsim.error.errors import SmartSimError
from ..settings import QsubBatchSettings, AprunSettings
from .orchestrator import Orchestrator

class PBSOrchestrator(Orchestrator):

    def __init__(self, port, db_nodes=1, batch=True, **kwargs):
        """Initialize an Orchestrator reference for PBSPro based systems

        The orchestrator launches as a batch by default. If batch=False,
        at launch, the orchestrator will look for an interactive
        allocation to launch on.

        The PBS orchestrator does not support multiple databases per node.

        :param port: TCP/IP port
        :type port: int
        :param db_nodes: number of database shards, defaults to 1
        :type db_nodes: int, optional
        :param batch: Run as a batch workload, defaults to True
        :type batch: bool, optional
        """
        super().__init__(port,
                         db_nodes=db_nodes,
                         batch=batch,
                         **kwargs)
        self.batch_settings = self._build_batch_settings(db_nodes, batch)

    def set_cpus(self, num_cpus):
        """Set the number of CPUs available to each database shard

        This effectively will determine how many cpus can be used for
        compute threads, background threads, and network I/O.

        :param num_cpus: number of cpus to set
        :type num_cpus: int
        """
        # if batched, make sure we have enough cpus
        if self.batch:
            self.batch_settings.set_ncpus(num_cpus)
        for db in self:
            db.run_settings.set_cpus_per_task(num_cpus)

    def set_walltime(self, walltime):
        """Set the batch walltime of the orchestrator

        Note: This will only effect orchestrators launched as a batch

        :param walltime: amount of time e.g. 10 hours is 10:00:00
        :type walltime: str
        :raises SmartSimError: if orchestrator isn't launching as batch
        """
        if not self.batch:
            raise SmartSimError("Not running in batch, cannot set walltime")
        self.batch_settings.set_walltime(walltime)

    def set_batch_arg(self, arg, value):
        """Set a Qsub argument the orchestrator should launch with

        Some commonly used arguments such as -e are used
        by SmartSim and will not be allowed to be set.

        :param arg: batch argument to set e.g. "exclusive"
        :type arg: str
        :param value: batch param - set to None if no param value
        :type value: str | None
        :raises SmartSimError: if orchestrator not launching as batch
        """
        if not self.batch:
            raise SmartSimError("Not running as batch, cannot set batch_arg")
        # TODO catch commonly used arguments we use for SmartSim here
        self.batch_settings.batch_args[arg] = value

    def _build_run_settings(self, exe, exe_args, **kwargs):
        run_args = kwargs.get("run_args", {})
        batch = kwargs.get("batch", True)

        if not batch:
            run_args["pes"] = 1
            run_args["pes-per-node"] = 1 # 1 database per node
            run_settings = AprunSettings(exe, exe_args, run_args=run_args)
            return run_settings
        else:
            run_args = {"pes": 1, "pes-per-node": 1}
            run_settings = AprunSettings(exe, exe_args, run_args=run_args)
            return run_settings

    def _build_batch_settings(self, db_nodes, batch):
        batch_settings = None
        if batch:
            # not possible to launch multiple DPN with Aprun
            batch_settings = QsubBatchSettings(nodes=db_nodes, ncpus=1)
        return batch_settings
