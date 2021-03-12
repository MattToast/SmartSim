import time
from threading import Thread
import itertools

import numpy as np
from ..entity import DBNode
from ..database import Orchestrator
from ..constants import LOCAL_JM_INTERVAL, TERMINAL_STATUSES, WLM_JM_INTERVAL
from ..error import SmartSimError
from ..launcher import SlurmLauncher, PBSLauncher
from ..utils import get_logger
from .job import Job
from ..database.orchestrator import get_ip_from_host


logger = get_logger(__name__)


class JobManager:
    """The JobManager maintains a mapping between user defined entities
    and the steps launched through the launcher. The JobManager
    holds jobs according to entity type.

    The JobManager is threaded and runs during the course of an experiment
    to update the statuses of Jobs.

    The JobManager and Controller share a single instance of a launcher
    object that allows both the Controller and launcher access to the
    wlm to query information about jobs that the user requests.
    """

    def __init__(self, lock, launcher=None):
        """Initialize a Jobmanager

        :param launcher: a Launcher object to manage jobs
        :type: SmartSim.Launcher
        """
        self.name = "JobManager" + "-" + str(np.base_repr(time.time_ns(), 36))
        self.actively_monitoring = False
        self.jobs = {}
        self.db_jobs = {}
        self.completed = {}
        self._launcher = launcher
        self._lock = lock

    def start(self):
        """Start a thread for the job manager"""

        self.monitor = Thread(name=self.name, daemon=True, target=self.run)
        self.monitor.start()

    def run(self):
        """Start the JobManager thread to continually check
        the status of all jobs. Whichever launcher is selected
        by the user will be responsible for returning statuses
        that progress the state of the job.

        The interval of the checks is controlled by
        smartsim.constats.TM_INTERVAL and should be set to values
        above 20 for congested, multi-user systems

        The job manager thread will exit when no jobs are left
        or when the main thread dies
        """
        logger.debug("Starting Job Manager")

        self.actively_monitoring = True
        while self.actively_monitoring:

            self._thread_sleep()
            self.check_jobs() # update all job statuses at once
            for _, job in self().items():

                # if the job has errors then output the report
                # this should only output once
                if job.returncode is not None and job.status in TERMINAL_STATUSES:
                    if int(job.returncode) != 0:
                        logger.warning(job)
                        logger.warning(job.error_report())
                        self.move_to_completed(job)
                    else:
                        # job completed without error
                        logger.info(job)
                        self.move_to_completed(job)

            # if no more jobs left to actively monitor
            if not self():
                self.actively_monitoring = False
                logger.debug("Sleeping, no jobs to monitor")

    def move_to_completed(self, job):
        """Move job to completed queue so that its no longer
           actively monitored by the job manager

        :param job: job instance we are transitioning
        :type job: Job
        """
        self._lock.acquire()
        try:
            self.completed[job.ename] = job
            job.record_history()

            # remove from actively monitored jobs
            if job.ename in self.db_jobs.keys():
                del self.db_jobs[job.ename]
            elif job.ename in self.jobs.keys():
                del self.jobs[job.ename]
        finally:
            self._lock.release()

    def __getitem__(self, entity_name):
        """Return the job associated with the name of the entity
        from which it was created.

        :param entity_name: The name of the entity of a job
        :type entity_name: str
        :returns: the Job associated with the entity_name
        :rtype: Job
        """
        self._lock.acquire()
        try:
            if entity_name in self.db_jobs.keys():
                return self.db_jobs[entity_name]
            if entity_name in self.jobs.keys():
                return self.jobs[entity_name]
            if entity_name in self.completed.keys():
                return self.completed[entity_name]
            raise KeyError
        finally:
            self._lock.release()

    def __call__(self):
        """Returns dictionary all jobs for () operator

        :returns: Dictionary of all jobs
        :rtype: dictionary
        """
        all_jobs = {**self.jobs, **self.db_jobs}
        return all_jobs

    def add_job(self, job_name, job_id, entity):
        """Add a job to the job manager which holds specific jobs by type.

        :param job_name: name of the job step
        :type job_name: str
        :param job_id: job step id created by launcher
        :type job_id: str
        :param entity: entity that was launched on job step
        :type entity: SmartSimEntity
        """
        # all operations here should be atomic
        job = Job(job_name, job_id, entity)
        if isinstance(entity, (DBNode, Orchestrator)):
            self.db_jobs[entity.name] = job
        else:
            self.jobs[entity.name] = job

    def is_finished(self, entity):
        """Detect if a job has completed

        :param entity: entity to check
        :type entity: SmartSimEntity
        :return: True if finished
        :rtype: bool
        """
        self._lock.acquire()
        try:
            job = self[entity.name]  # locked operation
            if entity.name in self.completed:
                if job.status in TERMINAL_STATUSES:
                    return True
            return False
        finally:
            self._lock.release()

    def check_jobs(self):
        """Update all jobs in jobmanager

        Update all jobs returncode, status, error and output
        through one call to the launcher.

        """
        self._lock.acquire()
        try:
            jobs = self().values()
            job_names = [job.name for job in jobs]
            statuses = self._launcher.get_step_update(job_names)
            for status, job in zip(statuses, jobs):
                # uses abstract step interface
                job.set_status(
                    status.status,
                    status.launcher_status,
                    status.returncode,
                    error=status.error,
                    output=status.output,
                )
        finally:
            self._lock.release()

    def get_status(self, entity):
        """Return the workload manager given status of a job.

        :param entity: SmartSimEntity or EntityList instance
        :type entity: SmartSimEntity | EntityList
        :returns: tuple of status
        """
        self._lock.acquire()
        try:
            if entity.name in self.completed:
                return self.completed[entity.name].status

            job = self[entity.name]  # locked
        except KeyError:
            raise SmartSimError(
                f"Entity by the name of {entity.name} has not been launched by this Controller"
            ) from None
        finally:
            self._lock.release()
        return job.status

    def set_launcher(self, launcher):
        """Set the launcher of the job manager to a specific launcher instance

        :param launcher: child of Launcher
        :type launcher: Launcher instance
        """
        self._launcher = launcher

    def query_restart(self, entity_name):
        """See if the job just started should be restarted or not.

        :param entity_name: name of entity to check for a job for
        :type entity_name: str
        :return: if job should be restarted instead of started
        :rtype: bool
        """
        if entity_name in self.completed:
            return True
        return False

    def restart_job(self, job_name, job_id, entity_name):
        """Function to reset a job to record history and be
        ready to launch again.

        :param job_name: new job step name
        :type job_name: str
        :param job_id: new job id
        :type job_id: str
        :param entity_name: name of the entity of the job
        :type entity_name: str
        """
        self._lock.acquire()
        try:
            job = self.completed[entity_name]
            del self.completed[entity_name]
            job.reset(job_name, job_id)
            if isinstance(job.entity, (DBNode, Orchestrator)):
                self.db_jobs[entity_name] = job
            else:
                self.jobs[entity_name] = job
        finally:
            self._lock.release()

    def get_db_host_addresses(self):
        """Retrieve the list of hosts for the database

        :return: list of host ip addresses
        :rtype: list[str]
        """
        addresses = []
        for db_job in self.db_jobs.values():
            for combine in itertools.product(db_job.hosts, db_job.entity.ports):
                ip_addr = get_ip_from_host(combine[0])
                addresses.append(":".join((ip_addr, str(combine[1]))))
        return addresses

    def set_db_hosts(self, orchestrator):
        """Set the DB hosts in db_jobs so future entities can query this

        :param orchestrator: orchestrator instance
        :type orchestrator: Orchestrator
        """
        # should only be called during launch in the controller
        self._lock.acquire()
        try:
            if orchestrator.batch:
                self.db_jobs[orchestrator.name].hosts = orchestrator.hosts
            else:
                for dbnode in orchestrator:
                    self.db_jobs[dbnode.name].hosts = [dbnode.host]
        finally:
            self._lock.release()


    def _thread_sleep(self):
        """Sleep the job manager for a specific constant
        set for the launcher type.
        """
        if isinstance(self._launcher, (SlurmLauncher, PBSLauncher)):
            time.sleep(WLM_JM_INTERVAL)
        else:
            time.sleep(LOCAL_JM_INTERVAL)

    def __len__(self):
        # number of active jobs
        return len(self.db_jobs) + len(self.jobs)
