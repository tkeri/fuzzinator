# Copyright (c) 2016-2018 Renata Hodovan, Akos Kiss.
#
# Licensed under the BSD 3-Clause License
# <LICENSE.rst or https://opensource.org/licenses/BSD-3-Clause>.
# This file may not be copied, modified, or distributed except
# according to those terms.

import os
import psutil
import shutil
import signal
import time
import traceback

from multiprocessing import Lock, Process, Queue

from .config import config_get_callable, config_get_kwargs, config_get_name_from_section, config_get_with_writeback, import_entity
from .job import FuzzJob, ReduceJob, UpdateJob, ValidateJob
from .listener import ListenerManager
from .mongo_driver import MongoDriver


class Controller(object):
    """
    Fuzzinator's main controller that orchestrates a fuzz session by scheduling
    all related activities (e.g., keeps SUTs up-to-date, runs fuzzers and feeds
    test cases to SUTs, or minimizes failure inducing test cases) . All
    configuration options of the framework must be encapsulated in a
    :class:`configparser.ConfigParser` object.

    The following config sections and options are recognized:

      - Section ``fuzzinator``: Global settings of the framework.

        - Option ``work_dir``: Pattern of work directory for temporary files,
          which may contain the substring ``{uid}`` as a placeholder for a
          unique string (replaced by the framework). (Optional, default:
          ``~/.fuzzinator-{uid}``)

        - Option ``db_uri``: URI to a MongoDB database to store found issues and
          execution statistics. (Optional, default:
          ``mongodb://localhost/fuzzinator``)

        - Option ``cost_budget``: (Optional, default: number of cpus)

      - Sections ``sut.NAME``: Definitions of a SUT named *NAME*

        - Option ``call``: Fully qualified name of a python callable that must
          accept a ``test`` keyword argument representing the input to the SUT
          and must return a dictionary object if the input triggered an issue
          in the SUT, or a value considered false otherwise (which can be a
          simple ``None``, but can also be a ``NonIssue`` in complex cases).
          The returned issue dictionary (if any) *should* contain an ``'id'``
          field that equals for issues that are not considered unique.
          (Mandatory)

          See package :mod:`fuzzinator.call` for potential callables.

        - Option ``cost``: (Optional, default: 1)

        - Option ``reduce``: Fully qualified name of a python callable that must
          accept ``issue``, ``sut_call``, ``sut_call_kwargs``, ``listener``,
          ``ident``, ``work_dir`` keyword arguments representing an issue to be
          reduced (and various other potentially needed objects), and must
          return a tuple consisting of a reduced test case for the issue (or
          ``None`` if the issue's current test case could not be reduced) and a
          (potentially empty) list of new issues that were discovered during
          test case reduction (if any). (Optional, no reduction for this SUT if
          option is missing.)

          See package :mod:`fuzzinator.reduce` for potential callables.

        - Option ``reduce_call``: Fully qualified name of a python callable that
          acts as the SUT's ``call`` option during test case reduction.
          (Optional, default: the value of option ``call``)

          See package :mod:`fuzzinator.call` for potential callables.

        - Option ``reduce_cost``: (Optional, default: the value of option
          ``cost``)

        - Option ``validate_call``: Fully qualified name of a python callable
          that acts as the SUT's ``call`` option during test case validation.
          (Optional, default: the value of option ``reduce_call`` if defined,
          otherwise the value of option ``call``)

          See package :mod:`fuzzinator.call` for potential callables.

        - Option ``update_condition``: Fully qualified name of a python callable
          that must return ``True`` if and only if the SUT should be updated.
          (Optional, SUT is never updated if option is missing.)

          See package :mod:`fuzzinator.update` for potential callables.

        - Option ``update``: Fully qualified name of a python callable that
          should perform the update of the SUT. (Optional, SUT is never updated
          if option is missing.)

          See package :mod:`fuzzinator.update` for potential callables.

        - Option ``formatter``: Fully qualified name of a python callable that
          formats the issue dictionary of the SUT and returns a custom string
          representation. It must accept ``issue`` and ``format`` keyword
          arguments representing an issue to be formatted and a formatting
          instruction. If ``format`` is ``'long'`` or not specified, the issue
          should be formatted in full, while if ``'short'`` is given, a
          summary description (preferably a single line of text) should be
          returned.
          (Optional, default: :mod:`fuzzinator.formatter.JsonFormatter`.)

          See package :mod:`fuzzinator.formatter` for further potential
          callables.

        - Option ``tui_formatter``: Fully qualified name of a python
          callable that formats the issue dictionary of the SUT to display
          it in the TUI issue viewer interface.
          (Optional, default: the value of option ``formatter``)

          See package :mod:`fuzzinator.formatter` for further potential
          callables.

        - Option ``email_formatter``: Fully qualified name of a python
          callable that formats the issue dictionary of the SUT to insert
          it into an e-mail notification.
          (Optional, default: the value of option ``formatter``)

          See package :mod:`fuzzinator.formatter` for further potential
          callables.

      - Sections ``fuzz.NAME``: Definitions of a fuzz job named *NAME*

        - Option ``sut``: Name of the SUT that describes the subject of
          this fuzz job. (Mandatory)

        - Option ``fuzzer``: Fully qualified name of a python callable that must
          accept and ``index`` keyword argument representing a running counter
          in the fuzz job and must return a test input (or ``None``, which
          signals that the fuzzer is "exhausted" and cannot generate more test
          cases in this fuzz job). The semantics of the generated test input is
          not restricted by the framework, it is up to the configuration to
          ensure that the SUT of the fuzz job can deal with the tests generated
          by the fuzzer of the fuzz job. (Mandatory)

          See package :mod:`fuzzinator.fuzzer` for potential callables.

        - Option ``batch``: Number of times the fuzzer is requested to generate
          a new test and the SUT is called with it. (Optional, default: 1)

        - Option ``instances``: Number of instances of this fuzz job allowed to
          run in parallel. (Optional, default: ``inf``)

        - Option ``refresh``: Statistic update frequency in terms of executed
          test cases. (Optional, default: ``batch`` size)

      - Section ``listeners``: Definitions of custom event listeners.
        This section is optional.

        - Options ``OPT``: Fully qualified name of python class that
          executes custom actions to selected events.

        See package :mod:`fuzzinator.listeners` for potential listeners.

      - Callable options can be implemented as functions or classes with
        ``__call__`` method (the latter are instantiated first to get a callable
        object). Both constructor calls (if any) and the "real" calls can be
        given keyword arguments. These arguments have to be specified in
        sections ``(sut|fuzz).NAME.OPT[.init]`` with appropriate names (where
        the ``.init`` sections stand for the constructor arguments).

      - All callables can be decorated according to python semantics. The
        decorators must be callable classes themselves and have to be specified
        in options ``OPT.decorate(N)`` with fully qualified name. Multiple
        decorators can be applied to a callable ``OPT``, their order is
        specified by an integer index in parentheses. Keyword arguments to be
        passed to the decorators have to be listed in sections
        ``(sut|fuzz).NAME.OPT.decorate(N)``.

        See packages :mod:`fuzzinator.call` and :mod:`fuzzinator.fuzzer` for
        potential decorators.
    """

    def __init__(self, config):
        """
        :param configparser.ConfigParser config: the configuration options of the
            fuzz session.

        :ivar fuzzinator.ListenerManager listener: a listener manager object that is
            called on various events during the fuzz session.
        """
        self.config = config

        # Extract fuzzer names from sections describing fuzzing jobs.
        self.fuzzers = [config_get_name_from_section(section) for section in config.sections() if section.startswith('fuzz.') and section.count('.') == 1]

        self.capacity = int(config_get_with_writeback(self.config, 'fuzzinator', 'cost_budget', str(os.cpu_count())))
        self.work_dir = config_get_with_writeback(self.config, 'fuzzinator', 'work_dir', os.path.join(os.getcwd(), '.fuzzinator-{uid}')).format(uid=os.getpid())
        self.config.set('fuzzinator', 'work_dir', self.work_dir)

        self.db = MongoDriver(config_get_with_writeback(self.config, 'fuzzinator', 'db_uri', 'mongodb://localhost/fuzzinator'))
        self.db.init_db([(self.config.get('fuzz.' + fuzzer, 'sut'), fuzzer) for fuzzer in self.fuzzers])

        self.listener = ListenerManager()
        for name in config_get_kwargs(self.config, 'listeners'):
            entity = import_entity(self.config.get('listeners', name))
            self.listener += entity(config=config, **config_get_kwargs(config, 'listeners.' + name + '.init'))

        self._job_id = 0
        self._issue_queue = Queue()
        self._lock = Lock()

    def run(self, *, max_cycles=None):
        """
        Start the fuzz session.

        :param int max_cycles: maximum number to iterate through the fuzz jobs
            defined in the configuration (defaults to ``inf``).
        """
        max_cycles = max_cycles if max_cycles is not None else float('inf')
        cycle = 0
        running_jobs = dict()
        fuzz_idx = 0
        try:
            while True:
                self._wait_for_load(0, running_jobs)

                if fuzz_idx == 0:
                    cycle += 1
                if cycle > max_cycles or (not self.fuzzers and max_cycles != float('inf')):
                    self._wait_for_load(self.capacity, running_jobs)
                    break

                next_job = None
                if not self._issue_queue.empty():

                    # Perform all the reduce jobs before start hunting for new issues.
                    while not self._issue_queue.empty():
                        issue = self._issue_queue.get_nowait()
                        if self.config.has_option('sut.' + issue['sut'], 'reduce'):
                            next_job_id = self._next_job_id()
                            next_job = ReduceJob(id=next_job_id,
                                                 config=self.config,
                                                 issue=issue,
                                                 work_dir=self.work_dir,
                                                 db=self.db,
                                                 listener=self.listener)
                            self.listener.new_reduce_job(ident=next_job_id,
                                                         sut=next_job.sut_name,
                                                         cost=next_job.cost,
                                                         issue_id=issue['id'],
                                                         size=len(issue['test']))
                            break

                if not next_job:
                    if not self.fuzzers:
                        time.sleep(1)
                        continue

                    fuzz_section = 'fuzz.' + self.fuzzers[fuzz_idx]
                    instances = self.config.get(fuzz_section, 'instances', fallback='inf')
                    instances = float(instances) if instances == 'inf' else int(instances)
                    if instances <= sum(1 for job in running_jobs.values() if isinstance(job['job'], FuzzJob) and job['job'].fuzzer_name == self.fuzzers[fuzz_idx]):
                        # Update fuzz_idx to point the next job's parameters.
                        fuzz_idx = (fuzz_idx + 1) % len(self.fuzzers)
                        continue

                    next_job_id = self._next_job_id()
                    next_job = FuzzJob(id=next_job_id,
                                       config=self.config,
                                       fuzzer_name=self.fuzzers[fuzz_idx],
                                       db=self.db,
                                       listener=self.listener)

                    # Before starting a new fuzz job let's check if we are working with
                    # the latest version of the SUT and update it if needed.
                    self._check_update(next_job, running_jobs)

                    # Update fuzz_idx to point the next job's parameters.
                    fuzz_idx = (fuzz_idx + 1) % len(self.fuzzers)

                    # Notify the active listener about the new job.
                    self.listener.new_fuzz_job(ident=next_job_id,
                                               fuzzer=next_job.fuzzer_name,
                                               sut=next_job.sut_name,
                                               cost=next_job.cost,
                                               batch=next_job.batch)

                # Wait until there is enough capacity for the next job.
                self._wait_for_load(next_job.cost, running_jobs)

                proc = Process(target=self._run_job, args=(next_job,))
                running_jobs[next_job_id] = dict(job=next_job, proc=proc)
                # Notify the active listener that a job has been activated.
                self.listener.activate_job(ident=next_job_id)
                proc.start()

        except KeyboardInterrupt:
            pass
        except Exception as e:
            self.listener.warning(msg='Exception in the main controller loop: {exception}\n{trace}'.format(exception=e, trace=traceback.format_exc()))
        finally:
            Controller.kill_process_tree(os.getpid(), kill_root=False)
            if os.path.exists(self.work_dir):
                shutil.rmtree(self.work_dir, ignore_errors=True)

    def _check_update(self, job, running_jobs):
        sut_section = 'sut.' + job.sut_name
        if not self.config.has_option(sut_section, 'update'):
            return

        update_condition, update_condition_kwargs = config_get_callable(self.config, sut_section, 'update_condition')
        if not update_condition:
            return

        with update_condition:
            if not update_condition(**update_condition_kwargs):
                return

        next_job_id = self._next_job_id()
        next_job = UpdateJob(id=next_job_id,
                             config=self.config,
                             sut_name=job.sut_name)
        self.listener.new_update_job(ident=next_job_id, sut=job.sut_name)
        # Wait until every job has finished.
        self._wait_for_load(self.capacity, running_jobs)
        # Emit 'next_job available' event.
        self.listener.activate_job(ident=next_job_id)
        # Update job runs in the main thread since it's blocking for any other jobs.
        next_job.run()
        self.listener.remove_job(ident=next_job_id)

    def _wait_for_load(self, new_load, running_jobs):
        while True:
            load = 0
            for ident in list(running_jobs):
                if not running_jobs[ident]['proc'].is_alive():
                    self.listener.remove_job(ident=ident)
                    del running_jobs[ident]
                else:
                    load += running_jobs[ident]['job'].cost
            self.listener.update_load(load=load)
            if load + new_load <= self.capacity:
                return load
            time.sleep(1)

    def _run_job(self, job):
        try:
            for issue in job.run():
                self.add_reduce_job(issue=issue)
        except Exception as e:
            self.listener.warning(msg='Exception in {job}: {exception}\n{trace}'.format(
                job=repr(job),
                exception=e,
                trace=traceback.format_exc()))

    def _next_job_id(self):
        next_job_id = self._job_id
        self._job_id += 1
        return next_job_id

    def add_reduce_job(self, issue):
        with self._lock:
            self._issue_queue.put(issue)

    def reduce_all(self):
        for issue in self.db.find_issues_by_suts([section for section in self.config.sections() if section.startswith('sut.') and section.count('.') == 1]):
            if not issue['reported'] and not issue['reduced']:
                self.add_reduce_job(issue)

    def validate(self, issue):
        next_job_id = self._next_job_id()
        next_job = ValidateJob(id=next_job_id,
                               config=self.config,
                               issue=issue,
                               db=self.db,
                               listener=self.listener)
        self.listener.new_validate_job(ident=next_job_id,
                                       sut=next_job.sut_name,
                                       issue_id=issue['id'])
        self.listener.activate_job(ident=next_job_id)
        next_job.run()
        self.listener.remove_job(ident=next_job_id)

    @staticmethod
    def kill_process_tree(pid, kill_root=True, sig=signal.SIGTERM):
        try:
            root_proc = psutil.Process(pid)
            children = root_proc.children(recursive=True)
            if kill_root:
                children.append(root_proc)
            for proc in children:
                # Would be easier to use proc.terminate() here but psutils
                # (up to version 5.4.0) on Windows terminates processes with
                # the 0 signal/code, making the outcome of the terminated
                # process indistinguishable from a successful execution.
                try:
                    os.kill(proc.pid, sig)
                except OSError:
                    pass
            psutil.wait_procs(children, timeout=1)
        except psutil.NoSuchProcess:
            pass
